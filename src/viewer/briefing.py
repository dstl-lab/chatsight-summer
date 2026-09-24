"""One-call, evidence-backed professor briefing for an episode dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.episodes.models import EpisodeDataset, SourceKind
from src.ingest.episode_events import build_dataset
from src.viewer.classification import (
    DEFAULT_CLASSIFICATION_FILENAME,
    ClassificationArtifact,
    StudentQuestionClassification,
    load_cached_classifications,
)
from src.viewer.insights import (
    StudentQuestionJourney,
    build_journeys,
    entry_context,
    evidence_episode,
    response_use,
)

BRIEFING_SCHEMA_VERSION = "1.0.0"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_FILENAME = "briefing.json"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComparisonPoint(StrictModel):
    label: str
    value: float
    display: str
    question_id: str | None = None


class ComputedFact(StrictModel):
    fact_id: str
    title: str
    evidence: str
    question_ids: list[str] = Field(default_factory=list)
    comparison: list[ComparisonPoint] = Field(default_factory=list)
    caution: str | None = None


class BriefingTurn(StrictModel):
    role: Literal["student", "tutor"]
    text: str


class JourneyEvidence(StrictModel):
    journey_id: str
    evidence_episode_id: str
    question_id: str
    summary: str
    attempts: int
    tutor_questions: int
    active_seconds: int
    tutor_used: bool
    entry_context: str | None
    response_use: str | None
    tested_after_response: bool
    passed_after_response: bool
    classified_purpose: str | None = None
    classification_confidence: str | None = None
    interaction_acts: list[str]
    transcript: list[BriefingTurn]


class BriefingPacket(StrictModel):
    bundle_id: str
    source_kind: SourceKind
    lab_label: str
    cohort_statement: str
    classification_model: str | None = None
    classification_accuracy: float | None = None
    facts: list[ComputedFact]
    journeys: list[JourneyEvidence]
    caveats: list[str]


class DraftFinding(StrictModel):
    headline: str = Field(min_length=3, max_length=100)
    explanation: str = Field(min_length=10, max_length=500)
    instructor_prompt: str = Field(min_length=5, max_length=240)
    fact_ids: list[str] = Field(min_length=1, max_length=3)
    journey_ids: list[str] = Field(min_length=1, max_length=3)


class BriefingDraft(StrictModel):
    summary_sentences: list[str] = Field(min_length=2, max_length=2)
    findings: list[DraftFinding] = Field(min_length=3, max_length=4)


class BriefingExample(StrictModel):
    journey_id: str
    evidence_episode_id: str
    question_id: str
    summary: str
    contextual_label: str | None = None


class ResolvedFinding(StrictModel):
    headline: str
    explanation: str
    instructor_prompt: str
    facts: list[ComputedFact]
    examples: list[BriefingExample]


class BriefingArtifact(StrictModel):
    schema_version: Literal["1.0.0"] = BRIEFING_SCHEMA_VERSION
    bundle_id: str
    source_kind: SourceKind
    lab_label: str
    cohort_statement: str
    generation_mode: Literal["gemini", "deterministic-fallback"]
    fallback_reason: str | None = None
    model: str | None
    generated_at: datetime | None
    packet_hash: str
    prompt_hash: str
    summary_sentences: list[str]
    findings: list[ResolvedFinding]
    caveats: list[str]


DraftGenerator = Callable[[str], BriefingDraft]


def _canonical_json(value: BaseModel | dict[str, Any]) -> str:
    raw = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _pct_text(numerator: int, denominator: int) -> str:
    return f"{_percentage(numerator, denominator) * 100:.1f}%"


def _nearest_rank(values: list[int], proportion: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, math.ceil(proportion * len(ordered)) - 1),
    )
    return ordered[index]


def _first_index(journey: StudentQuestionJourney, event_type: str) -> int | None:
    return next(
        (
            index
            for index, event in enumerate(journey.events)
            if event.event_type == event_type
        ),
        None,
    )


def _tested_after_response(journey: StudentQuestionJourney) -> bool:
    index = _first_index(journey, "tutor_response")
    if index is None:
        return False
    return any(
        (
            event.event_type == "cell_execution_started"
            and event.payload.get("is_autograder") is not True
        )
        or event.event_type == "autograder_completed"
        for event in journey.events[index + 1 :]
    )


def _passed_after_response(journey: StudentQuestionJourney) -> bool:
    index = _first_index(journey, "tutor_response")
    if index is None:
        return False
    return any(
        event.event_type == "autograder_completed"
        and event.payload.get("success") is True
        for event in journey.events[index + 1 :]
    )


def _lab_label(dataset: EpisodeDataset) -> str:
    notebook_ids = sorted({episode.notebook_id for episode in dataset.episodes})
    match = next(
        (
            re.search(r"lab[\s_-]*(\d+)", notebook_id, flags=re.IGNORECASE)
            for notebook_id in notebook_ids
            if re.search(r"lab[\s_-]*(\d+)", notebook_id, flags=re.IGNORECASE)
        ),
        None,
    )
    return f"Lab {match.group(1)}" if match else "Loaded assignment"


def _entry_phrase(value: str | None) -> str:
    return {
        "before-attempt": "used the tutor before editing or running code",
        "after-attempt": "edited or ran code before using the tutor",
        "after-problem": (
            "had an error or failed autograder check before using the tutor"
        ),
        "after-pass": "passed the autograder before using the tutor",
        None: "did not use the tutor",
    }[value]


def _response_phrase(value: str | None) -> str:
    return {
        "no-code-change": "no code change was recorded after the reply",
        "edited-no-transfer": (
            "code was edited afterward without an exact tutor-code transfer"
        ),
        "exact-transfer-no-edit": (
            "exact tutor code was used with no later edit recorded"
        ),
        "exact-transfer-then-edit": (
            "exact tutor code was used and a later edit was recorded"
        ),
        None: "there was no recorded tutor response",
    }[value]


def _interaction_acts(journey: StudentQuestionJourney) -> list[str]:
    return sorted(
        {
            str(event.payload["synthetic_message_act"])
            for event in journey.events
            if event.event_type == "tutor_query"
            and event.payload.get("synthetic_ground_truth") is True
            and event.payload.get("synthetic_message_act")
        }
    )


def _transcript(
    journey: StudentQuestionJourney,
    dataset: EpisodeDataset,
) -> list[BriefingTurn]:
    conversation_ids = list(
        dict.fromkeys(
            conversation_id
            for episode in journey.episodes
            for conversation_id in episode.conversation_ids
        )
    )
    return [
        BriefingTurn(role=turn.role, text=turn.text)
        for conversation_id in conversation_ids
        for turn in dataset.transcripts.get(conversation_id, [])
    ]


def _journey_evidence(
    journey: StudentQuestionJourney,
    dataset: EpisodeDataset,
    classification: StudentQuestionClassification | None = None,
) -> JourneyEvidence:
    entry = entry_context(journey)
    use = response_use(journey)
    if journey.tutor_used:
        summary = f"The student {_entry_phrase(entry)}; {_response_phrase(use)}."
    else:
        summary = "The student did not use the tutor for this question."
    summary += (
        f" {journey.attempt_count} code run"
        f"{'' if journey.attempt_count == 1 else 's'} and "
        f"{journey.tutor_turn_count} tutor question"
        f"{'' if journey.tutor_turn_count == 1 else 's'} were recorded."
    )
    summary += (
        " A passing autograder check was recorded."
        if journey.eventually_passed
        else " No passing autograder check was recorded."
    )
    return JourneyEvidence(
        journey_id=journey.journey_id,
        evidence_episode_id=evidence_episode(journey).episode_id,
        question_id=journey.question_id,
        summary=summary,
        attempts=journey.attempt_count,
        tutor_questions=journey.tutor_turn_count,
        active_seconds=round(journey.active_duration_ms / 1000),
        tutor_used=journey.tutor_used,
        entry_context=entry,
        response_use=use,
        tested_after_response=_tested_after_response(journey),
        passed_after_response=_passed_after_response(journey),
        classified_purpose=(
            classification.primary_purpose if classification else None
        ),
        classification_confidence=(
            classification.confidence if classification else None
        ),
        interaction_acts=_interaction_acts(journey),
        transcript=_transcript(journey, dataset),
    )


def _comparison_fact(
    *,
    fact_id: str,
    title: str,
    points: list[ComparisonPoint],
    measure: str,
    caution: str | None = None,
) -> ComputedFact:
    ordered = sorted(points, key=lambda point: (point.value, point.label))
    low, high = ordered[0], ordered[-1]
    evidence = (
        f"{high.label} had the highest {measure} ({high.display}); "
        f"{low.label} had the lowest ({low.display})."
    )
    return ComputedFact(
        fact_id=fact_id,
        title=title,
        evidence=evidence,
        question_ids=[
            point.question_id for point in points if point.question_id is not None
        ],
        comparison=points,
        caution=caution,
    )


_CONTEXT_LABELS = {
    "before-attempt": "before editing or running code",
    "after-attempt": "after editing or running code",
    "after-problem": "after an error or failed autograder check",
    "after-pass": "after passing the autograder",
}
_PURPOSE_LABELS = {
    "validation": "validation",
    "debugging": "debugging",
    "conceptual": "conceptual explanation",
    "syntax": "syntax help",
    "direct-answer-request": "a direct answer",
    "assignment-clarification": "assignment clarification",
    "mixed": "mixed help",
    "unclear": "unclear help",
}


def _classified_facts(
    classifications: ClassificationArtifact,
) -> list[ComputedFact]:
    records = classifications.classifications
    total = len(records)
    caution = (
        "These purposes were classified by Gemini from each complete "
        "student-question record. They remain model interpretations."
    )
    pattern_counts = Counter(
        (item.sequence_context, item.primary_purpose) for item in records
    )
    top_patterns = pattern_counts.most_common(5)
    pattern_points = [
        ComparisonPoint(
            label=(
                f"{_PURPOSE_LABELS[purpose].capitalize()} "
                f"{_CONTEXT_LABELS[context]}"
            ),
            value=_percentage(count, total),
            display=f"{count} of {total} ({_pct_text(count, total)})",
        )
        for (context, purpose), count in top_patterns
    ]
    pattern_evidence = "; ".join(
        f"{point.label}: {point.display}" for point in pattern_points
    ) + "."
    facts = [
        ComputedFact(
            fact_id="classified_contextual_patterns",
            title="What students asked about and when",
            evidence=pattern_evidence,
            comparison=pattern_points,
            caution=caution,
        )
    ]

    by_question: dict[str, list[StudentQuestionClassification]] = defaultdict(
        list
    )
    for item in records:
        by_question[item.question_id].append(item)

    def question_fact(
        *,
        fact_id: str,
        title: str,
        context: str,
        purpose: str,
        measure: str,
    ) -> ComputedFact:
        points = []
        for question_id, items in sorted(by_question.items()):
            matching = sum(
                item.sequence_context == context
                and item.primary_purpose == purpose
                for item in items
            )
            points.append(
                ComparisonPoint(
                    label=f"Question {question_id}",
                    question_id=question_id,
                    value=_percentage(matching, len(items)),
                    display=(
                        f"{matching} of {len(items)} "
                        f"({_pct_text(matching, len(items))})"
                    ),
                )
            )
        return _comparison_fact(
            fact_id=fact_id,
            title=title,
            points=points,
            measure=measure,
            caution=caution,
        )

    facts.extend(
        [
            question_fact(
                fact_id="classified_validation_after_pass",
                title="Validation questions after passing the autograder",
                context="after-pass",
                purpose="validation",
                measure=(
                    "share classified as validation after passing the "
                    "autograder"
                ),
            ),
            question_fact(
                fact_id="classified_debugging_after_problem",
                title="Debugging questions after recorded problems",
                context="after-problem",
                purpose="debugging",
                measure=(
                    "share classified as debugging after an error or failed "
                    "autograder check"
                ),
            ),
            question_fact(
                fact_id="classified_direct_answer_requests",
                title="Direct-answer requests by question",
                context="before-attempt",
                purpose="direct-answer-request",
                measure=(
                    "share classified as a direct-answer request before "
                    "editing or running code"
                ),
            ),
        ]
    )
    return facts


def _build_facts(
    journeys: list[StudentQuestionJourney],
    classifications: ClassificationArtifact | None = None,
) -> list[ComputedFact]:
    tutor_journeys = [journey for journey in journeys if journey.tutor_used]
    class_count = len(journeys)
    tutor_count = len(tutor_journeys)
    facts = [
        ComputedFact(
            fact_id="class_tutor_use",
            title="How often the tutor appeared",
            evidence=(
                f"{tutor_count} of {class_count} records of student work "
                f"({_pct_text(tutor_count, class_count)}) included "
                "at least one tutor question."
            ),
        )
    ]

    entry_counts = Counter(entry_context(journey) for journey in tutor_journeys)
    entry_order = (
        ("before-attempt", "before editing or running code"),
        ("after-attempt", "after editing or running code"),
        ("after-problem", "after an error or failed autograder check"),
        ("after-pass", "after passing the autograder"),
    )
    facts.append(
        ComputedFact(
            fact_id="class_when_tutor_used",
            title="When students used the tutor",
            evidence="; ".join(
                f"{entry_counts[key]} of {tutor_count} tutor-using records "
                f"({_pct_text(entry_counts[key], tutor_count)}) began {label}"
                for key, label in entry_order
            )
            + ".",
        )
    )

    use_counts = Counter(response_use(journey) for journey in tutor_journeys)
    use_order = (
        ("no-code-change", "had no later recorded code change"),
        ("edited-no-transfer", "had a later edit without exact tutor code"),
        ("exact-transfer-no-edit", "used exact tutor code without a later edit"),
        ("exact-transfer-then-edit", "used exact tutor code and later edited"),
    )
    facts.append(
        ComputedFact(
            fact_id="class_after_tutor_reply",
            title="What followed tutor replies",
            evidence="; ".join(
                f"{use_counts[key]} of {tutor_count} tutor-using records "
                f"({_pct_text(use_counts[key], tutor_count)}) {label}"
                for key, label in use_order
            )
            + ".",
        )
    )

    tested = sum(_tested_after_response(journey) for journey in tutor_journeys)
    passed = sum(_passed_after_response(journey) for journey in tutor_journeys)
    facts.append(
        ComputedFact(
            fact_id="class_after_reply_checks",
            title="Testing after tutor replies",
            evidence=(
                f"{tested} of {tutor_count} tutor-using records "
                f"({_pct_text(tested, tutor_count)}) had a later recorded "
                f"test; {passed} ({_pct_text(passed, tutor_count)}) had a "
                "passing autograder check after the first tutor reply."
            ),
            caution=(
                "A passing autograder check does not establish learning or "
                "independent authorship."
            ),
        )
    )

    by_question: dict[str, list[StudentQuestionJourney]] = defaultdict(list)
    for journey in journeys:
        by_question[journey.question_id].append(journey)

    tutor_points: list[ComparisonPoint] = []
    attempt_points: list[ComparisonPoint] = []
    problem_points: list[ComparisonPoint] = []
    transfer_points: list[ComparisonPoint] = []
    no_change_points: list[ComparisonPoint] = []
    for question_id, items in sorted(by_question.items()):
        question_tutor = [item for item in items if item.tutor_used]
        question_tutor_count = len(question_tutor)
        tutor_rate = _percentage(question_tutor_count, len(items))
        tutor_points.append(
            ComparisonPoint(
                label=f"Question {question_id}",
                question_id=question_id,
                value=tutor_rate,
                display=(
                    f"{question_tutor_count} of {len(items)} "
                    f"({_pct_text(question_tutor_count, len(items))})"
                ),
            )
        )
        upper_attempts = _nearest_rank(
            [item.attempt_count for item in items], 0.75
        )
        attempt_points.append(
            ComparisonPoint(
                label=f"Question {question_id}",
                question_id=question_id,
                value=float(upper_attempts),
                display=(
                    f"75% of represented records had {upper_attempts} or "
                    "fewer recorded code runs"
                ),
            )
        )
        after_problem = sum(
            entry_context(item) == "after-problem" for item in question_tutor
        )
        problem_points.append(
            ComparisonPoint(
                label=f"Question {question_id}",
                question_id=question_id,
                value=_percentage(after_problem, question_tutor_count),
                display=(
                    f"{after_problem} of {question_tutor_count} "
                    f"({_pct_text(after_problem, question_tutor_count)})"
                ),
            )
        )
        transfers = sum(
            (response_use(item) or "").startswith("exact-transfer")
            for item in question_tutor
        )
        transfer_points.append(
            ComparisonPoint(
                label=f"Question {question_id}",
                question_id=question_id,
                value=_percentage(transfers, question_tutor_count),
                display=(
                    f"{transfers} of {question_tutor_count} "
                    f"({_pct_text(transfers, question_tutor_count)})"
                ),
            )
        )
        no_change = sum(
            response_use(item) == "no-code-change" for item in question_tutor
        )
        no_change_points.append(
            ComparisonPoint(
                label=f"Question {question_id}",
                question_id=question_id,
                value=_percentage(no_change, question_tutor_count),
                display=(
                    f"{no_change} of {question_tutor_count} "
                    f"({_pct_text(no_change, question_tutor_count)})"
                ),
            )
        )

    facts.extend(
        [
            _comparison_fact(
                fact_id="question_tutor_use",
                title="Tutor use by question",
                points=tutor_points,
                measure="share of records using the tutor",
            ),
            _comparison_fact(
                fact_id="question_attempts_upper_range",
                title="Recorded code runs by question",
                points=attempt_points,
                measure="upper-range code-run count",
                caution=(
                    "More code runs can reflect either productive iteration or "
                    "difficulty; the event log alone cannot distinguish them."
                ),
            ),
            _comparison_fact(
                fact_id="question_help_after_problem",
                title="Tutor use after recorded problems",
                points=problem_points,
                measure=(
                    "share of tutor use following an error or failed "
                    "autograder check"
                ),
            ),
            _comparison_fact(
                fact_id="question_exact_code_use",
                title="Exact tutor-code use by question",
                points=transfer_points,
                measure="share using exact tutor code",
                caution=(
                    "Exact transfer is established only by recorded exact-hash "
                    "provenance."
                ),
            ),
            _comparison_fact(
                fact_id="question_no_change_after_reply",
                title="No recorded code change after tutor replies",
                points=no_change_points,
                measure="share with no later recorded code change",
                caution=(
                    "No recorded code change does not show whether a student "
                    "read, understood, or used a conceptual explanation."
                ),
            ),
        ]
    )

    acts = Counter(
        act for journey in tutor_journeys for act in _interaction_acts(journey)
    )
    if acts:
        facts.append(
            ComputedFact(
                fact_id="synthetic_interaction_acts",
                title="Kinds of synthetic tutor questions",
                evidence="; ".join(
                    f"{count} of {tutor_count} tutor-using records "
                    f"({_pct_text(count, tutor_count)}) included {act.replace('-', ' ')}"
                    for act, count in acts.most_common()
                )
                + ".",
                caution=(
                    "These are generator-assigned synthetic scenario labels, "
                    "not measured findings about DSC 10 students."
                ),
            )
        )
    if classifications is not None:
        behavioral = {
            fact.fact_id: fact
            for fact in facts
            if fact.fact_id in {
                "class_after_tutor_reply",
                "class_after_reply_checks",
            }
        }
        return [
            *_classified_facts(classifications),
            *behavioral.values(),
        ]
    return facts


def build_briefing_packet(
    dataset: EpisodeDataset,
    classifications: ClassificationArtifact | None = None,
) -> BriefingPacket:
    if dataset.meta.source_kind != "synthetic":
        raise ValueError(
            "Detailed briefing packets are allowed only for synthetic data."
        )
    journeys = build_journeys(dataset.episodes)
    if (
        classifications is not None
        and classifications.bundle_id != dataset.meta.bundle_id
    ):
        raise ValueError("Classification bundle does not match the dataset.")
    classifications_by_id = {
        item.journey_id: item
        for item in (
            classifications.classifications if classifications else []
        )
    }
    represented_students = len({journey.student_key for journey in journeys})
    tutor_count = sum(journey.tutor_used for journey in journeys)
    lab_label = _lab_label(dataset)
    return BriefingPacket(
        bundle_id=dataset.meta.bundle_id,
        source_kind=dataset.meta.source_kind,
        lab_label=lab_label,
        cohort_statement=(
            f"This synthetic {lab_label} dataset represents "
            f"{represented_students} students across "
            f"{len({journey.question_id for journey in journeys})} questions. "
            f"It contains {len(journeys)} records of one student's work on "
            f"one question; {tutor_count} included at least one tutor question."
        ),
        classification_model=(classifications.model if classifications else None),
        classification_accuracy=(
            classifications.synthetic_accuracy if classifications else None
        ),
        facts=_build_facts(journeys, classifications),
        journeys=[
            _journey_evidence(
                journey,
                dataset,
                classifications_by_id.get(journey.journey_id),
            )
            for journey in journeys
        ],
        caveats=[
            (
                "This is synthetic scenario data. It does not estimate how "
                "real DSC 10 students behave."
            ),
            (
                "Recorded events describe actions, not intent, understanding, "
                "learning, or tutor effectiveness."
            ),
            (
                "A passing autograder check shows that recorded tests passed; "
                "it does not establish learning or independent authorship."
            ),
            *(
                [
                    "Gemini's student-question purpose classifications agreed "
                    f"with {classifications.synthetic_accuracy * 100:.1f}% of "
                    "the generator's synthetic labels."
                ]
                if classifications is not None
                and classifications.synthetic_accuracy is not None
                else []
            ),
        ],
    )


def build_prompt(packet: BriefingPacket) -> str:
    return """You are preparing a short briefing for a professor about one
SYNTHETIC programming-lab scenario.

Select three or four findings that are genuinely different from one another.
Prefer question contrasts and combinations that vary materially. Do not repeat
flat metrics merely because they are available.

Rules:
- Use only the supplied computed facts and synthetic journey evidence.
- Never claim student intent, dependence, cheating, understanding, learning,
  causality, or tutor effectiveness.
- Describe only recorded differences. Do not guess why students acted, even
  when a transcript sounds suggestive.
- Describe synthetic interaction acts only as generator-assigned labels. For
  example, write "a generator-labeled validation question was recorded," never
  a statement about what a student wanted.
- Do not use words such as suggests, indicates, implies, significant, likely,
  might, influence, or seeking in headlines or explanations.
- The interface will render all numbers from fact IDs. Do not put counts,
  percentages, durations, or attempt totals in your prose.
- Write plainly. Avoid jargon such as pathway, process cost, upper quartile,
  episode, and trajectory.
- Each finding must cite one to three valid fact IDs.
- Do not reuse a fact ID across findings.
- Prefer facts whose IDs begin with "classified_" because they combine what
  students asked with the recorded sequence around those messages.
- Each finding must cite one to three valid journey IDs that illustrate it.
- Examples must directly illustrate the finding, not serve as contrasts.
- The instructor prompt must be a question, not a recommendation or verdict.
- The two summary sentences should state what most stands out and what the
  professor can inspect next.
- Treat generator-assigned interaction acts as scenario assumptions, not real
  DSC 10 findings.

Use direct event-only sentence forms:
- "Tutor use was recorded before ..., after ..., and after ...."
- "The recorded share was highest for Question ... and lowest for Question ...."
- "Some records had ..., while other records had ...."
- "The professor can inspect the examples for the surrounding event sequence."

Return only the requested structured response.

DATA:
""" + _canonical_json(packet)


def _example(item: JourneyEvidence) -> BriefingExample:
    contextual_label = None
    if item.classified_purpose and item.entry_context:
        contextual_label = (
            f"{_PURPOSE_LABELS[item.classified_purpose].capitalize()} "
            f"{_CONTEXT_LABELS[item.entry_context]}"
        )
    return BriefingExample(
        journey_id=item.journey_id,
        evidence_episode_id=item.evidence_episode_id,
        question_id=item.question_id,
        summary=item.summary,
        contextual_label=contextual_label,
    )


def _comparison_extremes(
    fact: ComputedFact,
) -> tuple[str | None, str | None]:
    points = [point for point in fact.comparison if point.question_id]
    if not points:
        return None, None
    low = min(points, key=lambda point: (point.value, point.question_id or ""))
    high = max(points, key=lambda point: (point.value, point.question_id or ""))
    return low.question_id, high.question_id


def _supports_fact(
    journey: JourneyEvidence,
    fact: ComputedFact,
) -> bool:
    low_question, high_question = _comparison_extremes(fact)
    if fact.fact_id == "classified_contextual_patterns":
        return journey.classified_purpose is not None
    if fact.fact_id == "classified_validation_after_pass":
        return (
            journey.entry_context == "after-pass"
            and journey.classified_purpose == "validation"
        )
    if fact.fact_id == "classified_debugging_after_problem":
        return (
            journey.entry_context == "after-problem"
            and journey.classified_purpose == "debugging"
        )
    if fact.fact_id == "classified_direct_answer_requests":
        return (
            journey.entry_context == "before-attempt"
            and journey.classified_purpose == "direct-answer-request"
        )
    if fact.fact_id == "class_tutor_use":
        return True
    if fact.fact_id in {
        "class_when_tutor_used",
        "class_after_tutor_reply",
        "class_after_reply_checks",
        "synthetic_interaction_acts",
    }:
        return journey.tutor_used
    if fact.fact_id == "question_tutor_use":
        return (
            journey.question_id == high_question and journey.tutor_used
        ) or (
            journey.question_id == low_question and not journey.tutor_used
        )
    if fact.fact_id == "question_attempts_upper_range":
        return journey.question_id in {low_question, high_question}
    if fact.fact_id == "question_help_after_problem":
        return (
            journey.question_id == high_question
            and journey.entry_context == "after-problem"
        ) or (
            journey.question_id == low_question
            and journey.tutor_used
            and journey.entry_context != "after-problem"
        )
    if fact.fact_id == "question_exact_code_use":
        exact = (journey.response_use or "").startswith("exact-transfer")
        return (
            journey.question_id == high_question and exact
        ) or (
            journey.question_id == low_question
            and journey.tutor_used
            and not exact
        )
    if fact.fact_id == "question_no_change_after_reply":
        no_change = journey.response_use == "no-code-change"
        return (
            journey.question_id == high_question and no_change
        ) or (
            journey.question_id == low_question
            and journey.tutor_used
            and not no_change
        )
    return journey.question_id in fact.question_ids


def _grounded_examples(
    selected: list[JourneyEvidence],
    all_journeys: list[JourneyEvidence],
    facts: list[ComputedFact],
) -> list[BriefingExample]:
    def relevant(journey: JourneyEvidence) -> bool:
        return any(_supports_fact(journey, fact) for fact in facts)

    grounded = [journey for journey in selected if relevant(journey)]
    seen = {journey.journey_id for journey in grounded}
    high_questions = {
        high
        for fact in facts
        if (high := _comparison_extremes(fact)[1]) is not None
    }
    for journey in sorted(
        all_journeys,
        key=lambda item: (
            item.question_id not in high_questions,
            item.journey_id,
        ),
    ):
        if len(grounded) >= max(2, len(selected)):
            break
        if journey.journey_id not in seen and relevant(journey):
            grounded.append(journey)
            seen.add(journey.journey_id)
    return [_example(journey) for journey in grounded[:3]]


_UNSUPPORTED_CLAIM = re.compile(
    r"\b("
    r"suggest(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|impl(?:y|ies|ied|ying)|"
    r"statistically\s+significant|"
    r"significant(?:ly)?\s+(?:different|higher|lower|variation|relationship|association)|"
    r"var(?:y|ied|ies)\s+significantly|"
    r"likely|might|perhaps|influence(?:s|d|ing)?|"
    r"seek(?:s|ing)?\s+(?:validation|answers?|solutions?|alternatives?|confirmation)|"
    r"intent(?:ion)?|depend(?:s|ed|ence|ent|ing)?|"
    r"cheat(?:s|ed|ing)?|student\s+understanding|student\s+learning|"
    r"students?\s+(?:do\s+not\s+|did\s+not\s+|can(?:not)?\s+)?understand|"
    r"students?\s+(?:do\s+not\s+|did\s+not\s+|can(?:not)?\s+)?learn|"
    r"caus(?:e|es|ed|al|ality)|productive|unproductive"
    r")\b",
    flags=re.IGNORECASE,
)


def _validate_generated_language(draft: BriefingDraft) -> None:
    checked = [
        *draft.summary_sentences,
        *(
            text
            for finding in draft.findings
            for text in (finding.headline, finding.explanation)
        ),
    ]
    for text in checked:
        match = _UNSUPPORTED_CLAIM.search(text)
        if match:
            raise ValueError(
                "Gemini used unsupported claim language "
                f"{match.group(0)!r} in: {text}"
            )


def resolve_draft(
    packet: BriefingPacket,
    draft: BriefingDraft,
    *,
    model: str,
    packet_hash: str,
    prompt_hash: str,
    generated_at: datetime,
) -> BriefingArtifact:
    facts = {fact.fact_id: fact for fact in packet.facts}
    journeys = {journey.journey_id: journey for journey in packet.journeys}
    resolved: list[ResolvedFinding] = []
    used_fact_ids: set[str] = set()
    _validate_generated_language(draft)
    for finding in draft.findings:
        unknown_facts = set(finding.fact_ids) - facts.keys()
        unknown_journeys = set(finding.journey_ids) - journeys.keys()
        if unknown_facts:
            raise ValueError(
                "Gemini returned unknown fact IDs: "
                + ", ".join(sorted(unknown_facts))
            )
        if unknown_journeys:
            raise ValueError(
                "Gemini returned unknown journey IDs: "
                + ", ".join(sorted(unknown_journeys))
            )
        repeated_facts = set(finding.fact_ids).intersection(used_fact_ids)
        if repeated_facts:
            raise ValueError(
                "Gemini reused fact IDs across findings: "
                + ", ".join(sorted(repeated_facts))
            )
        used_fact_ids.update(finding.fact_ids)
        selected_facts = [facts[fact_id] for fact_id in finding.fact_ids]
        selected_journeys = [
            journeys[journey_id] for journey_id in finding.journey_ids
        ]
        resolved.append(
            ResolvedFinding(
                headline=finding.headline,
                explanation=finding.explanation,
                instructor_prompt=finding.instructor_prompt,
                facts=selected_facts,
                examples=_grounded_examples(
                    selected_journeys,
                    packet.journeys,
                    selected_facts,
                ),
            )
        )
    return BriefingArtifact(
        bundle_id=packet.bundle_id,
        source_kind=packet.source_kind,
        lab_label=packet.lab_label,
        cohort_statement=packet.cohort_statement,
        generation_mode="gemini",
        fallback_reason=None,
        model=model,
        generated_at=generated_at,
        packet_hash=packet_hash,
        prompt_hash=prompt_hash,
        summary_sentences=draft.summary_sentences,
        findings=resolved,
        caveats=packet.caveats,
    )


def deterministic_fallback(
    packet: BriefingPacket,
    *,
    packet_hash: str | None = None,
    prompt_hash: str | None = None,
    reason: str | None = None,
) -> BriefingArtifact:
    facts = {fact.fact_id: fact for fact in packet.facts}
    preferred = [
        "classified_contextual_patterns",
        "classified_validation_after_pass",
        "classified_debugging_after_problem",
        "classified_direct_answer_requests",
        "question_attempts_upper_range",
        "question_help_after_problem",
        "question_tutor_use",
        "question_exact_code_use",
    ]
    selected = [facts[fact_id] for fact_id in preferred if fact_id in facts][:3]
    tutor_examples = [
        journey
        for journey in packet.journeys
        if journey.tutor_questions > 0
    ]
    findings = []
    for index, fact in enumerate(selected):
        examples = [
            _example(item)
            for item in tutor_examples[index * 2 : index * 2 + 2]
        ]
        findings.append(
            ResolvedFinding(
                headline=fact.title,
                explanation=(
                    "The recorded values differ across questions. The computed "
                    "evidence below shows the comparison without assigning a "
                    "cause."
                ),
                instructor_prompt=(
                    "Which question should be inspected in more detail?"
                ),
                facts=[fact],
                examples=examples,
            )
        )
    prompt = build_prompt(packet)
    return BriefingArtifact(
        bundle_id=packet.bundle_id,
        source_kind=packet.source_kind,
        lab_label=packet.lab_label,
        cohort_statement=packet.cohort_statement,
        generation_mode="deterministic-fallback",
        fallback_reason=reason,
        model=None,
        generated_at=None,
        packet_hash=packet_hash or _hash(_canonical_json(packet)),
        prompt_hash=prompt_hash or _hash(prompt),
        summary_sentences=[
            (
                f"This synthetic {packet.lab_label} dataset contains several "
                "recorded differences between questions."
            ),
            (
                "The findings below identify where the event data supports a "
                "closer look without claiming why the differences occurred."
            ),
        ],
        findings=findings,
        caveats=packet.caveats,
    )


def generate_briefing(
    dataset: EpisodeDataset,
    generate: DraftGenerator,
    *,
    classifications: ClassificationArtifact | None = None,
    model: str = DEFAULT_MODEL,
    now: datetime | None = None,
) -> BriefingArtifact:
    packet = build_briefing_packet(dataset, classifications)
    packet_hash = _hash(_canonical_json(packet))
    prompt = build_prompt(packet)
    prompt_hash = _hash(prompt)
    try:
        draft = generate(prompt)
        return resolve_draft(
            packet,
            draft,
            model=model,
            packet_hash=packet_hash,
            prompt_hash=prompt_hash,
            generated_at=now or datetime.now(timezone.utc),
        )
    except (ValidationError, ValueError, KeyError) as exc:
        return deterministic_fallback(
            packet,
            packet_hash=packet_hash,
            prompt_hash=prompt_hash,
            reason=f"{type(exc).__name__}: {exc}",
        )


def _gemini_schema(value: Any) -> Any:
    """Remove JSON Schema keywords unsupported by Gemini's schema endpoint."""
    if isinstance(value, dict):
        return {
            key: _gemini_schema(item)
            for key, item in value.items()
            if key != "additionalProperties"
        }
    if isinstance(value, list):
        return [_gemini_schema(item) for item in value]
    return value


def gemini_generator(api_key: str, model: str) -> DraftGenerator:
    from google import genai

    client = genai.Client(api_key=api_key)

    def generate(prompt: str) -> BriefingDraft:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": _gemini_schema(
                    BriefingDraft.model_json_schema()
                ),
                "temperature": 0,
            },
        )
        return BriefingDraft.model_validate_json(response.text)

    return generate


def load_cached_briefing(
    path: Path,
    dataset: EpisodeDataset,
    classifications: ClassificationArtifact | None = None,
) -> BriefingArtifact | None:
    if not path.is_file() or dataset.meta.source_kind != "synthetic":
        return None
    try:
        artifact = BriefingArtifact.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        packet = build_briefing_packet(dataset, classifications)
    except (OSError, ValidationError, ValueError):
        return None
    expected_hash = _hash(_canonical_json(packet))
    expected_prompt_hash = _hash(build_prompt(packet))
    if (
        artifact.bundle_id != dataset.meta.bundle_id
        or artifact.packet_hash != expected_hash
        or artifact.prompt_hash != expected_prompt_hash
        or artifact.source_kind != dataset.meta.source_kind
    ):
        return None
    return artifact


def briefing_for_dataset(
    dataset: EpisodeDataset,
    path: Path | None = None,
    classifications: ClassificationArtifact | None = None,
) -> BriefingArtifact:
    if path is not None:
        cached = load_cached_briefing(path, dataset, classifications)
        if cached is not None:
            return cached
    if dataset.meta.source_kind != "synthetic":
        raise ValueError(
            "Professor briefing currently supports synthetic datasets only."
        )
    return deterministic_fallback(
        build_briefing_packet(dataset, classifications)
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate one evidence-backed Gemini briefing."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--source-kind",
        choices=("synthetic",),
        default="synthetic",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--classifications",
        type=Path,
        help=(
            "student-question classifications; defaults to "
            "classifications.json beside the event log"
        ),
    )
    parser.add_argument("--dotenv", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"input JSONL does not exist: {args.input}")
    if args.dotenv is not None:
        if not args.dotenv.is_file():
            parser.error(f"dotenv file does not exist: {args.dotenv}")
        load_dotenv(args.dotenv, override=False)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        parser.error("GEMINI_API_KEY is not configured")

    dataset = build_dataset(args.input, source_kind=args.source_kind)
    classification_path = (
        args.classifications
        or args.input.parent / DEFAULT_CLASSIFICATION_FILENAME
    )
    classifications = load_cached_classifications(
        classification_path,
        dataset,
    )
    output = args.output or args.input.parent / DEFAULT_FILENAME
    if not args.force:
        cached = load_cached_briefing(output, dataset, classifications)
        if cached is not None and cached.model == args.model:
            print(f"Reused cached briefing: {output}")
            return

    artifact = generate_briefing(
        dataset,
        gemini_generator(api_key, args.model),
        classifications=classifications,
        model=args.model,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        artifact.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {artifact.generation_mode} briefing with "
        f"{len(artifact.findings)} findings: {output}"
    )
    if artifact.fallback_reason:
        print(f"Fallback reason: {artifact.fallback_reason}")


if __name__ == "__main__":
    main()
