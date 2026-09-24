"""Professor lab overview: computed question stats plus short Gemini notes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.episodes.models import EpisodeDataset, SourceKind
from src.ingest.episode_events import build_dataset
from src.synthetic.config import QUESTIONS
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

OVERVIEW_SCHEMA_VERSION = "1.0.0"
DEFAULT_FILENAME = "overview.json"
DEFAULT_MODEL = "gemini-2.5-flash"

PURPOSE_LABELS = {
    "validation": "validation",
    "debugging": "debugging",
    "conceptual": "conceptual help",
    "syntax": "syntax help",
    "direct-answer-request": "a direct answer",
    "assignment-clarification": "assignment clarification",
    "mixed": "mixed help",
    "unclear": "unclear help",
}
CONTEXT_LABELS = {
    "before-attempt": "before editing or running code",
    "after-attempt": "after editing or running code",
    "after-problem": "after an error or failed autograder check",
    "after-pass": "after passing the autograder",
}
QUESTION_PROMPTS = {item.question_id: item.prompt for item in QUESTIONS}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CountDisplay(StrictModel):
    numerator: int
    denominator: int
    display: str
    value: float


class PatternCount(StrictModel):
    label: str
    context: str | None = None
    purpose: str | None = None
    count: int
    display: str


class QuestionExample(StrictModel):
    journey_id: str
    evidence_episode_id: str
    summary: str
    contextual_label: str | None = None


class QuestionOverview(StrictModel):
    question_id: str
    prompt: str | None
    one_line: str
    student_count: int
    tutor_use: CountDisplay
    passed: CountDisplay
    median_active_seconds: int
    median_active_display: str
    median_tutor_queries: float
    median_errors: float
    most_common_purpose: str | None
    most_common_purpose_label: str
    top_patterns: list[PatternCount]
    examples: list[QuestionExample]


class NotableQuestion(StrictModel):
    question_id: str
    reason: str


class LabOverviewArtifact(StrictModel):
    schema_version: Literal["1.0.0"] = OVERVIEW_SCHEMA_VERSION
    bundle_id: str
    source_kind: SourceKind
    lab_label: str
    closed_summary: str
    cohort_statement: str
    tutor_use: CountDisplay
    passed: CountDisplay
    most_common_pattern: str | None
    notable_questions: list[NotableQuestion]
    notes: list[str]
    questions: list[QuestionOverview]
    generation_mode: Literal["gemini", "deterministic-fallback"]
    fallback_reason: str | None = None
    model: str | None
    generated_at: datetime | None
    packet_hash: str
    prompt_hash: str
    caveats: list[str]


class DraftQuestionLine(StrictModel):
    question_id: str
    one_line: str = Field(min_length=8, max_length=90)


class OverviewDraft(StrictModel):
    notes: list[str] = Field(min_length=3, max_length=5)
    question_summaries: list[DraftQuestionLine] = Field(min_length=1)


class _ComputedQuestion(StrictModel):
    question_id: str
    prompt: str | None
    student_count: int
    tutor_use: CountDisplay
    passed: CountDisplay
    median_active_seconds: int
    median_active_display: str
    median_tutor_queries: float
    median_errors: float
    most_common_purpose: str | None
    most_common_purpose_label: str
    top_patterns: list[PatternCount]
    examples: list[QuestionExample]


class _ComputedPacket(StrictModel):
    bundle_id: str
    source_kind: SourceKind
    lab_label: str
    closed_summary: str
    cohort_statement: str
    tutor_use: CountDisplay
    passed: CountDisplay
    most_common_pattern: str | None
    notable_questions: list[NotableQuestion]
    questions: list[_ComputedQuestion]
    caveats: list[str]


DraftGenerator = Callable[[str], OverviewDraft]


def _canonical(value: BaseModel | dict[str, Any]) -> str:
    raw = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pct(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _count(numerator: int, denominator: int) -> CountDisplay:
    return CountDisplay(
        numerator=numerator,
        denominator=denominator,
        value=_pct(numerator, denominator),
        display=f"{numerator} of {denominator} ({_pct(numerator, denominator) * 100:.0f}%)",
    )


def _median(values: list[int | float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def _format_seconds(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} sec"
    minutes, remainder = divmod(seconds, 60)
    if remainder == 0:
        return f"{minutes} min"
    return f"{minutes} min {remainder} sec"


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


def _error_count(journey: StudentQuestionJourney) -> int:
    return sum(
        event.event_type == "cell_error"
        or (
            event.event_type == "autograder_completed"
            and event.payload.get("success") is False
        )
        for event in journey.events
    )


def _purpose_label(purpose: str | None) -> str:
    if purpose is None:
        return "no classified tutor questions"
    return PURPOSE_LABELS.get(purpose, purpose.replace("-", " "))


def _pattern_label(context: str | None, purpose: str | None) -> str:
    purpose_text = _purpose_label(purpose)
    if context is None:
        return purpose_text
    return f"{purpose_text} {CONTEXT_LABELS[context]}"


def _examples(
    journeys: list[StudentQuestionJourney],
    classifications: dict[str, StudentQuestionClassification],
    *,
    purpose: str | None = None,
    context: str | None = None,
    limit: int = 2,
) -> list[QuestionExample]:
    selected = []
    for journey in journeys:
        item = classifications.get(journey.journey_id)
        if purpose is not None and (
            item is None or item.primary_purpose != purpose
        ):
            continue
        if context is not None and entry_context(journey) != context:
            continue
        selected.append(journey)
        if len(selected) >= limit:
            break
    if not selected:
        selected = [journey for journey in journeys if journey.tutor_used][:limit]
    examples = []
    for journey in selected:
        item = classifications.get(journey.journey_id)
        context_id = entry_context(journey)
        if journey.tutor_used:
            summary = (
                f"The student {_entry_phrase(context_id)}; "
                f"{_response_phrase(response_use(journey))}."
            )
        else:
            summary = "The student did not use the tutor for this question."
        examples.append(
            QuestionExample(
                journey_id=journey.journey_id,
                evidence_episode_id=evidence_episode(journey).episode_id,
                summary=summary,
                contextual_label=(
                    _pattern_label(
                        item.sequence_context if item else context_id,
                        item.primary_purpose if item else None,
                    )
                    if journey.tutor_used
                    else None
                ),
            )
        )
    return examples


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


def _question_overview(
    question_id: str,
    journeys: list[StudentQuestionJourney],
    classifications: dict[str, StudentQuestionClassification],
) -> _ComputedQuestion:
    tutor = [journey for journey in journeys if journey.tutor_used]
    classified = [
        classifications[journey.journey_id]
        for journey in tutor
        if journey.journey_id in classifications
    ]
    purpose_counts = Counter(item.primary_purpose for item in classified)
    most_common_purpose = (
        purpose_counts.most_common(1)[0][0] if purpose_counts else None
    )
    pattern_counts = Counter(
        (item.sequence_context, item.primary_purpose) for item in classified
    )
    top_patterns = [
        PatternCount(
            label=_pattern_label(context, purpose),
            context=context,
            purpose=purpose,
            count=count,
            display=f"{count} of {len(tutor)} ({_pct(count, len(tutor)) * 100:.0f}%)",
        )
        for (context, purpose), count in pattern_counts.most_common(5)
    ]
    median_seconds = int(
        round(_median([journey.active_duration_ms / 1000 for journey in journeys]))
    )
    return _ComputedQuestion(
        question_id=question_id,
        prompt=QUESTION_PROMPTS.get(question_id),
        student_count=len(journeys),
        tutor_use=_count(len(tutor), len(journeys)),
        passed=_count(
            sum(journey.eventually_passed for journey in journeys),
            len(journeys),
        ),
        median_active_seconds=median_seconds,
        median_active_display=_format_seconds(median_seconds),
        median_tutor_queries=_median(
            [journey.tutor_turn_count for journey in tutor] or [0]
        ),
        median_errors=_median([_error_count(journey) for journey in journeys]),
        most_common_purpose=most_common_purpose,
        most_common_purpose_label=_purpose_label(most_common_purpose),
        top_patterns=top_patterns,
        examples=_examples(
            tutor or journeys,
            classifications,
            purpose=most_common_purpose,
            limit=2,
        ),
    )


def _notable_questions(questions: list[_ComputedQuestion]) -> list[NotableQuestion]:
    if not questions:
        return []
    by_errors = max(questions, key=lambda item: (item.median_errors, item.question_id))
    by_debug = max(
        questions,
        key=lambda item: (
            next(
                (
                    pattern.count
                    for pattern in item.top_patterns
                    if pattern.purpose == "debugging"
                ),
                0,
            ),
            item.question_id,
        ),
    )
    notable = [
        NotableQuestion(
            question_id=by_errors.question_id,
            reason="highest median recorded errors",
        )
    ]
    if by_debug.question_id != by_errors.question_id:
        notable.append(
            NotableQuestion(
                question_id=by_debug.question_id,
                reason="most classified debugging questions after recorded problems",
            )
        )
    return notable


def build_overview_packet(
    dataset: EpisodeDataset,
    classifications: ClassificationArtifact | None = None,
) -> _ComputedPacket:
    if dataset.meta.source_kind != "synthetic":
        raise ValueError("Lab overview currently supports synthetic datasets only.")
    journeys = build_journeys(dataset.episodes)
    classified = {
        item.journey_id: item
        for item in (classifications.classifications if classifications else [])
    }
    by_question: dict[str, list[StudentQuestionJourney]] = defaultdict(list)
    for journey in journeys:
        by_question[journey.question_id].append(journey)
    questions = [
        _question_overview(question_id, items, classified)
        for question_id, items in sorted(by_question.items())
    ]
    tutor_count = sum(journey.tutor_used for journey in journeys)
    passed_count = sum(journey.eventually_passed for journey in journeys)
    pattern_counts = Counter(
        (item.sequence_context, item.primary_purpose)
        for item in classified.values()
    )
    top_pattern = pattern_counts.most_common(1)[0] if pattern_counts else None
    lab_label = _lab_label(dataset)
    student_count = len({journey.student_key for journey in journeys})
    tutor_use = _count(tutor_count, len(journeys))
    return _ComputedPacket(
        bundle_id=dataset.meta.bundle_id,
        source_kind=dataset.meta.source_kind,
        lab_label=lab_label,
        closed_summary=(
            f"{student_count} students · {len(questions)} questions · "
            f"{tutor_use.display} used the tutor"
        ),
        cohort_statement=(
            f"This synthetic {lab_label} dataset represents {student_count} "
            f"students across {len(questions)} questions."
        ),
        tutor_use=tutor_use,
        passed=_count(passed_count, len(journeys)),
        most_common_pattern=(
            _pattern_label(*top_pattern[0]) if top_pattern else None
        ),
        notable_questions=_notable_questions(questions),
        questions=questions,
        caveats=[
            "This is synthetic scenario data. It does not estimate how real DSC 10 students behave.",
            "Recorded events describe actions, not intent, understanding, learning, or tutor effectiveness.",
            "Gemini notes organize the computed patterns. They do not supply the displayed numbers.",
        ],
    )


def build_prompt(packet: _ComputedPacket) -> str:
    compact = {
        "lab_label": packet.lab_label,
        "tutor_use": packet.tutor_use.display,
        "passed": packet.passed.display,
        "most_common_pattern": packet.most_common_pattern,
        "notable_questions": [item.model_dump() for item in packet.notable_questions],
        "questions": [
            {
                "question_id": item.question_id,
                "prompt": item.prompt,
                "tutor_use": item.tutor_use.display,
                "passed": item.passed.display,
                "median_time": item.median_active_display,
                "median_tutor_queries": item.median_tutor_queries,
                "median_errors": item.median_errors,
                "most_common_purpose": item.most_common_purpose_label,
                "top_patterns": [pattern.label for pattern in item.top_patterns],
            }
            for item in packet.questions
        ],
    }
    return """Write a concise professor overview of one SYNTHETIC lab.

Return:
- 3 to 5 short important-notes bullets about the whole lab.
- One 8-90 character line for every supplied question_id.

Rules:
- Use only the supplied computed facts.
- Do not put counts, percentages, times, or other numbers in notes or one-liners.
- Do not claim student intent, learning, cheating, dependence, or tutor effectiveness.
- Do not use suggests, indicates, implies, significant, likely, might, or seeking.
- Notes should name the important patterns plainly, including when students used
  the tutor and what they asked about.
- Each question one-liner should start like "Students often..." or "Students mostly..."
  and name the most common recorded pattern for that question.
- Write one summary for every question_id. Do not add extra IDs.

DATA:
""" + _canonical(compact)


_UNSUPPORTED = re.compile(
    r"\b("
    r"suggest(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|impl(?:y|ies|ied|ying)|"
    r"statistically\s+significant|"
    r"significant(?:ly)?\s+(?:different|higher|lower|variation)|"
    r"likely|might|perhaps|influence(?:s|d|ing)?|"
    r"seek(?:s|ing)?\s+(?:validation|answers?|solutions?)|"
    r"cheat(?:s|ed|ing)?|student\s+understanding|student\s+learning"
    r")\b",
    flags=re.IGNORECASE,
)
_NUMBER = re.compile(r"\d")


def _validate_draft(packet: _ComputedPacket, draft: OverviewDraft) -> None:
    expected = {item.question_id for item in packet.questions}
    returned = [item.question_id for item in draft.question_summaries]
    if len(returned) != len(set(returned)):
        raise ValueError("Gemini returned duplicate question IDs")
    if set(returned) != expected:
        raise ValueError("Gemini returned mismatched question IDs")
    question_ids = sorted(expected, key=len, reverse=True)
    for text in [*draft.notes, *(item.one_line for item in draft.question_summaries)]:
        match = _UNSUPPORTED.search(text)
        if match:
            raise ValueError(
                f"Gemini used unsupported claim language {match.group(0)!r} in: {text}"
            )
        stripped = text
        for question_id in question_ids:
            stripped = stripped.replace(f"Question {question_id}", "QUESTION")
            stripped = stripped.replace(question_id, "QUESTION")
        if _NUMBER.search(stripped):
            raise ValueError(f"Gemini put a number in overview text: {text}")


def _fallback_line(question: _ComputedQuestion) -> str:
    if question.top_patterns:
        return f"Students often recorded {question.top_patterns[0].label}."
    if question.most_common_purpose:
        return f"Students mostly asked for {question.most_common_purpose_label}."
    return "Students mostly worked without the tutor."


def _fallback_notes(packet: _ComputedPacket) -> list[str]:
    notes = []
    if packet.most_common_pattern:
        notes.append(
            f"The most common tutor-use pattern was {packet.most_common_pattern}."
        )
    if packet.notable_questions:
        notes.append(
            "Recorded errors were highest on Question "
            + " and Question ".join(item.question_id for item in packet.notable_questions)
            + "."
        )
    notes.append(
        "Some students asked for a direct answer before editing or running code."
    )
    notes.append(
        "These notes describe the synthetic lab only; they are not findings about real students."
    )
    return notes[:5]


def resolve_draft(
    packet: _ComputedPacket,
    draft: OverviewDraft,
    *,
    model: str,
    packet_hash: str,
    prompt_hash: str,
    generated_at: datetime,
) -> LabOverviewArtifact:
    _validate_draft(packet, draft)
    lines = {
        item.question_id: item.one_line for item in draft.question_summaries
    }
    return LabOverviewArtifact(
        bundle_id=packet.bundle_id,
        source_kind=packet.source_kind,
        lab_label=packet.lab_label,
        closed_summary=packet.closed_summary,
        cohort_statement=packet.cohort_statement,
        tutor_use=packet.tutor_use,
        passed=packet.passed,
        most_common_pattern=packet.most_common_pattern,
        notable_questions=packet.notable_questions,
        notes=draft.notes,
        questions=[
            QuestionOverview(
                **item.model_dump(),
                one_line=lines[item.question_id],
            )
            for item in packet.questions
        ],
        generation_mode="gemini",
        model=model,
        generated_at=generated_at,
        packet_hash=packet_hash,
        prompt_hash=prompt_hash,
        caveats=packet.caveats,
    )


def deterministic_fallback(
    packet: _ComputedPacket,
    *,
    packet_hash: str | None = None,
    prompt_hash: str | None = None,
    reason: str | None = None,
) -> LabOverviewArtifact:
    return LabOverviewArtifact(
        bundle_id=packet.bundle_id,
        source_kind=packet.source_kind,
        lab_label=packet.lab_label,
        closed_summary=packet.closed_summary,
        cohort_statement=packet.cohort_statement,
        tutor_use=packet.tutor_use,
        passed=packet.passed,
        most_common_pattern=packet.most_common_pattern,
        notable_questions=packet.notable_questions,
        notes=_fallback_notes(packet),
        questions=[
            QuestionOverview(**item.model_dump(), one_line=_fallback_line(item))
            for item in packet.questions
        ],
        generation_mode="deterministic-fallback",
        fallback_reason=reason,
        model=None,
        generated_at=None,
        packet_hash=packet_hash or _hash(_canonical(packet)),
        prompt_hash=prompt_hash or _hash(build_prompt(packet)),
        caveats=packet.caveats,
    )


def generate_overview(
    dataset: EpisodeDataset,
    generate: DraftGenerator,
    *,
    classifications: ClassificationArtifact | None = None,
    model: str = DEFAULT_MODEL,
    now: datetime | None = None,
) -> LabOverviewArtifact:
    packet = build_overview_packet(dataset, classifications)
    packet_hash = _hash(_canonical(packet))
    prompt = build_prompt(packet)
    prompt_hash = _hash(prompt)
    try:
        return resolve_draft(
            packet,
            generate(prompt),
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

    def generate(prompt: str) -> OverviewDraft:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": _gemini_schema(OverviewDraft.model_json_schema()),
                "temperature": 0,
            },
        )
        return OverviewDraft.model_validate_json(response.text)

    return generate


def load_cached_overview(
    path: Path,
    dataset: EpisodeDataset,
    classifications: ClassificationArtifact | None = None,
) -> LabOverviewArtifact | None:
    if not path.is_file() or dataset.meta.source_kind != "synthetic":
        return None
    try:
        artifact = LabOverviewArtifact.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        packet = build_overview_packet(dataset, classifications)
    except (OSError, ValidationError, ValueError):
        return None
    if (
        artifact.bundle_id != dataset.meta.bundle_id
        or artifact.packet_hash != _hash(_canonical(packet))
        or artifact.prompt_hash != _hash(build_prompt(packet))
        or artifact.source_kind != dataset.meta.source_kind
    ):
        return None
    return artifact


def overview_for_dataset(
    dataset: EpisodeDataset,
    path: Path | None = None,
    classifications: ClassificationArtifact | None = None,
) -> LabOverviewArtifact:
    if path is not None:
        cached = load_cached_overview(path, dataset, classifications)
        if cached is not None:
            return cached
    return deterministic_fallback(build_overview_packet(dataset, classifications))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate the concise professor lab overview."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-kind", choices=("synthetic",), default="synthetic")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--classifications", type=Path)
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
    classifications = load_cached_classifications(
        args.classifications
        or args.input.parent / DEFAULT_CLASSIFICATION_FILENAME,
        dataset,
    )
    output = args.output or args.input.parent / DEFAULT_FILENAME
    if not args.force:
        cached = load_cached_overview(output, dataset, classifications)
        if cached is not None and cached.model == args.model:
            print(f"Reused cached overview: {output}")
            return

    artifact = generate_overview(
        dataset,
        gemini_generator(api_key, args.model),
        classifications=classifications,
        model=args.model,
    )
    output.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {artifact.generation_mode} overview with "
        f"{len(artifact.notes)} notes and {len(artifact.questions)} questions: "
        f"{output}"
    )
    if artifact.fallback_reason:
        print(f"Fallback reason: {artifact.fallback_reason}")


if __name__ == "__main__":
    main()
