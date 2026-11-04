import copy
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from session_review.normalize import load_json, normalize
from session_review.schema import Envelope, Event
from session_review.sessions import SessionConfig, reconstruct

FIXTURE = Path(__file__).parents[1] / "fixtures" / "synthetic_sessions.json"


def event(identity="a", at="2026-01-01T10:00:00Z", **changes):
    value = {"event_id": identity, "occurred_at": at, "learner_id": "invented-student",
             "course_id": "course", "cohort_id": "term", "assignment_id": "lab",
             "assignment_version": "v1", "notebook_id": "book",
             "question": {"basis": "explicit", "question_id": "q1"},
             "detail": {"type": "student_message", "text": "Invented text"}}
    value.update(changes)
    return value


def response(identity="help", at="2026-01-01T10:01:00Z", status="completed", **changes):
    detail = {"type": "tutor_response", "status": status, "request_id": "request1",
              "response_id": identity}
    if status == "completed":
        detail["completion_basis"] = "server_completed"
    return event(identity, at, detail=detail, **changes)


def run(events, **kwargs):
    envelope = {"format": "anomaly-review.canonical.v1", "dataset_id": "synthetic-tests",
                "origin": "synthetic", "events": events}
    return reconstruct(load_json(json.dumps(envelope).encode()), **kwargs)


def ids(report, refs):
    index = {r["ref"]: r["event"]["event_id"] for r in report["normalization"]["records"]}
    return [index[r] for r in refs]


def test_synthetic_demo_and_evidence_closure():
    report = reconstruct(load_json(FIXTURE.read_bytes()))
    assert report["origin"] == "synthetic"
    assert not report["normalization"]["rejected"]
    assert len(report["unassigned"]) == 1
    q1, q2, q3 = report["episodes"]
    assert len(q1["bouts"]) == 2
    assert q1["bouts"][1]["resumed_from"] == q1["bouts"][0]["bout_id"]
    assert len(q1["tutor_interactions"]) == 2
    assert q1["outcome"]["status"] == "unfinished"
    assert q2["outcome"]["status"] == "unknown"
    assert q2["help"]["first_boundary_status"] == "not_observed"
    assert q3["outcome"]["status"] == "completed"
    assert q3["help"]["first_boundary_status"] == "known"
    assert q1["checks"][1]["binding"] == "verified"
    assert q1["checks"][2]["binding"] == "unverified"
    first, second = q1["help"]["boundaries"]
    assert ids(report, first["behavior_window"]["before_refs"]) == ["e01", "e02"]
    assert ids(report, first["behavior_window"]["after_until_next_help_refs"]) == ["e05", "e06", "e07", "e08"]
    assert ids(report, second["behavior_window"]["after_until_next_help_refs"]) == ["e10", "e11"]
    assert all(ep["active_seconds"] is None for ep in report["episodes"])
    known = {r["ref"] for r in report["normalization"]["records"]}
    def walk(value, key=""):
        if isinstance(value, dict):
            for k, v in value.items(): walk(v, k)
        elif isinstance(value, list):
            if key.endswith("refs"): assert set(value) <= known
            else:
                for v in value: walk(v)
        elif key.endswith("_ref") and value is not None:
            assert value in known
    walk(report["episodes"])


def test_shuffle_preserves_session_result_and_source_pointer_roundtrip():
    data = json.loads(FIXTURE.read_text())
    baseline = reconstruct(load_json(json.dumps(data).encode()))
    random.Random(5).shuffle(data["events"])
    report = reconstruct(load_json(json.dumps(data).encode()))
    assert report["episodes"] == baseline["episodes"]
    for r in report["normalization"]["records"]:
        for s in r["sources"]:
            index = int(s["record_pointer"].split("/")[-1])
            assert data["events"][index]["event_id"] == r["event"]["event_id"]


def test_received_time_does_not_reorder_events():
    a = event("a", received_at="2026-01-02T00:00:00Z")
    b = event("b", "2026-01-01T10:01:00Z", received_at="2026-01-01T10:02:00Z")
    report = run([b, a])
    assert ids(report, report["episodes"][0]["event_refs"]) == ["a", "b"]


@pytest.mark.parametrize("field", ["learner_id", "course_id", "cohort_id", "assignment_id", "assignment_version", "notebook_id", "occurred_at"])
def test_unknown_identity_or_timestamp_is_retained_unassigned(field):
    report = run([event(**{field: None})])
    assert not report["episodes"]
    assert len(report["normalization"]["records"]) == 1
    assert f"missing_{field}" in report["unassigned"][0]["reasons"]


@pytest.mark.parametrize("basis", ["missing", "ambiguous"])
def test_question_is_never_guessed_from_text_or_nearby_event(basis):
    report = run([event(), event("b", question={"basis": basis},
                                detail={"type": "student_message", "text": "help with q1"})])
    assert len(report["episodes"][0]["event_refs"]) == 1
    assert report["unassigned"][0]["reasons"] == ["question_" + basis]


def test_mapping_requires_evidence_and_unknown_fields_rejected():
    report = run([event(question={"basis": "verified_mapping", "question_id": "q1"}),
                  event("b", unexpected="private content")])
    assert len(report["normalization"]["rejected"]) == 2
    assert "private content" not in json.dumps(report["normalization"]["rejected"])
    good = run([event(question={"basis": "verified_mapping", "question_id": "q1", "mapping_ref": "mapping-v1"})])
    assert len(good["episodes"]) == 1


@pytest.mark.parametrize("field,value", [("assignment_version", "v2"), ("learner_id", "other"), ("cohort_id", "term2"), ("notebook_id", "book2")])
def test_incompatible_scopes_never_merge(field, value):
    assert len(run([event(), event("b", **{field: value})])["episodes"]) == 2


def test_tied_boundary_keeps_uncertainty():
    report = run([event(), response(at="2026-01-01T10:00:00Z")])
    ep = report["episodes"][0]
    assert ids(report, ep["help"]["boundaries"][0]["behavior_window"]["ambiguous_refs"]) == ["a"]
    assert ep["ambiguous_order_groups"]


def test_tied_boundary_uses_only_a_declared_shared_sequence():
    report = run([event(sequence=2, order_stream_id="s"),
                  response(at="2026-01-01T10:00:00Z", sequence=1, order_stream_id="s")])
    ep = report["episodes"][0]
    assert not ep["ambiguous_order_groups"]
    assert ids(report, ep["help"]["boundaries"][0]["behavior_window"]["after_until_next_help_refs"]) == ["a"]


def test_two_tied_responses_do_not_get_arbitrary_first_boundary():
    report = run([response("a"), response("b"), event("c", "2026-01-01T10:02:00Z")])
    help_info = report["episodes"][0]["help"]
    assert help_info["first_boundary_status"] == "ambiguous"
    assert help_info["first_completed_response_ref"] is None
    for boundary in help_info["boundaries"]:
        assert ids(report, boundary["behavior_window"]["ambiguous_refs"]) == ["c"]


def test_normal_response_lifecycle_has_one_completed_boundary():
    streaming = response("same-response", status="streaming")
    completed = response("same-response", "2026-01-01T10:01:30Z")
    streaming["event_id"] = "response-streaming"
    completed["event_id"] = "response-completed"
    report = run([event(detail={"type":"student_message", "request_id":"request1"}),
                  streaming, completed])
    episode = report["episodes"][0]
    assert not report["linkage_conflicts"]
    assert ids(report, [episode["help"]["first_completed_response_ref"]]) == ["response-completed"]
    assert len(episode["help"]["boundaries"]) == 1


def test_duplicate_terminal_response_lifecycle_is_not_a_help_boundary():
    first = response("same-response", "2026-01-01T10:01:00Z")
    second = response("same-response", "2026-01-01T10:01:01Z")
    first["event_id"] = "terminal-a"
    second["event_id"] = "terminal-b"
    report = run([first, second])
    episode = report["episodes"][0]
    assert report["linkage_conflicts"][0]["code"] == "response_lifecycle_ambiguous"
    assert episode["help"]["first_boundary_status"] == "ambiguous"
    assert not episode["help"]["boundaries"]
    assert set(ids(report, episode["help"]["unresolved_completed_response_refs"])) == {
        "terminal-a", "terminal-b"
    }


def test_request_reused_across_questions_does_not_create_help_boundaries():
    q2 = {"basis":"explicit", "question_id":"q2"}
    report = run([event(detail={"type":"student_message", "request_id":"request1"}),
                  response(), response("q2-help", question=q2)])
    assert report["linkage_conflicts"][0]["code"] == "request_spans_question_scopes"
    assert all(ep["help"]["first_boundary_status"] == "ambiguous"
               for ep in report["episodes"])


@pytest.mark.parametrize("status", ["streaming", "failed", "cancelled", "unknown"])
def test_incomplete_tutor_responses_never_start_post_help(status):
    report = run([response(status=status), event("b", "2026-01-01T10:02:00Z")])
    ep = report["episodes"][0]
    assert not ep["help"]["boundaries"]
    assert len(ep["tutor_interactions"]) == 1
    assert ep["outcome"]["status"] == "unknown"


def test_response_completion_evidence_is_required():
    r = response()
    del r["detail"]["completion_basis"]
    assert len(run([r])["normalization"]["rejected"]) == 1


def test_multiple_bouts_keep_one_question_and_pass_does_not_end_it():
    report = run([event(), event("pass", "2026-01-01T10:01:00Z", detail={"type":"check_result", "scope":"question", "outcome":"pass"}),
                  event("return", "2026-01-01T12:00:00Z")])
    ep = report["episodes"][0]
    assert len(ep["bouts"]) == 2
    assert ep["outcome"]["status"] == "unknown"
    assert len(ep["event_refs"]) == 3


def test_explicit_completion_and_reopening_preserve_both():
    complete = event("c", "2026-01-01T10:01:00Z", detail={"type":"question_status", "status":"completed", "evidence_basis":"invented final submission"})
    reopened = event("r", "2026-01-01T10:02:00Z", detail={"type":"question_status", "status":"reopened", "evidence_basis":"invented reopen event"})
    report = run([event(), complete])
    assert report["episodes"][0]["outcome"]["status"] == "completed"
    report = run([event(), complete, reopened])
    assert report["episodes"][0]["outcome"]["status"] == "reopened"
    assert ids(report, report["episodes"][0]["outcome"]["completion_event_refs"]) == ["c"]
    report = run([event(), complete, event("later", "2026-01-01T10:03:00Z")])
    assert report["episodes"][0]["outcome"]["status"] == "activity_after_completion"


def test_duplicate_and_conflicting_ids_account_for_every_record():
    a = event()
    report = run([a, copy.deepcopy(a)])
    assert report["normalization"]["duplicate_records"] == 1
    assert len(report["normalization"]["records"][0]["sources"]) == 2
    report = run([a, event(detail={"type":"student_message", "text":"different"})])
    assert not report["episodes"]
    assert [r["code"] for r in report["normalization"]["rejected"]] == ["conflicting_event_id"] * 2


def test_timezone_and_inconsistent_sequence_controls():
    assert len(run([event(at="2026-01-01T10:00:00")])["normalization"]["rejected"]) == 1
    assert len(run([event(at=1767261600)])["normalization"]["rejected"]) == 1
    report = run([event(sequence=2, order_stream_id="s"),
                  event("b", "2026-01-01T10:01:00Z", sequence=1, order_stream_id="s")])
    assert len(report["unassigned"]) == 2
    assert not report["episodes"]


def test_check_revision_mismatch_is_not_verified():
    execution = event("x", detail={"type":"execution", "execution_id":"run", "revision_id":"one", "status":"completed"})
    check = event("c", "2026-01-01T10:00:01Z", detail={"type":"check_result", "execution_id":"run", "revision_id":"two", "scope":"subcheck", "outcome":"fail"})
    link = run([execution, check])["episodes"][0]["checks"][0]
    assert link["binding"] == "unverified"
    assert link["reasons"] == ["revision_mismatch"]


def test_adapter_can_translate_without_session_changes():
    class TestAdapter:
        name = "invented-test-adapter"
        def convert(self, row):
            return row["wrapped"]
    envelope = Envelope(format="anomaly-review.canonical.v1", dataset_id="invented", origin="synthetic", events=[{"wrapped":event()}])
    normalized = normalize(envelope, "test-input-digest", TestAdapter())
    assert len(reconstruct(normalized)["episodes"]) == 1
    assert normalized.records[0].sources[0].adapter == "invented-test-adapter"


def test_coverage_is_not_inferred_and_outside_events_are_reported():
    data = json.loads(FIXTURE.read_text())
    data["events"][0]["occurred_at"] = "2025-01-01T00:00:00Z"
    report = reconstruct(load_json(json.dumps(data).encode()))
    assert report["normalization"]["rejected"][0]["code"] == "outside_coverage"
    assert report["coverage"]["completeness"] == "partial"
    assert run([event()])["coverage"] is None


def test_invalid_json_keys_and_nonfinite_numbers_are_refused():
    with pytest.raises(ValueError): load_json(b'{"events":[],"events":[]}')
    with pytest.raises(ValueError): load_json(b'{"x":NaN}')


def test_explicit_pause_resume_and_gap_threshold():
    pause = event("p", "2026-01-01T10:01:00Z", detail={"type":"activity","action":"pause"})
    resumed = event("r", "2026-01-01T10:02:00Z", detail={"type":"activity","action":"resume"})
    ep = run([event(), pause, resumed])["episodes"][0]
    assert len(ep["bouts"]) == 2
    assert ep["gaps"][0]["reason"] == "explicit_pause"
    assert len(run([event(), event("b", "2026-01-01T10:30:00Z")])["episodes"][0]["bouts"]) == 1
    with pytest.raises(ValueError): SessionConfig(gap_seconds=0)


def test_cli_is_offline_create_only_and_inputs_unchanged(tmp_path):
    before = FIXTURE.read_bytes()
    output = tmp_path / "report.json"
    cmd = [sys.executable, "-m", "session_review.cli", str(FIXTURE), "--output", str(output)]
    first = subprocess.run(cmd, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["origin"] == "synthetic"
    saved = output.read_bytes()
    second = subprocess.run(cmd, capture_output=True, text=True)
    assert second.returncode == 2
    assert output.read_bytes() == saved
    assert FIXTURE.read_bytes() == before


def test_canonical_schema_can_be_exported():
    schema = Event.model_json_schema()
    assert schema["properties"]["detail"]["discriminator"]["propertyName"] == "type"
