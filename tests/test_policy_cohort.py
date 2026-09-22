"""Fixed tutor-policy cohorts compose immutable comparisons without hidden calls."""
from copy import deepcopy
import json

import pytest

from src.agents import chat_student, notebook_student as store
from src.eval.student_continuation import Continuation
from tests.test_chat_student import QUERY, files


def _source(folder, number, *, model="authored-model"):
    query = deepcopy(QUERY)
    query["id"] = f"AUTHORED_QUERY_{number}"
    query["conversation_id"] = f"AUTHORED_CONVERSATION_{number}"
    initial = chat_student.create(folder, query=query, model=model)
    chat_student.step(
        folder,
        binding=initial["binding"],
        generate=lambda *_: Continuation(decision="reply", text=f"Authored question {number}?"),
    )


def test_freezes_multiple_cases_offline_and_reopens_without_changes(tmp_path, monkeypatch):
    from src.agents import policy_cohort

    sources = [tmp_path / f"source-{number}" for number in (1, 2, 3)]
    for number, source in enumerate(sources, 1):
        _source(source, number)
    before_sources = {source.name: files(source) for source in sources}
    monkeypatch.setattr(store.llm, "make_generate", lambda *_a, **_k: pytest.fail("Provider called"))

    folder = tmp_path / "cohort"
    saved = policy_cohort.create(
        folder,
        sources=list(reversed(sources)),
        current_policy="Current authored policy.",
        proposed_policy="Proposed authored policy.",
    )

    assert saved["summary"] == {
        "case_count": 3,
        "logical_requests_if_fully_run": 12,
        "conditions": {
            "a": {"ready": 3, "student-replied": 0, "no-follow-up": 0,
                  "incomplete": 0, "failed": 0},
            "b": {"ready": 3, "student-replied": 0, "no-follow-up": 0,
                  "incomplete": 0, "failed": 0},
        },
        "comparisons": {
            "both-replied": 0,
            "both-no-follow-up": 0,
            "proposed-gained-follow-up": 0,
            "proposed-lost-follow-up": 0,
            "not-comparable": 3,
        },
        "different_reply_status": 0,
    }
    assert [case["case_id"] for case in saved["cases"]] == [
        "case-0001", "case-0002", "case-0003",
    ]
    assert all(case["outcomes"] == {"a": "ready", "b": "ready"}
               for case in saved["cases"])
    assert {source.name: files(source) for source in sources} == before_sources
    frozen = files(folder)
    assert policy_cohort.show(folder) == saved and files(folder) == frozen


def test_runs_each_case_once_and_summarizes_reply_status(tmp_path):
    from src.agents import policy_cohort

    sources = [tmp_path / f"source-{number}" for number in (1, 2)]
    for number, source in enumerate(sources, 1):
        _source(source, number)
    folder = tmp_path / "cohort"
    policy_cohort.create(
        folder,
        sources=sources,
        current_policy="Current authored policy.",
        proposed_policy="Proposed authored policy.",
    )
    calls = []

    def tutor(prompt, schema):
        payload = json.loads(prompt.split("POLICY AND CONTEXT JSON:\n")[1])
        condition = "a" if payload["policy"].startswith("Current") else "b"
        question = payload["context"]["pending_message"]
        calls.append((question, condition, "tutor"))
        return schema(text=f"Authored tutor {condition} for {question}")

    def student(prompt, schema):
        condition = "a" if "Authored tutor a" in prompt else "b"
        question = "Authored question 1?" if "question 1" in prompt else "Authored question 2?"
        calls.append((question, condition, "student"))
        decision = "no-reply" if condition == "b" else "reply"
        return schema(decision=decision, text="Authored follow-up." if decision == "reply" else "")

    saved = policy_cohort.run(
        folder,
        send=True,
        generate_tutor=tutor,
        generate_student=student,
    )

    assert len(calls) == 8
    assert saved["summary"]["conditions"]["a"]["student-replied"] == 2
    assert saved["summary"]["conditions"]["b"]["no-follow-up"] == 2
    assert saved["summary"]["different_reply_status"] == 2
    assert saved["summary"]["comparisons"]["proposed-lost-follow-up"] == 2
    complete = files(folder)
    assert policy_cohort.run(
        folder,
        send=True,
        generate_tutor=lambda *_: pytest.fail("Tutor rerun"),
        generate_student=lambda *_: pytest.fail("Student rerun"),
    ) == saved
    assert files(folder) == complete and len(calls) == 8


def test_numbered_cohort_runs_preserve_history_and_reject_exact_rerun(tmp_path):
    from src.agents import policy_cohort

    sources = [tmp_path / f"source-{number}" for number in (1, 2)]
    for number, source in enumerate(sources, 1):
        _source(source, number)
    workspace = tmp_path / "workspace"
    first_path, first = policy_cohort.freeze_next(
        workspace,
        sources=sources,
        current_policy="Current authored policy.",
        proposed_policy="First proposed policy.",
    )
    second_path, second = policy_cohort.freeze_next(
        workspace,
        sources=sources,
        current_policy="Current authored policy.",
        proposed_policy="Second proposed policy.",
    )

    assert first_path.name == "cohort-0001" and second_path.name == "cohort-0002"
    assert policy_cohort.runs(workspace) == {
        "cohort-0001": first_path.resolve(),
        "cohort-0002": second_path.resolve(),
    }
    assert policy_cohort.show(first_path) == first
    assert policy_cohort.show(second_path) == second
    before = files(workspace)
    with pytest.raises(ValueError, match="already exists as cohort-0001"):
        policy_cohort.freeze_next(
            workspace,
            sources=list(reversed(sources)),
            current_policy="Current authored policy.",
            proposed_policy="First proposed policy.",
        )
    assert files(workspace) == before


def test_rejects_bad_sources_permissions_and_tampered_cohort(tmp_path):
    from src.agents import policy_cohort

    source = tmp_path / "source"
    _source(source, 1)
    with pytest.raises(ValueError):
        policy_cohort.create(
            tmp_path / "empty", sources=[],
            current_policy="Current.", proposed_policy="Proposed.",
        )
    with pytest.raises(ValueError, match="twice"):
        policy_cohort.create(
            tmp_path / "duplicate", sources=[source, source],
            current_policy="Current.", proposed_policy="Proposed.",
        )
    folder = tmp_path / "cohort"
    policy_cohort.create(
        folder, sources=[source],
        current_policy="Current.", proposed_policy="Proposed.",
    )
    before = files(folder)
    with pytest.raises(ValueError, match="permission"):
        policy_cohort.run(folder)
    assert files(folder) == before

    receipt_path = folder / "cohort.json"
    receipt = store._read(receipt_path)
    receipt["plan"]["max_new_decisions"] = 2
    receipt_path.write_text(json.dumps(receipt))
    damaged = files(folder)
    with pytest.raises(ValueError):
        policy_cohort.show(folder)
    assert files(folder) == damaged


def test_validates_every_case_before_dispatching_any_provider(tmp_path):
    from src.agents import policy_cohort

    sources = [tmp_path / f"source-{number}" for number in (1, 2)]
    for number, source in enumerate(sources, 1):
        _source(source, number)
    folder = tmp_path / "cohort"
    policy_cohort.create(
        folder, sources=sources,
        current_policy="Current.", proposed_policy="Proposed.",
    )
    damaged_path = folder / "cases" / "case-0002" / "comparison.json"
    damaged = store._read(damaged_path)
    damaged["plan"]["policies"]["a"] = "Changed."
    damaged_path.write_text(json.dumps(damaged))
    before = files(folder)

    with pytest.raises(ValueError):
        policy_cohort.run(
            folder,
            send=True,
            generate_tutor=lambda *_: pytest.fail("Provider called before validation"),
            generate_student=lambda *_: pytest.fail("Provider called before validation"),
        )
    assert files(folder) == before


def test_parallel_workers_run_cases_independently(tmp_path):
    from threading import Barrier
    from src.agents import policy_cohort

    sources = [tmp_path / f"source-{number}" for number in (1, 2)]
    for number, source in enumerate(sources, 1):
        _source(source, number)
    folder = tmp_path / "cohort"
    policy_cohort.create(
        folder, sources=sources,
        current_policy="Current.", proposed_policy="Proposed.",
    )
    first_tutors = Barrier(2)

    def tutor(prompt, schema):
        if "Current." in prompt:
            first_tutors.wait(timeout=2)
        return schema(text="Authored tutor response.")

    saved = policy_cohort.run(
        folder,
        send=True,
        workers=2,
        generate_tutor=tutor,
        generate_student=lambda _, schema: schema(decision="reply", text="Follow-up."),
    )
    assert saved["summary"]["conditions"]["a"]["student-replied"] == 2
    assert saved["summary"]["conditions"]["b"]["student-replied"] == 2
    assert saved["summary"]["comparisons"]["both-replied"] == 2


@pytest.mark.parametrize("workers", [0, True, 9])
def test_rejects_invalid_parallel_worker_count(tmp_path, workers):
    from src.agents import policy_cohort

    source, folder = tmp_path / "source", tmp_path / "cohort"
    _source(source, 1)
    policy_cohort.create(
        folder, sources=[source],
        current_policy="Current.", proposed_policy="Proposed.",
    )
    before = files(folder)
    with pytest.raises(ValueError, match="workers"):
        policy_cohort.run(folder, send=True, workers=workers)
    assert files(folder) == before


def test_interrupted_request_is_incomplete_and_not_comparable(tmp_path):
    from src.agents import policy_cohort

    source, folder = tmp_path / "source", tmp_path / "cohort"
    _source(source, 1)
    policy_cohort.create(
        folder, sources=[source],
        current_policy="Current.", proposed_policy="Proposed.",
    )

    def interrupted(*_):
        raise KeyboardInterrupt("Authored interruption")

    with pytest.raises(KeyboardInterrupt):
        policy_cohort.run(folder, send=True, generate_tutor=interrupted)
    saved = policy_cohort.show(folder)
    assert saved["cases"][0]["outcomes"] == {"a": "incomplete", "b": "ready"}
    assert saved["cases"][0]["comparison_outcome"] == "not-comparable"
    assert saved["summary"]["conditions"]["a"]["incomplete"] == 1
    assert saved["summary"]["comparisons"]["not-comparable"] == 1


def test_failed_request_is_not_misclassified_by_wording_in_saved_history(tmp_path):
    from src.agents import policy_cohort

    source, folder = tmp_path / "source", tmp_path / "cohort"
    _source(source, 1)
    policy_cohort.create(folder, sources=[source],
                         current_policy="Current.", proposed_policy="Proposed.")

    def tutor(prompt, schema):
        if "Current." in prompt:
            raise RuntimeError("Authored incomplete input failure")
        return schema(text="Authored response.")

    saved = policy_cohort.run(folder, send=True, generate_tutor=tutor,
                              generate_student=lambda _, schema: schema(decision="no-reply", text=""))
    assert saved["cases"][0]["outcomes"] == {"a": "failed", "b": "no-follow-up"}
    assert saved["summary"]["conditions"]["a"]["failed"] == 1
    assert saved["summary"]["conditions"]["a"]["incomplete"] == 0


@pytest.mark.parametrize("mode", ["conversation", "model", "source-link", "nested-output"])
def test_cohort_preserves_source_and_comparability_guards(tmp_path, mode):
    from src.agents import policy_cohort

    first, second, folder = tmp_path / "first", tmp_path / "second", tmp_path / "cohort"
    _source(first, 1)
    _source(second, 1 if mode == "conversation" else 2,
            model="different-model" if mode == "model" else "authored-model")
    if mode == "source-link":
        original = second / "session.json"
        moved = tmp_path / "external-session.json"
        original.rename(moved)
        original.symlink_to(moved)
    if mode == "nested-output":
        folder = first / "cohort"
    before = files(tmp_path)
    with pytest.raises(ValueError):
        policy_cohort.create(folder, sources=[first, second],
                             current_policy="Current.", proposed_policy="Proposed.")
    assert not folder.exists() and files(tmp_path) == before


def test_cohort_rejects_symlink_before_any_dispatch(tmp_path):
    from src.agents import policy_cohort

    source, folder = tmp_path / "source", tmp_path / "cohort"
    _source(source, 1)
    policy_cohort.create(folder, sources=[source],
                         current_policy="Current.", proposed_policy="Proposed.")
    receipt = folder / "cases" / "case-0001" / "comparison.json"
    external = tmp_path / "external-comparison.json"
    receipt.rename(external)
    receipt.symlink_to(external)
    before = files(tmp_path)
    with pytest.raises(ValueError, match="symbolic"):
        policy_cohort.run(folder, send=True,
                          generate_tutor=lambda *_: pytest.fail("Provider called"))
    assert files(tmp_path) == before


@pytest.mark.parametrize("damage", ["missing-a", "corrupt-a", "both-missing"])
def test_damaged_startup_keeps_valid_peer_or_unavailable_case_visible(tmp_path, damage):
    from src.agents import policy_cohort

    source, folder = tmp_path / "source", tmp_path / "cohort"
    _source(source, 1)
    policy_cohort.create(folder, sources=[source],
                         current_policy="Current.", proposed_policy="Proposed.")
    complete = policy_cohort.run(folder, send=True,
                                 generate_tutor=lambda _, schema: schema(text="Authored tutor."),
                                 generate_student=lambda _, schema: schema(decision="no-reply", text=""))
    sessions = folder / "cases" / "case-0001" / "sessions"
    if damage == "corrupt-a":
        (sessions / "a" / "session.json").write_text("{")
    else:
        (sessions / "a" / "session.json").unlink()
    if damage == "both-missing":
        (sessions / "b" / "session.json").unlink()
    before = files(folder)
    saved = policy_cohort.show(folder)
    assert len(saved["cases"]) == 1
    case = saved["cases"][0]
    assert case["outcomes"] == {"a": "failed", "b": "failed" if damage == "both-missing" else "no-follow-up"}
    assert case["comparison_outcome"] == "not-comparable"
    assert case["comparison"]["conditions"]["a"]["error"]
    if damage == "both-missing":
        assert case["comparison"]["conditions"]["b"]["error"]
    else:
        assert case["comparison"]["conditions"]["b"] == complete["cases"][0]["comparison"]["conditions"]["b"]
    assert files(folder) == before
