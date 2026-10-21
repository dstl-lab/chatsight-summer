"""Complete import coverage, linked-window boundaries, disk storage and reuse."""
from datetime import datetime, timezone
import gzip
import io
import json
from pathlib import Path

import pytest

from session_review.findings import bulk, historical, production, web
from session_review.findings.extract import export_all
from test_findings_extract import Database
from test_findings_upload import jobs

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/findings/pr100-upload.synthetic.jsonl"


def data(scopes=1):
    header = {"format": production.EXPORT_FORMAT, "since": production.DEPLOYED.isoformat(), "until": "2026-10-17T00:00:00Z"}
    lines = [json.dumps(header)]
    for i in range(scopes):
        for line in FIXTURE.read_text().splitlines():
            row = json.loads(line)
            row["id"] = f'{i}-{row["id"]}'
            for key in ("event_id", "analytics_session_id", "notebook_session_id"):
                row["payload"][key] += f"-{i}"
            lines.append(json.dumps(row))
    return ("\n".join(lines) + "\n").encode()


def upload(store, payload):
    state = store.upload_collection(io.BytesIO(payload), len(payload), "whole-week.jsonl", minutes=25)
    store.futures[-1].result(timeout=20)
    result = store.summary(state["id"])
    assert result["status"] == "ready", result
    return result


def test_all_scopes_become_bounded_review_batches_and_reopen_without_calls(jobs):
    store, calls = jobs
    payload = gzip.compress(data(21))
    state = upload(store, payload)
    assert calls == []
    assert state["coverage"]["tutor_requests"] == state["coverage"]["eligible"] == 21
    assert [b["count"] for b in state["batches"]] == [20, 1]
    assert state["source"]["events"] == 147
    assert len(store.listing()) == 1
    first_batch = state["batches"][0]["id"]
    assert not (store.folder(first_batch) / "bundle.private.json").exists()
    assert len(json.loads(store.get_bundle(first_batch))["sessions"]) == 20
    assert not calls
    assert store.upload_collection(io.BytesIO(payload), len(payload), "renamed.gz")["id"] == state["id"]
    store.start(state["id"]); store.futures[-1].result(timeout=20)
    finished = store.summary(state["id"])
    assert finished["status"] == "completed" and finished["progress"]["completed"] == 21
    assert len(calls) == 21
    for batch in finished["batches"]:
        assert json.loads(store.get_bundle(batch["id"]))["sessions"]


def test_overlapping_exports_reuse_identical_evidence_but_keep_new_windows(jobs):
    store, calls = jobs
    first = upload(store, data())
    store.start(first["id"]); store.futures[-1].result(timeout=10)
    second = upload(store, data(2))
    store.start(second["id"]); store.futures[-1].result(timeout=10)
    assert len(calls) == 2  # One earlier window reused, one newly observed window sent.


def test_every_request_is_accounted_for_including_ineligible_and_recent(jobs):
    store, calls = jobs
    rows = [json.loads(line) for line in data().splitlines()]
    query = next(r for r in rows[1:] if r["event_type"] == "tutor_query")
    for label, changes in (("missing", {"notebook_session_id": None}), ("other", {"mode": "other", "notebook_session_id": "another-notebook"}), ("recent", {"timestamp": "2026-10-16T23:59:00Z"})):
        new = json.loads(json.dumps(query)); new["id"] = label
        new["payload"].update(event_id=label, **changes)
        rows.append(new)
    state = upload(store, ("\n".join(map(json.dumps, rows)) + "\n").encode())
    assert state["coverage"] == {"tutor_requests": 4, "eligible": 1, "missing_scope": 1, "not_tutor_mode": 1, "awaiting_followup_window": 1}
    assert not calls


def test_multiple_requests_in_same_notebook_are_not_sampled_away(jobs):
    store, _ = jobs
    rows = [json.loads(line) for line in data().splitlines()]
    for row in list(rows[1:]):
        if row["event_type"] not in {"tutor_query", "tutor_response"}: continue
        new = json.loads(json.dumps(row)); new["id"] += "-second"
        p = new["payload"]; p["event_id"] += "-second"; p["request_id"] += "-second"; p["client_sequence"] += 100
        if isinstance(p.get("request"), dict): p["request"]["request_id"] = p["request_id"]
        rows.append(new)
    state = upload(store, ("\n".join(map(json.dumps, rows)) + "\n").encode())
    assert state["coverage"]["eligible"] == 2


def test_duplicate_records_deduplicate_but_conflicting_uuid_stops_import(tmp_path):
    rows = data().splitlines()
    path = tmp_path / "source.jsonl"
    redelivered = json.loads(rows[1])
    redelivered.update(id="new-db-receipt", created_at="2026-10-16T23:00:00Z")
    path.write_bytes(b"\n".join([*rows, json.dumps(redelivered).encode()]) + b"\n")
    result = bulk.index_source(path, tmp_path / "index.sqlite")
    assert result["events"] == 7 and result["duplicate_events"] == 1
    conflicting = json.loads(rows[1]); conflicting["payload"]["client_sequence"] = 999
    path.write_bytes(b"\n".join([*rows, json.dumps(conflicting).encode()]) + b"\n")
    with pytest.raises(ValueError, match="Conflicting"):
        bulk.index_source(path, tmp_path / "bad.sqlite")


def test_export_all_uses_observed_production_boundary_and_stable_pseudonyms(tmp_path):
    db = Database()
    key = tmp_path / "private.key"
    manifests = []
    for name in ("first", "second"):
        manifests.append(export_all(tmp_path / name, until=datetime(2026, 10, 17, tzinfo=timezone.utc), key_file=key, connect=lambda: db))
    assert db.readonly and db.closed
    selects = [(q, args) for q, args in db.queries if "SELECT" in q]
    assert len(selects) == 2 and all(args[0] == production.DEPLOYED for _, args in selects)
    assert all("LIMIT" not in q and "ANY" not in q for q, _ in selects)
    with gzip.open(tmp_path / "first/events.jsonl.gz", "rt") as f: first = list(map(json.loads, f))
    with gzip.open(tmp_path / "second/events.jsonl.gz", "rt") as f: second = list(map(json.loads, f))
    assert first == second and first[0]["format"] == production.EXPORT_FORMAT
    assert key.stat().st_mode & 0o777 == 0o600
    assert manifests[0]["event_count"] == 7
    indexed = bulk.index_source(tmp_path / "first/events.jsonl.gz", tmp_path / "real-format.sqlite")
    assert indexed["events"] == 7


def test_stream_upload_interrupt_never_creates_an_analyzable_job(jobs):
    store, calls = jobs
    with pytest.raises(web.InputError, match="interrupted"):
        store.upload_collection(io.BytesIO(b"tiny"), 100, "bad.jsonl")
    assert not store.listing() and not calls
