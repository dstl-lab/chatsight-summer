"""Class-level, observational summaries of student-question journeys.

The summaries in this module cross what was recorded before the first tutor
query with what was recorded after the first tutor response.  They do not
infer intent, reliance, learning, or tutor effectiveness.
"""

from __future__ import annotations

import hashlib
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from src.episodes.models import Episode, EpisodeEvent

ENTRY_CONTEXTS = (
    {
        "id": "before-attempt",
        "label": "Used tutor before editing or running code",
        "short_label": "Before editing or running code",
        "description": (
            "No notebook edit, code run, failed check, or pass was recorded "
            "before the first tutor question."
        ),
    },
    {
        "id": "after-attempt",
        "label": "Used tutor after editing or running code",
        "short_label": "After editing or running code",
        "description": (
            "A notebook edit or code run was recorded before asking, but no "
            "error, failed check, or pass was recorded first."
        ),
    },
    {
        "id": "after-problem",
        "label": "Used tutor after an error or failed autograder check",
        "short_label": "After an error or failed autograder check",
        "description": (
            "At least one execution error or failed autograder check was "
            "recorded before the first tutor question."
        ),
    },
    {
        "id": "after-pass",
        "label": "Used tutor after passing the autograder",
        "short_label": "After passing the autograder",
        "description": (
            "A passing autograder check was recorded before the first tutor "
            "question for this student and question."
        ),
    },
)

RESPONSE_USES = (
    {
        "id": "no-code-change",
        "label": "No code change recorded after the tutor replied",
        "short_label": "No code change recorded",
        "description": (
            "No exact tutor-code transfer or later notebook edit was recorded "
            "after the first tutor response."
        ),
    },
    {
        "id": "edited-no-transfer",
        "label": "Code edited without using exact tutor code",
        "short_label": "Code edited; no exact tutor code used",
        "description": (
            "A later notebook edit was recorded, but no exact tutor-code "
            "insert or paste was recorded."
        ),
    },
    {
        "id": "exact-transfer-no-edit",
        "label": "Exact tutor code used with no later edit recorded",
        "short_label": "Exact tutor code used; no later edit",
        "description": (
            "Exact tutor code was inserted or pasted, with no later notebook "
            "edit recorded."
        ),
    },
    {
        "id": "exact-transfer-then-edit",
        "label": "Exact tutor code used and then code edited",
        "short_label": "Exact tutor code used, then code edited",
        "description": (
            "Exact tutor code was inserted or pasted and a later notebook "
            "edit was recorded. The edit is not assumed to modify that code."
        ),
    },
)

_ENTRY_INDEX = {item["id"]: index for index, item in enumerate(ENTRY_CONTEXTS)}
_RESPONSE_INDEX = {
    item["id"]: index for index, item in enumerate(RESPONSE_USES)
}


@dataclass(frozen=True)
class StudentQuestionJourney:
    """All reconstructed sessions for one student, notebook, and question."""

    student_key: str
    notebook_id: str
    question_id: str
    episodes: tuple[Episode, ...]

    @property
    def journey_id(self) -> str:
        raw = f"{self.student_key}\x1f{self.notebook_id}\x1f{self.question_id}"
        return "journey_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def events(self) -> list[EpisodeEvent]:
        return sorted(
            (
                event
                for episode in self.episodes
                for event in episode.events
            ),
            key=lambda event: (
                event.occurred_at,
                event.client_sequence,
                event.event_id,
            ),
        )

    @property
    def tutor_used(self) -> bool:
        return any(
            event.event_type == "tutor_query" for event in self.events
        )

    @property
    def attempt_count(self) -> int:
        return sum(
            episode.measures.attempt_count for episode in self.episodes
        )

    @property
    def tutor_turn_count(self) -> int:
        return sum(
            episode.measures.tutor_turn_count for episode in self.episodes
        )

    @property
    def active_duration_ms(self) -> int:
        # Episode durations exclude gaps that caused inactivity splits.
        return sum(episode.duration_ms for episode in self.episodes)

    @property
    def eventually_passed(self) -> bool:
        return any(
            episode.measures.eventually_passed for episode in self.episodes
        )


def build_journeys(episodes: Iterable[Episode]) -> list[StudentQuestionJourney]:
    grouped: dict[tuple[str, str, str], list[Episode]] = defaultdict(list)
    for episode in episodes:
        if episode.question_id == "unknown":
            continue
        grouped[
            (episode.student_key, episode.notebook_id, episode.question_id)
        ].append(episode)

    journeys = [
        StudentQuestionJourney(
            student_key=key[0],
            notebook_id=key[1],
            question_id=key[2],
            episodes=tuple(
                sorted(items, key=lambda episode: episode.started_at)
            ),
        )
        for key, items in grouped.items()
    ]
    return sorted(
        journeys,
        key=lambda journey: (
            journey.notebook_id,
            journey.question_id,
            journey.student_key,
        ),
    )


def _first_index(events: list[EpisodeEvent], event_type: str) -> int | None:
    return next(
        (
            index
            for index, event in enumerate(events)
            if event.event_type == event_type
        ),
        None,
    )


def sequence_context_at(
    events: list[EpisodeEvent],
    query_index: int,
) -> str:
    """Return the recorded context immediately before one tutor query."""
    before = events[:query_index]
    for event in reversed(before):
        if event.event_type == "autograder_completed":
            return (
                "after-pass"
                if event.payload.get("success") is True
                else "after-problem"
            )
        if event.event_type == "cell_error":
            return "after-problem"
        if event.event_type == "cell_edit" or (
            event.event_type == "cell_execution_started"
            and event.payload.get("is_autograder") is not True
        ):
            return "after-attempt"
    return "before-attempt"


def entry_context(journey: StudentQuestionJourney) -> str | None:
    """Return the recorded context before the journey's first tutor query."""
    events = journey.events
    query_index = _first_index(events, "tutor_query")
    if query_index is None:
        return None
    return sequence_context_at(events, query_index)


def response_use(journey: StudentQuestionJourney) -> str | None:
    """Return the recorded notebook action after the first tutor response."""
    events = journey.events
    response_index = _first_index(events, "tutor_response")
    if response_index is None:
        return None
    after = events[response_index + 1 :]
    transfer_indexes = [
        index
        for index, event in enumerate(after)
        if event.event_type == "tutor_code_inserted"
        or (
            event.event_type == "notebook_paste"
            and event.payload.get("provenance") == "copied_then_pasted"
        )
    ]
    if transfer_indexes:
        first_transfer = transfer_indexes[0]
        later_edit = any(
            event.event_type == "cell_edit"
            for event in after[first_transfer + 1 :]
        )
        return (
            "exact-transfer-then-edit"
            if later_edit
            else "exact-transfer-no-edit"
        )
    if any(event.event_type == "cell_edit" for event in after):
        return "edited-no-transfer"
    return "no-code-change"


def _tested_after_response(journey: StudentQuestionJourney) -> bool:
    events = journey.events
    response_index = _first_index(events, "tutor_response")
    if response_index is None:
        return False
    return any(
        (
            event.event_type == "cell_execution_started"
            and event.payload.get("is_autograder") is not True
        )
        or event.event_type == "autograder_completed"
        for event in events[response_index + 1 :]
    )


def _passed_after_response(journey: StudentQuestionJourney) -> bool:
    events = journey.events
    response_index = _first_index(events, "tutor_response")
    if response_index is None:
        return False
    return any(
        event.event_type == "autograder_completed"
        and event.payload.get("success") is True
        for event in events[response_index + 1 :]
    )


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _median(values: list[int]) -> float | None:
    return float(statistics.median(values)) if values else None


def _pathway_cells(
    journeys: list[StudentQuestionJourney],
) -> list[dict[str, Any]]:
    tutor_journeys = [journey for journey in journeys if journey.tutor_used]
    grouped: dict[tuple[str, str], list[StudentQuestionJourney]] = defaultdict(
        list
    )
    for journey in tutor_journeys:
        entry = entry_context(journey)
        use = response_use(journey)
        if entry is not None and use is not None:
            grouped[(entry, use)].append(journey)

    denominator = sum(len(items) for items in grouped.values())
    cells: list[dict[str, Any]] = []
    for entry in ENTRY_CONTEXTS:
        for use in RESPONSE_USES:
            items = grouped[(entry["id"], use["id"])]
            cells.append(
                {
                    "entry_context": entry["id"],
                    "response_use": use["id"],
                    "count": len(items),
                    "share": _ratio(len(items), denominator),
                    "tested_after_response": _ratio(
                        sum(_tested_after_response(item) for item in items),
                        len(items),
                    ),
                    "passed_after_response": _ratio(
                        sum(_passed_after_response(item) for item in items),
                        len(items),
                    ),
                }
            )
    return cells


def _dominant_pathway(
    journeys: list[StudentQuestionJourney],
) -> dict[str, Any] | None:
    counts = Counter(
        (entry_context(journey), response_use(journey))
        for journey in journeys
        if journey.tutor_used
        and entry_context(journey) is not None
        and response_use(journey) is not None
    )
    if not counts:
        return None
    (entry, use), count = min(
        counts.items(),
        key=lambda item: (
            -item[1],
            _ENTRY_INDEX[item[0][0]],
            _RESPONSE_INDEX[item[0][1]],
        ),
    )
    tutor_count = sum(counts.values())
    return {
        "entry_context": entry,
        "response_use": use,
        "count": count,
        "share": _ratio(count, tutor_count),
    }


def summarize_scope(
    journeys: list[StudentQuestionJourney],
) -> dict[str, Any]:
    tutor_journeys = [journey for journey in journeys if journey.tutor_used]
    grid_journeys = [
        journey
        for journey in tutor_journeys
        if entry_context(journey) is not None
        and response_use(journey) is not None
    ]
    represented_students = {journey.student_key for journey in journeys}
    return {
        "population": {
            "represented_students": len(represented_students),
            "student_question_journeys": len(journeys),
            "tutor_using_journeys": len(tutor_journeys),
            "grid_eligible_tutor_journeys": len(grid_journeys),
            "tutor_journeys_without_response": (
                len(tutor_journeys) - len(grid_journeys)
            ),
            "non_tutor_journeys": len(journeys) - len(tutor_journeys),
        },
        "entry_contexts": list(ENTRY_CONTEXTS),
        "response_uses": list(RESPONSE_USES),
        "cells": _pathway_cells(journeys),
        "dominant_pathway": _dominant_pathway(journeys),
    }


def _question_summary(
    notebook_id: str,
    question_id: str,
    journeys: list[StudentQuestionJourney],
) -> dict[str, Any]:
    tutor_journeys = [journey for journey in journeys if journey.tutor_used]
    return {
        "notebook_id": notebook_id,
        "question_id": question_id,
        "represented_students": len(
            {journey.student_key for journey in journeys}
        ),
        "student_question_journeys": len(journeys),
        "tutor_using_journeys": len(tutor_journeys),
        "tutor_use": _ratio(len(tutor_journeys), len(journeys)),
        "median_attempts": _median(
            [journey.attempt_count for journey in journeys]
        ),
        "median_active_minutes": (
            _median([journey.active_duration_ms for journey in journeys])
            / 60_000
            if journeys
            else None
        ),
        "median_tutor_turns": _median(
            [journey.tutor_turn_count for journey in tutor_journeys]
        ),
        "dominant_pathway": _dominant_pathway(journeys),
        "pathways": summarize_scope(journeys),
    }


def build_insight_payload(episodes: Iterable[Episode]) -> dict[str, Any]:
    """Build class and per-question summaries from canonical episodes."""
    journeys = build_journeys(episodes)
    by_question: dict[
        tuple[str, str], list[StudentQuestionJourney]
    ] = defaultdict(list)
    for journey in journeys:
        by_question[(journey.notebook_id, journey.question_id)].append(journey)

    questions = [
        _question_summary(notebook_id, question_id, items)
        for (notebook_id, question_id), items in sorted(by_question.items())
    ]
    questions.sort(
        key=lambda item: (
            -(item["median_attempts"] or 0),
            -(item["median_active_minutes"] or 0),
            item["question_id"],
        )
    )
    return {
        "class_overview": summarize_scope(journeys),
        "questions": questions,
        "claim_boundary": (
            "These summaries describe recorded sequences. They do not measure "
            "intent, reliance, learning, or tutor effectiveness."
        ),
        "ranking": (
            "Questions are ordered by median recorded code attempts, then "
            "median active recorded time. No composite risk score is used."
        ),
    }


def representative_pathway_journeys(
    journeys: Iterable[StudentQuestionJourney],
    *,
    entry: str,
    use: str,
    size: int,
    seed: int,
) -> list[StudentQuestionJourney]:
    matching = [
        journey
        for journey in journeys
        if entry_context(journey) == entry and response_use(journey) == use
    ]
    matching.sort(
        key=lambda journey: hashlib.sha256(
            f"{seed}:{journey.journey_id}".encode("utf-8")
        ).hexdigest()
    )
    return matching[:size]


def evidence_episode(journey: StudentQuestionJourney) -> Episode:
    """Choose the first tutor-containing session as the evidence entry point."""
    return next(
        (
            episode
            for episode in journey.episodes
            if episode.measures.tutor_turn_count > 0
        ),
        journey.episodes[0],
    )
