"""Hermetic tests for the labeling web UI. No DB, no Gemini, no network."""
from pathlib import Path

import pytest

from src.labeling.cli import ACCEPT_NOTE
from src.labeling.webapp import LoopSession, PhaseError
from tests.test_cli import make_fake_generate
from tests.test_sampler import CONVS


def make_session(tmp_path: Path) -> LoopSession:
    def fake_fetch(url, limit, on_progress=None):
        convs = CONVS[:limit] if limit else CONVS
        if on_progress:
            for i in range(len(convs)):
                on_progress(i + 1, len(convs))
        return convs
    return LoopSession(
        fetch=fake_fetch,
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
    def boom(url, limit, on_progress=None):
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


def test_status_steps_after_start(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    st = session.state()["status"]
    assert [s["key"] for s in st["steps"]] == ["fetch", "schema", "label"]
    assert all(s["state"] == "done" for s in st["steps"])
    fetch = st["steps"][0]
    assert "4" in fetch["name"]                      # "Fetched 4 conversations"
    assert fetch["progress"] == {"done": 4, "total": 4}
    label = st["steps"][2]
    assert label["progress"] == {"done": 4, "total": 4}
    assert label["started_at"] is not None
    assert st["retry"] is None


def test_status_steps_after_accept_and_review_labels_reused(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    labeled_after_review = len(session.labeled)
    session.accept()
    st = session.state()["status"]
    assert [s["key"] for s in st["steps"]] == ["save", "sample", "label",
                                               "snapshot"]
    assert all(s["state"] == "done" for s in st["steps"])
    label = st["steps"][2]
    # corpus total, with the review-sample labels counted as already done
    assert label["progress"]["done"] == label["progress"]["total"]
    assert label["progress"]["total"] >= labeled_after_review
    # every corpus message labeled exactly once (review labels reused, not redone)
    keys = [(r.chatlog_id, r.message_index) for r in session.labeled]
    assert len(keys) == len(set(keys)) == label["progress"]["total"]
    assert session.state()["snapshot_path"] is not None


def test_recent_holds_last_three_newest_first(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    recent = session.state()["status"]["recent"]
    assert len(recent) == 3
    assert all(set(r) == {"text", "labels"} for r in recent)
    # newest-first, positionally: labeling proceeds in session.sample order
    # (draft_labels/_label_incremental label sequentially), so the last three
    # sample messages appear in recent, most-recently-labeled first.
    labeled_order = session.sample
    assert recent[0]["text"] == labeled_order[-1].text
    assert recent[1]["text"] == labeled_order[-2].text
    assert recent[2]["text"] == labeled_order[-3].text


def test_tweak_clears_labels_and_recent_for_new_schema(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.tweak("split it")
    st = session.state()
    assert st["phase"] == "review"
    assert [s["key"] for s in st["status"]["steps"]] == ["schema", "label"]
    # all 4 sample messages relabeled under the new schema (not skipped)
    assert len(session.labeled) == 4
    assert all("label-v2" in r.labels for r in session.labeled)


def test_label_incremental_guards_against_stale_schema_labels(tmp_path):
    """CLAUDE.md rule 2 / invariant 6: the manifest stamps a single
    schema_version/classifier_hash over the whole snapshot, so accumulated
    labels must never survive an untracked schema swap. `tweak()` clears
    self.labeled itself; this test proves _label_incremental's own guard
    (self._labeled_schema) catches a swap that skips that clear, so a future
    code path (not just tweak) can't silently mix label vintages."""
    from src.labeling.elicit import revise_schema

    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    v1_labeled = list(session.labeled)
    assert len(v1_labeled) == 4
    assert session._labeled_schema == session.schema.version_id

    # Simulate a future path swapping the schema WITHOUT clearing
    # self.labeled/self.recent (i.e. without going through tweak()).
    session.schema = revise_schema(session.schema, "split it", session.generate)
    assert session._labeled_schema != session.schema.version_id

    session._label_incremental(session.sample, "label")

    # Stale v1 labels were not reused: every message was relabeled under the
    # new schema, and the label objects are fresh (not the old v1 ones).
    assert len(session.labeled) == 4
    assert all("label-v2" in r.labels for r in session.labeled)
    assert session.labeled != v1_labeled
    assert session._labeled_schema == session.schema.version_id
    # recent was cleared alongside labeled, so it now reflects only the
    # relabeling pass just run (not stale entries from before the swap)
    assert len(session.recent) == 3
    sample_texts = {m.text for m in session.sample}
    assert all(r["text"] in sample_texts for r in session.recent)


def test_note_retry_surfaces_in_state(tmp_path):
    session = make_session(tmp_path)
    session.note_retry({"attempt": 2, "max": 4, "wait_s": 4.0})
    assert session.state()["status"]["retry"] == {
        "attempt": 2, "max": 4, "wait_s": 4.0}
    session.note_retry(None)
    assert session.state()["status"]["retry"] is None


# --- resumable errors --------------------------------------------------------


def make_flaky_generate(fail_at: int):
    """Delegates to make_fake_generate() but raises on the fail_at-th
    labeling call (schema calls never fail)."""
    inner = make_fake_generate()
    label_calls = {"n": 0}

    def gen(prompt, response_model):
        from src.labeling.draft import LabelVerdicts
        if response_model is LabelVerdicts:
            label_calls["n"] += 1
            if label_calls["n"] == fail_at:
                raise RuntimeError("boom")
        return inner(prompt, response_model)
    return gen


def test_error_keeps_partial_labels_and_retry_resumes(tmp_path):
    session = make_session(tmp_path)
    session.generate = make_flaky_generate(fail_at=3)  # 3rd sample msg dies
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    s = session.state()
    assert s["phase"] == "error"
    assert "boom" in s["error"]
    assert s["recovery"]["can_retry"] is True
    assert s["recovery"]["labeled_count"] == 2        # first two survived
    session.retry_step()                              # flaky gen now passes
    s = session.state()
    assert s["phase"] == "review"
    assert s["error"] is None
    # exactly 4 labels, none duplicated
    keys = [(r.chatlog_id, r.message_index) for r in session.labeled]
    assert len(keys) == len(set(keys)) == 4


def test_error_during_mass_label_retry_completes_snapshot(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    total_sample_labels = len(session.labeled)
    session.generate = make_flaky_generate(fail_at=1)  # 1st corpus call dies
    session.accept()
    assert session.state()["phase"] == "error"
    assert len(session.labeled) == total_sample_labels  # review work kept
    session.retry_step()
    s = session.state()
    assert s["phase"] == "done"
    assert s["snapshot_path"] is not None


def test_back_to_review_from_error(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.generate = make_flaky_generate(fail_at=1)
    session.accept()
    assert session.state()["phase"] == "error"
    assert session.state()["recovery"]["can_review"] is True
    session.back_to_review()
    s = session.state()
    assert s["phase"] == "review"
    assert s["error"] is None


def test_recovery_invalid_outside_error(tmp_path):
    session = make_session(tmp_path)
    with pytest.raises(PhaseError):
        session.retry_step()
    with pytest.raises(PhaseError):
        session.back_to_review()
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.retry_step()          # review is not error


def test_api_retry_and_back_to_review_endpoints(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    assert client.post("/api/retry").status_code == 409
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    session.generate = make_flaky_generate(fail_at=1)
    client.post("/api/accept")
    assert client.get("/api/state").json()["phase"] == "error"
    assert client.post("/api/back-to-review").status_code == 200
    assert client.get("/api/state").json()["phase"] == "review"
