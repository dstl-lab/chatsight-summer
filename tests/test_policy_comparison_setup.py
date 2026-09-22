"""Policy setup freezes authored plans without provider calls."""
import pytest

from src.agents import chat_student, notebook_student as store
from src.eval.student_continuation import Continuation
from tests.test_chat_student import QUERY, files


def _eligible(folder):
    initial = chat_student.create(folder, query=QUERY, model="authored-model")
    chat_student.step(
        folder, binding=initial["binding"],
        generate=lambda *_: Continuation(decision="reply", text="Authored pending message"),
    )


def test_discovers_only_eligible_direct_children_without_changes(tmp_path, monkeypatch):
    from src.agents import policy_comparison_setup as setup

    eligible = tmp_path / "eligible"
    _eligible(eligible)
    empty = tmp_path / "empty"
    chat_student.create(empty, query=QUERY)
    (tmp_path / "plain-folder").mkdir()
    nested = tmp_path / "nested" / "child"
    nested.parent.mkdir()
    _eligible(nested)
    before = files(tmp_path)
    monkeypatch.setattr(store.llm, "make_generate", lambda *_a, **_k: pytest.fail("Provider called"))

    assert setup.sources(tmp_path) == {"eligible": eligible.resolve()}
    assert files(tmp_path) == before


def test_default_current_policy_is_pinned_and_describes_the_packaged_baseline():
    from src.agents import policy_comparison_setup as setup

    assert setup.PACKAGED_POLICY_COMMIT == "d899879c3e7537b021d16bb901da341945606891"
    assert setup.PACKAGED_POLICY_COMMIT in setup.PACKAGED_POLICY_URL
    assert "Socratic" in setup.DEFAULT_CURRENT_POLICY
    assert "complete solutions immediately" in setup.DEFAULT_CURRENT_POLICY
    assert "unavailable notebook work" in setup.DEFAULT_CURRENT_POLICY


def test_freezes_distinct_policies_once_and_reopens_offline(tmp_path, monkeypatch):
    from src.agents import policy_comparison_setup as setup

    source, destination = tmp_path / "source", tmp_path / "comparison"
    _eligible(source)
    source_before = files(source)
    monkeypatch.setattr(store.llm, "make_generate", lambda *_a, **_k: pytest.fail("Provider called"))

    saved = setup.freeze(
        destination, source=source,
        current_policy="Current authored policy.",
        proposed_policy="Proposed authored policy.",
    )

    assert saved == setup.reopen(destination)
    assert saved["max_new_decisions"] == 1
    assert saved["conditions"]["a"]["policy"] == "Current authored policy."
    assert saved["conditions"]["b"]["policy"] == "Proposed authored policy."
    assert all(item["snapshot"]["decisions_remaining"] == 1
               for item in saved["conditions"].values())
    assert files(source) == source_before
    frozen = files(destination)
    assert setup.reopen(destination) == saved and files(destination) == frozen
    with pytest.raises(FileExistsError):
        setup.freeze(destination, source=source, current_policy="Current.", proposed_policy="Other.")
    assert files(destination) == frozen


def test_runs_both_frozen_conditions_once_and_reopens_without_resending(tmp_path):
    from src.agents import policy_comparison_setup as setup

    source, destination = tmp_path / "source", tmp_path / "comparison"
    _eligible(source)
    setup.freeze(destination, source=source,
                 current_policy="Current authored policy.",
                 proposed_policy="Proposed authored policy.")
    calls = []

    def tutor(prompt, schema):
        condition = "a" if "Current authored policy." in prompt else "b"
        calls.append((condition, "tutor"))
        return schema(text=f"Authored tutor {condition} response.")

    def student(prompt, schema):
        condition = "a" if "Authored tutor a response." in prompt else "b"
        calls.append((condition, "student"))
        return schema(decision="reply", text=f"Authored student {condition} response.")

    saved = setup.run_both(destination, send=True,
                           generate_tutor=tutor, generate_student=student)

    assert calls == [("a", "tutor"), ("a", "student"),
                     ("b", "tutor"), ("b", "student")]
    for name in ("a", "b"):
        snapshot = saved["conditions"][name]["snapshot"]
        assert snapshot["status"] == "awaiting-tutor"
        assert snapshot["decisions_remaining"] == 0
        assert snapshot["pending_message"] == f"Authored student {name} response."
    completed = files(destination)
    assert setup.run_both(destination, send=True,
                          generate_tutor=tutor, generate_student=student) == saved
    assert calls == [("a", "tutor"), ("a", "student"),
                     ("b", "tutor"), ("b", "student")]
    assert files(destination) == completed


def test_run_requires_permission_and_preserves_failure_while_running_other_arm(tmp_path):
    from src.agents import policy_comparison_setup as setup

    source, destination = tmp_path / "source", tmp_path / "comparison"
    _eligible(source)
    setup.freeze(destination, source=source,
                 current_policy="Current authored policy.",
                 proposed_policy="Proposed authored policy.")
    before = files(destination)
    with pytest.raises(ValueError, match="permission"):
        setup.run_both(destination)
    assert files(destination) == before
    calls = []

    def tutor(prompt, schema):
        if "Current authored policy." in prompt:
            calls.append("a-failed")
            raise RuntimeError("Authored tutor failure")
        calls.append("b-tutor")
        return schema(text="Authored tutor b response.")

    def student(_, schema):
        calls.append("b-student")
        return schema(decision="no-reply", text="")

    saved = setup.run_both(destination, send=True,
                           generate_tutor=tutor, generate_student=student)
    assert calls == ["a-failed", "b-tutor", "b-student"]
    assert saved["conditions"]["a"]["error"]
    assert saved["conditions"]["b"]["snapshot"]["status"] == "no-reply"
    preserved = files(destination)
    setup.run_both(destination, send=True,
                   generate_tutor=lambda *_: pytest.fail("Retried tutor"),
                   generate_student=lambda *_: pytest.fail("Retried student"))
    assert files(destination) == preserved


def test_numbered_workspace_preserves_runs_and_rejects_exact_reroll(tmp_path):
    from src.agents import policy_comparison_setup as setup

    source, workspace = tmp_path / "source", tmp_path / "lab"
    _eligible(source)
    first_path, first = setup.freeze_next(
        workspace, source=source,
        current_policy="Current authored policy.", proposed_policy="First proposal.",
    )
    second_path, second = setup.freeze_next(
        workspace, source=source,
        current_policy="Current authored policy.", proposed_policy="Second proposal.",
    )

    assert first_path.name == "run-0001" and second_path.name == "run-0002"
    assert setup.runs(workspace) == {
        "run-0001": first_path.resolve(), "run-0002": second_path.resolve(),
    }
    assert setup.reopen(first_path) == first
    assert setup.reopen(second_path) == second
    before = files(workspace)
    with pytest.raises(ValueError, match="already exists as run-0001"):
        setup.freeze_next(
            workspace, source=source,
            current_policy="Current authored policy.", proposed_policy="First proposal.",
        )
    assert files(workspace) == before


def test_run_discovery_ignores_unverified_directories(tmp_path):
    from src.agents import policy_comparison_setup as setup

    workspace = tmp_path / "lab"
    (workspace / "run-0001").mkdir(parents=True)
    (workspace / "notes").mkdir()
    assert setup.runs(workspace) == {}


@pytest.mark.parametrize("current,proposed", [
    ("", "Proposed."), ("Current.", " "), ("Same.", " Same. "),
])
def test_rejects_missing_or_identical_policies(tmp_path, current, proposed):
    from src.agents import policy_comparison_setup as setup

    source, destination = tmp_path / "source", tmp_path / "comparison"
    _eligible(source)
    with pytest.raises(ValueError):
        setup.freeze(destination, source=source, current_policy=current, proposed_policy=proposed)
    assert not destination.exists()
