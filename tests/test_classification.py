from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ingest.episode_events import build_dataset
from src.synthetic.cohort import generate_cohort
from src.synthetic.config import CohortConfig
from src.viewer.classification import (
    ClassificationDraft,
    ClassificationDraftItem,
    build_classification_inputs,
    classify_dataset,
    load_cached_classifications,
)
from src.viewer.briefing import build_briefing_packet


@pytest.fixture
def dataset(tmp_path: Path):
    generated = generate_cohort(
        CohortConfig(student_count=16, seed=141),
        tmp_path,
    )
    return build_dataset(
        Path(generated["event_path"]),
        source_kind="synthetic",
    )


def _draft(data):
    return ClassificationDraft(
        records=[
            ClassificationDraftItem(
                journey_id=record.journey_id,
                primary_purpose="validation",
                confidence="medium",
            )
            for record in build_classification_inputs(data)
        ]
    )


def test_inputs_are_complete_student_question_records(dataset):
    records = build_classification_inputs(dataset)

    assert records
    assert len(records) == len({record.journey_id for record in records})
    assert all(record.question_id != "unknown" for record in records)
    assert all(record.event_sequence for record in records)
    assert all(record.conversation for record in records)
    assert {
        record.sequence_context for record in records
    }.issubset(
        {"before-attempt", "after-attempt", "after-problem", "after-pass"}
    )


def test_classification_resolves_ids_and_synthetic_labels(dataset):
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return _draft(dataset)

    artifact = classify_dataset(
        dataset,
        generate,
        model="test-model",
        now=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )

    assert len(calls) == 1
    assert artifact.model == "test-model"
    assert len(artifact.classifications) == len(
        build_classification_inputs(dataset)
    )
    assert all(
        item.synthetic_ground_truth for item in artifact.classifications
    )
    assert artifact.synthetic_accuracy is not None


def test_classification_batches_transport_not_analysis_unit(dataset):
    inputs = build_classification_inputs(dataset)
    calls = []

    def generate(prompt):
        calls.append(prompt)
        ids = [
            record.journey_id
            for record in inputs
            if f'"journey_id":"{record.journey_id}"' in prompt
        ]
        return ClassificationDraft(
            records=[
                ClassificationDraftItem(
                    journey_id=journey_id,
                    primary_purpose="validation",
                    confidence="medium",
                )
                for journey_id in ids
            ]
        )

    artifact = classify_dataset(
        dataset,
        generate,
        batch_size=10,
    )

    assert len(calls) > 1
    assert len(artifact.classifications) == len(inputs)
    assert artifact.batch_size == 10


def test_classification_rejects_missing_ids(dataset):
    draft = _draft(dataset)
    draft.records.pop()

    with pytest.raises(ValueError, match="mismatched IDs"):
        classify_dataset(dataset, lambda prompt: draft)


def test_classification_cache_requires_matching_input(dataset, tmp_path: Path):
    artifact = classify_dataset(dataset, lambda prompt: _draft(dataset))
    path = tmp_path / "classifications.json"
    path.write_text(artifact.model_dump_json(), encoding="utf-8")

    assert load_cached_classifications(path, dataset) == artifact


def test_briefing_combines_purpose_with_sequence(dataset):
    classifications = classify_dataset(
        dataset,
        lambda prompt: _draft(dataset),
    )

    packet = build_briefing_packet(dataset, classifications)
    fact_ids = {fact.fact_id for fact in packet.facts}

    assert packet.classification_model == classifications.model
    assert "classified_contextual_patterns" in fact_ids
    assert "classified_validation_after_pass" in fact_ids
    assert "classified_debugging_after_problem" in fact_ids
    assert any(
        journey.classified_purpose for journey in packet.journeys
    )
