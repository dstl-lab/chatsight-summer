"""One-case continuation controls use invented dialogue and injected providers."""
from copy import deepcopy
import json

import pytest

from src.agents import notebook_student as store
from src.eval.student_continuation import Continuation


def _row(target="HIDDEN RECORDED NEXT"):
    return {
        "chatlog_id": "PRIVATE CHATLOG",
        "conv_id": "PRIVATE CONVERSATION",
        "notebook": "PRIVATE NOTEBOOK",
        "turns": [
            {"index": 0, "role": "student", "text": "How do I count these?", "at": "t0"},
            {"index": 1, "role": "tutor", "text": "Try the distinct values.", "at": "t1"},
            {"index": 2, "role": "student", "text": target, "at": "t2"},
        ],
    }


def _snapshot(path, target="HIDDEN RECORDED NEXT"):
    path.mkdir()
    (path / "conversations.jsonl").write_text(json.dumps(_row(target)) + "\n")


def _files(path):
    return {str(file.relative_to(path)): file.read_bytes()
            for file in path.rglob("*") if file.is_file() and file.name != ".lock"}


def test_preparation_separates_target_and_target_changes_cannot_change_prompt(tmp_path):
    from src.eval import heldout_continuation as heldout

    first_source, second_source = tmp_path / "snapshot-a", tmp_path / "snapshot-b"
    _snapshot(first_source)
    _snapshot(second_source, "A DIFFERENT HIDDEN FUTURE")
    first, second = tmp_path / "first", tmp_path / "second"
    first_manifest = heldout.prepare(first_source, first)
    second_manifest = heldout.prepare(second_source, second)
    first_session = store._read(first / "session" / "session.json")
    second_session = store._read(second / "session" / "session.json")
    first_reference = store._read(first / "reference.json")
    second_reference = store._read(second / "reference.json")

    assert first_session["query"] == second_session["query"]
    assert first_manifest["case"]["prompt_sha256"] == second_manifest["case"]["prompt_sha256"]
    assert first_manifest["case"]["query_sha256"] == second_manifest["case"]["query_sha256"]
    assert first_manifest["case"]["reference_sha256"] != second_manifest["case"]["reference_sha256"]
    assert first_reference["target"]["text"] == "HIDDEN RECORDED NEXT"
    serialized_session = json.dumps(first_session)
    assert "HIDDEN RECORDED NEXT" not in serialized_session
    for private in ("PRIVATE CHATLOG", "PRIVATE CONVERSATION", "PRIVATE NOTEBOOK"):
        assert private not in serialized_session
    assert first_manifest["requests"] == 1 and first_manifest["model"] == "gemini-2.5-pro"
    assert first_manifest["authorization"]["user_direction"] == "ok, lets do the next milestone"
    with pytest.raises(FileExistsError):
        heldout.prepare(first_source, first)


def test_one_saved_request_joins_reference_only_after_generation_and_replays_offline(tmp_path, monkeypatch):
    from src.agents import chat_student as chat
    from src.eval import heldout_continuation as heldout

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    target = store._read(folder / "reference.json")["target"]["text"]
    calls = []

    def generate(prompt, schema):
        assert schema is Continuation
        assert target not in prompt
        assert json.loads((folder / "session" / "step-0001.json").read_text())["status"] == "pending"
        calls.append(prompt)
        return Continuation(decision="reply", text="I used the number of unique values.")

    comparison = heldout.run(folder, generate=generate)

    assert len(calls) == 1
    assert heldout.summary(comparison) == {
        "recorded": "recorded-followup", "generated": "reply", "prefix_turns": 2,
        "sha256": comparison["sha256"],
    }
    recorded, generated = comparison["review"]["candidates"]
    assert recorded["turns"][0]["text"] == target
    assert generated["turns"][0]["text"] == "I used the number of unique values."
    assert all(judgment["value"] == "" for candidate in (recorded, generated)
               for judgment in candidate["judgments"].values())
    receipt = store._read(folder / "session" / "step-0001.json")
    assert receipt["status"] == "complete" and receipt["response"]["decision"] == "reply"
    before = _files(folder)
    monkeypatch.setattr(chat.llm, "make_generate",
                        lambda *_a, **_kw: pytest.fail("Offline replay dispatched a model."))
    assert heldout.load(folder) == comparison
    assert _files(folder) == before and len(calls) == 1
    with pytest.raises(FileExistsError):
        heldout.run(folder, generate=generate)
    with pytest.raises(FileExistsError):
        heldout.finalize(folder)
    assert _files(folder) == before and len(calls) == 1


def test_changed_preparation_or_comparison_is_rejected(tmp_path):
    from src.eval import heldout_continuation as heldout

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    original = store._read(folder / "manifest.json")
    changed = deepcopy(original)
    changed["requests"] = 2
    store._save(folder / "manifest.json", changed)
    with pytest.raises(ValueError, match="preparation changed"):
        heldout.run(folder, generate=lambda *_: None)
