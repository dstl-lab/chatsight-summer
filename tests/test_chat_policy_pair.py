"""Policy comparisons reuse one cached start without sharing identities or dispatches."""
from copy import deepcopy
import importlib.util
import json

import pytest

from src.agents import chat_student as chat, notebook_student as store
from src.eval.student_continuation import Continuation
from tests.test_chat_student import QUERY, files


POLICIES = {'a': 'Give one concise hint.', 'b': 'Give the answer directly.'}


def _pair(monkeypatch):
    assert importlib.util.find_spec('src.agents.chat_policy_pair'), 'Chat policy comparison is missing'
    from src.agents import chat_policy_pair
    monkeypatch.setattr(store.llm, 'make_generate', _forbidden)
    return chat_policy_pair


def _forbidden(*_args, **_kwargs):
    pytest.fail('Offline or rejected comparison dispatched a provider')


def _source(folder):
    first = chat.create(folder, query=deepcopy(QUERY), model='authored-model')
    return chat.step(folder, binding=first['binding'],
                     generate=lambda *_: Continuation(decision='reply', text='7?'))


def test_common_cached_start_continues_independently_with_fixed_policies_and_budget(tmp_path, monkeypatch):
    pair = _pair(monkeypatch)
    source, folder = tmp_path/'source', tmp_path/'pair'
    original = _source(source)
    before = files(source)
    policies = deepcopy(POLICIES)
    created = pair.create(folder, source=source, policies=policies, max_new_decisions=1)
    assert created == pair.show(folder) and files(source) == before
    assert created['max_new_decisions'] == 1 and created['source']
    policies['a'] = 'A later draft must not change the saved policy.'
    children = {name: folder/'sessions'/name for name in ('a', 'b')}
    manifests = [store._read(path/'session.json') for path in (source, *children.values())]
    assert len({m['session_id'] for m in manifests}) == 3
    assert all(m['model'] == 'authored-model' and m['max_decisions'] == 2 for m in manifests[1:])
    for name, child in children.items():
        saved = chat.show(child)
        assert saved['state'] == original['state'] and saved['decisions'] == saved['remaining'] == 1
        assert created['conditions'][name]['snapshot']['pending_message'] == '7?'
        assert created['conditions'][name]['policy'] == POLICIES[name]
        assert not created['conditions'][name]['error']

    calls = []
    for name, decision, reply in (('a', 'reply', '3 values too?'), ('b', 'no-reply', '')):
        binding = created['conditions'][name]['snapshot']['binding']

        def tutor(prompt, schema):
            payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
            assert payload['policy'] == POLICIES[name]
            assert payload['context']['pending_message'] == '7?' and 'PRIVATE_' not in prompt
            calls.append((name, 'tutor'))
            return schema(text=f'Authored tutor {name}.')

        def student(prompt, schema):
            assert f'Authored tutor {name}.' in prompt and 'PRIVATE_' not in prompt
            calls.append((name, 'student'))
            return schema(decision=decision, text=reply)

        if name == 'a':
            with pytest.raises(ValueError):
                pair.respond(folder, name, binding=created['conditions']['b']['snapshot']['binding'],
                             send=True, generate_tutor=_forbidden, generate_student=_forbidden)
            with pytest.raises(ValueError):
                pair.respond(folder, name, binding=binding,
                             generate_tutor=_forbidden, generate_student=_forbidden)
        saved = pair.respond(folder, name, binding=binding, send=True,
                             generate_tutor=tutor, generate_student=student)
        assert saved == pair.show(folder)
        condition = saved['conditions'][name]
        assert condition['snapshot']['status'] == ('awaiting-tutor' if decision == 'reply' else 'no-reply')
        assert condition['snapshot']['decisions_remaining'] == 0
        assert POLICIES[name] in condition['history'] and f'Authored tutor {name}.' in condition['history']
        if name == 'a':
            assert saved['conditions']['b'] == created['conditions']['b']
        preserved = files(folder)
        with pytest.raises(ValueError):
            pair.respond(folder, name, binding=condition['snapshot']['binding'], send=True,
                         generate_tutor=_forbidden, generate_student=_forbidden)
        assert files(folder) == preserved
    assert calls == [('a', 'tutor'), ('a', 'student'), ('b', 'tutor'), ('b', 'student')]
    assert files(source) == before
    preserved = files(folder)
    assert pair.show(folder) == saved and files(folder) == preserved


@pytest.mark.parametrize('mode', ['empty', 'no-reply', 'pending', 'progressed', 'tutor-attempt', 'changed-prompt'])
def test_only_an_intact_first_reply_can_seed_a_pair(tmp_path, monkeypatch, mode):
    pair = _pair(monkeypatch)
    source, folder = tmp_path/'source', tmp_path/'pair'
    first = chat.create(source, query=QUERY)

    def interrupted(*_):
        raise KeyboardInterrupt('Authored interruption')

    if mode == 'pending':
        with pytest.raises(KeyboardInterrupt):
            chat.step(source, binding=first['binding'], generate=interrupted)
    elif mode != 'empty':
        saved = chat.step(source, binding=first['binding'], generate=lambda *_:
            Continuation(decision='no-reply', text='') if mode == 'no-reply'
            else Continuation(decision='reply', text='7?'))
        if mode == 'progressed':
            chat.step(source, binding=saved['binding'], tutor_reply='Yes.',
                      generate=lambda *_: Continuation(decision='reply', text='next?'))
        elif mode == 'tutor-attempt':
            from src.agents import chat_workspace
            with pytest.raises(KeyboardInterrupt):
                chat_workspace.respond(source, binding=saved['binding'], policy='An earlier policy.',
                                       send=True, generate_tutor=interrupted, generate_student=_forbidden)
        elif mode == 'changed-prompt':
            path = source/'step-0001.json'
            receipt = store._read(path)
            receipt['request']['prompt'] += '\nChanged cached request.'
            path.write_text(json.dumps(receipt))
    before = files(source)
    with pytest.raises(ValueError):
        pair.create(folder, source=source, policies=POLICIES)
    assert not folder.exists() and files(source) == before


def test_bad_inputs_existing_destination_and_interrupted_setup_do_not_publish_a_pair(tmp_path, monkeypatch):
    pair = _pair(monkeypatch)
    source, folder = tmp_path/'source', tmp_path/'pair'
    _source(source)
    before_source = files(source)
    for index, change in enumerate(({'policies': {'a': 'Only one.'}},
                                   {'policies': POLICIES | {'b': ' '}},
                                   {'max_new_decisions': 0}, {'max_new_decisions': True})):
        rejected = tmp_path/f'invalid-{index}'
        with pytest.raises(ValueError):
            pair.create(rejected, **({'source': source, 'policies': POLICIES} | change))
        assert not rejected.exists()
    pair.create(folder, source=source, policies=POLICIES)
    before_pair = files(folder)
    with pytest.raises(FileExistsError):
        pair.create(folder, source=source, policies=POLICIES)
    assert files(folder) == before_pair

    save = store._save

    def interrupt_second(path, value, **kwargs):
        if path.name == 'session.json' and path.parent.name == 'b':
            raise KeyboardInterrupt('Authored interruption during second condition setup')
        return save(path, value, **kwargs)

    with monkeypatch.context() as patched:
        patched.setattr(store, '_save', interrupt_second)
        with pytest.raises(KeyboardInterrupt):
            pair.create(tmp_path/'interrupted', source=source, policies=POLICIES)
    assert not (tmp_path/'interrupted').exists() and files(source) == before_source


@pytest.mark.parametrize('stage,interrupted', [('tutor', False), ('tutor', True), ('student', False), ('student', True)])
def test_failed_or_interrupted_arm_remains_visible_without_resend_or_hiding_other_arm(
        tmp_path, monkeypatch, stage, interrupted):
    pair = _pair(monkeypatch)
    source, folder = tmp_path/'source', tmp_path/'pair'
    _source(source)
    start = pair.create(folder, source=source, policies=POLICIES)
    binding = start['conditions']['a']['snapshot']['binding']
    calls = []

    def failure():
        if interrupted:
            raise KeyboardInterrupt('Authored interrupted request')
        raise RuntimeError('Authored failed request')

    def tutor(_, schema):
        calls.append('tutor')
        if stage == 'tutor':
            failure()
        return schema(text='Authored policy answer.')

    def student(*_):
        calls.append('student')
        failure()

    try:
        pair.respond(folder, 'a', binding=binding, send=True,
                     generate_tutor=tutor, generate_student=student)
    except (KeyboardInterrupt, RuntimeError):
        pass
    saved = pair.show(folder)
    assert saved['conditions']['b'] == start['conditions']['b']
    history = saved['conditions']['a']['history']
    assert POLICIES['a'] in history and '7?' in history
    assert ('incomplete' if interrupted else 'failed') in history.lower()
    if stage == 'student':
        assert 'Authored policy answer.' in history
    if stage == 'student' and not interrupted:
        assert saved['conditions']['a']['snapshot']['status'] == 'error'
    before = files(folder)
    with pytest.raises((ValueError, FileExistsError)):
        pair.respond(folder, 'a', binding=binding, send=True,
                     generate_tutor=_forbidden, generate_student=_forbidden)
    assert files(folder) == before
    assert calls == (['tutor'] if stage == 'tutor' else ['tutor', 'student'])

    result = pair.respond(folder, 'b', binding=start['conditions']['b']['snapshot']['binding'], send=True,
        generate_tutor=lambda _, schema: schema(text='The other arm still works.'),
        generate_student=lambda _, schema: schema(decision='no-reply', text=''))
    assert result['conditions']['b']['snapshot']['status'] == 'no-reply'
    assert result['conditions']['a'] == saved['conditions']['a']


@pytest.mark.parametrize('changed', ['policy', 'startup', 'missing-plan'])
def test_changed_policy_or_startup_is_visible_and_cannot_generate(tmp_path, monkeypatch, changed):
    pair = _pair(monkeypatch)
    source, folder = tmp_path/'source', tmp_path/'pair'
    _source(source)
    initial = pair.create(folder, source=source, policies=POLICIES)
    if changed == 'missing-plan':
        (folder/'comparison.json').write_text('{}')
    elif changed == 'policy':
        path = folder/'comparison.json'
        previous = path.read_text()
        assert POLICIES['a'] in previous
        path.write_text(previous.replace(POLICIES['a'], 'An altered policy.'))
    else:
        path = folder/'sessions/a/step-0001.json'
        receipt = store._read(path)
        receipt['response']['text'] = 'An altered cached reply.'
        path.write_text(json.dumps(receipt))
    before = files(folder)
    # Global comparison damage may reject the whole view; isolated child damage
    # must not be presented as a usable starting point or conceal the other arm.
    try:
        saved = pair.show(folder)
    except ValueError:
        assert changed in ('policy', 'missing-plan')
    else:
        assert saved['conditions']['a']['snapshot'] is None and saved['conditions']['a']['error']
        if changed == 'startup':
            assert saved['conditions']['b'] == initial['conditions']['b']
    with pytest.raises(ValueError):
        pair.respond(folder, 'a', binding=initial['conditions']['a']['snapshot']['binding'], send=True,
                     generate_tutor=_forbidden, generate_student=_forbidden)
    assert files(folder) == before
