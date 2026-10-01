"""The local policy must drive the saved reply, never fall back to a provider."""
import importlib.util
import json

import pytest
from fastapi.testclient import TestClient

from src.agents import browser_workspace as browser, chat_student as chat
from tests.test_chat_student import files


def adapter():
    assert importlib.util.find_spec('src.agents.authored_policy_chat'), 'Authored policy adapter is missing'
    from src.agents import authored_policy_chat
    return authored_policy_chat


def test_local_step_binds_actual_error_selection_and_saved_chat(tmp_path):
    policy = adapter()
    folder = tmp_path / 'demo'
    policy.create(folder)
    before = files(folder)
    with pytest.raises(FileExistsError):
        policy.create(folder)
    assert files(folder) == before
    app = browser.create_app(folder, chat_mode=True, authored_policy=True, send=True)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        packet = client.get('/api/workspace').json()
        encounter = packet['encounters'][0]
        fixture = encounter['authored_policy']
        assert fixture['checkpoint']['returncode'] == 1
        assert fixture['checkpoint']['stderr'].endswith('IndexError: list index out of range\n')
        assert fixture['preview']['query']['context']['feedback'] == 'runtime-error'
        assert encounter['frames'][0]['behavior_policy'] is None
        body = {'mode': 'advance', 'binding': encounter['frames'][0]['binding']}
        response = client.post('/api/continue', json=body)
        assert response.status_code == 200, response.text
        frame = response.json()['encounters'][0]['frames'][-1]
        assert frame['pending_message'] == 'IndexError: list index out of range\ncan you check this error?'
        assert frame['behavior_policy']['selection']['behavior']['material'] == ['diagnostic']
        assert frame['behavior_policy']['rendering']['text'] == frame['pending_message']
        assert frame['status'] == 'awaiting-tutor' and frame['decisions_remaining'] == 0
        assert client.post('/api/continue', json=body).status_code == 409
        saved = files(folder)
        assert client.get('/api/workspace').json() == response.json()
        assert files(folder) == saved
    assert policy.verify(folder)['result']['rendering']['text'] == frame['pending_message']
    # A normal live launch must not send this authored session to its default provider.
    with TestClient(browser.create_app(folder, chat_mode=True, send=True), base_url='http://127.0.0.1') as client:
        assert 'authored' in client.get('/api/workspace').json()['controls']['blocked_reason'].lower()
    receipt = folder / 'authored-policy-reply.json'
    receipt.unlink()
    assert TestClient(app, base_url='http://127.0.0.1').get('/api/workspace').status_code == 409


@pytest.mark.parametrize('problem', ['missing', 'unsupported'])
def test_unrenderable_policy_does_not_consume_a_step(tmp_path, problem):
    policy = adapter()
    folder = tmp_path / problem
    policy.create(folder)
    path = folder / 'authored-policy.json'
    config = json.loads(path.read_text())
    if problem == 'missing':
        config['request']['query']['diagnostic'] = None
    else:
        for example in config['request']['examples']:
            example['behavior']['assistance'] = ['explanation']
    path.write_text(json.dumps(config))
    before = files(folder)
    with TestClient(browser.create_app(folder, chat_mode=True, authored_policy=True, send=True), base_url='http://127.0.0.1') as client:
        response = client.get('/api/workspace')
        assert response.status_code == 200
        packet = response.json()
        assert packet['controls']['blocked_reason']
        assert client.post('/api/continue', json={'mode':'advance', 'binding': packet['encounters'][0]['frames'][0]['binding']}).status_code == 409
    assert not list(folder.glob('step-*.json')) and files(folder) == before
    assert chat.show(folder)['state']['status'] == 'ready'


def test_foreign_prefix_and_tampered_receipt_are_rejected(tmp_path):
    policy = adapter()
    folder = tmp_path / 'demo'
    policy.create(folder)
    callback = policy.make_reply(folder)
    with pytest.raises(ValueError, match='prefix'):
        callback([{'role':'student', 'text':'different'}])
    assert not (folder / 'authored-policy-reply.json').exists()
    from src.agents import chat_workspace
    chat_workspace.advance(folder, binding=chat.show(folder)['binding'], send=True, generate_reply=callback)
    path = folder / 'authored-policy-reply.json'
    receipt = json.loads(path.read_text())
    receipt['policy']['result']['selection']['behavior']['material'] = []
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        policy.verify(folder)
