"""Localhost-only Episode Explorer over an imported event bundle."""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from src.episodes.models import Episode, EpisodeDataset, EpisodeEvent, SourceKind
from src.ingest.episode_events import build_dataset, link_transcripts
from src.viewer.briefing import (
    DEFAULT_FILENAME as DEFAULT_BRIEFING_FILENAME,
    BriefingArtifact,
    briefing_for_dataset,
)
from src.viewer.classification import (
    ClassificationArtifact,
    DEFAULT_CLASSIFICATION_FILENAME,
    load_cached_classifications,
)
from src.viewer.overview import (
    DEFAULT_FILENAME as DEFAULT_OVERVIEW_FILENAME,
    LabOverviewArtifact,
    overview_for_dataset,
)
from src.viewer.insights import (
    ENTRY_CONTEXTS,
    RESPONSE_USES,
    build_insight_payload,
    build_journeys,
    entry_context,
    evidence_episode,
    representative_pathway_journeys,
    response_use,
)
from src.viewer.message_labels import purpose_for_event
from src.viewer.presentation import build_presentation
from src.viewer.interactions import build_exchanges

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_PORT = 8342


def _event_summary(event: EpisodeEvent) -> str:
    payload = event.payload
    if event.event_type == "cell_edit":
        return (
            f"Edited cell: +{payload.get('characters_inserted', '?')} / "
            f"-{payload.get('characters_deleted', '?')} characters"
        )
    if event.event_type == "cell_execution_started":
        return "Started autograder" if payload.get("is_autograder") else "Ran cell"
    if event.event_type == "cell_execution_completed":
        outcome = "succeeded" if payload.get("success") else "failed"
        duration = payload.get("duration_ms")
        return f"Execution {outcome}" + (
            f" in {duration} ms" if isinstance(duration, (int, float)) else ""
        )
    if event.event_type == "cell_error":
        return f"Execution error: {payload.get('error_name', 'unknown')}"
    if event.event_type == "tutor_query":
        act = payload.get("synthetic_message_act")
        prefix = f"Asked tutor: {act}" if act else "Asked tutor"
        return f"{prefix} ({payload.get('message_length', '?')} characters)"
    if event.event_type == "tutor_response":
        blocks = payload.get("code_block_count", 0)
        return f"Tutor responded ({blocks} code block{'s' if blocks != 1 else ''})"
    if event.event_type == "tutor_code_inserted":
        return "Inserted tutor code into notebook"
    if event.event_type == "tutor_code_copied":
        return "Copied tutor code"
    if event.event_type == "notebook_paste":
        provenance = payload.get("provenance", "unknown")
        return (
            "Pasted exact copied tutor code"
            if provenance == "copied_then_pasted"
            else "Pasted content; provenance unknown"
        )
    if event.event_type == "autograder_completed":
        outcome = "passed" if payload.get("success") else "failed"
        return f"Autograder {outcome}: {payload.get('grader_id', 'unknown')}"
    if event.event_type == "active_question_changed":
        return "Active question changed"
    if event.event_type == "notebook_session_started":
        return "Notebook session started"
    return event.event_type


def _event_view(event: EpisodeEvent, first: EpisodeEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at.isoformat(),
        "relative_ms": max(
            0, int((event.occurred_at - first.occurred_at).total_seconds() * 1000)
        ),
        "cell_id": event.cell_id,
        "cell_index": event.cell_index,
        "correlation_id": event.correlation_id,
        "turn_id": event.turn_id,
        "response_id": event.response_id,
        "conversation_id": event.conversation_id,
        "summary": _event_summary(event),
        "payload": event.payload,
    }


def _recorded_difficulty_count(episode: Episode) -> int:
    return sum(
        event.event_type == "cell_error"
        or (
            event.event_type == "autograder_completed"
            and event.payload.get("success") is False
        )
        for event in episode.events
    )


def _ending_label(episode: Episode) -> str:
    if episode.end_reason == "autograder_success":
        return "passed"
    if episode.end_reason == "inactivity":
        return "paused for 30+ minutes"
    return "data ended without a pass"


def _journey_summary(
    episode: Episode,
    journey: dict[str, Any],
) -> str:
    attempts = episode.measures.attempt_count
    difficulty = _recorded_difficulty_count(episode)
    parts = [
        (
            "No code run recorded"
            if attempts == 0
            else "Tried once"
            if attempts == 1
            else f"Tried {attempts} times"
        )
    ]
    if difficulty:
        parts.append(
            f"{difficulty} recorded error or failed check"
            if difficulty == 1
            else f"{difficulty} recorded errors or failed checks"
        )
    if episode.measures.tutor_turn_count:
        if episode.measures.prior_pass_recorded:
            parts.append("asked the tutor after a recorded pass")
        elif episode.measures.attempted_before_asking is False:
            parts.append("asked the tutor before attempting")
        else:
            parts.append("asked the tutor after working")
        if episode.measures.tutor_code_provenance == "inserted_from_tutor":
            parts.append("inserted exact tutor code")
        elif episode.measures.tutor_code_provenance == "copied_then_pasted":
            parts.append("pasted exact tutor code")
        if episode.measures.tested_after_response is True:
            parts.append("tested afterward")
        elif episode.measures.tested_after_response is False:
            parts.append("no later test recorded in this session")
    else:
        parts.append("did not use the tutor")
    parts.append(_ending_label(episode))
    if journey["session_count"] > 1:
        parts.append(
            f"session {journey['session_index']} of {journey['session_count']}"
        )
    return " → ".join(parts)


def _phase_view(episode: Episode) -> list[dict[str, str]]:
    attempts = episode.measures.attempt_count
    difficulty = _recorded_difficulty_count(episode)
    tutor_used = episode.measures.tutor_turn_count > 0
    if episode.measures.tutor_code_provenance == "inserted_from_tutor":
        action = "Exact tutor code inserted"
        action_state = "observed"
    elif episode.measures.tutor_code_provenance == "copied_then_pasted":
        action = "Exact tutor code pasted"
        action_state = "observed"
    elif episode.measures.edited_after_response is True:
        action = "Notebook edited after response"
        action_state = "observed"
    elif tutor_used:
        action = "No notebook change recorded after response"
        action_state = "not-recorded"
    else:
        action = "No tutor response"
        action_state = "not-applicable"
    return [
        {
            "name": "Attempt",
            "state": "observed" if attempts else "not-recorded",
            "detail": f"{attempts} code run{'s' if attempts != 1 else ''} recorded",
        },
        {
            "name": "Difficulty",
            "state": "observed" if difficulty else "not-recorded",
            "detail": (
                f"{difficulty} error{'s' if difficulty != 1 else ''} or failed checks"
                if difficulty
                else "No error or failed check recorded"
            ),
        },
        {
            "name": "Tutor",
            "state": "observed" if tutor_used else "not-applicable",
            "detail": (
                f"{episode.measures.tutor_turn_count} question"
                f"{'s' if episode.measures.tutor_turn_count != 1 else ''}"
                if tutor_used
                else "Tutor not used"
            ),
        },
        {"name": "Student action", "state": action_state, "detail": action},
        {
            "name": "Outcome",
            "state": (
                "resolved" if episode.measures.eventually_passed else "not-recorded"
            ),
            "detail": _ending_label(episode),
        },
    ]


def _episode_row(
    episode: Episode,
    journey: dict[str, Any],
) -> dict[str, Any]:
    return {
        "episode_id": episode.episode_id,
        "student_key": episode.student_key,
        "notebook_id": episode.notebook_id,
        "question_id": episode.question_id,
        "question_source": episode.question_source,
        "started_at": episode.started_at.isoformat(),
        "ended_at": episode.ended_at.isoformat(),
        "duration_ms": episode.duration_ms,
        "end_reason": episode.end_reason,
        "ending_label": _ending_label(episode),
        "patterns": episode.patterns,
        "interaction_acts": sorted(
            {
                str(event.payload["synthetic_message_act"])
                for event in episode.events
                if event.event_type == "tutor_query"
                and event.payload.get("synthetic_ground_truth") is True
                and event.payload.get("synthetic_message_act")
            }
        ),
        "measures": episode.measures.model_dump(),
        "recorded_difficulty_count": _recorded_difficulty_count(episode),
        "journey": journey,
        "journey_summary": _journey_summary(episode, journey),
        "phases": _phase_view(episode),
        "event_count": len(episode.events),
        "conversation_count": len(episode.conversation_ids),
    }


def _representative_sample(
    episodes: list[Episode],
    size: int,
    seed: int,
) -> list[Episode]:
    """Round-robin deterministic sample across observed pattern combinations."""
    buckets: dict[str, list[Episode]] = {}
    for episode in episodes:
        key = "|".join(episode.patterns) or "no-named-pattern"
        buckets.setdefault(key, []).append(episode)
    for key, bucket in buckets.items():
        bucket.sort(
            key=lambda episode: hashlib.sha256(
                f"{seed}:{key}:{episode.episode_id}".encode("utf-8")
            ).hexdigest()
        )
    selected: list[Episode] = []
    keys = sorted(buckets)
    while len(selected) < size and any(buckets[key] for key in keys):
        for key in keys:
            if buckets[key] and len(selected) < size:
                selected.append(buckets[key].pop())
    return selected


def _episode_detail(
    episode: Episode,
    dataset: EpisodeDataset,
    show_transcripts: bool,
    journey_by_episode: dict[str, dict[str, Any]],
    by_id: dict[str, Episode],
) -> dict[str, Any]:
    journey = journey_by_episode[episode.episode_id]
    row = _episode_row(episode, journey)
    row["conversation_ids"] = episode.conversation_ids
    row["events"] = [
        _event_view(event, episode.events[0]) for event in episode.events
    ]
    row["transcript"] = (
        [
            turn.model_dump()
            for conversation_id in episode.conversation_ids
            for turn in dataset.transcripts.get(conversation_id, [])
        ]
        if show_transcripts
        else []
    )
    row["transcript_available"] = any(
        dataset.transcripts.get(conversation_id)
        for conversation_id in episode.conversation_ids
    )
    row["transcript_enabled"] = show_transcripts
    row["related_sessions"] = [
        _episode_row(by_id[episode_id], journey_by_episode[episode_id])
        for episode_id in journey["episode_ids"]
        if episode_id != episode.episode_id
    ]
    return row


def _student_journey_view(
    journey: Any,
    *,
    display_name: str,
    dataset: EpisodeDataset,
    show_transcripts: bool,
) -> dict[str, Any]:
    """Represent one student's complete question journey in recorded order."""
    events = journey.events
    if not events:
        return {
            "journey_id": journey.journey_id,
            "student_name": display_name,
            "summary": "No recorded events",
            "metrics": {},
            "events": [],
        }

    session_by_event = {
        event.event_id: session_index
        for session_index, episode in enumerate(journey.episodes, start=1)
        for event in episode.events
    }
    linked_text = (
        link_transcripts(events, dataset.transcripts) if show_transcripts else {}
    )
    first = events[0]
    rows = []
    for step, event in enumerate(events, start=1):
        role = (
            "student"
            if event.event_type == "tutor_query"
            else "tutor"
            if event.event_type == "tutor_response"
            else None
        )
        transcript_text = linked_text.get(event.event_id)
        event_row = _event_view(event, first)
        event_row.update(
            {
                "step": step,
                "session_index": session_by_event[event.event_id],
                "transcript_role": role if transcript_text else None,
                "transcript_text": transcript_text,
                "request_purpose": purpose_for_event(event),
            }
        )
        rows.append(event_row)

    difficulty_count = sum(
        event.event_type == "cell_error"
        or (
            event.event_type == "autograder_completed"
            and event.payload.get("success") is False
        )
        for event in events
    )
    outcome = "passed" if journey.eventually_passed else "no pass recorded"
    summary = (
        f"{journey.attempt_count} code runs · "
        f"{difficulty_count} errors or failed checks · "
        f"{journey.tutor_turn_count} tutor questions · {outcome}"
    )
    return {
        "journey_id": journey.journey_id,
        "student_name": display_name,
        "summary": summary,
        "metrics": {
            "attempt_count": journey.attempt_count,
            "difficulty_count": difficulty_count,
            "tutor_turn_count": journey.tutor_turn_count,
            "active_duration_ms": journey.active_duration_ms,
            "eventually_passed": journey.eventually_passed,
            "session_count": len(journey.episodes),
        },
        "transcripts_enabled": show_transcripts,
        "entry_context": entry_context(journey),
        "exchanges": build_exchanges(journey),
        "events": rows,
    }


def create_app(
    dataset: EpisodeDataset,
    *,
    show_transcripts: bool = False,
    briefing: BriefingArtifact | None = None,
    overview: LabOverviewArtifact | None = None,
    classifications: ClassificationArtifact | None = None,
) -> FastAPI:
    """Create an immutable read-only API over one loaded dataset."""
    app = FastAPI(title="episode-viewer-v1")
    if briefing is None and dataset.meta.source_kind == "synthetic":
        briefing = briefing_for_dataset(dataset)
    if overview is None and dataset.meta.source_kind == "synthetic":
        overview = overview_for_dataset(dataset, classifications=classifications)
    presentation = (
        build_presentation(
            dataset,
            overview,
            classifications,
            include_transcripts=show_transcripts,
        )
        if overview
        else None
    )
    by_id = {episode.episode_id: episode for episode in dataset.episodes}
    student_question_journeys = build_journeys(dataset.episodes)
    student_names = {
        student_key: f"Student {index:03d}"
        for index, student_key in enumerate(
            sorted({journey.student_key for journey in student_question_journeys}),
            start=1,
        )
    }
    insight_payload = build_insight_payload(dataset.episodes)
    journey_groups: dict[tuple[str, str, str], list[Episode]] = {}
    for episode in dataset.episodes:
        key = (episode.student_key, episode.notebook_id, episode.question_id)
        journey_groups.setdefault(key, []).append(episode)
    journey_by_episode: dict[str, dict[str, Any]] = {}
    for group in journey_groups.values():
        ordered = sorted(group, key=lambda episode: episode.started_at)
        episode_ids = [episode.episode_id for episode in ordered]
        journey_passed = any(
            episode.measures.eventually_passed for episode in ordered
        )
        for index, episode in enumerate(ordered, start=1):
            journey_by_episode[episode.episode_id] = {
                "session_index": index,
                "session_count": len(ordered),
                "episode_ids": episode_ids,
                "journey_passed": journey_passed,
            }

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        patterns = Counter(
            pattern for episode in dataset.episodes for pattern in episode.patterns
        )
        patterns["no-named-pattern"] = sum(
            not episode.patterns for episode in dataset.episodes
        )
        acts = Counter(
            str(event.payload["synthetic_message_act"])
            for episode in dataset.episodes
            for event in episode.events
            if event.event_type == "tutor_query"
            and event.payload.get("synthetic_ground_truth") is True
            and event.payload.get("synthetic_message_act")
        )
        return {
            **dataset.meta.model_dump(),
            "pattern_counts": dict(sorted(patterns.items())),
            "interaction_act_counts": dict(sorted(acts.items())),
            "transcripts_enabled": show_transcripts,
            "transcript_conversation_count": len(dataset.transcripts),
        }

    @app.get("/api/questions")
    def questions() -> list[dict[str, Any]]:
        return [summary.model_dump() for summary in dataset.questions]

    @app.get("/api/insights")
    def insights() -> dict[str, Any]:
        return insight_payload

    @app.get("/api/briefing")
    def professor_briefing() -> dict[str, Any]:
        if briefing is None:
            raise HTTPException(
                status_code=404,
                detail="no professor briefing is available for this dataset",
            )
        return briefing.model_dump(mode="json")

    @app.get("/api/overview")
    def professor_overview() -> dict[str, Any]:
        if overview is None:
            raise HTTPException(
                status_code=404,
                detail="no lab overview is available for this dataset",
            )
        return {**overview.model_dump(mode="json"), "presentation": presentation}

    @app.get("/api/question-journeys")
    def question_journeys(
        question_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any]:
        selected = [
            journey
            for journey in student_question_journeys
            if journey.question_id == question_id
            and (notebook_id is None or journey.notebook_id == notebook_id)
        ]
        return {
            "question_id": question_id,
            "student_count": len(selected),
            "students": [
                _student_journey_view(
                    journey,
                    display_name=student_names[journey.student_key],
                    dataset=dataset,
                    show_transcripts=show_transcripts,
                )
                for journey in selected
            ],
        }

    @app.get("/api/pathway-examples")
    def pathway_examples(
        entry: str,
        use: str,
        notebook_id: str | None = None,
        question_id: str | None = None,
        size: int = Query(default=3, ge=1, le=20),
        seed: int = 0,
    ) -> dict[str, Any]:
        valid_entries = {item["id"] for item in ENTRY_CONTEXTS}
        valid_uses = {item["id"] for item in RESPONSE_USES}
        if entry not in valid_entries:
            raise HTTPException(status_code=400, detail="unknown entry context")
        if use not in valid_uses:
            raise HTTPException(status_code=400, detail="unknown response use")

        selected = student_question_journeys
        if notebook_id is not None:
            selected = [
                journey
                for journey in selected
                if journey.notebook_id == notebook_id
            ]
        if question_id is not None:
            selected = [
                journey
                for journey in selected
                if journey.question_id == question_id
            ]
        matching_count = sum(
            entry_context(journey) == entry
            and response_use(journey) == use
            for journey in selected
        )
        sample = representative_pathway_journeys(
            selected,
            entry=entry,
            use=use,
            size=size,
            seed=seed,
        )
        rows = []
        for journey in sample:
            episode = evidence_episode(journey)
            row = _episode_row(
                episode,
                journey_by_episode[episode.episode_id],
            )
            row["pathway"] = {
                "entry_context": entry,
                "response_use": use,
            }
            row["journey_totals"] = {
                "attempt_count": journey.attempt_count,
                "tutor_turn_count": journey.tutor_turn_count,
                "active_duration_ms": journey.active_duration_ms,
                "eventually_passed": journey.eventually_passed,
                "session_count": len(journey.episodes),
            }
            rows.append(row)
        return {
            "total": matching_count,
            "entry_context": entry,
            "response_use": use,
            "examples": rows,
        }

    @app.get("/api/episodes")
    def episodes(
        question_id: str | None = None,
        notebook_id: str | None = None,
        pattern: str | None = None,
        interaction_act: str | None = None,
        student_key: str | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
        representative_size: int | None = Query(default=None, ge=1, le=100),
        sample_seed: int = 0,
    ) -> dict[str, Any]:
        selected = dataset.episodes
        if question_id is not None:
            selected = [ep for ep in selected if ep.question_id == question_id]
        if notebook_id is not None:
            selected = [ep for ep in selected if ep.notebook_id == notebook_id]
        if pattern is not None:
            selected = (
                [ep for ep in selected if not ep.patterns]
                if pattern == "no-named-pattern"
                else [ep for ep in selected if pattern in ep.patterns]
            )
        if interaction_act is not None:
            selected = [
                ep
                for ep in selected
                if any(
                    event.payload.get("synthetic_message_act") == interaction_act
                    for event in ep.events
                )
            ]
        if student_key is not None:
            selected = [ep for ep in selected if ep.student_key == student_key]
        total = len(selected)
        if representative_size is not None:
            page = _representative_sample(selected, representative_size, sample_seed)
            selection_mode = "representative"
            result_offset = 0
            has_more = False
        else:
            page = selected[offset : offset + limit]
            selection_mode = "page"
            result_offset = offset
            has_more = offset + len(page) < total
        return {
            "total": total,
            "offset": result_offset,
            "limit": len(page),
            "has_more": has_more,
            "selection_mode": selection_mode,
            "episodes": [
                _episode_row(ep, journey_by_episode[ep.episode_id]) for ep in page
            ],
        }

    @app.get("/api/episodes/{episode_id}")
    def episode(episode_id: str) -> dict[str, Any]:
        selected = by_id.get(episode_id)
        if selected is None:
            raise HTTPException(status_code=404, detail="episode not found")
        return _episode_detail(
            selected,
            dataset,
            show_transcripts,
            journey_by_episode,
            by_id,
        )

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Open the localhost-only question episode explorer."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--source-kind",
        choices=("synthetic", "real", "unknown"),
        default="unknown",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--show-transcripts",
        action="store_true",
        help="show local legacy tutor text when conversation IDs link it",
    )
    parser.add_argument(
        "--briefing",
        type=Path,
        help=(
            "briefing artifact; defaults to briefing.json beside the input "
            "event log"
        ),
    )
    parser.add_argument(
        "--classifications",
        type=Path,
        help=(
            "student-question classifications; defaults to "
            "classifications.json beside the input event log"
        ),
    )
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"input JSONL does not exist: {args.input}")

    dataset = build_dataset(args.input, source_kind=args.source_kind)
    classification_path = (
        args.classifications
        or args.input.parent / DEFAULT_CLASSIFICATION_FILENAME
    )
    classifications = load_cached_classifications(
        classification_path,
        dataset,
    )
    briefing_path = args.briefing or args.input.parent / DEFAULT_BRIEFING_FILENAME
    overview_path = args.input.parent / DEFAULT_OVERVIEW_FILENAME
    briefing = (
        briefing_for_dataset(
            dataset,
            briefing_path,
            classifications,
        )
        if args.source_kind == "synthetic"
        else None
    )
    overview = (
        overview_for_dataset(
            dataset,
            overview_path,
            classifications,
        )
        if args.source_kind == "synthetic"
        else None
    )
    app = create_app(
        dataset,
        show_transcripts=args.show_transcripts,
        briefing=briefing,
        overview=overview,
        classifications=classifications,
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
