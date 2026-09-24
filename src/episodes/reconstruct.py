"""Deterministic reconstruction and aggregation of question-scoped episodes."""

from __future__ import annotations

import hashlib
import statistics
from collections import Counter, defaultdict

from src.episodes.models import (
    INACTIVITY_TIMEOUT_MS,
    RECONSTRUCTION_VERSION,
    EndReason,
    Episode,
    EpisodeEvent,
    EpisodeMeasures,
    Provenance,
    QuestionSource,
    QuestionSummary,
    Ratio,
)

_EXPLICIT_TUTOR_CODE = {"inserted_from_tutor", "copied_then_pasted"}
_QUESTION_SOURCE_RANK: dict[QuestionSource, int] = {
    "unknown": 0,
    "notebook_cell": 1,
    "nearest_markdown": 2,
    "grader_id": 3,
}


def _ms_between(start: EpisodeEvent, end: EpisodeEvent) -> int:
    return max(0, int((end.occurred_at - start.occurred_at).total_seconds() * 1000))


def _is_success(event: EpisodeEvent) -> bool:
    return (
        event.event_type == "autograder_completed"
        and event.payload.get("success") is True
    )


def _group_key(event: EpisodeEvent) -> tuple[str, str, str]:
    return (
        event.user_id,
        event.notebook_path or event.notebook_name or "unknown-notebook",
        event.question_id,
    )


def split_episodes(
    events: list[EpisodeEvent],
    inactivity_ms: int = INACTIVITY_TIMEOUT_MS,
) -> list[tuple[list[EpisodeEvent], EndReason]]:
    """Split independently within each student/notebook/question stream."""
    grouped: dict[tuple[str, str, str], list[EpisodeEvent]] = defaultdict(list)
    for event in events:
        grouped[_group_key(event)].append(event)

    out: list[tuple[list[EpisodeEvent], EndReason]] = []
    for key in sorted(grouped):
        bucket = sorted(
            grouped[key],
            key=lambda event: (
                event.occurred_at,
                event.client_sequence,
                event.event_id,
            ),
        )
        current: list[EpisodeEvent] = []
        for event in bucket:
            if current and _ms_between(current[-1], event) > inactivity_ms:
                out.append((current, "inactivity"))
                current = []
            current.append(event)
            if _is_success(event):
                out.append((current, "autograder_success"))
                current = []
        if current:
            out.append((current, "end_of_data"))

    out.sort(
        key=lambda item: (
            item[0][0].occurred_at,
            item[0][0].client_sequence,
            item[0][0].event_id,
        )
    )
    return out


def _first(events: list[EpisodeEvent], event_type: str) -> EpisodeEvent | None:
    return next((event for event in events if event.event_type == event_type), None)


def _count(events: list[EpisodeEvent], event_type: str) -> int:
    return sum(event.event_type == event_type for event in events)


def _attempt_count(events: list[EpisodeEvent]) -> int:
    return sum(
        event.event_type == "cell_execution_started"
        and event.payload.get("is_autograder") is not True
        for event in events
    )


def _provenance(events: list[EpisodeEvent]) -> Provenance:
    values = [event.payload.get("provenance") for event in events]
    for candidate in (
        "inserted_from_tutor",
        "copied_then_pasted",
        "tutor_copy_only",
    ):
        if candidate in values:
            return candidate
    return "unknown"


def _question_source(events: list[EpisodeEvent]) -> QuestionSource:
    return max(
        (event.question_source for event in events),
        key=lambda value: _QUESTION_SOURCE_RANK[value],
    )


def _opaque_id(prefix: str, *parts: str, length: int = 16) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"


def _measure(events: list[EpisodeEvent]) -> EpisodeMeasures:
    first_query = _first(events, "tutor_query")
    first_response = _first(events, "tutor_response")
    before_query = events[: events.index(first_query)] if first_query else []
    after_response = (
        events[events.index(first_response) + 1 :] if first_response else []
    )
    success = next((event for event in events if _is_success(event)), None)

    attempted_before = (
        any(
            event.event_type in {"cell_edit", "cell_execution_started"}
            for event in before_query
        )
        if first_query
        else None
    )
    return EpisodeMeasures(
        attempted_before_asking=attempted_before,
        edits_before_asking=_count(before_query, "cell_edit") if first_query else None,
        executions_before_asking=(
            _attempt_count(before_query) if first_query else None
        ),
        errors_before_asking=(
            _count(before_query, "cell_error") if first_query else None
        ),
        time_to_first_ask_ms=(
            _ms_between(events[0], first_query) if first_query else None
        ),
        tutor_turn_count=_count(events, "tutor_query"),
        tutor_code_provenance=_provenance(events),
        edited_after_response=(
            _count(after_response, "cell_edit") > 0 if first_response else None
        ),
        tested_after_response=(
            any(
                event.event_type
                in {"cell_execution_started", "autograder_completed"}
                for event in after_response
            )
            if first_response
            else None
        ),
        errors_after_response=(
            _count(after_response, "cell_error") if first_response else None
        ),
        eventually_passed=success is not None,
        attempt_count=_attempt_count(events),
        time_to_pass_ms=_ms_between(events[0], success) if success else None,
    )


def _patterns(measures: EpisodeMeasures) -> list[str]:
    patterns: list[str] = []
    if measures.attempted_before_asking is False:
        patterns.append("ask-before-attempt")
    if (measures.errors_before_asking or 0) > 0:
        patterns.append("struggle-then-ask")
    if measures.tutor_code_provenance in _EXPLICIT_TUTOR_CODE:
        patterns.append("tutor-code-transfer")
    if measures.edited_after_response:
        patterns.append("revised-after-response")
    if measures.tested_after_response:
        patterns.append("tested-after-tutor")
    if not measures.eventually_passed:
        patterns.append("unresolved")
    if measures.tutor_turn_count == 0:
        patterns.append("no-tutor-use")
    return patterns


def reconstruct_episodes(
    events: list[EpisodeEvent],
    inactivity_ms: int = INACTIVITY_TIMEOUT_MS,
) -> list[Episode]:
    episodes: list[Episode] = []
    for episode_events, end_reason in split_episodes(events, inactivity_ms):
        first, last = episode_events[0], episode_events[-1]
        notebook_id = first.notebook_path or first.notebook_name or "unknown-notebook"
        measures = _measure(episode_events)
        conversation_ids = list(
            dict.fromkeys(
                event.conversation_id
                for event in episode_events
                if event.conversation_id
            )
        )
        episodes.append(
            Episode(
                episode_id=_opaque_id(
                    "ep",
                    RECONSTRUCTION_VERSION,
                    first.user_id,
                    notebook_id,
                    first.question_id,
                    first.event_id,
                    last.event_id,
                ),
                student_key=_opaque_id("stu", first.user_id, length=10),
                notebook_id=notebook_id,
                question_id=first.question_id,
                question_source=_question_source(episode_events),
                started_at=first.occurred_at,
                ended_at=last.occurred_at,
                duration_ms=_ms_between(first, last),
                end_reason=end_reason,
                conversation_ids=conversation_ids,
                patterns=_patterns(measures),
                measures=measures,
                events=episode_events,
            )
        )
    passed_questions: set[tuple[str, str, str]] = set()
    for episode in sorted(episodes, key=lambda item: item.started_at):
        key = (episode.student_key, episode.notebook_id, episode.question_id)
        if (
            key in passed_questions
            and episode.measures.tutor_turn_count > 0
        ):
            episode.measures.prior_pass_recorded = True
            episode.patterns.insert(0, "post-pass-ask")
        if episode.measures.eventually_passed:
            passed_questions.add(key)
    return episodes


def _ratio(numerator: int, denominator: int) -> Ratio:
    return Ratio(
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator if denominator else None,
    )


def summarize_questions(episodes: list[Episode]) -> list[QuestionSummary]:
    """Aggregate without allowing repeat episodes to double-count students."""
    by_question: dict[tuple[str, str], list[Episode]] = defaultdict(list)
    for episode in episodes:
        if episode.question_id != "unknown":
            by_question[(episode.notebook_id, episode.question_id)].append(episode)

    summaries: list[QuestionSummary] = []
    for (notebook_id, question_id), question_episodes in sorted(by_question.items()):
        by_student: dict[str, list[Episode]] = defaultdict(list)
        for episode in question_episodes:
            by_student[episode.student_key].append(episode)

        students = list(by_student.values())
        n = len(students)
        recorded_struggle = sum(
            any(
                event.event_type == "cell_error"
                or (
                    event.event_type == "autograder_completed"
                    and event.payload.get("success") is False
                )
                for episode in items
                for event in episode.events
            )
            for items in students
        )
        repeated_attempts = sum(
            sum(ep.measures.attempt_count for ep in items) >= 2
            for items in students
        )
        asked_before = sum(
            any(ep.measures.attempted_before_asking is False for ep in items)
            for items in students
        )
        errors = [
            sum(ep.measures.errors_before_asking or 0 for ep in items)
            for items in students
            if any(ep.measures.tutor_turn_count > 0 for ep in items)
        ]
        used_code = sum(
            any(
                ep.measures.tutor_code_provenance in _EXPLICIT_TUTOR_CODE
                for ep in items
            )
            for items in students
        )
        tutor_users = [
            items
            for items in students
            if any(ep.measures.tutor_turn_count > 0 for ep in items)
        ]
        tested = sum(
            any(ep.measures.tested_after_response is True for ep in items)
            for items in tutor_users
        )
        passed_after = sum(
            any(
                ep.measures.tutor_turn_count > 0 and ep.measures.eventually_passed
                for ep in items
            )
            for items in tutor_users
        )
        unresolved = sum(
            not any(ep.measures.eventually_passed for ep in items)
            for items in students
        )
        pattern_counts = Counter(
            pattern for episode in question_episodes for pattern in episode.patterns
        )
        pattern_rates = {
            pattern: _ratio(count, len(question_episodes))
            for pattern, count in sorted(pattern_counts.items())
        }
        no_named_count = sum(not episode.patterns for episode in question_episodes)
        summaries.append(
            QuestionSummary(
                notebook_id=notebook_id,
                question_id=question_id,
                student_count=n,
                episode_count=len(question_episodes),
                pct_recorded_struggle=_ratio(recorded_struggle, n),
                pct_repeated_attempts=_ratio(repeated_attempts, n),
                pct_used_tutor=_ratio(len(tutor_users), n),
                pct_asked_before_attempting=_ratio(asked_before, n),
                median_errors_before_asking=(
                    float(statistics.median(errors)) if errors else None
                ),
                pct_used_tutor_code=_ratio(used_code, n),
                pct_tested_after_tutor=_ratio(tested, len(tutor_users)),
                pct_passed_after_tutor=_ratio(passed_after, len(tutor_users)),
                pct_unresolved=_ratio(unresolved, n),
                pattern_counts=dict(sorted(pattern_counts.items())),
                pattern_rates=pattern_rates,
                no_named_pattern=_ratio(no_named_count, len(question_episodes)),
            )
        )
    return summaries
