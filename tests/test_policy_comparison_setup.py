"""Policy setup freezes authored plans without provider calls."""
from copy import deepcopy
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


def test_unsaved_runner_failure_surfaces_without_running_peer(tmp_path, monkeypatch):
    from src.agents import policy_comparison_setup as setup

    source, destination = tmp_path / "source", tmp_path / "comparison"
    _eligible(source)
    setup.freeze(destination, source=source, current_policy="Current.", proposed_policy="Proposed.")
    before, calls = files(destination), []

    def unwritten_failure(*args, **kwargs):
        calls.append(args[1])
        raise OSError("Authored disk failure before saving a receipt")

    monkeypatch.setattr(setup.chat_policy_pair, "respond", unwritten_failure)
    with pytest.raises(OSError, match="before saving"):
        setup.run_both(destination, send=True)
    assert calls == ["a"] and files(destination) == before


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


def test_local_discovery_and_freeze_forward_explicit_tutor_model(tmp_path, monkeypatch):
    from src.agents import policy_comparison_setup as setup

    source = tmp_path / 'source'
    source.mkdir()
    (source / 'session.json').write_text('{}')
    checked, created = [], []
    def read_source(path, *, local=False):
        checked.append((path, local))
        return {}, {}, {}
    def create(destination, **options):
        created.append((destination, options))
        return {'authored': 'frozen'}
    monkeypatch.setattr(setup.chat_policy_pair, '_source', read_source)
    monkeypatch.setattr(setup.chat_policy_pair, 'create', create)
    before = files(tmp_path)
    assert setup.sources(tmp_path, gemini_tutor_model='gemini-authored') == {'source': source.resolve()}
    assert checked == [(source, True)]
    result = setup.freeze(tmp_path / 'pair', source=source, current_policy='Current.',
        proposed_policy='Proposed.', gemini_tutor_model='gemini-authored')
    assert result == {'authored': 'frozen'}
    assert created == [(tmp_path / 'pair', dict(source=source, policies={'a': 'Current.', 'b': 'Proposed.'},
        max_new_decisions=1, gemini_tutor_model='gemini-authored'))]
    assert files(tmp_path) == before


def test_local_duplicate_identity_includes_tutor_model(tmp_path, monkeypatch):
    from src.agents import policy_comparison_setup as setup

    source, workspace = tmp_path / 'source', tmp_path / 'workspace'
    workspace.mkdir()
    existing = workspace / 'run-0001'
    existing.mkdir()
    store._save(existing / 'comparison.json', {'plan': {'version': 2,
        'source': {'session_sha256': store.digest({'authored': 'source'})},
        'policies': {'a': 'Current.', 'b': 'Proposed.'}, 'gemini_tutor_model': 'gemini-first'}})
    def read_source(path, *, local=False):
        assert path == source and local is True
        return {'authored': 'source'}, {}, {}
    monkeypatch.setattr(setup.chat_policy_pair, '_source', read_source)
    monkeypatch.setattr(setup, 'runs', lambda _: {'run-0001': existing})
    created = []
    monkeypatch.setattr(setup.chat_policy_pair, 'create',
        lambda destination, **options: created.append((destination, options)) or {'frozen': True})
    before = files(workspace)
    with pytest.raises(ValueError, match='already exists as run-0001'):
        setup.freeze_next(workspace, source=source, current_policy='Current.',
            proposed_policy='Proposed.', gemini_tutor_model='gemini-first')
    assert files(workspace) == before and created == []
    path, _ = setup.freeze_next(workspace, source=source, current_policy='Current.',
        proposed_policy='Proposed.', gemini_tutor_model='gemini-second')
    assert path == (workspace / 'run-0002').resolve()
    assert created[0][1]['gemini_tutor_model'] == 'gemini-second'


@pytest.fixture
def local_plan(tmp_path, monkeypatch):
    from src.agents import policy_comparison_setup as setup

    plan = {'version': 2, 'gemini_tutor_model': 'gemini-authored'}
    saved = {'conditions': {name: {'error': '', 'lifecycle': 'ready', 'snapshot': {
        'status': 'awaiting-tutor', 'decisions_remaining': 1, 'binding': {'condition': name}}}
        for name in ('a', 'b')}}
    monkeypatch.setattr(setup.chat_policy_pair, '_comparison', lambda _: {'plan': plan})
    monkeypatch.setattr(setup, 'reopen', lambda _: deepcopy(saved))
    return setup, tmp_path / 'pair', plan, saved


def test_local_run_binds_each_eligible_child_once_and_skips_finished_arms(local_plan, monkeypatch):
    setup, destination, _, saved = local_plan
    calls = []
    def factory(child):
        calls.append(('factory', child))
        return lambda prefix: f'Authored student {child.name}: {prefix[-1]["text"]}'
    tutor = lambda *_: None
    def respond(folder, name, *, binding, send, generate_tutor, generate_reply, gemini_tutor_model):
        assert folder == destination and binding == {'condition': name} and send is True
        assert generate_tutor is tutor and gemini_tutor_model == 'gemini-authored'
        assert generate_reply([{'role': 'tutor', 'text': 'Exact tutor text.'}]) == (
            f'Authored student {name}: Exact tutor text.')
        calls.append(('respond', name))
        saved['conditions'][name]['snapshot']['decisions_remaining'] = 0
        saved['conditions'][name]['lifecycle'] = 'student-replied'
    monkeypatch.setattr(setup.chat_policy_pair, 'respond', respond)
    setup.run_both(destination, send=True, generate_tutor=tutor,
        make_student_reply=factory, gemini_tutor_model='gemini-authored')
    assert calls == [('factory', destination / 'sessions' / 'a'), ('respond', 'a'),
        ('factory', destination / 'sessions' / 'b'), ('respond', 'b')]
    before = list(calls)
    setup.run_both(destination, send=True, generate_tutor=tutor,
        make_student_reply=factory, gemini_tutor_model='gemini-authored')
    assert calls == before


@pytest.mark.parametrize('lifecycle', ['failed', 'incomplete'])
def test_local_run_never_constructs_backend_for_saved_failure(local_plan, monkeypatch, lifecycle):
    setup, destination, _, saved = local_plan
    saved['conditions']['a'].update(lifecycle=lifecycle, error='Saved request unavailable', snapshot=None)
    saved['conditions']['b']['snapshot']['decisions_remaining'] = 0
    def forbidden(*_):
        pytest.fail('A stopped arm must not construct a backend or dispatch')
    monkeypatch.setattr(setup.chat_policy_pair, 'respond', forbidden)
    assert setup.run_both(destination, send=True, generate_tutor=forbidden,
        make_student_reply=forbidden, gemini_tutor_model='gemini-authored') == saved


def test_local_runner_rejects_missing_or_mismatched_backends_before_calls(local_plan, monkeypatch):
    setup, destination, plan, _ = local_plan
    def forbidden(*_):
        pytest.fail('Invalid configuration must not dispatch or construct a backend')
    monkeypatch.setattr(setup.chat_policy_pair, 'respond', forbidden)
    options = dict(send=True, generate_tutor=forbidden, make_student_reply=forbidden,
        gemini_tutor_model='gemini-authored')
    for change in ({'send': False}, {'make_student_reply': None}, {'make_student_reply': 'invalid'},
            {'gemini_tutor_model': None}, {'gemini_tutor_model': 'different'},
            {'generate_tutor': None}, {'generate_student': forbidden}):
        with pytest.raises(ValueError):
            setup.run_both(destination, **(options | change))
    plan['version'] = 1
    with pytest.raises(ValueError):
        setup.run_both(destination, **options)


def test_noncallable_local_factory_result_cannot_dispatch_a_tutor(local_plan, monkeypatch):
    setup, destination, _, _ = local_plan
    def forbidden(*_):
        pytest.fail('Invalid local callback must fail before tutor dispatch')
    monkeypatch.setattr(setup.chat_policy_pair, 'respond', forbidden)
    with pytest.raises(ValueError):
        setup.run_both(destination, send=True, generate_tutor=forbidden,
            make_student_reply=lambda _: None, gemini_tutor_model='gemini-authored')


@pytest.mark.parametrize('model', ['', ' \n', False, 3])
def test_invalid_tutor_model_cannot_create_workspace(tmp_path, model):
    from src.agents import policy_comparison_setup as setup

    with pytest.raises(ValueError):
        setup.freeze_next(tmp_path / 'new', source=tmp_path / 'missing', current_policy='Current.',
            proposed_policy='Proposed.', gemini_tutor_model=model)
    assert not (tmp_path / 'new').exists()
