from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ingest.episode_events import build_dataset
from src.synthetic.cohort import generate_cohort
from src.synthetic.config import CohortConfig
from src.viewer.briefing import (
    BriefingDraft,
    DraftFinding,
    _gemini_schema,
    build_briefing_packet,
    build_prompt,
    generate_briefing,
    load_cached_briefing,
)


@pytest.fixture
def synthetic_dataset(tmp_path: Path):
    generated = generate_cohort(
        CohortConfig(student_count=16, seed=131),
        tmp_path,
    )
    return build_dataset(
        Path(generated["event_path"]),
        source_kind="synthetic",
    )


def _valid_draft(packet):
    facts = [fact.fact_id for fact in packet.facts[:3]]
    journeys = [
        journey.journey_id
        for journey in packet.journeys
        if journey.tutor_questions > 0
    ][:3]
    return BriefingDraft(
        summary_sentences=[
            "Tutor use differed across the synthetic lab questions.",
            "The evidence below identifies questions worth inspecting.",
        ],
        findings=[
            DraftFinding(
                headline=f"Finding {index + 1}",
                explanation=(
                    "This computed comparison stands out from the other "
                    "recorded values."
                ),
                instructor_prompt="What should the professor inspect next?",
                fact_ids=[facts[index]],
                journey_ids=[journeys[index]],
            )
            for index in range(3)
        ],
    )


def test_packet_contains_computed_facts_and_synthetic_details(
    synthetic_dataset,
):
    packet = build_briefing_packet(synthetic_dataset)

    assert packet.source_kind == "synthetic"
    assert packet.lab_label == "Lab 1"
    assert len(packet.facts) >= 9
    assert len(packet.journeys) > 80
    assert any(journey.transcript for journey in packet.journeys)
    assert {
        "question_tutor_use",
        "question_attempts_upper_range",
        "question_help_after_problem",
        "question_exact_code_use",
    }.issubset(fact.fact_id for fact in packet.facts)
    prompt = build_prompt(packet)
    assert "SYNTHETIC programming-lab scenario" in prompt
    assert "direct-request" in prompt


def test_gemini_schema_keeps_local_strictness_out_of_api_payload():
    schema = _gemini_schema(BriefingDraft.model_json_schema())

    assert "additionalProperties" not in str(schema)
    assert BriefingDraft.model_config["extra"] == "forbid"


def test_detailed_packet_rejects_real_source(tmp_path: Path):
    generated = generate_cohort(
        CohortConfig(student_count=4, seed=132),
        tmp_path,
    )
    real_dataset = build_dataset(
        Path(generated["event_path"]),
        source_kind="real",
    )

    with pytest.raises(ValueError, match="only for synthetic"):
        build_briefing_packet(real_dataset)


def test_generate_briefing_resolves_only_known_evidence(synthetic_dataset):
    packet = build_briefing_packet(synthetic_dataset)
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return _valid_draft(packet)

    artifact = generate_briefing(
        synthetic_dataset,
        generate,
        model="test-gemini",
        now=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )

    assert len(calls) == 1
    assert artifact.generation_mode == "gemini"
    assert artifact.model == "test-gemini"
    assert artifact.generated_at == datetime(
        2026, 9, 10, tzinfo=timezone.utc
    )
    assert len(artifact.findings) == 3
    assert artifact.findings[0].facts[0] == packet.facts[0]
    assert artifact.findings[0].examples[0].journey_id in {
        journey.journey_id for journey in packet.journeys
    }


def test_unknown_model_evidence_falls_back(synthetic_dataset):
    packet = build_briefing_packet(synthetic_dataset)
    draft = _valid_draft(packet)
    draft.findings[0].fact_ids = ["invented_fact"]

    artifact = generate_briefing(
        synthetic_dataset,
        lambda prompt: draft,
    )

    assert artifact.generation_mode == "deterministic-fallback"
    assert artifact.model is None
    assert len(artifact.findings) == 3
    assert all(finding.facts for finding in artifact.findings)


def test_unsupported_claim_language_and_repeated_facts_fall_back(
    synthetic_dataset,
):
    packet = build_briefing_packet(synthetic_dataset)
    unsupported = _valid_draft(packet)
    unsupported.findings[0].explanation = (
        "This suggests that students might be seeking validation."
    )
    repeated = _valid_draft(packet)
    repeated.findings[1].fact_ids = repeated.findings[0].fact_ids

    unsupported_artifact = generate_briefing(
        synthetic_dataset,
        lambda prompt: unsupported,
    )
    repeated_artifact = generate_briefing(
        synthetic_dataset,
        lambda prompt: repeated,
    )

    assert unsupported_artifact.generation_mode == "deterministic-fallback"
    assert repeated_artifact.generation_mode == "deterministic-fallback"


def test_cached_briefing_requires_matching_packet(
    synthetic_dataset,
    tmp_path: Path,
):
    packet = build_briefing_packet(synthetic_dataset)
    artifact = generate_briefing(
        synthetic_dataset,
        lambda prompt: _valid_draft(packet),
    )
    path = tmp_path / "briefing.json"
    path.write_text(artifact.model_dump_json(), encoding="utf-8")

    assert load_cached_briefing(path, synthetic_dataset) == artifact

    other_run = generate_cohort(
        CohortConfig(student_count=16, seed=133),
        tmp_path / "other",
    )
    other_dataset = build_dataset(
        Path(other_run["event_path"]),
        source_kind="synthetic",
    )
    assert load_cached_briefing(path, other_dataset) is None
