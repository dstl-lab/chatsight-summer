"""Hermetic tests for the labeling web UI. No DB, no Gemini, no network."""
from pathlib import Path

import pytest

from src.labeling.cli import ACCEPT_NOTE
from src.labeling.webapp import LoopSession, PhaseError
from tests.test_cli import make_fake_generate
from tests.test_sampler import CONVS


def make_session(tmp_path: Path) -> LoopSession:
    return LoopSession(
        fetch=lambda url, limit: CONVS[:limit] if limit else CONVS,
        count=lambda url: len(CONVS) + 3,   # 3 "excluded" beyond the fetch cap
        generate=make_fake_generate(),
        ext_db_url="postgresql+psycopg2://unused",
        data_dir=tmp_path,
        repo_sha="testsha",
        runner=lambda job: job(),           # synchronous in tests
    )


def test_initial_state_is_idle(tmp_path):
    s = make_session(tmp_path).state()
    assert s["phase"] == "idle"
    assert s["accept_note"] == ACCEPT_NOTE
    assert s["schema"] is None and s["sample"] is None


def test_start_reaches_review_with_schema_sample_provenance(tmp_path):
    session = make_session(tmp_path)
    session.start("what confuses students", max_conversations=4,
                  sample_size=4, seed=0)
    s = session.state()
    assert s["phase"] == "review"
    assert s["schema"]["labels"][0]["name"] == "label-v1"
    assert s["schema"]["intent"] == "what confuses students"
    assert len(s["sample"]) == 4
    assert all("stratum" in m and "text" in m for m in s["sample"])
    assert s["provenance"] == {"fetched": 4, "total": len(CONVS) + 3,
                               "excluded": len(CONVS) + 3 - 4}


def test_tweak_produces_new_chained_schema_version(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    v1 = session.state()["schema"]["version_id"]
    session.tweak("split confusion by cause")
    s = session.state()
    assert s["phase"] == "review"
    assert s["schema"]["labels"][0]["name"] == "label-v2"
    assert s["schema"]["version_id"] != v1


def test_accept_emits_snapshot_and_saves_schema(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    snap = Path(s["snapshot_path"])
    assert (snap / "manifest.json").exists()
    assert list((tmp_path / "labeling" / "schemas").glob("*.json"))  # save_schema ran


def test_invalid_phase_actions_raise(tmp_path):
    session = make_session(tmp_path)
    with pytest.raises(PhaseError):
        session.tweak("nope")           # idle: no tweak
    with pytest.raises(PhaseError):
        session.accept()                # idle: no accept
    with pytest.raises(PhaseError):
        session.quit()                  # idle: nothing to quit
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.start("again")          # review: no restart without quit


def test_quit_resets_to_idle(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.quit()
    s = session.state()
    assert s["phase"] == "idle"
    assert s["schema"] is None and s["sample"] is None


def test_job_error_surfaces_and_quit_recovers(tmp_path):
    def boom(url, limit):
        raise RuntimeError("tunnel down")
    session = make_session(tmp_path)
    session.fetch = boom
    session.start("intent")
    s = session.state()
    assert s["phase"] == "error"
    assert "tunnel down" in s["error"]
    session.quit()
    assert session.state()["phase"] == "idle"


# --- API layer -------------------------------------------------------------

from fastapi.testclient import TestClient

from src.labeling.webapp import create_app


def test_api_happy_path(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    assert client.get("/api/state").json()["phase"] == "idle"
    r = client.post("/api/start", json={
        "intent": "what confuses students", "max_conversations": 4,
        "sample_size": 4, "seed": 0})
    assert r.status_code == 200
    s = client.get("/api/state").json()
    assert s["phase"] == "review"
    assert s["accept_note"] == ACCEPT_NOTE
    assert client.post("/api/tweak",
                       json={"feedback": "split it"}).status_code == 200
    assert client.post("/api/accept").status_code == 200
    s = client.get("/api/state").json()
    assert s["phase"] == "done"
    assert s["snapshot_path"] is not None


def test_api_invalid_phase_returns_409(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    assert client.post("/api/accept").status_code == 409
    assert client.post("/api/tweak", json={"feedback": "x"}).status_code == 409
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    assert client.post("/api/start", json={"intent": "i"}).status_code == 409
    assert client.post("/api/quit").status_code == 200
    assert client.get("/api/state").json()["phase"] == "idle"


def test_index_served(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    r = client.get("/")
    assert r.status_code == 200
    assert "label-loop" in r.text


# --- progress reporting ----------------------------------------------------

from src.labeling.draft import draft_labels
from src.labeling.sampler import stratified_sample


def test_draft_labels_reports_progress():
    sample = stratified_sample(CONVS, n=4, seed=0)
    seen: list[tuple[int, int]] = []
    schema_gen = make_fake_generate()
    from src.labeling.elicit import draft_schema
    schema = draft_schema("intent", schema_gen)
    draft_labels(sample, schema, schema_gen,
                 on_progress=lambda done, total: seen.append((done, total)))
    assert seen == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_state_exposes_progress_after_mass_label(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert session.state()["progress"] is not None  # review drafting reported
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    p = s["progress"]
    assert p["done"] == p["total"] > 0
