"""Existing notebook A/B evidence is readable together without new requests."""
from copy import deepcopy
import fcntl
import json
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, notebook_student as student, notebook_teaching_pair as pair
from tests.test_notebook_example import files
from tests.test_notebook_session import ACTIVITY, TASK, observation
from tests.test_tutor_context import choose


REPLIES = ['Try **one distinct-value operation**. <script>literal</script>',
           'Use `len(swatches.get("shade").unique())`.']


def setup(tmp_path):
    task = deepcopy(TASK)
    task['captured_at'] = 'PRIVATE_CAPTURE'
    task['dialogue'] = [{'role':'student', 'text':'what comes first'},
                        {'role':'tutor', 'text':'Read **the task**.'}, *task['dialogue']]
    root = pair.create(tmp_path / 'pair', task=task, activity=ACTIVITY, tutor_replies=REPLIES,
                       evaluation={'expected':2}, max_decisions=4)
    return root, task


def client(root, **options):
    return TestClient(browser.create_app(teaching_comparison=root, **options), base_url='http://127.0.0.1')


@pytest.mark.parametrize('progressed', [False, True])
def test_shared_start_and_distinct_saved_outcomes_are_read_only(tmp_path, monkeypatch, progressed):
    root, task = setup(tmp_path)
    if progressed:
        choose(root / 'a', 'revise-work', source='n_shades = 2')
        def checked(work, *, evaluation, **kwargs):
            result = observation(work, status='checked', **kwargs)
            result['binding'] = student.notebook_runtime._binding(work, kwargs['branch_id'],
                student.notebook_runtime.Activity.model_validate(kwargs['activity']), kwargs['timeout'], evaluation)
            return result
        choose(root / 'a', 'request-check', check=checked)
        choose(root / 'a', 'no-reply')
        choose(root / 'b', 'reply', text='do i count the result?')
    def forbidden(*args, **kwargs):
        pytest.fail('Viewing dispatched a model or check')
    monkeypatch.setattr(student.llm, 'make_generate', forbidden)
    monkeypatch.setattr(student.notebook_runtime, 'check_work', forbidden)
    before = files(tmp_path)
    viewer = client(root, generate=forbidden, generate_tutor=forbidden, check=forbidden)
    catalog = viewer.get('/api/scenarios').json()
    assert catalog['comparison_available'] and catalog['teaching_comparison_available']
    assert catalog['replay_available'] is False and catalog['scenarios'] == []
    response = viewer.get('/api/comparison')
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['kind'] == 'saved-notebook-teaching-comparison' and len(data['cases']) == 1
    case = data['cases'][0]
    assert case['task'] == task['task'] and case['initial_work'] == task['work']
    assert case['prefix']['context'] == []
    assert [turn['text'] for turn in case['prefix']['turns']] == [turn['text'] for turn in task['dialogue'][:-1]]
    assert case['prefix']['turns'][1]['display_html'] == '<p>Read <strong>the task</strong>.</p>'
    assert [arm['id'] for arm in case['conditions']] == ['a', 'b']
    assert [arm['tutor_reply'] for arm in case['conditions']] == REPLIES
    assert '<script>' not in case['conditions'][0]['tutor_html']
    a, b = [arm['encounter'] for arm in case['conditions']]
    assert [frame['status'] for frame in a['frames']] == (
        ['active', 'active', 'active', 'no-reply'] if progressed else ['active'])
    assert b['frames'][-1]['status'] == ('awaiting-tutor' if progressed else 'active')
    assert a['frames'][-1]['decisions_remaining'] == (1 if progressed else 4)
    if progressed:
        assert a['frames'][-1]['feedback']['success'] is True
        assert a['frames'][-1]['work']['source'] == 'n_shades = 2'
        assert b['frames'][-1]['pending_message'] == 'do i count the result?'
    for secret in ('PRIVATE_CAPTURE', str(tmp_path), '"evaluation"', 'image_id', '"model_calls"', '"prepared"'):
        assert secret not in response.text
    assert viewer.get('/api/comparison').json() == data
    assert viewer.get('/api/workspace').status_code == 404
    assert viewer.post('/api/comparison', json={}).status_code == 405
    assert viewer.post('/api/comparison/run', json={}).status_code == 404
    assert viewer.get('/api/comparison?folder=elsewhere').status_code == 400
    assert viewer.get('/api/comparison', headers={'Origin':'http://evil.example'}).status_code == 403
    assert files(tmp_path) == before


@pytest.mark.parametrize('changed', ['receipt', 'child', 'reply', 'operation', 'swap', 'missing-lock', 'symlink'])
def test_changed_or_unavailable_saved_evidence_is_hidden(tmp_path, changed):
    root, _ = setup(tmp_path)
    if changed == 'operation':
        choose(root / 'a', 'reply', text='saved question')
    viewer = client(root)
    assert viewer.get('/api/comparison').status_code == 200
    if changed == 'receipt':
        path = root / 'comparison.json'
        path.write_bytes(path.read_bytes() + b' ')
    elif changed in ('child', 'reply'):
        path = root / 'a/session.json'
        manifest = student._read(path)
        if changed == 'child':
            manifest['initial']['work']['source'] = 'tampered'
        else:
            manifest['initial']['dialogue'][-1]['text'] = 'Changed supplied reply'
        path.write_text(json.dumps(manifest))
    elif changed == 'operation':
        path = root / 'a/step-0001.json'
        record = student._read(path)
        record['result']['state']['message'] = 'tampered question'
        path.write_text(json.dumps(record))
    elif changed == 'swap':
        (root / 'a').rename(root / 'temporary')
        (root / 'b').rename(root / 'a')
        (root / 'temporary').rename(root / 'b')
    elif changed == 'missing-lock':
        (root / 'a/.lock').unlink()
    else:
        path = root / 'a/session.json'
        path.rename(tmp_path / 'outside.json')
        path.symlink_to(tmp_path / 'outside.json')
    before = files(tmp_path)
    response = viewer.get('/api/comparison')
    assert response.status_code == 409 and 'cases' not in response.json()
    assert str(tmp_path) not in response.text and files(tmp_path) == before


@pytest.mark.parametrize('changed', ['work', 'evaluation', 'model', 'budget', 'condition', 'common', 'branch', 'linked', 'reply-hash'])
def test_self_consistent_child_hash_cannot_hide_unequal_inputs_or_wrong_provenance(tmp_path, changed):
    root, _ = setup(tmp_path)
    path = root / 'b/session.json'
    manifest = student._read(path)
    receipt = student._read(root / 'comparison.json')
    if changed == 'work':
        manifest['initial']['work']['source'] = 'different starting work'
    elif changed == 'evaluation':
        manifest['initial']['evaluation']['expected'] = 999
    elif changed == 'model':
        manifest['model'] = 'different-model'
    elif changed == 'budget':
        manifest['max_decisions'] = 5
    elif changed == 'condition':
        manifest['provenance']['teaching_pair']['condition'] = 'a'
    elif changed == 'common':
        manifest['provenance']['teaching_pair']['common_input_sha256'] = '0' * 64
    elif changed == 'branch':
        manifest['initial']['branch_id'] = student._read(root / 'a/session.json')['initial']['branch_id']
    elif changed == 'linked':
        manifest['provenance']['previous_encounter'] = {'path':'PRIVATE_OUTSIDE'}
    else:
        receipt['sessions']['b']['tutor_reply_sha256'] = '0' * 64
    path.write_text(json.dumps(manifest))
    receipt['sessions']['b']['manifest_sha256'] = student.digest(manifest)
    (root / 'comparison.json').write_text(json.dumps(receipt))
    before = files(tmp_path)
    response = client(root).get('/api/comparison')
    assert response.status_code == 409 and 'PRIVATE_OUTSIDE' not in response.text
    assert files(tmp_path) == before


def test_companion_replay_busy_lock_and_cli_keep_configuration_explicit(tmp_path, monkeypatch):
    import uvicorn
    root, _ = setup(tmp_path)
    legacy = TestClient(browser.create_app(root / 'a'), base_url='http://127.0.0.1')
    assert legacy.get('/api/scenarios').json()['workspace_id'] == student.digest(
        [str((root / 'a').resolve()), None, None, None])
    viewer = client(root, folder=root / 'a')
    assert viewer.get('/api/scenarios').json()['replay_available'] is True
    before = files(tmp_path)
    with (root / 'a/.lock').open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert viewer.get('/api/comparison').status_code == 409
    assert viewer.get('/api/workspace').status_code == 200 and files(tmp_path) == before
    for option in ('comparison', 'policy_comparison', 'policy_workspace', 'fidelity_comparison'):
        with pytest.raises(ValueError, match='one comparison'):
            browser.create_app(teaching_comparison=root, **{option:root})
    for options in ({'send':True}, {'chat_mode':True}, {'policy':'Tutor instructions'}):
        with pytest.raises(ValueError, match='session folder'):
            browser.create_app(teaching_comparison=root, **options)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **kwargs: apps.append(app))
    command = ['browser_workspace', '--teaching-comparison', str(root)]
    monkeypatch.setattr(sys, 'argv', command)
    browser.main()
    assert TestClient(apps[0], base_url='http://127.0.0.1').get('/api/comparison').status_code == 200
    monkeypatch.setattr(sys, 'argv', command + ['--send'])
    with pytest.raises(SystemExit) as error:
        browser.main()
    assert error.value.code == 2 and len(apps) == 1
