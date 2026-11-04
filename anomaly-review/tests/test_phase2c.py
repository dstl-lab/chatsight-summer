import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from session_review.json_adapter import JsonMapping, normalize_mapped_json, records_from_export
from session_review.normalize import parse_json
from session_review.phase2c import run_phase2c


ROOT = Path(__file__).parents[1]
EXPORT = ROOT / "fixtures" / "phase2c_export.synthetic.json"
MAPPING = ROOT / "fixtures" / "phase2c_mapping.synthetic.json"


def mapping():
    return JsonMapping.model_validate(parse_json(MAPPING.read_bytes()))


def export_data():
    return json.loads(EXPORT.read_text())


def run(data):
    return run_phase2c(
        json.dumps(data).encode(), mapping(), "synthetic-phase2c-test", origin="synthetic"
    )


def test_provisional_adapter_runs_existing_sessions_and_metrics_unchanged():
    result = run_phase2c(EXPORT.read_bytes(), mapping(), "synthetic-phase2c", origin="synthetic")
    assert result.quality["counts"] == {
        "input_records": 6,
        "accepted_normalized_records": 6,
        "rejected_records": 0,
        "coalesced_duplicate_records": 0,
        "unassigned_events": 0,
        "reconstructed_question_sessions": 1,
        "metric_sessions": 1,
    }
    assert result.quality["validation_gate"] == {
        "status": "review_required",
        "blocking_checks": [],
        "real_data_validated": False,
    }
    assert len(result.sessions["episodes"]) == 1
    assert result.metrics["episodes"][0]["time"]["active_time_after_first_help"]["value"] == 120
    assert result.normalization["records"][0]["sources"][0]["record_pointer"] == "/records/0"


def test_report_is_aggregate_and_does_not_copy_private_content_or_identifiers():
    data = export_data()
    data["records"][0]["payload"]["body"] = "DO-NOT-PRINT-STUDENT-MESSAGE"
    data["records"][2]["payload"]["after"] = "DO-NOT-PRINT-NOTEBOOK-CODE"
    data["records"][0]["scope"]["student_key"] = "DO-NOT-PRINT-STUDENT-ID"
    report = json.dumps(run(data).quality)
    assert "DO-NOT-PRINT-STUDENT-MESSAGE" not in report
    assert "DO-NOT-PRINT-NOTEBOOK-CODE" not in report
    assert "DO-NOT-PRINT-STUDENT-ID" not in report
    assert '"contains_raw_student_messages": false' in report
    assert '"contains_raw_notebook_code": false' in report


def test_malformed_and_unexpected_records_remain_in_pointer_manifest():
    data = export_data()
    data["records"].append("not an event object")
    unknown = copy.deepcopy(data["records"][0])
    unknown["uid"] = "synthetic-unknown"
    unknown["kind"] = "new.unmapped.event"
    data["records"].append(unknown)
    result = run(data)
    assert [item["code"] for item in result.normalization["rejected"]] == [
        "record_not_object", "unexpected_event_type"
    ]
    manifest = {item["record_pointer"]: item["codes"]
                for item in result.quality["unresolved_record_manifest"]}
    assert manifest["/records/6"] == ["missing_event_id", "record_not_object"]
    assert manifest["/records/7"] == ["unexpected_event_type"]
    assert result.quality["checks"]["event_types"]["status"] == "fail"


def test_missing_duplicate_ids_and_timestamp_problems_are_counted():
    data = export_data()
    del data["records"][0]["uid"]
    data["records"][1]["uid"] = data["records"][2]["uid"]
    del data["records"][3]["time"]
    data["records"][4]["received"] = "2026-01-10T09:00:00Z"
    result = run(data)
    ids = result.quality["checks"]["event_ids"]
    timestamps = result.quality["checks"]["timestamps"]
    assert ids["status"] == "fail"
    assert ids["issues"] == 3
    assert timestamps["status"] == "fail"
    assert timestamps["issues"] == 2
    assert result.quality["validation_gate"]["status"] == "blocked"


def test_ambiguous_questions_completion_conflicts_and_unmatched_help_are_reported():
    data = export_data()
    request = data["records"][0]
    del request["scope"]["question_key"]
    request["scope"]["question_candidates"] = ["q1", "q2"]
    response = data["records"][1]
    del response["payload"]["completion_evidence"]
    result = run(data)
    assert result.quality["checks"]["question_attribution"]["issues"] == 1
    assert result.quality["checks"]["tutor_response_completion"]["status"] == "fail"
    assert result.quality["counts"]["unassigned_events"] == 1
    assert result.quality["counts"]["rejected_records"] == 1


def test_inconsistent_order_and_unreliable_check_question_are_not_assigned():
    data = export_data()
    data["records"][2]["ordering"]["sequence"] = 0
    del data["records"][4]["scope"]["question_key"]
    result = run(data)
    assert result.quality["checks"]["chronological_order"]["status"] == "warning"
    assert result.quality["checks"]["check_question_association"]["status"] == "fail"
    assert result.quality["counts"]["unassigned_events"] == 6


def test_unmatched_tutor_response_and_insufficient_activity_remain_visible():
    data = export_data()
    data["records"] = [data["records"][1]]
    result = run(data)
    linkage = result.quality["checks"]["tutor_request_response_linkage"]
    assert linkage == {
        "status": "warning", "unit": "interactions",
        "evaluated": 1, "passed": 0, "issues": 1,
    }
    assert result.quality["checks"]["session_activity_evidence"]["issues"] == 1
    assert result.metrics["episodes"][0]["recovery"]["question_outcome"]["status"] == "unknown"


def test_request_identifier_conflict_across_questions_is_reported():
    data = export_data()
    other = copy.deepcopy(data["records"][1])
    other["uid"] = "synthetic-cross-question-response"
    other["payload"]["response_key"] = "synthetic-response-2"
    other["scope"]["question_key"] = "q2"
    other["ordering"] = {"stream": "synthetic-stream-b", "sequence": 1}
    data["records"].append(other)
    result = run(data)
    assert result.quality["checks"]["cross_source_identifiers"]["status"] == "fail"
    assert result.sessions["linkage_conflicts"][0]["code"] == "request_spans_question_scopes"


def test_mapping_root_and_unmapped_values_fail_without_guessing():
    bad_mapping = mapping().model_copy(update={"records_pointer": "/does-not-exist"})
    with pytest.raises(ValueError, match="records pointer"):
        records_from_export(EXPORT.read_bytes(), bad_mapping)

    data = export_data()
    data["records"][4]["payload"]["result"] = "source-specific-new-value"
    normalized = normalize_mapped_json(
        json.dumps(data).encode(), mapping(), "synthetic-phase2c", origin="synthetic"
    )
    assert normalized.rejected[0].code == "unmapped_field_value"
    assert normalized.rejected[0].locations == ["detail.outcome"]


def test_cli_is_create_only_and_does_not_modify_source(tmp_path):
    before = EXPORT.read_bytes()
    quality = tmp_path / "quality.json"
    artifacts = tmp_path / "private-artifacts"
    command = [
        sys.executable, "-m", "session_review.phase2c_cli", str(EXPORT),
        "--mapping", str(MAPPING), "--dataset-id", "synthetic-cli",
        "--quality-output", str(quality), "--artifacts-dir", str(artifacts),
    ]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["real_data_validated"] is False
    assert json.loads(quality.read_text())["privacy"]["contains_raw_notebook_code"] is False
    assert (artifacts / "normalization.json").exists()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2
    assert EXPORT.read_bytes() == before
