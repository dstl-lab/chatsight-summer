import json
import subprocess
import sys
from pathlib import Path

from session_review.demo_export import build_demo

FIXTURE = Path(__file__).parents[1] / "fixtures" / "frontend_demo_sessions.json"
FRONTEND_DATA = Path(__file__).parents[1] / "frontend" / "src" / "demo-data.synthetic.json"


def test_demo_contract_has_four_synthetic_scenarios():
    demo = build_demo(FIXTURE)
    assert demo["dataset"]["synthetic"] is True
    assert demo["summary"] == {
        "total_sessions": 4,
        "flagged_sessions": 3,
        "high_priority_sessions": 2,
    }
    assert [session["review_rank"] for session in demo["sessions"]] == [1, 2, 3, 4]
    assert {session["scenario"] for session in demo["sessions"]} == {
        "Repeated failures after tutor help",
        "Multiple tutor responses before recovery",
        "Missing or ambiguous activity data",
        "Quick recovery after tutor assistance",
    }
    assert all("not an anomaly score" in session["priority_basis"]
               for session in demo["sessions"])


def test_committed_frontend_data_matches_pipeline_export():
    assert json.loads(FRONTEND_DATA.read_text()) == build_demo(FIXTURE)


def test_unknown_metrics_are_not_exported_as_zero():
    session = next(item for item in build_demo(FIXTURE)["sessions"]
                   if item["question_id"] == "Q4.3")
    assert session["active_time"]["status"] == "unknown"
    assert session["active_time"]["value"] is None
    assert session["post_help_active_time"]["value"] is None
    assert session["outcome"]["value"] is None
    assert session["reference_active_time"]["status"] == "unknown"


def test_every_reason_and_metric_reference_is_traceable():
    demo = build_demo(FIXTURE)
    for session in demo["sessions"]:
        source_refs = set(session["source_event_refs"])
        timeline_refs = {event["id"] for event in session["timeline"]
                         if event["source_event_id"] is not None}
        assert timeline_refs == source_refs
        for reason in session["reasons"]:
            assert set(reason["supporting_refs"]) <= timeline_refs
        for metric_name in (
            "active_time", "post_help_active_time", "elapsed_time",
            "failed_checks_after_help", "tutor_requests", "completed_tutor_responses",
            "repeated_failures", "continued_after_help", "resumed_after_help",
        ):
            assert set(session[metric_name]["evidence_refs"]) <= timeline_refs


def test_timeline_contains_code_diff_and_inactivity_marker():
    demo = build_demo(FIXTURE)
    repeated = next(item for item in demo["sessions"] if item["question_id"] == "Q5.1")
    assert any(event["code_diff"] for event in repeated["timeline"]
               if event["kind"] == "code_edit")
    gap = next(event for event in repeated["timeline"] if event["kind"] == "inactivity")
    assert gap["duration_seconds"] > 1800
    assert set(gap["supporting_refs"]) <= set(repeated["source_event_refs"])


def test_demo_export_cli_is_create_only(tmp_path):
    output = tmp_path / "demo.json"
    command = [sys.executable, "-m", "session_review.demo_export", str(FIXTURE),
               "--output", str(output)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(output.read_text())["contract_version"] == 1
    saved = output.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2
    assert output.read_bytes() == saved
