import json
from pathlib import Path

from src.ingest.episode_events import build_dataset, load_event_log
from src.synthetic.cohort import generate_cohort
from src.synthetic.config import (
    HISTORICAL_SEQUENCE_ANCHORS,
    CohortConfig,
)


def test_generation_is_deterministic_and_manifested(tmp_path: Path):
    config = CohortConfig(student_count=12, seed=91, direct_request_share=0.25)

    first = generate_cohort(config, tmp_path / "first")
    second = generate_cohort(config, tmp_path / "second")

    assert first["run_id"] == second["run_id"]
    first_dir = Path(first["output_dir"])
    second_dir = Path(second["output_dir"])
    assert (first_dir / "events.jsonl").read_bytes() == (
        second_dir / "events.jsonl"
    ).read_bytes()
    manifest = json.loads((first_dir / "manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert manifest["generation"]["seed"] == 91
    assert "answer_code" not in json.dumps(manifest)
    assert (first_dir / "cohort_summary.json").is_file()
    assert (first_dir / "validation_report.md").is_file()


def test_default_class_has_unique_students_diverse_paths_and_calibration(
    tmp_path: Path,
):
    result = generate_cohort(CohortConfig(), tmp_path)
    outdir = Path(result["output_dir"])
    summary = json.loads((outdir / "cohort_summary.json").read_text())
    observed = summary["observed"]

    assert len(summary["students"]) == 100
    assert len({student["student_id"] for student in summary["students"]}) == 100
    assert observed["potential_question_paths"] == 800
    assert observed["represented_question_paths"] >= 740
    assert observed["tutor_using_question_paths"] >= 200
    for name, target in HISTORICAL_SEQUENCE_ANCHORS.items():
        assert abs(observed["pre_pattern"][name]["share"] - target) <= 0.01
    assert abs(
        observed["interaction_acts"]["direct-request"]["share"] - 0.25
    ) <= 0.01

    varied_students = 0
    for student in summary["students"]:
        represented = [
            path for path in student["question_paths"] if not path["skipped"]
        ]
        signatures = {
            (
                path["used_tutor"],
                path["pre_pattern"],
                path["interaction_act"],
                path["eventually_passed"],
            )
            for path in represented
        }
        if len(signatures) >= 2:
            varied_students += 1
    assert varied_students >= 80


def test_generated_events_validate_and_transfer_links_are_exact(tmp_path: Path):
    result = generate_cohort(CohortConfig(student_count=25, seed=44), tmp_path)
    event_path = Path(result["event_path"])
    events, transcripts, quality = load_event_log(event_path)

    assert quality.rejected_rows == 0
    assert quality.duplicate_events == 0
    assert quality.unknown_question_events == 0
    assert quality.legacy_rows > 0
    assert transcripts
    assert all(event.user_id.startswith("syn_") for event in events)
    assert all(
        "@" not in turn.text
        for turns in transcripts.values()
        for turn in turns
    )

    response_events = {
        event.response_id: event
        for event in events
        if event.event_type == "tutor_response" and event.response_id
    }
    copied_events = {
        event.payload["code_block_id"]: event
        for event in events
        if event.event_type == "tutor_code_copied"
    }
    execution_starts = {
        (event.user_id, event.correlation_id)
        for event in events
        if event.event_type == "cell_execution_started"
    }
    for event in events:
        if event.event_type == "notebook_paste":
            assert event.payload["provenance"] == "copied_then_pasted"
            response = response_events[event.payload["matched_response_id"]]
            copied = copied_events[event.payload["matched_code_block_id"]]
            assert response.occurred_at <= copied.occurred_at <= event.occurred_at
        if event.event_type == "tutor_code_inserted":
            assert event.response_id in response_events
            assert response_events[event.response_id].occurred_at <= event.occurred_at
        if (
            event.event_type == "autograder_completed"
            and event.payload.get("success") is True
        ):
            assert (event.user_id, event.correlation_id) in execution_starts


def test_direct_request_rate_is_an_explicit_scenario_parameter(tmp_path: Path):
    low = generate_cohort(
        CohortConfig(student_count=30, seed=9, direct_request_share=0.10),
        tmp_path / "low",
    )
    high = generate_cohort(
        CohortConfig(student_count=30, seed=9, direct_request_share=0.40),
        tmp_path / "high",
    )

    assert low["run_id"] != high["run_id"]
    low_share = low["observed"]["interaction_acts"]["direct-request"]["share"]
    high_share = high["observed"]["interaction_acts"]["direct-request"]["share"]
    assert abs(low_share - 0.10) <= 0.02
    assert abs(high_share - 0.40) <= 0.02


def test_dataset_loads_generation_metadata(tmp_path: Path):
    result = generate_cohort(CohortConfig(student_count=8, seed=7), tmp_path)

    dataset = build_dataset(Path(result["event_path"]), source_kind="synthetic")

    assert dataset.meta.generation is not None
    assert dataset.meta.generation["student_count"] == 8
    assert dataset.meta.generation["scenario_assumptions"][
        "direct_request_share"
    ] == 0.25
