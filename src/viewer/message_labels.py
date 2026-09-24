"""Per-message request labels, stored separately from student-question summaries.

Synthetic events already carry a ground-truth act on each student message. This
module turns those acts into inspectable labels and student counts. A later
classifier can replace the source without changing the UI contract.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.episodes.models import EpisodeDataset, EpisodeEvent
from src.viewer.insights import build_journeys, sequence_context_at

MESSAGE_LABEL_SCHEMA_VERSION = "1.0.0"

Purpose = Literal[
    "validation",
    "debugging",
    "conceptual",
    "syntax",
    "direct-answer-request",
    "assignment-clarification",
    "mixed",
    "unclear",
]

ACT_TO_PURPOSE: dict[str, Purpose] = {
    "validation": "validation",
    "debugging-request": "debugging",
    "conceptual-clarification": "conceptual",
    "syntax-help": "syntax",
    "direct-request": "direct-answer-request",
    "assignment-reference": "assignment-clarification",
}

PURPOSE_ORDER: tuple[Purpose, ...] = (
    "direct-answer-request",
    "debugging",
    "conceptual",
    "syntax",
    "validation",
    "assignment-clarification",
    "mixed",
    "unclear",
)

PURPOSE_LABELS: dict[str, str] = {
    "validation": "Checked an answer",
    "debugging": "Asked for debugging help",
    "conceptual": "Asked for an explanation",
    "syntax": "Asked how to write code",
    "direct-answer-request": "Asked for the answer",
    "assignment-clarification": "Asked what the question meant",
    "mixed": "Asked for several kinds of help",
    "unclear": "Purpose unclear",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageLabel(StrictModel):
    event_id: str
    journey_id: str
    question_id: str
    purpose: Purpose
    sequence_context: str
    source: Literal["synthetic-ground-truth"] = "synthetic-ground-truth"


class MessageLabelArtifact(StrictModel):
    schema_version: Literal["1.0.0"] = MESSAGE_LABEL_SCHEMA_VERSION
    labels: list[MessageLabel] = Field(default_factory=list)


def purpose_for_event(event: EpisodeEvent) -> Purpose | None:
    if event.event_type != "tutor_query":
        return None
    act = event.payload.get("synthetic_message_act")
    if not isinstance(act, str):
        return None
    return ACT_TO_PURPOSE.get(act)


def labels_from_dataset(dataset: EpisodeDataset) -> MessageLabelArtifact:
    labels: list[MessageLabel] = []
    for journey in build_journeys(dataset.episodes):
        events = journey.events
        for index, event in enumerate(events):
            purpose = purpose_for_event(event)
            if purpose is None:
                continue
            labels.append(
                MessageLabel(
                    event_id=event.event_id,
                    journey_id=journey.journey_id,
                    question_id=journey.question_id,
                    purpose=purpose,
                    sequence_context=sequence_context_at(events, index),
                )
            )
    labels.sort(key=lambda item: (item.question_id, item.event_id))
    return MessageLabelArtifact(labels=labels)


def request_categories(
    labels: list[MessageLabel],
    *,
    question_id: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"journey_ids": set(), "event_ids": set()}
    )
    for item in labels:
        if item.question_id != question_id:
            continue
        grouped[item.purpose]["journey_ids"].add(item.journey_id)
        grouped[item.purpose]["event_ids"].add(item.event_id)
    categories = []
    for purpose in PURPOSE_ORDER:
        bucket = grouped.get(purpose)
        if not bucket:
            continue
        journey_ids = sorted(bucket["journey_ids"])
        categories.append(
            {
                "purpose": purpose,
                "label": PURPOSE_LABELS[purpose],
                "student_count": len(journey_ids),
                "journey_ids": journey_ids,
                "event_ids": sorted(bucket["event_ids"]),
            }
        )
    return categories
