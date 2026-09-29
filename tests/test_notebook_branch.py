"""One source-only choice survives reopening and cannot silently resend."""
import importlib
import json
from copy import deepcopy
from hashlib import sha256

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


@pytest.fixture
def execution_branch(tmp_path):
    """Authored results only; this fixture never executes a cell or calls a model."""
    from src.agents import notebook_branch as branch
    folder = tmp_path/'execution-branch'
    manifest = branch.create(folder, recovered=recovered(), instruction_cells=[0], work_cell=1)
    branch.step(folder, checkpoint_sha256=branch.store.digest(manifest), send=True,
                generate=lambda _, schema:schema(decision='revise-work', source='total = 0', text=''))
    image_id = 'sha256:'+'a'*64
    result = {'version':1, 'checkpoint_sha256':branch.store.digest(manifest),
              'decision_sha256':sha256((folder/'decision.json').read_bytes()).hexdigest(),
              'dataset':{'sha256':'b'*64, 'rows':3, 'columns':2,
                         'provenance':'archived-course-asset; historical bytes/version unverified'},
              'image_id':image_id, 'model_calls':0, 'checks':[]}
    for revision, source in enumerate(('total = 3', 'total = 0')):
        result['checks'].append({'revision':revision, 'source_sha256':sha256(source.encode()).hexdigest(),
            'status':'ok', 'execution':'completed', 'value':0 if revision else None, 'error':None,
            'output':'EXECUTION_ONLY <script>inert()</script>',
            'runtime':{'python':'3.11.14', 'libraries':{'pandas':'2.3.3', 'babypandas':'1.0.0', 'numpy':'2.3.3'},
                       'image_id':image_id}})
    path = tmp_path/'execution.json'
    path.write_text(json.dumps(result))
    return folder, path, result


def test_saved_execution_is_separate_bound_read_only_evidence(execution_branch):
    from fastapi.testclient import TestClient
    from src.agents import browser_workspace
    folder, path, result = execution_branch
    original = {name:(folder/name).read_bytes() for name in ('checkpoint.json', 'decision.json')}
    plain = TestClient(browser_workspace.create_app(notebook_branch=folder), base_url='http://127.0.0.1')
    plain_packet = plain.get('/api/workspace').json()
    app = browser_workspace.create_app(notebook_branch=folder, notebook_execution=path,
                                      notebook_execution_sha256=sha256(path.read_bytes()).hexdigest())
    browser = TestClient(app, base_url='http://127.0.0.1')
    response = browser.get('/api/workspace')
    assert response.status_code == 200
    packet = response.json()
    frames = packet['encounters'][0]['frames']
    assert len(frames) == 2
    assert [f['external_execution']['value'] for f in frames] == [None, 0]
    assert [f['external_execution']['revision'] for f in frames] == [0, 1]
    for frame, source_only in zip(frames, plain_packet['encounters'][0]['frames']):
        assert frame['feedback'] is None
        assert frame['dialogue'] == source_only['dialogue']
        assert 'EXECUTION_ONLY' not in json.dumps(frame['dialogue'])
        assert 'external_execution' not in source_only
        assert frame['external_execution']['dataset'] == result['dataset']
    assert 'after generation' in packet['encounters'][0]['saved_results_html']
    assert 'did not see' in packet['encounters'][0]['saved_results_html']
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    assert browser.post('/api/continue', json={}).status_code == 404
    assert browser.get('/api/workspace?execution=other').status_code == 400
    assert {name:(folder/name).read_bytes() for name in original} == original
    assert all(b'EXECUTION_ONLY' not in raw for raw in original.values())


@pytest.mark.parametrize('target', ['execution', 'decision', 'source', 'symlink', 'ancestor-symlink'])
def test_execution_and_branch_changes_redact_the_entire_projection(execution_branch, target):
    from fastapi.testclient import TestClient
    from src.agents import browser_workspace
    folder, path, _ = execution_branch
    if target == 'ancestor-symlink':
        directory = path.parent/'checks'
        directory.mkdir()
        path.rename(directory/path.name)
        path = directory/path.name
    browser = TestClient(browser_workspace.create_app(notebook_branch=folder, notebook_execution=path,
        notebook_execution_sha256=sha256(path.read_bytes()).hexdigest()), base_url='http://127.0.0.1')
    assert browser.get('/api/workspace').status_code == 200
    if target == 'ancestor-symlink':
        directory.rename(directory.with_name('moved'))
        directory.symlink_to(directory.with_name('moved'), target_is_directory=True)
    elif target == 'symlink':
        actual = path.with_name('actual.json')
        path.rename(actual)
        path.symlink_to(actual)
    elif target in ('execution', 'decision'):
        changed = path if target == 'execution' else folder/'decision.json'
        changed.write_bytes(changed.read_bytes()+b'\n')
    else:
        checkpoint = json.loads((folder/'checkpoint.json').read_text())
        checkpoint['task']['work']['source'] = 'PRIVATE_CHANGED_SOURCE'
        (folder/'checkpoint.json').write_text(json.dumps(checkpoint))
    response = browser.get('/api/workspace')
    assert response.status_code == 409
    assert not any(text in response.text for text in ('EXECUTION_ONLY', 'PRIVATE_CHANGED_SOURCE', str(folder), str(path)))
    assert set(response.json()) == {'detail'}


@pytest.mark.parametrize('change', [
    lambda r:r.update(checkpoint_sha256='0'*64),
    lambda r:r.update(decision_sha256='0'*64),
    lambda r:r['checks'][0].update(source_sha256='0'*64),
    lambda r:r['checks'][1].update(revision=0),
    lambda r:r['checks'][0].update(revision=True),
    lambda r:r['checks'][0].update(status='checked'),
    lambda r:r['checks'][0].update(execution='attempted'),
    lambda r:r['checks'][0].update(value=[]),
    lambda r:r['checks'][0].update(value=float('nan')),
    lambda r:r['checks'][0].update(error={'type':'Error', 'message':'unexpected'}),
    lambda r:r['checks'][0].update(runtime=None),
    lambda r:r['checks'][0]['runtime'].update(image_id='sha256:'+'0'*64),
    lambda r:r['checks'][0].update(output='x'*8193),
    lambda r:r['dataset'].update(rows=0),
    lambda r:r['dataset'].update(path='/must/not/be/read'),
    lambda r:r.update(model_calls=1),
])
def test_execution_rejects_unbound_or_malformed_results(execution_branch, change):
    from src.agents import browser_workspace
    folder, path, result = execution_branch
    change(result)
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError):
        browser_workspace.create_app(notebook_branch=folder, notebook_execution=path,
                                     notebook_execution_sha256=sha256(path.read_bytes()).hexdigest())


@pytest.mark.parametrize(('status', 'execution'), [('cell-error', 'completed'), ('setup-error', 'not-started'),
    ('execution-limit', 'attempted'), ('environment-error', 'not-started'), ('environment-error', 'attempted')])
def test_saved_execution_errors_are_preserved_without_grading(execution_branch, status, execution):
    from fastapi.testclient import TestClient
    from src.agents import browser_workspace
    folder, path, result = execution_branch
    result['checks'][0].update(status=status, execution=execution, value=None,
                              error={'type':'AuthoredError', 'message':'<script>inert</script>'})
    if status != 'cell-error':
        result['checks'][0]['runtime'] = None
    path.write_text(json.dumps(result))
    browser = TestClient(browser_workspace.create_app(notebook_branch=folder, notebook_execution=path,
        notebook_execution_sha256=sha256(path.read_bytes()).hexdigest()), base_url='http://127.0.0.1')
    frame = browser.get('/api/workspace').json()['encounters'][0]['frames'][0]
    assert frame['external_execution']['status'] == status and frame['feedback'] is None
    assert frame['external_execution']['error'] == result['checks'][0]['error']
    assert 'success' not in frame['external_execution'] and 'grade' not in frame['external_execution']


def test_execution_flags_size_and_completed_revision_required(execution_branch):
    from src.agents import browser_workspace, notebook_branch as branch
    folder, path, _ = execution_branch
    pin = sha256(path.read_bytes()).hexdigest()
    for options in ({'notebook_execution':path}, {'notebook_execution_sha256':pin},
                    {'notebook_execution':path, 'notebook_execution_sha256':pin, 'notebook_branch':None}):
        with pytest.raises(ValueError):
            browser_workspace.create_app(**({'notebook_branch':folder}|options))
    for status in ('pending', 'error', 'reply', 'no-reply', 'missing'):
        manifest, receipt = branch.load(folder)
        if status == 'missing':
            (folder/'decision.json').unlink()
        elif status in ('pending', 'error'):
            receipt = {'status':status, 'request':receipt['request']}
            (folder/'decision.json').write_text(json.dumps(receipt))
        else:
            response = branch.action.Action(decision=status, text='question' if status == 'reply' else '', source=None)
            receipt.update(status='complete', response=response.model_dump(), applied=branch.action.apply_action(manifest['task'], response))
            (folder/'decision.json').write_text(json.dumps(receipt))
        with pytest.raises(ValueError, match='completed source revision'):
            browser_workspace.create_app(notebook_branch=folder, notebook_execution=path, notebook_execution_sha256=pin)
    path.write_bytes(b' '*(1024*1024+1))
    with pytest.raises(ValueError, match='size'):
        browser_workspace.create_app(notebook_branch=folder, notebook_execution=path,
                                     notebook_execution_sha256=sha256(path.read_bytes()).hexdigest())
