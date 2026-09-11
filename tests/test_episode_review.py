"""Review boundaries, using only invented dialogue."""
import copy
import json

import pytest
from fastapi.testclient import TestClient

from src.eval.episode_review import create_app
from src.labeling.episodes import episode_content_hash, rubric_hash


def _bundle(tmp_path):
    rubric = {
        "request": {"title": "Assistance requested", "options": {
            "explanation": "Asks for an explanation", "unclear": "Cannot tell"}},
        "tutor_response": {"title": "Tutor response", "options": {
            "hint": "Offers a hint", "unclear": "Cannot tell"}},
        "followup": {"title": "Student follow-up", "options": {
            "attempt": "Shows another attempt", "unclear": "Cannot tell",
            "no-followup-observed": "No follow-up is visible"}},
    }
    episodes = []
    for i, split in enumerate(["development", "holdout", "holdout", "holdout"]):
        turns = [
            {"id": f"{i}:1", "role": "student", "phase": "request",
             "text": "Why does this invented loop stop?", "at": None, "mode": "chat"},
            {"id": f"{i}:2", "role": "tutor", "phase": "response",
             "text": "Inspect the loop condition.", "at": "2026-01-01T12:00:00Z", "mode": "chat"},
            {"id": f"{i}:3", "role": "student", "phase": "followup",
             "text": "I changed the condition and tried again.", "at": None, "mode": "chat"},
        ]
        episodes.append({
            "id": f"ep-{i}", "split": split, "conversation_key": f"conversation-{i}",
            "notebook": "Invented notebook", "question_ref": "q1", "question_link": "",
            "context": [{"id": f"{i}:0", "role": "student", "text": "Earlier invented context",
                         "at": None, "mode": "chat"}],
            "turns": turns, "limitations": ["Code changes are not observed."],
            "legacy_labels": [{"turn_id": f"{i}:1", "labels": ["legacy-secret"]}],
            "annotation": {
                dim: {"value": value, "evidence": [{"turn_id": turns[j]["id"],
                        "quote": turns[j]["text"]}], "rationale": "machine-secret"}
                for j, (dim, value) in enumerate([
                    ("request", "explanation"), ("tutor_response", "hint"), ("followup", "attempt")])
            },
        })
    bundle = {"manifest": {"bundle_id": "invented-bundle", "snapshot_id": "invented-snapshot",
                           "seed": 7, "rubric_hash": rubric_hash(rubric),
                           "episode_content_hash": episode_content_hash(episodes),
                           "counts": {"development": 1, "holdout": 3}},
              "question": "What does the student visibly do next?", "rubric": rubric,
              "episodes": episodes}
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle))
    return path


def _client(path, **kwargs):
    return TestClient(create_app(path, reviewer="invented-reviewer", **kwargs),
                      base_url="http://127.0.0.1")


def _review(episode_id="ep-1"):
    return {"episode_id": episode_id, "judgments": {
        "request": {"value": "explanation", "evidence": [
            {"turn_id": "1:1", "quote": "invented loop"}], "rationale": "Visible question"}},
        "elapsed_ms": 1200, "complete": False,
        "instructor_action": {"text": "Clarify the loop condition", "evidence": [
            {"turn_id": "1:2", "quote": "loop condition"}]}}


def test_coding_stays_blind_after_save_and_only_serves_selected_split(tmp_path):
    path = _bundle(tmp_path)
    client = _client(path, task="coding")
    payload = client.get("/api/session").json()
    assert [ep["id"] for ep in payload["episodes"]] == ["ep-1", "ep-2", "ep-3"]
    assert "machine-secret" not in json.dumps(payload)
    assert "legacy-secret" not in json.dumps(payload)
    assert all("annotation" not in ep and "legacy_labels" not in ep for ep in payload["episodes"])
    assert client.post("/api/review", json=_review()).status_code == 200
    resumed = client.get("/api/session").json()
    assert "machine-secret" not in json.dumps(resumed)
    assert client.get("/reveal").status_code == 404
    assert client.get("/api/reveal").status_code == 404
    assert client.post("/api/review", json=_review("ep-0")).status_code == 422


def test_development_rejects_holdout_and_has_visible_drafts(tmp_path):
    path = _bundle(tmp_path)
    with pytest.raises(ValueError, match="development"):
        _client(path, task="development", split="holdout")
    payload = _client(path).get("/api/session").json()
    assert [ep["id"] for ep in payload["episodes"]] == ["ep-0"]
    assert payload["episodes"][0]["annotation"]["request"]["rationale"] == "machine-secret"


def test_comparison_rotates_overlays_without_changing_raw_evidence(tmp_path):
    path = _bundle(tmp_path)
    first = _client(path, task="comparison", cohort=0).get("/api/session").json()["episodes"]
    second = _client(path, task="comparison", cohort=1).get("/api/session").json()["episodes"]
    assert [ep["condition"] for ep in first] == ["baseline", "timeline", "annotated"]
    assert [ep["condition"] for ep in second] == ["timeline", "annotated", "baseline"]
    assert "legacy_labels" in first[0] and "annotation" not in first[0]
    assert "legacy_labels" not in first[1] and "annotation" not in first[1]
    assert "annotation" in first[2] and "legacy_labels" not in first[2]
    for left, right in zip(first, second):
        assert left["context"] == right["context"]
        assert left["turns"] == right["turns"]
    bundle = json.loads(path.read_text())
    bundle["episodes"][3]["annotation"] = None
    path.write_text(json.dumps(bundle))
    with pytest.raises(ValueError, match="annotat"):
        _client(path, task="comparison", cohort=0)


def test_partial_review_resumes_with_provenance_and_cumulative_time(tmp_path):
    path = _bundle(tmp_path)
    original = path.read_bytes()
    client = _client(path, task="coding")
    assert client.post("/api/review", json=_review()).status_code == 200
    review = _review()
    review["elapsed_ms"] = 600
    assert client.post("/api/review", json=review).status_code == 200
    resumed = _client(path, task="coding").get("/api/session").json()
    saved = resumed["reviews"]["ep-1"]
    assert saved["judgments"] == review["judgments"]
    assert saved["elapsed_ms"] == 1200
    assert saved["condition"] == "timeline"
    assert saved["instructor_action"]["evidence"][0]["turn_id"] == "1:2"
    assert path.read_bytes() == original
    disk = json.loads((tmp_path / "reviews/coding-holdout-invented-reviewer.json").read_text())
    assert disk["manifest"]["bundle_id"] == "invented-bundle"
    assert disk["rubric"] == resumed["rubric"]
    assert disk["reviewer"] == "invented-reviewer"
    assert not list((tmp_path / "reviews").glob("*.tmp"))


@pytest.mark.parametrize("bad", [
    {"value": "made-up"},
    {"evidence": [{"turn_id": "1:2", "quote": "loop condition"}]},
    {"evidence": [{"turn_id": "1:1", "quote": "not in transcript"}]},
    {"evidence": [{"turn_id": "1:1", "quote": ""}]},
    {"evidence": [{"turn_id": "1:0", "quote": "Earlier invented context"}]},
])
def test_invalid_judgment_cannot_replace_saved_progress(tmp_path, bad):
    client = _client(_bundle(tmp_path), task="coding")
    good = _review()
    assert client.post("/api/review", json=good).status_code == 200
    invalid = copy.deepcopy(good)
    invalid["judgments"]["request"].update(bad)
    assert client.post("/api/review", json=invalid).status_code == 422
    assert client.get("/api/session").json()["reviews"]["ep-1"]["judgments"] == good["judgments"]


def test_completion_requires_evidence_except_explicit_unknown(tmp_path):
    client = _client(_bundle(tmp_path), task="coding")
    review = _review()
    review["judgments"]["request"]["evidence"] = []
    assert client.post("/api/review", json=review).status_code == 200  # recoverable incomplete draft
    review["complete"] = True
    assert client.post("/api/review", json=review).status_code == 422
    review["judgments"] = {dim: {"value": "unclear", "evidence": [], "rationale": "Cannot tell"}
                           for dim in ("request", "tutor_response", "followup")}
    assert client.post("/api/review", json=review).status_code == 200


def test_no_followup_requires_explicit_absence_and_cannot_be_inferred_from_silence(tmp_path):
    path = _bundle(tmp_path)
    client = _client(path, task="coding")
    review = _review()
    review["judgments"]["followup"] = {"value": "no-followup-observed", "evidence": [], "rationale": ""}
    assert client.post("/api/review", json=review).status_code == 422
    bundle = json.loads(path.read_text())
    bundle["episodes"][1]["turns"] = bundle["episodes"][1]["turns"][:2]
    bundle["episodes"][1]["annotation"] = None
    bundle["manifest"]["episode_content_hash"] = episode_content_hash(bundle["episodes"])
    path.write_text(json.dumps(bundle))
    client = _client(path, task="coding")
    assert client.post("/api/review", json=review).status_code == 200
    review["judgments"]["followup"]["value"] = "attempt"
    assert client.post("/api/review", json=review).status_code == 422


def test_failed_atomic_replace_preserves_last_saved_review(tmp_path, monkeypatch):
    import src.eval.episode_review as server
    path = _bundle(tmp_path)
    client = _client(path, task="coding")
    assert client.post("/api/review", json=_review()).status_code == 200
    saved_path = tmp_path / "reviews/coding-holdout-invented-reviewer.json"
    prior = saved_path.read_bytes()
    def disk_failure(*args):
        raise OSError("invented disk failure")
    monkeypatch.setattr(server.os, "replace", disk_failure)
    changed = _review()
    changed["judgments"]["request"]["rationale"] = "An unsaved change"
    response = client.post("/api/review", json=changed)
    assert response.status_code == 503
    assert "retry" in response.json()["detail"]
    assert saved_path.read_bytes() == prior
    assert _client(path, task="coding").get("/api/session").json()["reviews"]["ep-1"]["judgments"] == _review()["judgments"]
    assert not list((tmp_path / "reviews").glob("*.tmp"))


def test_reviewer_paths_conflicting_sessions_and_negative_time_are_rejected(tmp_path):
    path = _bundle(tmp_path)
    with pytest.raises(ValueError, match="reviewer"):
        create_app(path, reviewer="../../outside")
    client = _client(path, task="comparison", cohort=0)
    assert client.post("/api/review", json=_review()).status_code == 200
    with pytest.raises(ValueError, match="conflict"):
        _client(path, task="comparison", cohort=1)
    review = _review()
    review["elapsed_ms"] = -1
    assert client.post("/api/review", json=review).status_code == 422
    bundle = json.loads(path.read_text())
    bundle["manifest"]["snapshot_id"] = "different-snapshot"
    path.write_text(json.dumps(bundle))
    with pytest.raises(ValueError, match="conflict"):
        _client(path, task="comparison", cohort=0)


def test_untrusted_origins_cannot_write_and_raw_text_is_not_embedded_in_html(tmp_path):
    path = _bundle(tmp_path)
    bundle = json.loads(path.read_text())
    attack = '</script><script>alert("invented")</script>'
    bundle["episodes"][1]["turns"][0]["text"] = attack
    bundle["episodes"][1]["annotation"] = None
    bundle["manifest"]["episode_content_hash"] = episode_content_hash(bundle["episodes"])
    path.write_text(json.dumps(bundle))
    client = _client(path, task="coding")
    page = client.get("/")
    assert page.status_code == 200
    assert attack not in page.text
    assert client.get("/api/session").json()["episodes"][0]["turns"][0]["text"] == attack
    assert client.post("/api/review", json=_review(), headers={"origin": "https://outside.invalid"}).status_code == 403
    assert client.get("/api/session", headers={"host": "outside.invalid"}).status_code == 400


def test_draft_review_requires_a_deliberate_decision_before_completion(tmp_path):
    client = _client(_bundle(tmp_path))
    review = {"episode_id": "ep-0", "workflow": "draft-review", "judgments": {
        dim: {"value": "unclear", "evidence": []}
        for dim in ("request", "tutor_response", "followup")}}
    assert client.post("/api/review", json=review).status_code == 200
    review["complete"] = True
    assert client.post("/api/review", json=review).status_code == 422
    for judgment in review["judgments"].values():
        judgment["assessment"] = "changed"
    assert client.post("/api/review", json=review).status_code == 200


def test_accepted_decisions_must_match_the_visible_draft(tmp_path):
    path = _bundle(tmp_path)
    client = _client(path)
    review = {"episode_id": "ep-0", "workflow": "draft-review", "judgments": {
        "request": {"assessment": "accepted", "value": "explanation", "evidence": [
            {"turn_id": "0:1", "quote": "Why does this invented loop stop?"}],
            "rationale": "My optional note"}}}
    response = client.post("/api/review", json=review)
    assert response.status_code == 200
    assert response.json()["review"]["judgments"]["request"]["rationale"] == "My optional note"
    for change in ({"value": "unclear"}, {"evidence": [
            {"turn_id": "0:1", "quote": "invented loop"}]}):
        invalid = copy.deepcopy(review)
        invalid["judgments"]["request"].update(change)
        assert client.post("/api/review", json=invalid).status_code == 422
    bundle = json.loads(path.read_text())
    bundle["episodes"][0]["annotation"] = None
    path.write_text(json.dumps(bundle))
    no_draft = TestClient(create_app(path, reviewer="no-draft"), base_url="http://127.0.0.1")
    assert no_draft.post("/api/review", json=review).status_code == 422


def test_cannot_assess_is_a_saved_decision_and_never_a_category(tmp_path):
    path = _bundle(tmp_path)
    client = _client(path)
    review = {"episode_id": "ep-0", "workflow": "draft-review", "complete": True,
              "judgments": {dim: {"assessment": "cannot-assess", "value": None,
                                 "evidence": [], "rationale": "I cannot read this language"}
                            for dim in ("request", "tutor_response", "followup")}}
    assert client.post("/api/review", json=review).status_code == 200
    resumed = _client(path).get("/api/session").json()["reviews"]["ep-0"]
    assert resumed["complete"] is True
    assert resumed["workflow"] == "draft-review"
    assert resumed["judgments"] == review["judgments"]
    for change in ({"value": "unclear"}, {"evidence": [
            {"turn_id": "0:1", "quote": "invented loop"}]}):
        invalid = copy.deepcopy(review)
        invalid["judgments"]["request"].update(change)
        assert client.post("/api/review", json=invalid).status_code == 422


def test_legacy_reviews_keep_their_shape_and_bytes_when_reopened(tmp_path):
    path = _bundle(tmp_path)
    client = _client(path)
    review = {"episode_id": "ep-0", "judgments": {
        "request": {"value": "unclear", "evidence": [], "rationale": "My earlier review"}}}
    assert client.post("/api/review", json=review).status_code == 200
    saved_path = tmp_path / "reviews/development-development-invented-reviewer.json"
    original = saved_path.read_bytes()
    saved = _client(path).get("/api/session").json()["reviews"]["ep-0"]
    assert saved_path.read_bytes() == original
    assert "workflow" not in saved
    assert "assessment" not in saved["judgments"]["request"]


@pytest.mark.parametrize("task", ["coding", "comparison"])
def test_draft_review_actions_are_rejected_outside_development(tmp_path, task):
    client = _client(_bundle(tmp_path), task=task)
    review = _review()
    assert client.post("/api/review", json=review).status_code == 200
    review["workflow"] = "draft-review"
    assert client.post("/api/review", json=review).status_code == 422
    del review["workflow"]
    for assessment in ("accepted", "changed", "cannot-assess"):
        review["judgments"]["request"]["assessment"] = assessment
        assert client.post("/api/review", json=review).status_code == 422
