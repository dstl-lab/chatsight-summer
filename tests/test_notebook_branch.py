"""One source-only choice survives reopening and cannot silently resend."""
import importlib
import json
from copy import deepcopy

import pytest


def recovered():
    return {'notebook':{'recorded_at':'2026-01-01T00:00:00Z', 'cells':[
        {'index':0, 'cell_type':'markdown', 'source':'# Add both values'},
        {'index':1, 'cell_type':'code', 'source':'total = 3'}]},
        'exchange':[{'role':'student', 'text':'check?'}, {'role':'tutor', 'text':'Include 4.'}],
        'later_evidence':'FUTURE_SENTINEL'}


def test_one_action_branch_replays_without_execution_and_never_resends(tmp_path):
    branch = importlib.import_module('src.agents.notebook_branch')
    original = recovered(); before = deepcopy(original)
    for index, response in enumerate([
        dict(decision='revise-work', text='', source='total = 3 + 4'),
        dict(decision='reply', text='which one', source=None),
        dict(decision='no-reply', text='', source=None)]):
        folder = tmp_path / str(index)
        manifest = branch.create(folder, recovered=original, instruction_cells=[0], work_cell=1)
        pin = branch.store.digest(manifest)
        assert 'FUTURE_SENTINEL' not in manifest['prompt']
        calls = []
        def generate(prompt, schema):
            calls.append(prompt)
            assert json.loads((folder/'decision.json').read_text())['status'] == 'pending'
            return schema(**response)
        with pytest.raises(ValueError, match='send'):
            branch.step(folder, checkpoint_sha256=pin, generate=generate)
        with pytest.raises(ValueError, match='changed'):
            branch.step(folder, checkpoint_sha256='0'*64, send=True, generate=generate)
        assert not (folder/'decision.json').exists()
        branch.step(folder, checkpoint_sha256=pin, send=True, generate=generate)
        saved, receipt = branch.load(folder)
        assert saved == manifest and len(calls) == 1
        assert receipt['response'] == response
        assert receipt['applied']['execution'] == 'not-run' and receipt['applied']['observation'] is None
        assert receipt['applied']['message'] == (response['text'] or None)
        assert receipt['applied']['work']['source'] == (response['source'] or 'total = 3')
        with pytest.raises(ValueError, match='already'):
            branch.step(folder, checkpoint_sha256=pin, send=True, generate=generate)
        receipt['applied']['work']['source'] = 'altered'
        (folder/'decision.json').write_text(json.dumps(receipt))
        with pytest.raises(ValueError, match='reproduce'):
            branch.load(folder)
    assert original == before
    folder = tmp_path/'interrupted'
    manifest = branch.create(folder, recovered=original, instruction_cells=[0], work_cell=1)
    def interrupt(*_):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        branch.step(folder, checkpoint_sha256=branch.store.digest(manifest), send=True, generate=interrupt)
    assert branch.load(folder)[1]['status'] == 'pending'
    with pytest.raises(ValueError, match='already'):
        branch.step(folder, checkpoint_sha256=branch.store.digest(manifest), send=True, generate=interrupt)


def test_failed_branch_records_error_and_refuses_symlinks(tmp_path):
    branch = importlib.import_module('src.agents.notebook_branch')
    folder = tmp_path/'failed'
    manifest = branch.create(folder, recovered=recovered(), instruction_cells=[0], work_cell=1)
    def fail(*_):
        raise RuntimeError('private provider error')
    receipt = branch.step(folder, checkpoint_sha256=branch.store.digest(manifest), send=True, generate=fail)
    assert receipt['status'] == 'error' and branch.load(folder)[1] == receipt
    link = tmp_path/'link'; link.symlink_to(folder, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        branch.load(link)


def test_source_branch_browser_shows_verified_work_and_chat_without_sending(tmp_path):
    from fastapi.testclient import TestClient
    from src.agents import browser_workspace, notebook_branch as branch
    folder = tmp_path/'browser'
    initial = recovered()
    initial['notebook']['cells'][0]['source'] += '\n<img src=x onerror=bad()>'
    manifest = branch.create(folder, recovered=initial, instruction_cells=[0], work_cell=1)
    app = browser_workspace.create_app(notebook_branch=folder)
    browser = TestClient(app, base_url='http://127.0.0.1')
    packet = browser.get('/api/workspace').json()
    assert packet['kind'] == 'notebook' and packet['source_only'] is True
    assert len(packet['encounters'][0]['frames']) == 1
    assert '<h1>' in packet['encounters'][0]['task_html'] and '<img' not in packet['encounters'][0]['task_html']
    branch.step(folder, checkpoint_sha256=branch.store.digest(manifest), send=True,
                generate=lambda _, schema:schema(decision='revise-work', source='total = 7', text='this?'))
    packet = browser.get('/api/workspace').json()
    before, after = packet['encounters'][0]['frames']
    assert before['work']['source'] == 'total = 3' and after['work']['source'] == 'total = 7'
    assert after['dialogue'][-1] == {'role':'student', 'text':'this?', 'origin':'generated'}
    assert after['feedback'] is None and after['decisions_remaining'] == 0
    assert '+total = 7' in after['changes']['unified_diff']
    assert packet['controls']['send_enabled'] is False
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    assert browser.get('/api/workspace?scenario=other').status_code == 400
    assert browser.post('/api/continue', json={}).status_code == 404
    for extra in ({'send':True}, {'folder':tmp_path}, {'chat_mode':True}, {'recorded_replay':tmp_path, 'recorded_sha256':'0'*64}):
        with pytest.raises(ValueError, match='read-only'):
            browser_workspace.create_app(notebook_branch=folder, **extra)
    manifest['task']['work']['source'] = 'changed'
    (folder/'checkpoint.json').write_text(json.dumps(manifest))
    response = browser.get('/api/workspace')
    assert response.status_code == 409 and str(folder) not in response.text
