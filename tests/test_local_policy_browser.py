"""Whole comparison flow with the real local worker and authored fake MLX modules."""
from functools import partial
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
import uvicorn

from src.agents import browser_workspace as browser, chat_student as chat, chat_policy_pair as pair, local_student
from tests.test_browser_policy_runs import save
from tests.test_chat_student import files
from tests.test_local_student_import import source as local_source


MODEL = 'gemini-authored-tutor'


@pytest.mark.parametrize('failure', [None, 'tutor', 'student'])
def test_local_pairs_keep_shared_start_and_separate_calls_through_browser(tmp_path, monkeypatch, failure):
    source, model, adapter, python, query, calls = local_source(tmp_path, monkeypatch)
    workspace = tmp_path / 'runs'
    original = files(source)
    factory = partial(local_student.make_reply, model=model, adapter=adapter, python=python)
    tutors = []
    def tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        tutors.append(payload)
        if failure == 'tutor' and len(tutors) == 1:
            raise RuntimeError('Authored tutor failure')
        return schema(text='Hint: count the entries.' if len(tutors) == 1 else 'Answer: two.')

    if failure == 'student':
        run = local_student.subprocess.run
        def fail_first(command, **options):
            path = Path(command[-1])
            if path.parent.parent.name == 'a':
                calls.append((path, json.loads((path / 'request.json').read_text())))
                return SimpleNamespace(returncode=1)
            return run(command, **options)
        monkeypatch.setattr(local_student.subprocess, 'run', fail_first)
    monkeypatch.setattr(chat.llm, 'make_generate', lambda *a, **kw: pytest.fail('Cloud fallback'))
    options = dict(chat_mode=True, policy_workspace=workspace, generate_reply=factory(source),
        make_student_reply=factory, generate_tutor=tutor, gemini_tutor_model=MODEL)
    client = TestClient(browser.create_app(source, send=True, **options), base_url='http://127.0.0.1')
    assert client.get('/api/comparison').json()['controls']['gemini_tutor_model'] == MODEL
    binding = save(client)
    destination = workspace / 'run-0001'
    plan = pair._comparison(destination)
    assert plan['plan']['version'] == 2 and plan['plan']['gemini_tutor_model'] == MODEL
    assert len(calls) == 1 and not tutors and files(source) == original
    starts = [pair.show(destination)['conditions'][arm]['snapshot'] for arm in ('a', 'b')]
    assert starts[0]['dialogue'] == starts[1]['dialogue']
    assert starts[0]['pending_message'] == starts[1]['pending_message'] == '  authored\n'
    assert starts[0]['binding']['session_sha256'] != starts[1]['binding']['session_sha256']
    for arm in ('a', 'b'):
        root = destination / 'sessions' / arm / 'local-student'
        assert files(root / 'cached-start/local-student') == files(source / 'local-student')
        assert not list(root.glob('call-*'))

    readonly = TestClient(browser.create_app(source, **options), base_url='http://127.0.0.1')
    assert readonly.post('/api/comparison/run', json=binding).status_code == 403
    result = client.post('/api/comparison/run', json=binding)
    assert result.status_code == 200, result.text
    case = result.json()['cases'][0]
    assert case['gemini_tutor_model'] == MODEL
    assert [condition['status'] for condition in case['conditions']] == [
        'failed' if failure else 'student-replied', 'student-replied']
    assert [item['policy'] for item in tutors] == ['Give one hint.', 'Give the answer.']
    assert tutors[0]['context'] == tutors[1]['context']
    assert tutors[0]['context']['pending_message'] == '  authored\n'
    fresh = calls[1:]
    assert len(fresh) == (1 if failure == 'tutor' else 2)
    assert {request['seed'] for _, request in fresh} == {20260929}
    for path, request in fresh:
        assert path.name == 'call-0002' and path.parent.parent.name in ('a', 'b')
        assert request['prefix'][:-1] == query['prefix'] + [{'role':'student', 'text':'  authored\n'}]
        assert request['prefix'][-1]['role'] == 'tutor'
        receipt = next(path.parent.parent.glob('tutor-exchanges/*/receipt.json'))
        saved = json.loads(receipt.read_text())
        assert saved['request']['model'] == MODEL and saved['request']['provider'] == 'google-gemini'
        assert request['prefix'][-1]['text'] == saved['response']['text']
    assert files(source) == original
    before, count = files(tmp_path), len(calls)
    assert client.post('/api/comparison/run', json=binding).status_code == 409
    reopened = TestClient(browser.create_app(source, **options), base_url='http://127.0.0.1')
    assert reopened.get('/api/comparison').status_code == 200
    assert files(tmp_path) == before and len(calls) == count and len(tutors) == 2

    with pytest.raises(ValueError, match='original tutor'):
        browser.create_app(source, **(options | {'gemini_tutor_model':'different-tutor'}))
    child = destination / 'sessions/a'
    (child / 'local-student/cached-start/step-0001.json').write_text('{}')
    assert client.get('/api/comparison').status_code == 409
    assert client.post('/api/comparison/run', json=binding).status_code == 409
    assert len(calls) == count and len(tutors) == 2


def test_cli_fresh_chat_becomes_comparison_source_without_restart(tmp_path, monkeypatch):
    _, model, adapter, python, query, calls = local_source(tmp_path, monkeypatch)
    fresh = tmp_path / 'fresh'
    start = chat.create(fresh, query=query, max_decisions=3)
    chat.show(fresh)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **kw: apps.append(app))
    monkeypatch.setattr(chat.llm, 'make_generate', lambda *a, **kw: pytest.fail('Offline setup sent tutor request'))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(fresh), '--chat', '--send',
        '--student-model', str(model), '--student-adapter', str(adapter), '--student-python', str(python),
        '--gemini-tutor-model', MODEL, '--policy-workspace', str(tmp_path / 'fresh-runs')])
    browser.main()
    client = TestClient(apps[0], base_url='http://127.0.0.1')
    assert client.get('/api/comparison').json()['controls']['sources'] == []
    assert client.post('/api/continue', json={'binding':start['binding'], 'mode':'advance'}).status_code == 200
    assert len(client.get('/api/comparison').json()['controls']['sources']) == 1
    count = len(calls)
    save(client)
    assert len(calls) == count  # Saving archives the first reply; it never regenerates it.
