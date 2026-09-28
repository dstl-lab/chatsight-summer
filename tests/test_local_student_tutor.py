"""Real CLI and saved chat lifecycle; only local inference and Gemini are faked."""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys

import dotenv
from fastapi.testclient import TestClient
import pytest
import uvicorn

from src.agents import browser_workspace, chat_student as chat, chat_workspace
from src.agents import local_student, notebook_student as store
from tests.test_chat_student import QUERY, files


MODEL = 'gemini-authored-tutor'
TUTOR = '  Try another value.\n\n中文\n'
POLICY = '  Ask one short question.\nDo not supply the answer.\n'


@pytest.fixture
def setup(tmp_path, monkeypatch):
    folder = tmp_path / 'chat'
    query = deepcopy(QUERY)
    query['prefix'][0]['text'] = '  中文\nvalues = [2, 5]\n'
    initial = chat.create(folder, query=query, max_decisions=3, model='legacy-session-model')
    chat.show(folder)
    state = SimpleNamespace(folder=folder, query=query, initial=initial, local=[], provider=[],
        keys=[], dotenv=[], factories=[], failure=None, apps=[])

    def reply(prefix):
        state.local.append(deepcopy(prefix))
        if state.failure == 'student' and len(state.local) > 1:
            raise RuntimeError('Authored private student failure')
        return '  student ' + str(len(state.local)) + '\n'

    def local_factory(session, **options):
        state.factories.append((session, options))
        return reply

    def provider_factory(key, **options):
        assert key == 'authored-test-key'
        assert options == {'model': MODEL, 'single_attempt': True}
        def generate(prompt, schema):
            state.provider.append(prompt)
            if state.failure == 'tutor':
                raise RuntimeError('Authored private tutor failure')
            return schema(text=TUTOR)
        return generate

    getitem = type(os.environ).__getitem__
    def tracked_key(environ, key):
        if key == 'GEMINI_API_KEY':
            state.keys.append(key)
        return getitem(environ, key)

    monkeypatch.setenv('GEMINI_API_KEY', 'authored-test-key')
    monkeypatch.setattr(type(os.environ), '__getitem__', tracked_key)
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda path: state.dotenv.append(path))
    monkeypatch.setattr(local_student, 'make_reply', local_factory)
    monkeypatch.setattr(store.llm, 'make_generate', provider_factory)
    monkeypatch.setattr(uvicorn, 'run', lambda app, **_: state.apps.append(app))

    state.arguments = ['browser_workspace', str(folder), '--chat', '--student-model',
        str(tmp_path / 'model'), '--student-python', sys.executable,
        '--student-adapter', str(tmp_path / 'adapter')]
    def start(*, send=True, gemini=True):
        args = state.arguments + (['--gemini-tutor-model', MODEL] if gemini else [])
        monkeypatch.setattr(sys, 'argv', args + (['--send'] if send else []))
        browser_workspace.main()
        return TestClient(state.apps[-1], base_url='http://127.0.0.1')
    state.start = start
    return state


def submit(client, binding, mode, text=None):
    return client.post('/api/continue', json={'binding': binding, 'mode': mode,
        **({'text': text} if text is not None else {})})


def test_cli_routes_local_and_explicit_tutor_without_startup_dispatch(setup):
    s = setup
    before = files(s.folder)
    client = s.start()
    controls = client.get('/api/workspace').json()['controls']
    assert controls['gemini_tutor_model'] == MODEL and controls['tutor_generation_enabled']
    assert files(s.folder) == before and not (s.local or s.provider or s.keys or s.dotenv)
    assert s.factories == [(s.folder, {'model': s.folder.parent / 'model',
        'python': Path(sys.executable), 'adapter': s.folder.parent / 'adapter'})]

    assert submit(client, s.initial['binding'], 'advance').status_code == 200
    assert s.local == [s.query['prefix']] and not (s.provider or s.keys or s.dotenv)
    first = chat.show(s.folder)
    before = files(s.folder)
    assert submit(client, s.initial['binding'], 'advance').status_code == 409
    assert files(s.folder) == before and len(s.local) == 1
    typed = '  Typed tutor\n\n保留空白\n'
    assert submit(client, first['binding'], 'reply', typed).status_code == 200
    expected = s.query['prefix'] + [{'role': 'student', 'text': '  student 1\n'},
        {'role': 'tutor', 'text': typed}]
    assert s.local[-1] == expected and not (s.provider or s.keys or s.dotenv)

    second = chat.show(s.folder)
    assert submit(client, second['binding'], 'policy', POLICY).status_code == 200
    assert len(s.provider) == len(s.keys) == 1 and len(s.local) == 3
    payload = json.loads(s.provider[0][len(chat_workspace.PROMPT):])
    assert payload['policy'] == POLICY and payload['context']['pending_message'] == '  student 2\n'
    prior = expected + [{'role': 'student', 'text': '  student 2\n'}]
    assert [{k: turn[k] for k in ('role', 'text')} for turn in payload['context']['dialogue']] == expected
    assert 'PRIVATE_' not in s.provider[0]
    assert s.local[-1] == prior + [{'role': 'tutor', 'text': TUTOR}]
    receipt = json.loads(next(s.folder.glob('tutor-exchanges/*/receipt.json')).read_text())
    assert receipt['request']['model'] == MODEL
    assert receipt['request']['provider'] == 'google-gemini'
    assert receipt['request']['prompt'] == s.provider[0] and receipt['request']['policy'] == POLICY
    assert receipt['response'] == {'text': TUTOR} and receipt['status'] == 'complete'
    assert json.loads((s.folder / 'session.json').read_text())['model'] == 'legacy-session-model'
    assert chat.show(s.folder)['remaining'] == 0

    before = files(s.folder)
    reopened = s.start()
    assert reopened.get('/api/workspace').status_code == 200
    for binding in (s.initial['binding'], second['binding'], chat.show(s.folder)['binding']):
        assert submit(reopened, binding, 'policy', POLICY).status_code == 409
    assert files(s.folder) == before and len(s.local) == 3 and len(s.provider) == len(s.keys) == 1


def test_manual_default_and_read_only_reopen_never_contact_tutor(setup):
    s = setup
    before = files(s.folder)
    closed = s.start(send=False)
    assert closed.get('/api/workspace').status_code == 200
    assert submit(closed, s.initial['binding'], 'advance').status_code == 403
    assert files(s.folder) == before and not (s.local or s.provider or s.keys or s.dotenv)
    manual = s.start(gemini=False)
    controls = manual.get('/api/workspace').json()['controls']
    assert controls['tutor_generation_enabled'] is False and 'gemini_tutor_model' not in controls
    assert submit(manual, s.initial['binding'], 'advance').status_code == 200
    binding = chat.show(s.folder)['binding']
    before = files(s.folder)
    assert submit(manual, binding, 'policy', POLICY).status_code == 403
    assert files(s.folder) == before
    assert submit(manual, binding, 'reply', TUTOR).status_code == 200
    assert s.local[-1][-1] == {'role': 'tutor', 'text': TUTOR}
    assert not (s.provider or s.keys or s.dotenv) and not (s.folder / 'tutor-exchanges').exists()


def test_explicit_tutor_mode_rejects_other_workspace_modes_before_reading_them(setup):
    s = setup
    def forbidden(*_):
        pytest.fail('Invalid configuration dispatched')
    before = files(s.folder)
    for options in ({'chat_mode': False}, {'chat_sessions': True}, {'manual_tutor': True},
            {'generate_reply': None}, {'generate_tutor': None},
            *({name: s.folder.parent / 'missing'} for name in ('comparison', 'policy_comparison',
                'policy_workspace', 'fidelity_comparison', 'teaching_comparison',
                'next_exercise_file', 'next_exercise_output'))):
        with pytest.raises(ValueError):
            browser_workspace.create_app(s.folder, **(dict(chat_mode=True, generate_reply=forbidden,
                generate_tutor=forbidden, gemini_tutor_model=MODEL) | options))
    assert files(s.folder) == before


@pytest.mark.parametrize('failure', ['tutor', 'student'])
def test_failed_exchange_is_saved_and_reopen_cannot_resend_or_fall_back(setup, failure):
    s = setup
    client = s.start()
    assert submit(client, s.initial['binding'], 'advance').status_code == 200
    binding = chat.show(s.folder)['binding']
    s.failure = failure
    response = submit(client, binding, 'policy', POLICY)
    assert response.status_code == (409 if failure == 'tutor' else 200)
    assert 'Authored private' not in response.text
    assert len(s.provider) == len(s.keys) == 1
    assert len(s.local) == (1 if failure == 'tutor' else 2)
    receipt = json.loads(next(s.folder.glob('tutor-exchanges/*/receipt.json')).read_text())
    assert receipt['request']['model'] == MODEL
    if failure == 'tutor':
        assert receipt['status'] == 'error' and receipt['continuation']['status'] == 'not-started'
        assert chat.show(s.folder)['state']['status'] == 'awaiting-tutor'
    else:
        assert receipt['status'] == 'complete' and receipt['response'] == {'text': TUTOR}
        assert chat.show(s.folder)['state']['status'] == 'error'
        assert s.local[-1][-1] == {'role': 'tutor', 'text': TUTOR}
    before = files(s.folder)
    reopened = s.start()
    assert reopened.get('/api/workspace').status_code == 200
    for current in (binding, chat.show(s.folder)['binding']):
        assert submit(reopened, current, 'policy', POLICY).status_code == 409
        assert submit(reopened, current, 'reply', TUTOR).status_code == 409
    assert files(s.folder) == before and len(s.provider) == len(s.keys) == 1
    assert len(s.local) == (1 if failure == 'tutor' else 2)


def test_invalid_cli_options_reject_before_backend_or_app_start(setup, monkeypatch):
    s = setup
    before = files(s.folder)
    args = s.arguments
    bad = [args[:3] + ['--gemini-tutor-model', MODEL], args + ['--gemini-tutor-model', '  '],
        args[:2] + args[3:] + ['--gemini-tutor-model', MODEL],
        args + ['--gemini-tutor-model', MODEL, '--comparison', str(s.folder.parent / 'comparison')],
        args + ['--gemini-tutor-model', MODEL, '--next-exercise-file', str(s.folder.parent / 'exercise')],
        args + ['--policy-file', str(s.folder.parent / 'policy')]]
    for arguments in bad:
        monkeypatch.setattr(sys, 'argv', arguments)
        with pytest.raises(SystemExit) as error:
            browser_workspace.main()
        assert error.value.code == 2
    assert files(s.folder) == before and not (s.factories or s.apps or s.local or s.provider or s.keys or s.dotenv)


@pytest.mark.parametrize('model', ['', ' \n', False, 3])
def test_invalid_model_override_rejects_before_any_saved_exchange(setup, model):
    s = setup
    def forbidden(*_):
        pytest.fail('Invalid configuration dispatched')
    before = files(s.folder)
    with pytest.raises(ValueError):
        browser_workspace.create_app(s.folder, chat_mode=True, generate_reply=forbidden,
            generate_tutor=forbidden, gemini_tutor_model=model)
    with pytest.raises(ValueError):
        chat_workspace.respond(s.folder, binding=s.initial['binding'], send=True, policy=POLICY,
            generate_reply=forbidden, generate_tutor=forbidden, gemini_tutor_model=model)
    assert files(s.folder) == before
