"""Contextual classification for one student's work on one question."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from src.episodes.models import EpisodeDataset
from src.ingest.episode_events import build_dataset
from src.viewer.insights import StudentQuestionJourney, build_journeys

CLASSIFICATION_SCHEMA_VERSION = "1.0.0"
DEFAULT_CLASSIFICATION_FILENAME = "classifications.json"
DEFAULT_MODEL = "gemini-2.5-flash"

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
Confidence = Literal["high", "medium", "low"]
SequenceContext = Literal[
    "before-attempt",
    "after-attempt",
    "after-problem",
    "after-pass",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassificationInput(StrictModel):
    journey_id: str
    question_id: str
    sequence_context: SequenceContext
    event_sequence: list[str]
    conversation: list[str]


class ClassificationDraftItem(StrictModel):
    journey_id: str
    primary_purpose: Purpose
    confidence: Confidence


class ClassificationDraft(StrictModel):
    records: list[ClassificationDraftItem] = Field(min_length=1)


class StudentQuestionClassification(StrictModel):
    journey_id: str
    question_id: str
    sequence_context: SequenceContext
    primary_purpose: Purpose
    confidence: Confidence
    synthetic_ground_truth: list[Purpose]
    matches_synthetic_ground_truth: bool | None


class ClassificationArtifact(StrictModel):
    schema_version: Literal["1.0.0"] = CLASSIFICATION_SCHEMA_VERSION
    bundle_id: str
    source_kind: str
    model: str
    generated_at: datetime
    batch_size: int | None
    input_hash: str
    prompt_hash: str
    classifications: list[StudentQuestionClassification]
    synthetic_accuracy: float | None


DraftGenerator = Callable[[str], ClassificationDraft]


def _canonical(value: BaseModel | dict[str, Any]) -> str:
    raw = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _nearest_sequence_context(
    journey: StudentQuestionJourney,
) -> SequenceContext:
    query_index = next(
        index
        for index, event in enumerate(journey.events)
        if event.event_type == "tutor_query"
    )
    before = journey.events[:query_index]
    for event in reversed(before):
        if event.event_type == "autograder_completed":
            return (
                "after-pass"
                if event.payload.get("success") is True
                else "after-problem"
            )
        if event.event_type == "cell_error":
            return "after-problem"
        if event.event_type in {"cell_edit", "cell_execution_started"}:
            return "after-attempt"
    return "before-attempt"


def _event_label(event: Any) -> str | None:
    if event.event_type == "autograder_completed":
        return (
            "passed autograder"
            if event.payload.get("success") is True
            else "failed autograder"
        )
    return {
        "cell_edit": "edited code",
        "cell_execution_started": "ran code",
        "cell_error": "code produced an error",
        "tutor_query": "asked tutor",
        "tutor_response": "received tutor reply",
        "tutor_code_inserted": "used exact tutor code",
        "notebook_paste": "pasted into notebook",
    }.get(event.event_type)


def _conversation(
    dataset: EpisodeDataset,
    journey: StudentQuestionJourney,
) -> list[str]:
    conversation_ids = list(
        dict.fromkeys(
            conversation_id
            for episode in journey.episodes
            for conversation_id in episode.conversation_ids
        )
    )
    return [
        f"{turn.role}: {turn.text}"
        for conversation_id in conversation_ids
        for turn in dataset.transcripts.get(conversation_id, [])
    ]


def build_classification_inputs(
    dataset: EpisodeDataset,
) -> list[ClassificationInput]:
    return [
        ClassificationInput(
            journey_id=journey.journey_id,
            question_id=journey.question_id,
            sequence_context=_nearest_sequence_context(journey),
            event_sequence=[
                label
                for event in journey.events
                if (label := _event_label(event)) is not None
            ],
            conversation=_conversation(dataset, journey),
        )
        for journey in build_journeys(dataset.episodes)
        if journey.tutor_used
    ]


def build_classification_prompt(records: list[ClassificationInput]) -> str:
    return """Classify each complete student-question record. Each record is
one student's work on one assignment question and may contain multiple tutor
messages.

Choose one primary purpose for the record:
- validation: asks whether an answer, result, or understanding is correct
- debugging: asks to diagnose an error, failure, or incorrect result
- conceptual: asks for an explanation of an idea or approach
- syntax: asks how to write or fix language syntax
- direct-answer-request: asks for the answer or executable solution
- assignment-clarification: asks what the prompt, requirement, or term means
- mixed: contains multiple purposes with no clear primary purpose
- unclear: the available language does not support a purpose

Use the conversation and event sequence together. Sequence context says what
was recorded immediately before the first tutor message; it does not by itself
prove the purpose. Return exactly one result for every supplied journey_id.
Do not add or alter IDs.

RECORDS:
""" + _canonical({"records": [record.model_dump(mode="json") for record in records]})


def _input_hash(records: list[ClassificationInput]) -> str:
    return _digest(
        _canonical(
            {"records": [record.model_dump(mode="json") for record in records]}
        )
    )


def _prompts(
    records: list[ClassificationInput],
    batch_size: int | None,
) -> list[str]:
    if batch_size is None:
        return [build_classification_prompt(records)]
    return [
        build_classification_prompt(records[index : index + batch_size])
        for index in range(0, len(records), batch_size)
    ]


def _prompt_hash(
    records: list[ClassificationInput],
    batch_size: int | None,
) -> str:
    return _digest(_canonical({"prompts": _prompts(records, batch_size)}))


def _ground_truth(journey: StudentQuestionJourney) -> list[Purpose]:
    mapping: dict[str, Purpose] = {
        "validation": "validation",
        "debugging-request": "debugging",
        "conceptual-clarification": "conceptual",
        "syntax-help": "syntax",
        "direct-request": "direct-answer-request",
        "assignment-reference": "assignment-clarification",
    }
    return sorted(
        {
            mapping[str(event.payload["synthetic_message_act"])]
            for event in journey.events
            if event.event_type == "tutor_query"
            and event.payload.get("synthetic_ground_truth") is True
            and event.payload.get("synthetic_message_act") in mapping
        }
    )


def classify_dataset(
    dataset: EpisodeDataset,
    generate: DraftGenerator,
    *,
    batch_size: int | None = None,
    model: str = DEFAULT_MODEL,
    now: datetime | None = None,
) -> ClassificationArtifact:
    inputs = build_classification_inputs(dataset)
    generated_records = [
        record
        for prompt in _prompts(inputs, batch_size)
        for record in generate(prompt).records
    ]
    draft = ClassificationDraft(records=generated_records)
    expected = {record.journey_id for record in inputs}
    returned = [record.journey_id for record in draft.records]
    if len(returned) != len(set(returned)):
        raise ValueError("Gemini returned duplicate journey IDs")
    if set(returned) != expected:
        missing = sorted(expected - set(returned))
        unknown = sorted(set(returned) - expected)
        raise ValueError(
            f"Gemini returned mismatched IDs; missing={missing}, unknown={unknown}"
        )

    inputs_by_id = {record.journey_id: record for record in inputs}
    journeys_by_id = {
        journey.journey_id: journey
        for journey in build_journeys(dataset.episodes)
        if journey.tutor_used
    }
    classifications: list[StudentQuestionClassification] = []
    matches: list[bool] = []
    for item in sorted(draft.records, key=lambda record: record.journey_id):
        record = inputs_by_id[item.journey_id]
        truth = _ground_truth(journeys_by_id[item.journey_id])
        matched = item.primary_purpose in truth if truth else None
        if matched is not None:
            matches.append(matched)
        classifications.append(
            StudentQuestionClassification(
                journey_id=item.journey_id,
                question_id=record.question_id,
                sequence_context=record.sequence_context,
                primary_purpose=item.primary_purpose,
                confidence=item.confidence,
                synthetic_ground_truth=truth,
                matches_synthetic_ground_truth=matched,
            )
        )
    return ClassificationArtifact(
        bundle_id=dataset.meta.bundle_id,
        source_kind=dataset.meta.source_kind,
        model=model,
        generated_at=now or datetime.now(timezone.utc),
        batch_size=batch_size,
        input_hash=_input_hash(inputs),
        prompt_hash=_prompt_hash(inputs, batch_size),
        classifications=classifications,
        synthetic_accuracy=(sum(matches) / len(matches) if matches else None),
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

    def generate(prompt: str) -> ClassificationDraft:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": _gemini_schema(
                    ClassificationDraft.model_json_schema()
                ),
                "temperature": 0,
                "max_output_tokens": 32768,
            },
        )
        return ClassificationDraft.model_validate_json(response.text)

    return generate


def load_cached_classifications(
    path: Path,
    dataset: EpisodeDataset,
) -> ClassificationArtifact | None:
    if not path.is_file():
        return None
    try:
        artifact = ClassificationArtifact.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
    inputs = build_classification_inputs(dataset)
    if (
        artifact.bundle_id != dataset.meta.bundle_id
        or artifact.source_kind != dataset.meta.source_kind
        or artifact.input_hash != _input_hash(inputs)
        or artifact.prompt_hash
        != _prompt_hash(inputs, artifact.batch_size)
    ):
        return None
    return artifact


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Classify complete student-question records with Gemini."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-kind", default="synthetic")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dotenv", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=80)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"input JSONL does not exist: {args.input}")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.dotenv:
        if not args.dotenv.is_file():
            parser.error(f"dotenv file does not exist: {args.dotenv}")
        load_dotenv(args.dotenv, override=False)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        parser.error("GEMINI_API_KEY is not configured")

    dataset = build_dataset(args.input, source_kind=args.source_kind)
    output = args.output or args.input.parent / DEFAULT_CLASSIFICATION_FILENAME
    if not args.force:
        cached = load_cached_classifications(output, dataset)
        if cached is not None and cached.model == args.model:
            print(f"Reused cached classifications: {output}")
            return

    artifact = classify_dataset(
        dataset,
        gemini_generator(api_key, args.model),
        batch_size=args.batch_size,
        model=args.model,
    )
    output.write_text(
        artifact.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    accuracy = (
        f"{artifact.synthetic_accuracy * 100:.1f}%"
        if artifact.synthetic_accuracy is not None
        else "not available"
    )
    print(
        f"Wrote {len(artifact.classifications)} classifications to {output}; "
        f"synthetic-label agreement: {accuracy}"
    )


if __name__ == "__main__":
    main()
