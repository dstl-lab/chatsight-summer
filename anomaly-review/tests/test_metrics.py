import json
import subprocess
import sys
from pathlib import Path

import pytest

from session_review.metrics import MetricsConfig, calculate_metrics
from session_review.normalize import load_json
from session_review.sessions import reconstruct

FIXTURE = Path(__file__).parents[1] / "fixtures" / "synthetic_sessions.json"


def canonical(events):
    envelope = {"format": "anomaly-review.canonical.v1", "dataset_id": "metric-tests",
                "origin": "synthetic", "events": events}
    return reconstruct(load_json(json.dumps(envelope).encode()))


def event(identity, at, detail, **changes):
    value = {"event_id": identity, "occurred_at": at, "learner_id": "invented-student",
             "course_id": "course", "cohort_id": "term", "assignment_id": "lab",
             "assignment_version": "v1", "notebook_id": "book",
             "question": {"basis": "explicit", "question_id": "q1"}, "detail": detail}
    value.update(changes)
    return value


@pytest.fixture
def demo():
    sessions = reconstruct(load_json(FIXTURE.read_bytes()))
    metrics = calculate_metrics(sessions)
    return sessions, {ep["scope"]["question_id"]: ep for ep in metrics["episodes"]}


def test_time_metrics_exclude_inactivity_and_keep_elapsed_separate(demo):
    _, episodes = demo
    q1 = episodes["q1"]
    assert q1["time"]["observed_elapsed_span"]["value"] == 2460
    assert q1["time"]["total_observed_active_time"]["value"] == 70
    assert q1["time"]["active_time_before_first_help"]["value"] == 10
    assert q1["time"]["active_time_after_first_help"]["value"] == 60
    assert q1["time"]["active_time_between_completed_responses"]["value"][0]["value"] == 50
    assert [item["value"] for item in
            q1["time"]["response_to_next_action_elapsed_time"]["value"]] == [30, 2240]


def test_activity_and_recovery_metrics_have_expected_values(demo):
    _, episodes = demo
    q1 = episodes["q1"]
    assert q1["activity"]["tutor_request_count"]["value"] == 2
    assert q1["activity"]["completed_tutor_response_count"]["value"] == 2
    assert q1["activity"]["failed_check_count"]["before_first_help"]["value"] == 1
    assert q1["activity"]["failed_check_count"]["after_first_help"]["value"] == 1
    assert q1["activity"]["repeated_failure_count"]["value"] == 1
    assert q1["activity"]["code_edit_count"]["after_first_help"]["value"] == 2
    assert q1["activity"]["execution_count"]["after_first_help"]["value"] == 1
    assert q1["recovery"]["continued_work_after_help"]["value"] is True
    assert q1["recovery"]["resumed_work_after_help"]["value"] is True

    q3 = episodes["q3"]
    assert q3["recovery"]["eventually_passed_question_check"]["value"] is True
    assert q3["recovery"]["failed_checks_between_help_and_recovery"]["value"] == 1
    assert q3["recovery"]["question_outcome"]["value"] == "completed"
    assert q3["recovery"]["resumed_work_after_help"]["value"] is False


def test_every_completed_response_has_its_own_behavior_window(demo):
    _, episodes = demo
    windows = episodes["q1"]["per_completed_response"]
    assert len(windows) == 2
    assert windows[0]["active_time_after_until_next_response"]["value"] == 50
    assert windows[0]["activity_after_until_next_response"]["failed_check_count"]["value"] == 1
    assert windows[0]["activity_after_until_next_response"]["student_message_count"]["value"] == 1
    assert windows[1]["active_time_after_until_next_response"]["value"] == 10
    assert windows[1]["activity_after_until_next_response"]["code_edit_count"]["value"] == 1
    assert episodes["q2"]["per_completed_response"] == []
    assert len(episodes["q3"]["per_completed_response"]) == 1


def test_intermediate_pass_and_missing_outcome_are_not_failures(demo):
    _, episodes = demo
    q1 = episodes["q1"]
    assert q1["recovery"]["intermediate_pass_refs"]
    assert q1["recovery"]["eventually_passed_question_check"]["status"] == "unknown"
    assert q1["recovery"]["question_outcome"]["value"] == "unfinished"

    q2 = episodes["q2"]
    assert q2["recovery"]["eventually_passed_question_check"]["value"] is True
    assert q2["recovery"]["question_outcome"]["status"] == "unknown"
    assert q2["recovery"]["question_outcome"]["value"] is None
    assert q2["time"]["active_time_after_first_help"]["status"] == "unknown"


def test_ambiguous_help_order_produces_unknown_partitioned_metrics():
    report = canonical([
        event("student", "2026-01-01T10:00:00Z",
              {"type": "student_message", "request_id": "r1"}),
        event("help", "2026-01-01T10:00:00Z",
              {"type": "tutor_response", "request_id": "r1", "response_id": "h1",
               "status": "completed", "completion_basis": "server_completed"}),
        event("edit1", "2026-01-01T10:01:00Z", {"type": "code_edit"}),
        event("edit2", "2026-01-01T10:01:10Z", {"type": "code_edit"}),
    ])
    episode = calculate_metrics(report)["episodes"][0]
    assert episode["time"]["active_time_before_first_help"]["status"] == "unknown"
    assert episode["time"]["active_time_after_first_help"]["status"] == "unknown"
    assert episode["activity"]["code_edit_count"]["after_first_help"]["value"] == 2
    assert episode["eligibility"]["post_help_behavior"]["eligible"] is False


def test_active_interval_cap_is_configurable_and_never_counts_long_gap():
    report = canonical([
        event("a", "2026-01-01T10:00:00Z", {"type": "code_edit"}),
        event("b", "2026-01-01T10:05:01Z", {"type": "execution", "status": "completed"}),
    ])
    metric = calculate_metrics(report)["episodes"][0]["time"]["total_observed_active_time"]
    assert metric["status"] == "unknown"
    assert metric["details"]["excluded_intervals"][0]["reason"] == "active_interval_cap_exceeded"
    assert calculate_metrics(report, MetricsConfig(301))["episodes"][0]["time"][
        "total_observed_active_time"]["value"] == 301
    with pytest.raises(ValueError):
        MetricsConfig(0)


def test_repeated_failure_is_unknown_without_stable_check_identity():
    report = canonical([
        event("f1", "2026-01-01T10:00:00Z",
              {"type": "check_result", "scope": "question", "outcome": "fail"}),
        event("f2", "2026-01-01T10:00:10Z",
              {"type": "check_result", "scope": "question", "outcome": "fail"}),
    ])
    metric = calculate_metrics(report)["episodes"][0]["activity"]["repeated_failure_count"]
    assert metric["status"] == "unknown"
    assert metric["reason"] == "logical_check_identifier_missing"


def test_every_metric_evidence_reference_resolves_to_source_event(demo):
    sessions, episodes = demo
    known = {record["ref"] for record in sessions["normalization"]["records"]}

    def walk(value, key=""):
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, child_key)
        elif isinstance(value, list):
            if key.endswith("refs"):
                assert set(value) <= known
            else:
                for child in value:
                    walk(child)
        elif key.endswith("_ref") and value is not None:
            assert value in known

    walk(episodes)


def test_metrics_cli_is_create_only(tmp_path):
    session_path = tmp_path / "sessions.json"
    output_path = tmp_path / "metrics.json"
    session_path.write_text(json.dumps(reconstruct(load_json(FIXTURE.read_bytes()))))
    command = [sys.executable, "-m", "session_review.metrics_cli", str(session_path),
               "--output", str(output_path)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(output_path.read_text())["method"] == "behavioral-metrics-v1"
    saved = output_path.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2
    assert output_path.read_bytes() == saved
