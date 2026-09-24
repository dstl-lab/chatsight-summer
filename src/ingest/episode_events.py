"""Import the Jupyter episode-event contract without opening the live DB."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.episodes.models import (
    EVENT_SCHEMA_VERSION,
    FORBIDDEN_PAYLOAD_KEYS,
    INACTIVITY_TIMEOUT_MS,
    MAX_PAYLOAD_BYTES,
    RECONSTRUCTION_VERSION,
    DatasetMeta,
    EpisodeDataset,
    EpisodeEvent,
    ImportQuality,
    SourceKind,
    TranscriptTurn,
)
from src.episodes.reconstruct import reconstruct_episodes, summarize_questions


def _reason(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error.get("loc", ()))
    return f"invalid_{location or 'event'}"


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _legacy_turn(record: dict[str, Any]) -> TranscriptTurn | None:
    payload = record.get("payload")
    event_type = record.get("event_type")
    if not isinstance(payload, dict):
        return None
    conversation_id = payload.get("conversation_id")
    if not isinstance(conversation_id, str) or not conversation_id:
        return None
    if event_type == "tutor_query":
        text = payload.get("question")
        role = "student"
    elif event_type == "tutor_response":
        text = payload.get("response")
        role = "tutor"
    else:
        return None
    if not isinstance(text, str) or not text:
        return None
    return TranscriptTurn(
        role=role,
        text=text,
        conversation_id=conversation_id,
        occurred_at=_parse_time(record.get("occurred_at") or payload.get("occurred_at")),
        event_id=_optional_text(record.get("event_id") or payload.get("event_id")),
        turn_id=_optional_text(record.get("turn_id") or payload.get("turn_id")),
        response_id=_optional_text(
            record.get("response_id") or payload.get("response_id")
        ),
    )


def _talk_role(event: EpisodeEvent) -> str | None:
    if event.event_type == "tutor_query":
        return "student"
    if event.event_type == "tutor_response":
        return "tutor"
    return None


def link_transcripts(
    events: list[EpisodeEvent],
    transcripts: dict[str, list[TranscriptTurn]],
) -> dict[str, str | None]:
    """Attach transcript text to talk events without guessing across students.

    Prefer an explicit event, turn, or response ID, then an exact timestamp.
    Legacy order is used only when one student owns the conversation and the
    remaining role counts match. Ambiguous text stays unlinked.
    """
    linked: dict[str, str | None] = {event.event_id: None for event in events}
    unused: dict[tuple[str, str], list[TranscriptTurn]] = defaultdict(list)
    for conversation_id, turns in transcripts.items():
        for turn in turns:
            unused[(conversation_id, turn.role)].append(turn)

    def take(conversation_id: str | None, role: str, matcher) -> TranscriptTurn | None:
        if not conversation_id:
            return None
        remaining = unused.get((conversation_id, role), [])
        match = next((turn for turn in remaining if matcher(turn)), None)
        if match is None:
            return None
        remaining.remove(match)
        return match

    claimed: set[str] = set()
    for event in events:
        role = _talk_role(event)
        if role is None:
            continue
        conversation_id = event.conversation_id
        turn = (
            take(conversation_id, role, lambda item: item.event_id == event.event_id)
            or take(conversation_id, role, lambda item: (
                item.turn_id is not None and item.turn_id == event.turn_id
            ))
            or take(conversation_id, role, lambda item: (
                event.event_type == "tutor_response"
                and item.response_id is not None
                and item.response_id == event.response_id
            ))
            or take(conversation_id, role, lambda item: (
                item.occurred_at is not None and item.occurred_at == event.occurred_at
            ))
        )
        if turn is not None:
            linked[event.event_id] = turn.text
            claimed.add(event.event_id)

    by_conversation: dict[str, list[EpisodeEvent]] = defaultdict(list)
    for event in events:
        if event.conversation_id and _talk_role(event) and event.event_id not in claimed:
            by_conversation[event.conversation_id].append(event)
    for conversation_id, leftover_events in by_conversation.items():
        owners = {event.user_id for event in leftover_events}
        if len(owners) != 1:
            continue
        leftover_roles = Counter(_talk_role(event) for event in leftover_events)
        leftover_turns = {
            role: unused.get((conversation_id, role), [])
            for role in ("student", "tutor")
        }
        if leftover_roles["student"] != len(leftover_turns["student"]):
            continue
        if leftover_roles["tutor"] != len(leftover_turns["tutor"]):
            continue
        for event in leftover_events:
            role = _talk_role(event)
            if role is None:
                continue
            remaining = leftover_turns[role]
            if not remaining:
                continue
            linked[event.event_id] = remaining.pop(0).text
    return linked


def load_event_log(
    path: Path,
) -> tuple[list[EpisodeEvent], dict[str, list[TranscriptTurn]], ImportQuality]:
    """Validate events, index optional local transcripts, and report losses."""
    events: list[EpisodeEvent] = []
    transcripts: dict[str, list[TranscriptTurn]] = defaultdict(list)
    seen: set[str] = set()
    reasons: Counter[str] = Counter()
    total_rows = duplicate_events = rejected_rows = legacy_rows = 0

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            total_rows += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                rejected_rows += 1
                reasons["malformed_json"] += 1
                continue
            if not isinstance(record, dict):
                rejected_rows += 1
                reasons["not_an_object"] += 1
                continue
            if record.get("record_kind") == "legacy":
                legacy_rows += 1
                turn = _legacy_turn(record)
                if turn:
                    transcripts[turn.conversation_id].append(turn)
                continue

            payload = record.get("payload")
            if isinstance(payload, dict):
                forbidden = FORBIDDEN_PAYLOAD_KEYS.intersection(payload)
                if forbidden:
                    rejected_rows += 1
                    reasons["forbidden_payload_key"] += 1
                    continue
                size = len(
                    json.dumps(payload, separators=(",", ":")).encode("utf-8")
                )
                if size > MAX_PAYLOAD_BYTES:
                    rejected_rows += 1
                    reasons["payload_too_large"] += 1
                    continue
            try:
                event = EpisodeEvent.model_validate(record)
            except ValidationError as exc:
                rejected_rows += 1
                reasons[_reason(exc)] += 1
                continue
            if event.occurred_at.tzinfo is None:
                rejected_rows += 1
                reasons["timestamp_without_timezone"] += 1
                continue
            if event.question_id == "unknown" and event.question_source != "unknown":
                rejected_rows += 1
                reasons["inconsistent_unknown_question"] += 1
                continue
            if event.event_id in seen:
                duplicate_events += 1
                continue
            seen.add(event.event_id)
            events.append(event)

    events.sort(
        key=lambda event: (
            event.occurred_at,
            event.client_sequence,
            event.event_id,
        )
    )
    quality = ImportQuality(
        total_rows=total_rows,
        accepted_events=len(events),
        duplicate_events=duplicate_events,
        rejected_rows=rejected_rows,
        legacy_rows=legacy_rows,
        unknown_question_events=sum(
            event.question_id == "unknown" for event in events
        ),
        rejection_reasons=dict(sorted(reasons.items())),
    )
    return events, dict(transcripts), quality


def _bundle_id(events: list[EpisodeEvent]) -> str:
    digest = hashlib.sha256()
    digest.update(EVENT_SCHEMA_VERSION.encode("utf-8"))
    for event_id in sorted(event.event_id for event in events):
        digest.update(b"\x1f")
        digest.update(event_id.encode("utf-8"))
    return f"bundle_{digest.hexdigest()[:16]}"


def _generation_metadata(path: Path) -> dict[str, Any] | None:
    manifest_path = path.parent / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    generation = manifest.get("generation") if isinstance(manifest, dict) else None
    return generation if isinstance(generation, dict) else None


def build_dataset(
    path: Path,
    source_kind: SourceKind = "unknown",
) -> EpisodeDataset:
    events, transcripts, quality = load_event_log(path)
    episodes = reconstruct_episodes(events)
    questions = summarize_questions(episodes)
    return EpisodeDataset(
        meta=DatasetMeta(
            bundle_id=_bundle_id(events),
            source_kind=source_kind,
            source_file=path.name,
            event_schema_version=EVENT_SCHEMA_VERSION,
            reconstruction_version=RECONSTRUCTION_VERSION,
            inactivity_timeout_ms=INACTIVITY_TIMEOUT_MS,
            episode_count=len(episodes),
            question_count=len(questions),
            quality=quality,
            generation=_generation_metadata(path),
        ),
        episodes=episodes,
        questions=questions,
        transcripts=transcripts,
    )
