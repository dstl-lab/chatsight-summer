"""Raw-prefix reply callbacks use saved state, with no model or provider access."""
from contextlib import contextmanager
from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from src.agents import browser_workspace, chat_student as chat, chat_workspace as workspace
from src.agents import notebook_student as store
from tests.test_chat_student import QUERY, files


def test_browser_routes_exact_prefixes_and_preserves_guarded_lifecycle(tmp_path, monkeypatch):
    query = deepcopy(QUERY)
    query['prefix'][0]['text'] = ' 中文\n\n  values = [2, 5]\n'
    other = deepcopy(query)
    other['prefix'][0]['text'] = 'Other student\n\nvalues = [8, 9]'
    collection = tmp_path / 'chats'
    starts = {name: chat.create(collection / name, query=value, max_decisions=3)
              for name, value in [('a', query), ('b', other)]}
    for name, initial in starts.items():
        assert chat.show(collection / name) == initial
    calls, events = [], []
    depth = [0]
    original_lock, original_show = store._locked, chat.show

    @contextmanager
    def lock(folder):
        with original_lock(folder):
            depth[0] += 1
            try:
                yield
            finally:
                depth[0] -= 1

    def unlocked_show(folder):
        assert depth[0] == 0, 'Reply adaptation must not reacquire the student lock'
        return original_show(folder)

    monkeypatch.setattr(store, '_locked', lock)
    monkeypatch.setattr(chat, 'show', unlocked_show)
    monkeypatch.setattr(store.llm, 'make_generate', lambda *a, **kw: pytest.fail('Unexpected provider dispatch'))

    def reply(prefix):
        assert depth[0] == 1
        assert all(set(turn) == {'role', 'text'} for turn in prefix)
        calls.append(deepcopy(prefix))
        events.append('student')
        return '  学生\n\nreply ' + str(len(calls)) + '\n'

    tutor_text = 'Try one value.\n\n 保留空白 \n'

    def tutor(prompt, schema):
        assert depth[0] == 0
        payload = json.loads(prompt[len(workspace.PROMPT):])
        assert payload['policy'] == 'Authored policy.'
        assert payload['context']['pending_message'] == '  学生\n\nreply 2\n'
        events.append('tutor')
        return schema(text=tutor_text)

    browser = TestClient(browser_workspace.create_app(collection, chat_sessions=True, send=True,
        generate_reply=reply, generate_tutor=tutor), base_url='http://127.0.0.1')
    ids = [item['id'] for item in browser.get('/api/scenarios').json()['scenarios']]
    assert len(ids) == 2

    def submit(scenario, binding, mode, text=None):
        body = {'binding': binding, 'mode': mode}
        if text is not None:
            body['text'] = text
        return browser.post('/api/continue', params={'scenario': scenario}, json=body)

    first = submit(ids[0], starts['a']['binding'], 'advance')
    assert first.status_code == 200 and calls == [query['prefix']]
    first_frame = first.json()['encounters'][0]['frames'][-1]
    first_text = chat.show(collection / 'a')['state']['message']
    assert first_text == '  学生\n\nreply 1\n'
    before = files(collection)
    assert submit(ids[0], starts['a']['binding'], 'advance').status_code == 409
    assert files(collection) == before and len(calls) == 1

    manual = 'Manual tutor\n\n  中文 \n'
    second = submit(ids[0], first_frame['binding'], 'reply', manual)
    assert second.status_code == 200
    expected = query['prefix'] + [{'role': 'student', 'text': first_text}, {'role': 'tutor', 'text': manual}]
    assert calls[-1] == expected
    second_frame = second.json()['encounters'][0]['frames'][-1]
    third = submit(ids[0], second_frame['binding'], 'policy', 'Authored policy.')
    assert third.status_code == 200
    assert calls[-1] == expected + [{'role': 'student', 'text': '  学生\n\nreply 2\n'},
                                  {'role': 'tutor', 'text': tutor_text}]
    assert events == ['student', 'student', 'tutor', 'student']
    last = chat.show(collection / 'a')
    assert last['remaining'] == 0 and last['state']['status'] == 'awaiting-tutor'
    before = files(collection)
    assert submit(ids[0], last['binding'], 'reply', 'Again?').status_code == 409
    assert files(collection) == before and len(calls) == 3
    assert submit(ids[1], starts['b']['binding'], 'advance').status_code == 200
    assert calls[-1] == other['prefix'] and len(calls) == 4

    closed = TestClient(browser_workspace.create_app(collection, chat_sessions=True,
        generate_reply=reply, generate_tutor=tutor), base_url='http://127.0.0.1')
    before = files(collection)
    response = closed.post('/api/continue', params={'scenario': ids[1]}, json={
        'binding': chat.show(collection / 'b')['binding'], 'mode': 'reply', 'text': 'Continue?'})
    assert response.status_code == 403 and len(calls) == 4 and files(collection) == before


def test_reply_backend_configuration_rejects_ambiguous_or_unsupported_routing(tmp_path):
    folder = tmp_path / 'chat'
    initial = chat.create(folder, query=QUERY, max_decisions=3)

    def forbidden(*_):
        pytest.fail('Invalid configuration must not dispatch')

    before = files(folder)
    for kwargs in [dict(chat_mode=False), dict(generate_tutor=None), dict(generate=forbidden),
                   dict(policy_workspace=tmp_path / 'comparisons')]:
        options = dict(chat_mode=True, generate_reply=forbidden, generate_tutor=forbidden) | kwargs
        with pytest.raises(ValueError):
            browser_workspace.create_app(folder, **options)
    for kwargs in [dict(send=False), dict(generate=forbidden)]:
        with pytest.raises(ValueError):
            workspace.advance(folder, **(dict(binding=initial['binding'], send=True,
                generate_reply=forbidden) | kwargs))
    assert files(folder) == before
    ready = workspace.advance(folder, binding=initial['binding'], send=True, generate_reply=lambda _: '7?')
    before = files(folder)
    with pytest.raises(ValueError):
        workspace.respond(folder, binding=ready['binding'], send=True, policy='Authored policy.',
                          generate_tutor=forbidden, generate_student=forbidden, generate_reply=forbidden)
    assert files(folder) == before


@pytest.mark.parametrize('failure', ['blank', 'wrong-type', 'exception'])
def test_failed_reply_remains_an_error_and_cannot_resend(tmp_path, failure):
    folder = tmp_path / failure
    initial = chat.create(folder, query=QUERY, max_decisions=2)
    calls = []

    def failed(prefix):
        calls.append(deepcopy(prefix))
        if failure == 'exception':
            raise RuntimeError('Authored callback failure')
        return ' \n' if failure == 'blank' else {'text': 'Incorrect result type'}

    result = workspace.advance(folder, binding=initial['binding'], send=True, generate_reply=failed)
    assert result['status'] == 'error' and calls == [QUERY['prefix']]
    saved = chat.show(folder)
    assert saved['decisions'] == 1 and saved['remaining'] == 1
    before = files(folder)
    for binding in (initial['binding'], saved['binding']):
        with pytest.raises(ValueError):
            workspace.advance(folder, binding=binding, send=True, generate_reply=failed)
    assert files(folder) == before and calls == [QUERY['prefix']]


def test_manual_tutor_blocks_policy_before_reserving_and_keeps_typed_history(tmp_path, monkeypatch):
    folder = tmp_path / 'local'
    initial = chat.create(folder, query=QUERY, max_decisions=2)
    chat.show(folder)
    calls = []
    monkeypatch.setattr(store.llm, 'make_generate', lambda *a, **kw: pytest.fail('Provider dispatch'))

    def reply(prefix):
        calls.append(deepcopy(prefix))
        return 'a short authored question'

    before = files(folder)
    browser = TestClient(browser_workspace.create_app(folder, chat_mode=True, send=True,
        generate_reply=reply, manual_tutor=True), base_url='http://127.0.0.1')
    assert browser.get('/api/workspace').json()['controls']['tutor_generation_enabled'] is False
    assert files(folder) == before and calls == []
    first = browser.post('/api/continue', json={'binding': initial['binding'], 'mode': 'advance'})
    assert first.status_code == 200 and calls == [QUERY['prefix']]
    binding = chat.show(folder)['binding']
    before = files(folder)
    refused = browser.post('/api/continue', json={'binding': binding, 'mode': 'policy', 'text': 'Hint only.'})
    assert refused.status_code == 403 and files(folder) == before and len(calls) == 1
    text = '  Try one value.\n\n中文\n'
    response = browser.post('/api/continue', json={'binding': binding, 'mode': 'reply', 'text': text})
    assert response.status_code == 200 and calls[-1] == QUERY['prefix'] + [
        {'role': 'student', 'text': 'a short authored question'}, {'role': 'tutor', 'text': text}]
    before = files(folder)
    closed = TestClient(browser_workspace.create_app(folder, chat_mode=True,
        generate_reply=reply, manual_tutor=True), base_url='http://127.0.0.1')
    assert closed.get('/api/workspace').status_code == 200
    assert closed.post('/api/continue', json={'binding': chat.show(folder)['binding'],
        'mode': 'reply', 'text': text}).status_code == 403
    assert files(folder) == before and len(calls) == 2
    for options in ({'chat_mode': False}, {'generate_tutor': lambda *_: None},
                    {'policy_workspace': tmp_path / 'policies'}, {'manual_tutor': 'yes'}):
        with pytest.raises(ValueError):
            browser_workspace.create_app(folder, **(dict(chat_mode=True,
                generate_reply=reply, manual_tutor=True) | options))


def test_cli_local_student_paths_are_explicit_and_never_enable_a_tutor(tmp_path, monkeypatch):
    import sys
    import uvicorn
    from src.agents import local_student

    folder = tmp_path / 'session'
    chat.create(folder, query=QUERY, max_decisions=2)
    chat.show(folder)
    calls, apps = [], []
    def factory(session, **options):
        calls.append((session, options))
        return lambda _: 'An authored reply.'
    monkeypatch.setattr(local_student, 'make_reply', factory)
    monkeypatch.setattr(uvicorn, 'run', lambda app, **options: apps.append(app))
    arguments = ['browser_workspace', str(folder), '--chat', '--student-model', str(tmp_path / 'model'),
                 '--student-python', sys.executable, '--student-adapter', str(tmp_path / 'adapter')]
    monkeypatch.setattr(sys, 'argv', arguments)
    before = files(folder)
    browser_workspace.main()
    from pathlib import Path
    assert calls == [(folder, {'model': tmp_path / 'model', 'python': Path(sys.executable),
                              'adapter': tmp_path / 'adapter'})]
    client = TestClient(apps[0], base_url='http://127.0.0.1')
    controls = client.get('/api/workspace').json()['controls']
    assert controls['send_enabled'] is False and controls['tutor_generation_enabled'] is False
    assert files(folder) == before
    for bad in [arguments[:2] + arguments[3:], arguments + ['--policy-workspace', str(tmp_path / 'pair')],
                arguments + ['--policy-file', str(tmp_path / 'policy')],
                arguments[:3] + arguments[5:], arguments[:5]]:
        monkeypatch.setattr(sys, 'argv', bad)
        with pytest.raises(SystemExit) as error:
            browser_workspace.main()
        assert error.value.code == 2
    assert len(calls) == len(apps) == 1 and files(folder) == before


def test_bound_local_session_cannot_fall_through_provider_entry_points(tmp_path, monkeypatch):
    import sys
    from src.agents.student_workspace import _generate

    folder = tmp_path / 'bound'
    initial = chat.create(folder, query=QUERY)
    chat.show(folder)
    (folder / 'local-student').mkdir()  # Also protect incomplete first-call binding.
    monkeypatch.setattr(store.llm, 'make_generate', lambda *a, **kw: pytest.fail('Provider fallback'))
    before = files(folder)
    client = TestClient(browser_workspace.create_app(folder, chat_mode=True, send=True),
                        base_url='http://127.0.0.1')
    assert 'local student' in client.get('/api/workspace').json()['controls']['blocked_reason']
    assert client.post('/api/continue', json={'binding': initial['binding'], 'mode': 'advance'}).status_code == 409
    with pytest.raises(ValueError):
        _generate(folder, 'Do not send', object)
    with pytest.raises(ValueError):
        browser_workspace.create_app(folder, chat_mode=True, policy_workspace=tmp_path / 'policies')
    monkeypatch.setattr(sys, 'argv', ['chat_student', 'step', str(folder), '--send',
        '--context-file', str(tmp_path / 'context.json')])
    with pytest.raises(SystemExit) as error:
        chat.main()
    assert error.value.code == 2 and files(folder) == before
