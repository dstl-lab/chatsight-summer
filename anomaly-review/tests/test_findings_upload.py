"""Upload, durable jobs and local HTTP boundary; no database or real model calls."""
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from session_review.findings import analyze_sessions as analyzer
from session_review.findings import historical, runner, web
from session_review.findings.contract import ReviewBundle

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/findings/pr100-upload.synthetic.jsonl"


@pytest.fixture
def jobs(tmp_path):
    calls = []
    def generate(evidence, model):
        calls.append(evidence["session_id"])
        return analyzer.Assessment(session_id=evidence["session_id"], decision="no_supported_finding", summary="Authored test response, not model inference.")
    store = web.Jobs(tmp_path / "private", generate=generate)
    yield store, calls
    store.executor.shutdown(wait=True)


def ready(store, *, data=None):
    state = store.upload(data or FIXTURE.read_bytes(), "../fictional.jsonl", count=1, minutes=25)
    store.futures[-1].result(timeout=5)
    assert store.summary(state["id"])["status"] == "ready"
    return state["id"]


def test_upload_preview_analysis_reopen_and_duplicate_send_guard(jobs):
    store, calls = jobs
    job_id = ready(store, data=gzip.compress(FIXTURE.read_bytes()))
    assert calls == []
    view = ReviewBundle.model_validate_json(store.get_bundle(job_id))
    assert view.sessions[0].analysis.state == "not_analyzed"
    state = store.summary(job_id)
    assert state["filename"] == "fictional.jsonl"
    assert state["source"]["events"] == 7 and state["eligible_sessions"] == 1
    assert (store.folder(job_id) / "source.jsonl.gz").stat().st_mode & 0o777 == 0o600
    store.start(job_id)
    store.futures[-1].result(timeout=5)
    assert store.summary(job_id)["status"] == "completed" and len(calls) == 1
    view = ReviewBundle.model_validate_json(store.get_bundle(job_id))
    assert view.sessions[0].analysis.state == "completed"
    assert store.get_bundle(job_id) == store.get_bundle(job_id)
    with pytest.raises(web.InputError, match="already running or finished"):
        store.start(job_id)
    assert len(calls) == 1


@pytest.mark.parametrize("data", [b'{}\n', b'{"sessions":[]}\n', b'not json', b'\x1f\x8bnot-a-valid-gzip'])
def test_legacy_results_and_corrupt_uploads_never_reach_the_model(jobs, data):
    store, calls = jobs
    state = store.upload(data, "bad.jsonl", count=1)
    store.futures[-1].result(timeout=5)
    assert store.summary(state["id"])["status"] == "failed"
    with pytest.raises(web.InputError):
        store.start(state["id"])
    assert calls == []


def test_decompression_and_line_budgets_are_enforced(tmp_path, monkeypatch):
    path = tmp_path / "too-large.jsonl.gz"
    path.write_bytes(gzip.compress(FIXTURE.read_bytes()))
    monkeypatch.setattr(web, "MAX_EXPANDED", 50)
    with pytest.raises(web.InputError, match="too large"):
        web.inspect_upload(path)


def test_insufficient_sessions_error_is_actionable_and_no_silent_truncation(jobs):
    store, calls = jobs
    state = store.upload(FIXTURE.read_bytes(), "small.jsonl", count=20)
    store.futures[-1].result(timeout=5)
    state = store.summary(state["id"])
    assert state["status"] == "failed" and "Only 1 eligible" in state["error"]
    assert calls == []


def test_restart_preserves_completed_results_without_a_key(jobs):
    store, calls = jobs
    job_id = ready(store)
    store.start(job_id); store.futures[-1].result(timeout=5)
    restarted = web.Jobs(store.root)
    try:
        assert restarted.summary(job_id)["status"] == "completed"
        assert restarted.get_bundle(job_id) == store.get_bundle(job_id)
        assert len(calls) == 1
    finally:
        restarted.executor.shutdown(wait=True)


def test_interrupted_preparation_is_not_offered_as_resumable_analysis(tmp_path):
    store = web.Jobs(tmp_path / "interrupted-upload")
    job_id = "f" * 32
    (store.root / job_id).mkdir()
    store.save(job_id, {"id": job_id, "status": "preparing", "created_at": "2026-10-16T12:00:00Z"})
    restarted = web.Jobs(store.root)
    try:
        state = restarted.summary(job_id)
        assert state["status"] == "failed" and "Upload the file again" in state["error"]
    finally:
        store.executor.shutdown(wait=True); restarted.executor.shutdown(wait=True)


def test_preview_needs_no_provider_key_and_missing_key_does_not_dispatch(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    store = web.Jobs(tmp_path / "no-credentials")
    try:
        job_id = ready(store)
        with pytest.raises(web.InputError, match="Database access is not needed"):
            store.start(job_id)
        assert store.summary(job_id)["status"] == "ready"
        assert not (store.folder(job_id) / "prepared/analysis").exists()
    finally:
        store.executor.shutdown(wait=True)


def test_provider_failure_is_saved_without_echoing_private_diagnostics(tmp_path):
    def failed_generate(*args):
        raise RuntimeError("private prompt or credential diagnostic")
    store = web.Jobs(tmp_path / "provider-failure", generate=failed_generate)
    try:
        job_id = ready(store)
        store.start(job_id); store.futures[-1].result(timeout=5)
        assert store.summary(job_id)["progress"]["failed"] == 1
        doc = ReviewBundle.model_validate_json(store.get_bundle(job_id))
        assert doc.sessions[0].analysis.state == "failed" and not doc.sessions[0].analysis.findings
        assert not any("private prompt or credential diagnostic" in p.read_text() for p in store.root.rglob("*.json"))
    finally:
        store.executor.shutdown(wait=True)


def test_interrupted_receipt_is_skipped_when_continuing(jobs):
    store, calls = jobs
    job_id = ready(store)
    folder = store.folder(job_id) / "prepared"
    _, sessions, _, evidence = historical.load_prepared(folder)
    output = folder / "analysis"; output.mkdir()
    config = runner.configuration(sessions, evidence, store.model)
    historical.private_json(output / "plan.json", config)
    historical.private_json(output / (historical.digest(sessions[0].session_id) + ".json"), {
        "status": "pending", "config_sha256": historical.digest(config), "evidence_sha256": historical.digest(evidence[0]), "assessment": None})
    state = store.read(job_id); state["status"] = "interrupted"; store.save(job_id, state)
    store.start(job_id); store.futures[-1].result(timeout=5)
    assert calls == []
    assert store.summary(job_id)["progress"]["failed"] == 1
    doc = ReviewBundle.model_validate_json(store.get_bundle(job_id))
    assert doc.sessions[0].analysis.state == "failed"


def test_http_workflow_rejects_foreign_origins_and_has_no_database_endpoint(jobs, tmp_path):
    store, calls = jobs
    frontend = tmp_path / "frontend"; frontend.mkdir(); (frontend / "index.html").write_text("fictional dashboard")
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    server.RequestHandlerClass = web.handler_for(store, frontend, server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    def get(path):
        with urlopen(base + path, timeout=5) as response: return json.load(response)
    def post(path, data=b"", **headers):
        req = Request(base + path, data=data, method="POST", headers={"X-Review-Request": "1", **headers})
        with urlopen(req, timeout=5) as response: return json.load(response)
    try:
        assert get("/api/status")["ready"]
        for path in ("/api/database", "/api/extract", "/%2e%2e/secrets"):
            with pytest.raises(HTTPError) as error: get(path)
            assert error.value.code == 404
        with pytest.raises(HTTPError) as error:
            post("/api/uploads", FIXTURE.read_bytes(), Origin="https://untrusted.example")
        assert error.value.code == 403 and not store.listing()
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + "/api/uploads", data=FIXTURE.read_bytes()), timeout=5)
        assert error.value.code == 403
        state = post("/api/uploads?count=1&minutes=25", FIXTURE.read_bytes(), **{"X-File-Name": "fictional.jsonl"})
        store.futures[-1].result(timeout=5)
        assert get("/api/jobs/" + state["id"])["status"] == "ready" and not calls
        post("/api/jobs/" + state["id"] + "/analyze")
        store.futures[-1].result(timeout=5)
        doc = get("/api/jobs/" + state["id"] + "/bundle")
        assert doc["sessions"][0]["analysis"]["state"] == "completed"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
