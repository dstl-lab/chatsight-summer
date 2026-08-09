"""Hermetic tests for the labeling web UI. No DB, no Gemini, no network."""
from pathlib import Path

import pytest

from src.labeling.cli import ACCEPT_NOTE
from src.labeling.webapp import LoopSession, PhaseError
from tests.test_cli import make_fake_generate
from tests.test_sampler import CONVS


def make_session(tmp_path: Path, workers: int = 8) -> LoopSession:
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
        workers=workers,
        profiles_dir=tmp_path / "profiles",
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
    from src.labeling.course import DSC10_PROFILE
    schema_gen = make_fake_generate()
    from src.labeling.elicit import draft_schema
    schema = draft_schema("intent", DSC10_PROFILE, schema_gen)
    draft_labels(sample, schema, DSC10_PROFILE, schema_gen,
                 on_progress=lambda done, total: seen.append((done, total)))
    assert seen == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_status_steps_after_start(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    st = session.state()["status"]
    assert [s["key"] for s in st["steps"]] == ["count", "fetch", "schema",
                                               "label"]
    assert all(s["state"] == "done" for s in st["steps"])
    count = st["steps"][0]
    assert str(len(CONVS) + 3) in count["name"]       # "Counted N conversations"
    fetch = st["steps"][1]
    assert "4" in fetch["name"]                      # "Fetched 4 conversations"
    assert fetch["progress"] == {"done": 4, "total": 4}
    label = st["steps"][3]
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
    # workers=1: ordering assertions below assume sequential completion,
    # which real parallel fan-out (workers > 1) does not guarantee.
    session = make_session(tmp_path, workers=1)
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
    session.schema = revise_schema(session.schema, "split it",
                                   session.profile, session.generate)
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


def test_retry_banner_cleared_by_fresh_actions(tmp_path):
    """A retry banner set before a run dies must not survive into a fresh
    action (start/tweak/accept) or a retry_step() re-entry — otherwise a
    stale 'retry 4 of 4' banner renders over an unrelated, healthy run."""
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.note_retry({"attempt": 4, "max": 4, "wait_s": 8.0})
    assert session.state()["status"]["retry"] is not None
    session.tweak("split it")
    assert session.state()["status"]["retry"] is None

    # same via retry_step() on an error
    session2 = make_session(tmp_path)
    session2.generate = make_flaky_generate(fail_at=1)
    session2.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert session2.state()["phase"] == "error"
    session2.note_retry({"attempt": 4, "max": 4, "wait_s": 8.0})
    session2.generate = make_fake_generate()
    session2.retry_step()
    assert session2.state()["status"]["retry"] is None


# --- resumable errors --------------------------------------------------------


def make_flaky_generate(fail_at: int):
    """Delegates to make_fake_generate() but raises on the fail_at-th
    labeling call (schema calls never fail)."""
    inner = make_fake_generate()
    label_calls = {"n": 0}

    def gen(prompt, response_model):
        from src.labeling.draft import SingleLabelVerdict
        # Count only the single-label call, one per message (this test's
        # schema always has exactly one label) — so fail_at still means
        # "the fail_at-th sample message dies," matching the old
        # one-call-per-message semantics the test's comments describe.
        if response_model is SingleLabelVerdict:
            label_calls["n"] += 1
            if label_calls["n"] == fail_at:
                raise RuntimeError("boom")
        return inner(prompt, response_model)
    return gen


def test_error_keeps_partial_labels_and_retry_resumes(tmp_path):
    # workers=1: labeled_count assertion below assumes sequential completion.
    session = make_session(tmp_path, workers=1)
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


def test_summary_only_in_done(tmp_path):
    session = make_session(tmp_path)
    assert session.state()["summary"] is None
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert session.state()["summary"] is None          # review
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    summary = s["summary"]
    assert summary["totals"]["messages"] == 13         # corpus of CONVS[:4]
    assert [p["name"] for p in summary["per_label"]] == ["label-v1"]
    assert summary["coverage"] is not None
    session.quit()
    assert session.state()["summary"] is None          # reset clears it


def test_summary_includes_classifier_hash_and_model(tmp_path):
    from src.labeling.draft import classifier_hash
    from src.labeling.llm import DEFAULT_MODEL

    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.accept()
    s = session.state()
    classifier = s["summary"]["classifier"]
    assert set(classifier) == {"hash", "model", "profile_id", "profile2_id"}
    assert classifier["model"] == DEFAULT_MODEL
    assert classifier["hash"] == classifier_hash(session.schema, DEFAULT_MODEL,
                                                 session.profile)
    assert classifier["profile_id"] == session.profile.profile_id
    assert classifier["profile2_id"] is None


def test_done_summary_carries_profile_id(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.accept()
    assert session.state()["summary"]["classifier"]["profile_id"] == \
        session.profile.profile_id


def test_examples_endpoint(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    assert client.get("/api/examples", params={"label": "x"}).status_code == 409
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    client.post("/api/accept")
    assert client.get("/api/state").json()["phase"] == "done"
    r = client.get("/api/examples",
                   params={"label": "label-v1", "n": 3, "seed": 1})
    assert r.status_code == 200
    ex = r.json()["examples"]
    assert 0 <= len(ex) <= 3
    assert all(set(e) == {"text", "rationale", "conv", "week"} for e in ex)
    assert client.get("/api/examples",
                      params={"label": "nope"}).status_code == 404


def test_examples_endpoint_clamps_n(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    client.post("/api/accept")
    for n in (-1, 100000):
        r = client.get("/api/examples",
                       params={"label": "label-v1", "n": n, "seed": 1})
        assert r.status_code == 200
        ex = r.json()["examples"]
        assert 0 <= len(ex) <= 25


# --- /api/peek (first-load data peek) --------------------------------------

def test_peek_returns_plain_word_stratified_messages(tmp_path):
    session = make_session(tmp_path)
    out = session.peek(n=3, seed=0)
    assert len(out["messages"]) == 3
    for m in out["messages"]:
        assert m["text"]
        assert " · " in m["stratum"]      # plain words with a separator...
        assert "/" not in m["stratum"]    # ...never the raw "short/early" key
    assert out["total_messages"] == sum(len(c.student_turns) for c in CONVS)


def test_peek_rejected_outside_idle(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.peek()


def test_peek_does_not_mutate_session_state(tmp_path):
    session = make_session(tmp_path)
    session.peek()
    assert session.state()["phase"] == "idle"
    assert session.conversations == []    # display-only: nothing retained


def test_peek_fetch_is_capped_at_40(tmp_path):
    session = make_session(tmp_path)
    seen = {}
    orig = session.fetch

    def spy(url, limit, on_progress=None):
        seen["limit"] = limit
        return orig(url, limit, on_progress)

    session.fetch = spy
    session.peek()
    assert seen["limit"] == 40


def test_peek_endpoint_shape_and_phase_guard(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    r = client.get("/api/peek?n=2&seed=1")
    assert r.status_code == 200
    assert len(r.json()["messages"]) == 2
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert client.get("/api/peek").status_code == 409


# --- abstention feed ---------------------------------------------------------


def make_abstaining_generate():
    """Every coverage check abstains, for exercising the abstention feed.
    Invented text only (CLAUDE.md rule 4: no student data in fixtures)."""
    inner = make_fake_generate()

    def gen(prompt, response_model):
        from src.labeling.draft import CoverageVerdict
        if response_model is CoverageVerdict:
            return CoverageVerdict(no_label_fits=True,
                                   note="asks about grades")
        return inner(prompt, response_model)
    return gen


def test_state_carries_abstention_feed(tmp_path):
    # workers=1: ordering assertion below (recent newest-first) assumes
    # sequential completion.
    session = make_session(tmp_path, workers=1)
    session.generate = make_abstaining_generate()
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    state = session.state()
    ab = state["status"]["abstention"]
    assert ab["count"] == len(session.labeled)
    assert ab["recent"][0]["note"] == "asks about grades"
    assert all(set(r) == {"text", "note"} for r in ab["recent"])
    assert len(ab["recent"]) <= 3


def test_explore_reaches_profile_review_with_draft(tmp_path):
    session = make_session(tmp_path)
    session.explore_course("dsc10", [{"name": "syllabus.md", "text": "babypandas"}])
    s = session.state()
    assert s["phase"] == "profile_review"
    draft = s["profile"]["draft"]
    assert [c["name"] for c in draft["concepts"]] == ["groupby", "loops"]
    assert draft["affect"][0]["name"] == "frustrated"
    assert draft["intent"][0]["name"] == "wants-hint"
    assert (tmp_path / "profiles" / "dsc10-draft.json").exists()
    # materials text never appears in any state payload (rule 4)
    import json as j
    assert "babypandas" not in j.dumps(s)


def test_explore_phase_guards(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.explore_course("dsc10", [])   # review: no explore
    session.quit()
    session.explore_course("dsc10", [])
    with pytest.raises(PhaseError):
        session.start("intent")               # profile_review: no labeling run
    with pytest.raises(PhaseError):
        session.explore_course("dsc10", [])   # no double-explore


def _explored(tmp_path):
    session = make_session(tmp_path)
    session.explore_course("dsc10", [])
    return session


def test_accept_profile_applies_surgery_and_persists(tmp_path):
    session = _explored(tmp_path)
    session.accept_profile(deleted={"concepts": ["loops"], "affect": [],
                                    "intent": []},
                           promoted=["groupby"])
    s = session.state()
    assert s["phase"] == "idle"
    acc = s["profile"]["accepted"]
    assert acc["concepts"] == 1 and acc["promoted"] == 1
    from src.labeling.profile2 import load_profile
    v2 = load_profile(tmp_path / "profiles" / "dsc10.json")
    assert v2.accepted
    assert [c.name for c in v2.concepts] == ["groupby"]
    assert v2.concepts[0].promoted
    assert v2.concepts[0].positive_criteria      # template criteria filled
    assert v2.concepts[0].negative_criteria


def test_accept_profile_is_deterministic_no_llm(tmp_path):
    session = _explored(tmp_path)
    calls_before = session.generate.schema_calls
    session.accept_profile(deleted={}, promoted=[])
    assert session.generate.schema_calls == calls_before


def test_accept_profile_rejects_internal_collision(tmp_path):
    session = _explored(tmp_path)
    # sabotage: duplicate name across layers
    dup = session.profile2_draft.affect_labels[0].model_copy(
        update={"name": "wants-hint"})
    session.profile2_draft = session.profile2_draft.model_copy(
        update={"affect_labels": [dup]})
    with pytest.raises(ValueError, match="wants-hint"):
        session.accept_profile(deleted={}, promoted=[])
    assert session.state()["phase"] == "profile_review"


def test_discard_returns_to_setup_state(tmp_path):
    session = _explored(tmp_path)
    session.discard_profile()
    s = session.state()
    assert s["phase"] == "idle"
    assert s["profile"]["draft"] is None
    session.explore_course("dsc10", [])
    session.accept_profile(deleted={}, promoted=[])
    session.discard_profile()                    # from idle-with-profile
    assert session.state()["profile"]["accepted"] is None


def test_no_abstention_state_is_zeroed(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert session.state()["status"]["abstention"] == {"count": 0,
                                                        "recent": []}


def test_tweak_clears_abstention_feed(tmp_path):
    session = make_session(tmp_path, workers=1)
    session.generate = make_abstaining_generate()
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert session.state()["status"]["abstention"]["count"] > 0
    session.generate = make_fake_generate()  # new schema's checks all fit
    session.tweak("split it")
    assert session.state()["status"]["abstention"] == {"count": 0,
                                                        "recent": []}


def _accepted_session(tmp_path):
    session = _explored(tmp_path)
    session.accept_profile(deleted={}, promoted=["groupby"])
    return session


def test_run_with_profile_composes_at_accept(tmp_path):
    session = _accepted_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    review_names = [l["name"] for l in session.state()["schema"]["labels"]]
    assert review_names == ["label-v1"]          # review: instructor-only
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    names = [l["name"] for l in s["schema"]["labels"]]
    assert "groupby" in names and "frustrated" in names \
        and "wants-hint" in names                 # composed for the mass pass
    import json as j
    manifest = j.loads(
        (Path(s["snapshot_path"]) / "manifest.json").read_text())
    assert manifest["profile2_id"] == session.profile2.profile_id
    assert s["summary"]["classifier"]["profile_id"] == session.profile.profile_id


def test_run_without_profile_unchanged(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.accept()
    import json as j
    manifest = j.loads((Path(session.state()["snapshot_path"])
                        / "manifest.json").read_text())
    assert manifest["profile2_id"] is None
