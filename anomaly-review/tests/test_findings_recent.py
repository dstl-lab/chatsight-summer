"""Invented PR100 observations exercise joins without a database or model."""
import copy
import hashlib
import json
import pytest

from session_review.findings import analyze_sessions as analyzer
from session_review.findings import bundle, historical, recent


def invented_rows():
    snapshot = json.dumps({"cells": [{"id": "cell-a", "cell_type": "code", "source": "x = 1"}]})
    command = 'grader.check("q1")'
    events = [
        ("notebook_cell_created", 2, {"cell_id": "cell-a", "cell_index": 0}),
        ("tutor_query", 3, {"mode": "tutor", "conversation_id": None, "request_id": "request-a",
            "question": "Why is my example failing?", "active_cell_id": "cell-a",
            "request": {"request_id": "request-a", "notebook_json": snapshot},
            "notebook_sha256": hashlib.sha256(snapshot.encode()).hexdigest()}),
        ("tutor_response", 4, {"conversation_id": "resolved-conversation", "request_id": "request-a",
            "status": "completed", "response": "Inspect the value of x."}),
        ("notebook_cell_source_changed", 5, {"cell_id": "cell-a", "source_revision": 1,
            "source_change_count": 2, "source_length": 5,
            "edit_started_at": "2026-10-15T12:04:59Z", "edit_ended_at": "2026-10-15T12:05:00Z"}),
        ("notebook_execution_requested", 6, {"cell_id": "cell-check", "kernel_id": "kernel-a",
            "execution_id": "exec-a", "source": command, "source_capture": "execute_request"}),
        ("notebook_execution_finished", 7, {"cell_id": "cell-check", "kernel_id": "kernel-a",
            "execution_id": "exec-a", "source": command, "status": "ok", "output": "Test failed",
            "output_complete": True}),
        ("autograder_info", 7, {"cell_id": "cell-check", "kernel_id": "kernel-a",
            "execution_id": "exec-a", "checked_source": command, "grader_id": "q1",
            "success": False, "output": "Test failed", "output_complete": True,
            "execution_status": "ok", "verdict_method": "text_heuristic"}),
    ]
    result = []
    for seq, (kind, minute, extra) in enumerate(events, 1):
        payload = {"schema_version": 1, "event_id": f"fictional-event-{seq}", "client_sequence": seq,
            "analytics_session_id": "fictional-page", "notebook_session_id": "fictional-notebook",
            "notebook_path": "invented-lab.ipynb", "timestamp": f"2026-10-15T12:{minute:02}:00Z",
            "task_context": {"task_id": "q-structure", "attribution": "nearest_preceding_cell_metadata"}, **extra}
        result.append({"id": seq, "event_type": kind, "user_email": "STU-FICTIONAL",
            "created_at": "2026-10-15T13:00:00Z", "payload": payload})
    return result


def normalize(events=None):
    return recent.normalize_session(list(enumerate(events or invented_rows(), 1)), "invented-input-hash")


def test_exact_request_execution_and_check_links_and_actual_edit_semantics():
    session, ctx, evidence, quality = normalize()
    assert {link["relationship"] for link in evidence["links"]} == {
        "responds_to_request", "executes_revision", "checks_execution"}
    assert quality["request_snapshot_hash_verified"] == quality["matched_execution_checks"] == 1
    assert all(record.question_id is None for record in [*session.messages, *session.activity])
    assert all(r.timestamp.hour == 12 for r in session.messages)  # Not DB insert time.
    revisions = [r for r in session.activity if isinstance(r, analyzer.Revision)]
    assert {r.capture_basis for r in revisions} == {"execution_capture", "request_snapshot"}
    assert not any(r.capture_basis == "edit" for r in revisions)
    edit = next(r for r in session.activity if isinstance(r, analyzer.Observation) and r.type == "edit_observation")
    assert "Source text is not included" in edit.description
    check = next(r for r in session.activity if isinstance(r, analyzer.Check))
    assert check.result == "fail" and check.grader_id == "q1" and check.question_id is None
    doc = bundle.build([session], input_hash="invented", context={session.session_id: ctx})
    view = doc["sessions"][0]
    assert view["scope"] == "notebook_session"
    assert view["completed_tutor_responses"]["value"] == 1
    assert view["failed_checks_after_help"]["value"] is None
    assert len([e for e in view["timeline"] if e["kind"] == "code_capture"]) == 2
    assert all({"label": "Timestamp basis", "value": "Event-specific client time"} in e["metadata"]
               for e in view["timeline"] if e["kind"] == "code_capture")


@pytest.mark.parametrize("change", ["kernel", "source", "cell", "missing_submission"])
def test_execution_binding_is_not_inferred_from_time_or_execution_id_alone(change):
    events = invented_rows()
    if change == "kernel": events[5]["payload"]["kernel_id"] = "different-kernel"
    elif change == "source": events[5]["payload"]["source"] = "different submitted source"
    elif change == "cell": events[5]["payload"]["cell_id"] = "different-cell"
    else: events.pop(4)
    session, _, evidence, quality = normalize(events)
    assert not any(isinstance(r, analyzer.Execution) for r in session.activity)
    assert not any(link["relationship"] == "checks_execution" for link in evidence["links"])
    assert quality["unlinked_checks"] == 1


def test_bad_checked_source_does_not_link_and_incomplete_output_has_unknown_verdict():
    events = invented_rows()
    events[6]["payload"].update(checked_source="another command", output_complete=False)
    session, _, _, quality = normalize(events)
    check = next(r for r in session.activity if isinstance(r, analyzer.Check))
    assert check.execution_id is None and check.result == "unknown"
    assert quality["unlinked_checks"] == 1


def test_hash_mismatch_never_becomes_verified_request_snapshot():
    events = invented_rows()
    events[1]["payload"]["notebook_sha256"] = "incorrect"
    session, _, _, quality = normalize(events)
    assert quality["request_snapshot_hash_unverified"] == 1
    assert not any(isinstance(r, analyzer.Revision) and r.capture_basis == "request_snapshot" for r in session.activity)


@pytest.mark.parametrize("change", ["wrong_request_id", "failed_response", "duplicate_terminal", "bad_question"])
def test_invalid_or_noncompleted_tutor_pairs_do_not_count_completed(change):
    events = invented_rows()
    if change == "wrong_request_id": events[1]["payload"]["request"]["request_id"] = "wrong"
    elif change == "failed_response": events[2]["payload"]["status"] = "error"
    elif change == "bad_question": events[1]["payload"]["question"] = ""
    else:
        terminal = copy.deepcopy(events[2])
        terminal.update(id=99, event_type="tutor_request_failed")
        terminal["payload"].update(event_id="another-terminal", client_sequence=99, status="cancelled")
        events.append(terminal)
    session, _, _, quality = normalize(events)
    assert not any(r.role == "tutor" for r in session.messages)
    assert quality["matched_completed_tutor_responses"] == 0


def test_conflicting_sequence_and_uuid_are_rejected():
    events = invented_rows()
    events[2]["payload"]["client_sequence"] = events[1]["payload"]["client_sequence"]
    with pytest.raises(ValueError, match="Conflicting client sequence"):
        normalize(events)
    events = invented_rows()
    events[2]["payload"]["event_id"] = events[1]["payload"]["event_id"]
    with pytest.raises(ValueError, match="Conflicting event UUID"):
        normalize(events)


def test_preparation_freezes_one_window_and_does_not_use_historical_fallback(tmp_path):
    events = invented_rows()
    later = copy.deepcopy(events[-1])
    later.update(id=99)
    later["payload"].update(event_id="later-pass", client_sequence=99, success=True, timestamp="2026-10-15T12:30:00Z")
    events.append(later)
    historical_event = copy.deepcopy(events[0])
    historical_event.update(id=100)
    del historical_event["payload"]["schema_version"]
    events.append(historical_event)
    path = tmp_path / "invented.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in events))
    a = recent.prepare(path, tmp_path / "a", count=1)
    b = recent.prepare(path, tmp_path / "b", count=1)
    assert a == b and a["historical_fallback"] is False
    assert a["quality"]["not_pr100_schema"] == 1
    assert a["window_counts"] == {"candidate_windows": 1, "eligible_windows": 1}
    _, sessions, context, evidence = historical.load_prepared(tmp_path / "a")
    assert not any(r.id == "later-pass" for r in sessions[0].activity)
    assert context[sessions[0].session_id]["window"]["end"] == "2026-10-15T12:10:00+00:00"
    assert any("later recovery" in warning for warning in evidence[0]["warnings"])
    with pytest.raises(ValueError, match="Only 1 recent notebook scopes"):
        recent.prepare(path, tmp_path / "c", count=2)
    assert not (tmp_path / "c").exists()


def test_longer_dialogue_window_includes_later_events_without_requiring_checks(tmp_path):
    events = [row for row in invented_rows() if row["event_type"] != "autograder_info"]
    later = copy.deepcopy(events[-1])
    later.update(id=99, event_type="notebook_cell_source_changed")
    later["payload"].update(event_id="later-edit", client_sequence=99, timestamp="2026-10-15T12:16:00Z", source_revision=2)
    events.append(later)
    path = tmp_path / "invented.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in events))
    with pytest.raises(ValueError, match="Only 0"):
        recent.prepare(path, tmp_path / "rich", count=1)
    m = recent.prepare(path, tmp_path / "long", count=1, coverage="dialogue", before_minutes=5, after_minutes=15)
    _, sessions, _, evidence = historical.load_prepared(tmp_path / "long")
    assert any(r.id == "later-edit" for r in sessions[0].activity)
    assert m["selection"]["coverage"] == "dialogue"
    assert any("5 minutes before and 15 after" in w for w in evidence[0]["warnings"])


def test_exclusions_follow_page_identity_across_exports_and_notebook_scopes(tmp_path):
    events = invented_rows()
    path = tmp_path / "first.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in events))
    recent.prepare(path, tmp_path / "first", count=1)
    # Pseudonyms change between private exports; notebook tabs on the same page
    # must still be excluded, regardless of the source file or model result.
    for row in events:
        row["user_email"] = "STU-ANOTHER-EXPORT-PSEUDONYM"
        row["payload"]["notebook_session_id"] = "another-notebook-on-same-page"
    path = tmp_path / "second.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in events))
    with pytest.raises(ValueError, match="previously_analyzed_page_scopes"):
        recent.prepare(path, tmp_path / "second", count=1, exclude_prepared=[tmp_path / "first"])
    assert not (tmp_path / "second").exists()
