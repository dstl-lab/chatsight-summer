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


@pytest.mark.parametrize("reader", ["finalize", "load"])
@pytest.mark.parametrize("changed", ["prompt", "binding", "result"])
def test_saved_continuation_replays_receipt_before_accepting_it(tmp_path, reader, changed):
    from src.agents import chat_student as chat
    from src.eval import heldout_continuation as heldout

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    initial = chat.show(folder / "session")
    chat.step(folder / "session", binding=initial["binding"],
              generate=lambda *_: Continuation(decision="reply", text="Try this?"))
    if reader == "load":
        heldout.finalize(folder)
    path = folder / "session" / "step-0001.json"
    receipt = store._read(path)
    if changed == "prompt":
        receipt["request"]["prompt"] += " Changed request"
    elif changed == "binding":
        receipt["request"]["binding"]["state_sha256"] = "f" * 64
    else:
        receipt["result"]["message"] = "Different saved result"
    store._save(path, receipt)
    if reader == "load":
        # A content hash alone must not bless a request the runner cannot replay.
        comparison = store._read(folder / "comparison.json")
        comparison["receipt_sha256"] = store.digest(receipt)
        comparison["sha256"] = store.digest({k: v for k, v in comparison.items() if k != "sha256"})
        store._save(folder / "comparison.json", comparison)
    before = _files(folder)
    with pytest.raises(ValueError):
        getattr(heldout, reader)(folder)
    assert _files(folder) == before


def test_request_provenance_does_not_claim_to_count_provider_retries(tmp_path):
    from src.eval import heldout_continuation as heldout
    from src.labeling.llm import with_retries

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    attempts = []

    def provider(*_):
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("Authored transient failure")
        return Continuation(decision="no-reply", text="")

    comparison = heldout.run(folder, generate=with_retries(provider, sleep=lambda _: None))
    assert len(attempts) == 3
    assert comparison["provenance"]["logical_requests"] == 1
    assert comparison["provenance"]["provider_attempts"] is None
    assert "provider_requests" not in comparison["provenance"]


def test_original_reader_version_remains_readable_without_rewriting_artifacts(tmp_path):
    from src.eval import heldout_continuation as heldout

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    heldout.run(folder, generate=lambda *_: Continuation(decision="reply", text="Try this?"))
    manifest = store._read(folder / "manifest.json")
    manifest["sources"]["heldout_continuation.py"] = (
        "c34326095b2223273bed51eab9d7543daad19d5d29a6921cd2e4bbc9aff15829")
    manifest["sha256"] = store.digest({k: v for k, v in manifest.items() if k != "sha256"})
    store._save(folder / "manifest.json", manifest)
    comparison = store._read(folder / "comparison.json")
    comparison["manifest_sha256"] = manifest["sha256"]
    comparison["provenance"].pop("logical_requests", None)
    comparison["provenance"].pop("provider_attempts", None)
    comparison["provenance"]["provider_requests"] = 1
    comparison["sha256"] = store.digest({k: v for k, v in comparison.items() if k != "sha256"})
    store._save(folder / "comparison.json", comparison)
    before = _files(folder)
    assert heldout.load(folder) == comparison
    assert _files(folder) == before


def test_saved_continuation_uses_existing_readonly_lock(tmp_path):
    import fcntl
    from src.eval import heldout_continuation as heldout

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    comparison = heldout.run(folder, generate=lambda *_: Continuation(decision="no-reply", text=""))
    lock = folder / "session" / ".lock"
    with lock.open("rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        assert heldout.load(folder) == comparison
    with store._locked(folder / "session"), pytest.raises(ValueError, match="busy"):
        heldout.load(folder)
    lock.unlink()
    before = _files(folder)
    with pytest.raises(ValueError, match="saved session lock"):
        heldout.load(folder)
    assert not lock.exists() and _files(folder) == before


@pytest.mark.parametrize("changed", ["candidate", "logical_requests", "provider_attempts", "model"])
def test_saved_comparison_must_reproduce_verified_review_and_provenance(tmp_path, changed):
    from src.eval import heldout_continuation as heldout

    source, folder = tmp_path / "snapshot", tmp_path / "case"
    _snapshot(source)
    heldout.prepare(source, folder)
    comparison = heldout.run(folder, generate=lambda *_: Continuation(decision="reply", text="Try this?"))
    if changed == "candidate":
        comparison["review"]["candidates"][1]["turns"][0]["text"] = "Not the saved response"
    else:
        comparison["provenance"][changed] = "different-model" if changed == "model" else 2
    comparison["sha256"] = store.digest({k: v for k, v in comparison.items() if k != "sha256"})
    store._save(folder / "comparison.json", comparison)
    before = _files(folder)
    with pytest.raises(ValueError, match="comparison changed"):
        heldout.load(folder)
    assert _files(folder) == before
