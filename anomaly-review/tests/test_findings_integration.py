"""Offline integration checks using authored events, never private course records."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from session_review.findings import analyze_sessions as analyzer
from session_review.findings import bundle, historical, runner
from session_review.findings.cli import main
from session_review.findings.contract import ReviewBundle


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "findings"


def authored_rows(count=3):
    result = []
    for i in range(count):
        common = {"conversation_id": f"CONV-{i}", "notebook": "lab1.ipynb", "mode": "tutor"}
        for kind, content, minute in [("tutor_query", {"question": f"Question {i}"}, 1),
                                      ("tutor_response", {"response": "A hint"}, 2),
                                      ("tutor_notebook_info", {"initial_notebook_json": "invented snapshot"}, 3)]:
            result.append({"id": len(result) + 1, "event_type": kind, "user_email": f"STU-{i}",
                "created_at": f"2026-05-01T12:0{minute}:00+00:00", "payload": {**common, **content}})
        result.append({"id": len(result) + 1, "event_type": "autograder_info", "user_email": f"STU-{i}",
            "created_at": "2026-05-01T12:04:00+00:00", "payload": {"notebook": "lab1.ipynb", "success": False, "grader_id": "q2"}})
    return result


def prepared(tmp_path, rows=None):
    source = tmp_path / "events.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in (rows if rows is not None else authored_rows())))
    target = tmp_path / "prepared"
    historical.prepare(source, target, count=2)
    return target


def test_historical_adapter_preserves_context_without_fabricating_actions(tmp_path):
    folder = prepared(tmp_path)
    manifest, sessions, context, evidence = historical.load_prepared(folder)
    assert len(sessions) == 2
    assert manifest["quality"]["input_lines"] == manifest["quality"]["accepted_lines"] == 12
    assert all(not session.activity for session in sessions)
    assert all(message.question_id is None for session in sessions for message in session.messages)
    assert all(item["links"] == [] for item in evidence)
    for ctx in context.values():
        assert {event["kind"] for event in ctx["events"]} == {"notebook_snapshot", "check_result"}
        assert all(source["timestamp_basis"] == "database_created_at" for source in ctx["sources"].values())
    doc = bundle.build(sessions, input_hash=manifest["input_file_sha256"], context=context)
    assert all(session["active_time"]["status"] == "unknown" for session in doc["sessions"])
    assert all(session["analysis"]["state"] == "not_analyzed" and session["question_id"] is None for session in doc["sessions"])
    assert all(session["failed_checks_after_help"]["value"] is None for session in doc["sessions"])


def test_selection_is_deterministic_and_counts_duplicate_rows(tmp_path):
    events = authored_rows()
    events.append(copy.deepcopy(events[0]))
    source = tmp_path / "events.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in events))
    a = historical.prepare(source, tmp_path / "a", count=2, seed=9)
    b = historical.prepare(source, tmp_path / "b", count=2, seed=9)
    assert a == b
    assert a["quality"]["invalid_or_duplicate_lines"] == 1
    assert a["quality"]["input_lines"] == a["quality"]["accepted_lines"] + 1


def test_preparation_rejects_conflicting_accounts_and_oversized_inputs(tmp_path):
    events = authored_rows()
    events[1]["user_email"] = "OTHER-ACCOUNT"
    source = tmp_path / "events.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in events))
    doc = historical.prepare(source, tmp_path / "a", count=2)
    assert doc["conversation_exclusions"]["conflicting_identity"] == 1
    events[4]["payload"]["question"] = "x" * (historical.MAX_CHARACTERS + 1)
    source.write_text("".join(json.dumps(row) + "\n" for row in events))
    with pytest.raises(ValueError, match="Only 1 eligible"):
        historical.prepare(source, tmp_path / "b", count=2)


def test_missing_notebook_on_reply_does_not_hide_conflicting_or_oversized_content(tmp_path):
    events = authored_rows()
    del events[1]["payload"]["notebook"]
    events[1]["payload"]["response"] = "x" * (historical.MAX_CHARACTERS + 1)
    source = tmp_path / "events.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in events))
    doc = historical.prepare(source, tmp_path / "a", count=2)
    assert doc["conversation_exclusions"]["oversized_dialogue"] == 1
    assert "CONV-0" not in doc["selected_session_ids"]


def test_snapshot_excerpt_is_bounded_and_never_becomes_a_revision():
    payload = {"initial_notebook_json": json.dumps({"cells": [
        {"cell_type": "code", "source": ["x = 1\n", "print(x)"]},
        {"cell_type": "code", "source": "z" * 10000},
    ]})}
    excerpt = historical.snapshot_excerpt(payload)
    assert "x = 1" in excerpt and "Display excerpt only" in excerpt
    assert len(excerpt) < 5200
    assert "Capture format is unavailable" in historical.snapshot_excerpt({})


def test_changed_prepared_context_is_refused_before_analysis(tmp_path):
    folder = prepared(tmp_path)
    path = folder / "context.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="evidence changed"):
        historical.load_prepared(folder)


def test_model_receipts_are_reused_and_failures_are_not_resent(tmp_path):
    folder = prepared(tmp_path)
    _, sessions, _, evidence = historical.load_prepared(folder)
    calls = []
    def generate(item, model):
        calls.append(item["session_id"])
        if len(calls) == 1:
            raise RuntimeError("private provider diagnostic must not be stored")
        return analyzer.Assessment(session_id=item["session_id"], decision="no_supported_finding", summary="No supported issue.")
    output = tmp_path / "analysis"
    results = runner.run(output, sessions, evidence, model="authored-model", send=True, generate=generate)
    assert len(calls) == 2
    assert sum(result["validation_status"] == "valid" for result in results.values()) == 1
    again = runner.run(output, sessions, evidence, model="authored-model", send=True,
                       generate=lambda *_: pytest.fail("A saved request was resent"))
    assert results == again
    assert all("private provider diagnostic" not in p.read_text() for p in output.glob("*.json"))
    with pytest.raises(ValueError, match="configuration changed"):
        runner.run(output, sessions, evidence, model="changed-model", send=True, generate=generate)
    assert len(calls) == 2


def test_interrupted_request_is_preserved_not_retried(tmp_path):
    folder = prepared(tmp_path)
    _, sessions, _, evidence = historical.load_prepared(folder)
    output = tmp_path / "analysis"
    with pytest.raises(KeyboardInterrupt):
        runner.run(output, sessions, evidence, model="authored", send=True,
                   generate=lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    saved = runner.saved_results(output, sessions, evidence, "authored")
    assert list(saved.values())[0]["decision"] == "insufficient_evidence"
    assert "Interrupted" in list(saved.values())[0]["validation_errors"][0]


def test_offline_demo_contract_and_recovery_evidence(tmp_path):
    path = tmp_path / "demo.json"
    assert main(["demo", "--output", str(path)]) == 0
    doc = ReviewBundle.model_validate_json(path.read_bytes())
    assert len(doc.sessions) == 6
    assert doc.sessions[-1].analysis.findings[0].recovery_evidence_ids
    assert all(s.analysis.source.startswith("authored") for s in doc.sessions)
    # The checked-in browser contract and demo must come from this exact exporter.
    frontend = Path(__file__).resolve().parents[1] / "frontend" / "src"
    assert json.loads((frontend / "review-schema.json").read_text()) == ReviewBundle.model_json_schema()
    assert json.loads((frontend / "findings-demo.synthetic.json").read_text()) == json.loads(path.read_text())
    with pytest.raises(SystemExit):
        main(["demo", "--output", str(path)])


def test_contract_rejects_fabricated_evidence_and_unsafe_result_states(tmp_path):
    folder = prepared(tmp_path)
    manifest, sessions, context, _ = historical.load_prepared(folder)
    doc = bundle.build(sessions, input_hash=manifest["input_file_sha256"], context=context)
    changed = copy.deepcopy(doc)
    changed["sessions"][0]["source_event_refs"].append("FAKE")
    with pytest.raises(ValueError, match="missing timeline"):
        ReviewBundle.model_validate(changed)
    changed = copy.deepcopy(doc)
    changed["sessions"][0]["flagged"] = True
    with pytest.raises(ValueError, match="Flag status"):
        ReviewBundle.model_validate(changed)
