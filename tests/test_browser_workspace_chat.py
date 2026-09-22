"""Browser chat sessions retain recorded text without inventing notebook evidence."""
import json
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_student as chat, notebook_student as store
from tests.test_chat_student import QUERY, files


def session(tmp_path, budget=3):
    folder = tmp_path / 'chat'
    chat.create(folder, query=QUERY, max_decisions=budget)
    chat.show(folder)  # Initialize the runner lock before opening the read-only viewer.
    return folder


def client(folder, **options):
    return TestClient(browser.create_app(folder, chat_mode=True, **options), base_url='http://127.0.0.1')


def body(folder, mode='advance', **extra):
    return {'binding': chat.show(folder)['binding'], 'mode': mode} | extra


def latest(response):
    assert response.status_code == 200, response.text
    return response.json()['encounters'][0]['frames'][-1]


def test_chat_frames_are_verified_private_and_read_only(tmp_path, monkeypatch):
    folder = session(tmp_path)
    chat.step(folder, binding=chat.show(folder)['binding'],
              generate=lambda _, schema: schema(decision='reply', text='<script>7?</script>'))
    chat.step(folder, binding=chat.show(folder)['binding'], tutor_reply='Yes.',
              generate=lambda _, schema: schema(decision='no-reply', text=''))
    before = files(folder)
    monkeypatch.setattr(store.llm, 'make_generate', lambda *_a, **_kw: pytest.fail('Provider dispatch'))
    viewer = client(folder)
    response = viewer.get('/api/workspace')
    packet = response.json()
    assert packet['kind'] == 'chat' and packet['controls']['send_enabled'] is False
    encounter, = packet['encounters']
    assert encounter['title'] == 'Conversation' and encounter['activity'] is None
    frames = encounter['frames']
    assert [frame['status'] for frame in frames] == ['ready', 'awaiting-tutor', 'no-reply']
    assert [frame['decisions_remaining'] for frame in frames] == [3, 2, 1]
    assert [frame['label'] for frame in frames] == ['Initial state', 'Saved step 1', 'Saved step 2']
    assert frames[1]['pending_message'] == '<script>7?</script>'
    assert frames[1]['dialogue'] == frames[0]['dialogue']
    assert frames[2]['dialogue'][-2:] == [
        {'role': 'student', 'text': '<script>7?</script>', 'origin': 'generated'},
        {'role': 'tutor', 'text': 'Yes.', 'origin': 'scripted'}]
    assert frames[2]['binding'] == chat.show(folder)['binding']
    assert frames[2]['actions'] == [{'decision': 'no-reply', 'text': '', 'source': None}]
    assert all(frame[key] is None for frame in frames for key in ('work', 'feedback', 'changes'))
    assert 'PRIVATE_' not in response.text and 'engine' not in response.text
    assert viewer.get('/api/workspace').json() == packet and files(folder) == before
    assert viewer.post('/api/continue', json=body(folder)).status_code == 403

    receipt_path = folder / 'step-0001.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['result']['message'] = 'tampered'
    receipt_path.write_text(json.dumps(receipt))
    changed = files(folder)
    assert viewer.get('/api/workspace').status_code == 409
    assert files(folder) == changed
    receipt['status'] = 'pending'
    receipt_path.write_text(json.dumps(receipt))
    assert viewer.get('/api/workspace').status_code == 409


@pytest.mark.parametrize('mode', ['reply', 'policy'])
def test_bound_chat_controls_use_existing_runner_without_checks(tmp_path, mode):
    folder = session(tmp_path, budget=2)
    calls = []

    def student(prompt, schema):
        calls.append('student')
        assert 'PRIVATE_' not in prompt
        return schema(decision='reply', text='7?') if len(calls) == 1 else schema(decision='no-reply', text='')

    def tutor(prompt, schema):
        calls.append('tutor')
        assert 'Edited policy.' in prompt and '7?' in prompt
        return schema(text='Yes, seven.')

    viewer = client(folder, send=True, generate=student, generate_tutor=tutor,
                    check=lambda *_a, **_kw: pytest.fail('Chat executed code'))
    first = body(folder)
    assert viewer.post('/api/continue', json=body(folder, 'reply', text='Premature.')).status_code == 409
    assert latest(viewer.post('/api/continue', json=first))['status'] == 'awaiting-tutor'
    assert viewer.post('/api/continue', json=first).status_code == 409
    assert viewer.post('/api/continue', json=body(folder)).status_code == 409
    submitted = body(folder, mode, text='Edited policy.' if mode == 'policy' else 'Yes, seven.')
    saved = latest(viewer.post('/api/continue', json=submitted))
    assert saved['status'] == 'no-reply' and saved['decisions_remaining'] == 0
    assert saved['dialogue'][-1]['text'] == 'Yes, seven.'
    assert calls == (['student', 'tutor', 'student'] if mode == 'policy' else ['student', 'student'])
    assert viewer.post('/api/continue', json=body(folder)).status_code == 409


def test_chat_budget_errors_and_interrupted_tutor_remain_stopped(tmp_path):
    folder = session(tmp_path, budget=1)
    viewer = client(folder, send=True, generate=lambda _, schema: schema(decision='reply', text='7?'))
    saved = latest(viewer.post('/api/continue', json=body(folder)))
    assert saved['status'] == 'awaiting-tutor' and saved['decisions_remaining'] == 0
    assert viewer.post('/api/continue', json=body(folder, 'reply', text='Yes.')).status_code == 409

    error_folder = tmp_path / 'error'
    chat.create(error_folder, query=QUERY)
    chat.show(error_folder)

    def fail(*_):
        raise RuntimeError('PRIVATE_PROVIDER_DIAGNOSTIC')

    failed = client(error_folder, send=True, generate=fail)
    response = failed.post('/api/continue', json=body(error_folder))
    assert latest(response)['status'] == 'error'
    assert response.json()['operation']['status'] == 'error'
    assert 'PRIVATE_PROVIDER_DIAGNOSTIC' not in response.text
    assert failed.post('/api/continue', json=body(error_folder)).status_code == 409

    waiting = tmp_path / 'waiting'
    initial = chat.create(waiting, query=QUERY)
    chat.step(waiting, binding=initial['binding'], generate=lambda _, schema: schema(decision='reply', text='7?'))
    failed_tutor = client(waiting, send=True, generate_tutor=fail,
                          generate=lambda *_: pytest.fail('Unexpected student dispatch'))
    assert failed_tutor.post('/api/continue', json=body(waiting, 'policy', text='One hint.')).status_code == 409
    restarted = client(waiting, send=True, generate=lambda *_: pytest.fail('Unexpected resend'))
    assert restarted.get('/api/workspace').json()['controls']['blocked_reason']
    for mode in ('advance', 'reply', 'policy'):
        submission = body(waiting, mode, **({} if mode == 'advance' else {'text': 'One hint.'}))
        assert restarted.post('/api/continue', json=submission).status_code == 409


def test_chat_missing_lock_and_notebook_reference_are_refused(tmp_path):
    folder = tmp_path / 'fresh'
    chat.create(folder, query=QUERY)
    before = files(folder)
    assert client(folder).get('/api/workspace').status_code == 409
    assert not (folder / '.lock').exists() and files(folder) == before
    with pytest.raises(ValueError, match='reference'):
        browser.create_app(folder, chat_mode=True, reference={})
    chat.show(folder)
    with store._locked(folder):
        assert client(folder).get('/api/workspace').status_code == 409


def test_cli_opens_explicit_chat_without_enabling_send(tmp_path, monkeypatch):
    import uvicorn

    folder = session(tmp_path)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **options: apps.append((app, options)))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(folder), '--chat', '--port', '8499'])
    browser.main()
    assert apps[0][1] == {'host': '127.0.0.1', 'port': 8499}
    shown = TestClient(apps[0][0], base_url='http://127.0.0.1').get('/api/workspace').json()
    assert shown['kind'] == 'chat' and shown['controls']['send_enabled'] is False
    assert shown['controls']['reference'] is None
    assert 'conversation' in shown['controls']['policy'] and 'check' not in shown['controls']['policy']
    monkeypatch.setattr(sys, 'argv', [*sys.argv, '--reference-file', 'does-not-exist.json'])
    with pytest.raises(SystemExit) as error:
        browser.main()
    assert error.value.code == 2 and len(apps) == 1
