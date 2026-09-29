"""Authored saved draws only: this preview cannot sample or execute notebook code."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from threading import Event

import pytest
from fastapi.testclient import TestClient

from src.agents import notebook_branch as branch
from tests.test_notebook_branch import execution_branch, reaction_branch, reaction_options


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('saved_draws', ROOT/'experiments/2026-09-29-next-action-monte-carlo/run.py')
SAMPLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SAMPLER)


def save(path, value):
    path.write_text(json.dumps(value))
    return sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def saved_batch(reaction_branch, tmp_path):
    # Make the original saved reaction visibly different from every sampled reply.
    bundle = reaction_branch
    original = branch.action.Action(decision='reply', text='ORIGINAL_REACTION', source=None)
    bundle['receipt'].update(response=original.model_dump(),
        applied=branch.action.apply_action(bundle['prepared']['task'], original))
    options = reaction_options(bundle)
    batch = tmp_path/'batch'
    prepared = bundle['path'].with_name('reaction-preparation.json')
    SAMPLER.prepare(prepared, SAMPLER.sha(prepared), batch)
    plan = json.loads((batch/'plan.json').read_text())
    plan['attempts'] = 4
    pin = save(batch/'plan.json', plan)
    save(batch/'started.json', {'plan_sha256':pin, 'started_at':'2026-09-29T01:00:00+00:00'})
    choices = [dict(decision='no-reply', text='', source=None),
               dict(decision='reply', text='SAMPLED_REPLY', source=None),
               dict(decision='revise-work', text='', source='total = 7'), None]
    for index, choice in enumerate(choices, 1):
        record = dict(index=index, plan_sha256=pin, prompt_sha256=plan['prompt_sha256'],
            started_at='2026-09-29T01:00:01+00:00', finished_at='2026-09-29T01:00:02+00:00',
            status='complete' if choice else 'error')
        if choice:
            record.update(response=choice, raw_response={'candidates':[{
                'finish_reason':'STOP', 'content':{'parts':[{'text':json.dumps(choice)}]}}]})
        else:
            record['raw_response'] = {'candidates':[{'finish_reason':'MAX_TOKENS'}]}
        save(batch/f'draw-{index:02d}.json', record)
    report_pin = save(batch/'report.json', SAMPLER.analyse(batch))
    return bundle, {**options, 'batch':batch, 'report_sha256':report_pin}


def test_saved_samples_project_same_input_without_mutation_or_post(saved_batch):
    from apps import next_actions_preview as preview
    bundle, options = saved_batch
    paths = [*bundle['folder'].glob('*.json'), *options['batch'].glob('*.json'),
             bundle['execution'], bundle['path'], bundle['path'].with_name('reaction-preparation.json')]
    before = {p:p.read_bytes() for p in paths}
    options['notebook_reaction'] = bundle['folder']/'..'/bundle['path'].name
    app = preview.create_app(**options)
    browser = TestClient(app, base_url='http://127.0.0.1')
    packet = browser.get('/api/next-actions').json()
    assert (packet['attempts'], packet['valid'], packet['failed']) == (4, 3, 1)
    assert {c['decision']:c['count'] for c in packet['categories']} == {
        'reply':1, 'no-reply':1, 'revise-work':1}
    assert all(c['proportion'] == pytest.approx(1/3) for c in packet['categories'])
    quiet, reply, edit = [s['frame'] for s in packet['samples']]
    baseline = browser.get('/api/workspace').json()['encounters'][0]['frames'][1]
    assert quiet['dialogue'] == baseline['dialogue'] == edit['dialogue']
    assert reply['dialogue'] == baseline['dialogue'] + [
        {'role':'student', 'origin':'generated', 'text':'SAMPLED_REPLY'}]
    assert 'ORIGINAL_REACTION' not in json.dumps(packet)
    assert edit['work'] == {'cell_index':1, 'revision':2, 'source':'total = 7'}
    assert [f['status'] for f in (quiet, reply, edit)] == ['no-reply', 'awaiting-tutor', 'active']
    for frame in (quiet, reply, edit):
        assert frame['feedback'] is None and 'external_execution' not in frame
        assert frame['reaction']['observation']['revision'] == 1
        assert frame['reaction']['action'] == frame['actions'][0]
        assert frame['changes']['baseline_revision'] == 1
    assert '+total = 7' in edit['changes']['unified_diff']
    assert 'prompt' not in packet and 'raw_response' not in packet
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    assert browser.post('/api/next-actions', json={}).status_code == 405
    assert browser.post('/api/continue', json={}).status_code == 404
    assert browser.get('/api/next-actions?sample=other').status_code == 400
    page = browser.get('/')
    assert '/next-actions.js' in page.text and '/next-actions.css' in page.text
    assert "style-src 'self' 'unsafe-inline'" in page.headers['content-security-policy']
    assert '/next-actions.js' not in browser.get('/student-workspace.html').text
    assert {p:p.read_bytes() for p in paths} == before


@pytest.mark.parametrize('target', ['draw', 'source', 'report'])
def test_changed_evidence_redacts_samples(saved_batch, target):
    from apps import next_actions_preview as preview
    bundle, options = saved_batch
    browser = TestClient(preview.create_app(**options), base_url='http://127.0.0.1')
    path = {'draw':options['batch']/'draw-01.json', 'source':bundle['folder']/'checkpoint.json',
            'report':options['batch']/'report.json'}[target]
    path.write_text(path.read_text()+' ')
    if target == 'source':
        value = json.loads(path.read_text())
        value['task']['work']['source'] = 'ALTERED_SOURCE'
        save(path, value)
    response = browser.get('/api/next-actions')
    assert response.status_code == 409
    assert str(path) not in response.text and 'SAMPLED_REPLY' not in response.text


def test_rejects_rebound_input_even_when_copy_has_identical_bytes(saved_batch):
    from apps import next_actions_preview as preview
    bundle, options = saved_batch
    batch = options['batch']
    alternate = batch/'alternate-input.json'
    alternate.write_bytes(bundle['path'].with_name('reaction-preparation.json').read_bytes())
    plan = json.loads((batch/'plan.json').read_text())
    plan['input_path'] = str(alternate)
    pin = save(batch/'plan.json', plan)
    started = json.loads((batch/'started.json').read_text()); started['plan_sha256'] = pin
    save(batch/'started.json', started)
    for path in batch.glob('draw-*.json'):
        record = json.loads(path.read_text()); record['plan_sha256'] = pin
        save(path, record)
    options['report_sha256'] = save(batch/'report.json', SAMPLER.analyse(batch))
    with pytest.raises(ValueError, match='input'):
        preview.create_app(**options)


def test_rejects_raw_action_disagreement_even_with_rehashed_report(saved_batch):
    from apps import next_actions_preview as preview
    _, options = saved_batch
    batch = options['batch']
    path = batch/'draw-01.json'
    record = json.loads(path.read_text())
    record['raw_response']['candidates'][0]['content']['parts'][0]['text'] = json.dumps(
        dict(decision='reply', text='UNACCEPTED', source=None))
    report = json.loads((batch/'report.json').read_text())
    report['draw_sha256'][path.name] = save(path, record)
    options['report_sha256'] = save(batch/'report.json', report)
    with pytest.raises(ValueError, match='provider response'):
        preview.create_app(**options)


def test_rejects_rehashed_false_counts(saved_batch):
    from apps import next_actions_preview as preview
    _, options = saved_batch
    path = options['batch']/'report.json'
    report = json.loads(path.read_text())
    report['actions']['reply']['count'] = 2
    options['report_sha256'] = save(path, report)
    with pytest.raises(ValueError, match='does not reproduce'):
        preview.create_app(**options)


def test_live_batch_api_guards_start_and_preserves_partial_results(saved_batch, tmp_path):
    from apps import next_actions_preview as preview
    entered, release = Event(), Event()
    def generate(plan, prompt):
        entered.set()
        assert release.wait(5)
        return {'candidates':[{'finish_reason':'STOP', 'content':{'parts':[{'text':json.dumps(
            {'decision':'reply','text':'NEW_AUTHORED_REPLY','source':None})}]}}]}
    _, options = saved_batch
    app = preview.create_app(**options, sampling_dir=tmp_path/'jobs', generate=generate)
    try:
        with TestClient(app, base_url='http://127.0.0.1') as client:
            initial = client.get('/api/next-actions').json()
            assert initial['enabled'] and initial['selected_batch'] == 'saved'
            assert len(initial['batches']) == 1
            body = {'request_id':'5a3a05e5-c9d8-4aa4-bc59-2892f683f8dc', 'runs':3,
                    'input_sha256':initial['binding']['input_sha256']}
            headers = {'X-Workspace-Token':initial['csrf_token']}
            assert client.post('/api/next-actions/batches', json=body).status_code == 403
            assert client.post('/api/next-actions/batches', json=body,
                headers={**headers,'Origin':'https://unrelated.example'}).status_code == 403
            assert client.post('/api/next-actions/batches', json={**body,'runs':0}, headers=headers).status_code == 422
            assert client.post('/api/next-actions/batches', json={**body,'input_sha256':'0'*64}, headers=headers).status_code == 409
            response = client.post('/api/next-actions/batches', json=body, headers=headers)
            assert response.status_code == 200
            active = response.json()
            assert active['selected_batch'] == body['request_id']
            assert active['active_batch']['requested'] == 3 and active['valid'] == 0
            assert entered.wait(2)
            again = client.post('/api/next-actions/batches', json=body, headers=headers).json()
            assert again['selected_batch'] == active['selected_batch']
            assert len(again['batches']) == 2
            cancelled = client.post(f'/api/next-actions/batches/{body["request_id"]}/cancel', headers=headers)
            assert cancelled.status_code == 200 and cancelled.json()['active_batch']['cancel_requested']
            release.set()
        # Lifespan waits for the in-flight receipt before releasing the folder.
        with TestClient(preview.create_app(**options, sampling_dir=tmp_path/'jobs', generate=generate),
                        base_url='http://127.0.0.1') as client:
            saved = client.get('/api/next-actions?batch='+body['request_id']).json()
            assert (saved['valid'],saved['failed']) == (1,0)
            assert saved['active_batch'] is None
            assert saved['samples'][0]['frame']['dialogue'][-1]['text'] == 'NEW_AUTHORED_REPLY'
            assert saved['samples'][0]['frame']['reaction']['observation']['revision'] == 1
            assert len(client.get('/api/next-actions').json()['batches']) == 2
            assert client.get('/api/next-actions?batch=../../input.json').status_code == 404
    finally:
        release.set()
