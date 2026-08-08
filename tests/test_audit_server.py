import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from src.eval.audit_server import build_audit_metadata, build_payload, make_handler
from src.ingest.rawlog import Conversation, Turn
from src.labeling.draft import MessageLabels
from src.labeling.schema import LabelDef, LabelSchema


def _snapshot(tmp_path: Path) -> Path:
    turns = []
    for i in range(30):
        turns.append(Turn(index=2 * i, role="student",
                          text=f"invented q{i}", student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"a{i}"))
    conv = Conversation(conv_id="c", chatlog_id=1, notebook=None,
                        started_at=None, turns=turns)
    schema = LabelSchema(instructor_intent="i", labels=[
        LabelDef(name="x", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n"),
        LabelDef(name="y", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n")])
    rows = [MessageLabels(chatlog_id=1, message_index=2 * i,
                          labels={"x": i < 5, "y": False},
                          rationales={"x": "r", "y": "r"},
                          no_label_fits=(i == 6))
            for i in range(30)]
    d = tmp_path / "snap"
    d.mkdir()
    (d / "conversations.jsonl").write_text(conv.model_dump_json() + "\n")
    (d / "schema.json").write_text(schema.model_dump_json())
    (d / "labels.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in rows))
    (d / "manifest.json").write_text(json.dumps({
        "snapshot_id": d.name,
        "schema_version": schema.version_id,
        "classifier_hash": "abc123",
    }))
    return d


def test_per_label_payload_is_blind_and_sized(tmp_path):
    snap = _snapshot(tmp_path)
    payload, strata = build_payload(snap, n=25, seed=0, n_per_label=8)
    assert [len(l["keys"]) for l in payload["labels"]] == [8, 8]
    # strata never enter the page payload (invariant 8)
    assert "strata" not in payload
    assert "model-positive" not in json.dumps(payload)
    # ...but are recorded per label for scoring
    assert "model-positive" in json.dumps(strata["x"])
    # nofit pass covers the union of sampled keys
    union = {k for l in payload["labels"] for k in l["keys"]}
    assert set(payload["nofit_keys"]) == union
    assert set(payload["msgs"]) == union


def test_label_subset_and_legacy_mode(tmp_path):
    snap = _snapshot(tmp_path)
    payload, _ = build_payload(snap, n=25, seed=0, n_per_label=6,
                               only_labels=["x"])
    assert [l["name"] for l in payload["labels"]] == ["x"]
    legacy, strata = build_payload(snap, n=10, seed=0)
    assert [len(l["keys"]) for l in legacy["labels"]] == [10, 10]
    assert "_message" in strata


def test_http_save_writes_rows_strata_and_metadata(tmp_path):
    snap = _snapshot(tmp_path)
    payload, strata = build_payload(snap, n=25, seed=7, n_per_label=8)
    metadata = build_audit_metadata(
        snap, payload, annotator="steven", seed=7, n=25,
        n_per_label=8, exclude_review_sample_size=6,
        profile_path=Path("profiles/dsc10.json"), only_labels=None)
    out = tmp_path / "audit" / snap.name / "human-labels-steven.json"
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), make_handler(payload, strata, out, metadata))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        conn = HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/")
        res = conn.getresponse()
        html = res.read().decode()
        assert res.status == 200
        assert "model-positive" not in html
        conn.close()

        rows = [{"key": [1, 0], "labels": {"x": True},
                 "no_label_fits": False}]
        conn = HTTPConnection(host, port, timeout=2)
        conn.request("POST", "/save", body=json.dumps(rows),
                     headers={"content-type": "application/json"})
        res = conn.getresponse()
        res.read()
        assert res.status == 200
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    saved = json.loads(out.read_text())
    assert saved["rows"] == rows
    assert saved["strata"] == strata
    assert saved["metadata"] == metadata
    assert saved["metadata"]["snapshot_id"] == snap.name
    assert saved["metadata"]["classifier_hash"] == "abc123"
    assert saved["metadata"]["annotator"] == "steven"
    assert saved["metadata"]["audited_labels"] == ["x", "y"]
    assert saved["metadata"]["sample_mode"] == "per-label"
