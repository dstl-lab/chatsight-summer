"""Authored source-only comparison: no inherited fix, output, or original tutor."""
from copy import deepcopy
from hashlib import sha256
import json

from fastapi.testclient import TestClient
import pytest

from apps.policy_sampling_preview import project, student_loop
from src.agents.notebook_branch import action
from tests.test_notebook_branch import recovered


def test_saved_execution_is_shared_by_source_but_reaction_belongs_to_one_sample():
    from src.agents.notebook_student import digest
    shared = action.initial_task(recovered(), instruction_cells=[0], work_cell=1)
    shared['dialogue'] = shared['dialogue'][:1]
    task = deepcopy(shared)
    task['dialogue'].append({'role':'tutor', 'text':'AUTHORED_TUTOR'})
    choice = {'decision':'revise-work', 'text':'First edit', 'source':'total = 7'}
    report = dict(model='authored', plan_sha256='a'*64, shared_task=shared, scope='Authored',
        conditions={'direct':dict(label='Direct', policy='Authored', task=task,
            records=[{'index':index, 'status':'complete', 'response':choice} for index in (1,2)],
            valid=2, failed=0, requested=30, status='complete', categories=[])})
    reaction_task = deepcopy(task)
    reaction_task['work'] = {'cell_index':1, 'source':'total = 7', 'revision':1}
    response = {'decision':'revise-work', 'text':'After feedback', 'source':'total = 8'}
    check = dict(revision=1, source_sha256=sha256(b'total = 7').hexdigest(), status='ok',
        execution='completed', value=7, error=None, output='', runtime={'python':'3.12',
        'libraries':{'authored':'1'}, 'image_id':'sha256:'+'b'*64})
    attachment = dict(comparison_sha256=digest(report), dataset={'provenance':'authored'},
        image_id='sha256:'+'b'*64, checks={check['source_sha256']:check},
        reactions={'direct':dict(sample_index=1, status='complete', model='authored', task=reaction_task,
            response=response, applied=action.apply_action(reaction_task, action.Action.model_validate(response)),
            started_at='2026-09-29T00:00:00+00:00', finished_at='2026-09-29T00:00:01+00:00')})
    before = deepcopy((report, attachment))
    packet, sampling = project(report, attachment)
    assert (report, attachment) == before
    assert all('external_execution' not in frame for frame in packet['encounters'][0]['frames'])
    first, duplicate = sampling['conditions'][0]['samples']
    assert first['frame']['external_execution'] == duplicate['frame']['external_execution']
    assert first['frame']['external_execution']['value'] == 7
    assert 'reaction_frame' not in duplicate
    reacted = first['reaction_frame']
    assert reacted['work']['source'] == 'total = 8' and reacted['work']['revision'] == 2
    assert 'external_execution' not in reacted
    assert [turn['text'] for turn in reacted['dialogue']] == ['check?', 'AUTHORED_TUTOR', 'First edit', 'After feedback']
    assert reacted['reaction']['observed_revision'] == 1
    assert reacted['reaction']['observation']['value'] == 7
    assert '+total = 8' in reacted['changes']['unified_diff']
    projection = deepcopy((packet, sampling))
    loop = student_loop(packet, sampling, 'direct')
    assert (packet, sampling) == projection
    frames = loop['encounters'][0]['frames']
    assert [f['loop_stage'] for f in frames] == ['captured', 'tutor', 'edit', 'execution', 'reaction']
    assert [f['work']['revision'] for f in frames] == [0, 0, 1, 1, 2]
    assert all('external_execution' not in f and 'reaction' not in f for f in frames[:3])
    assert [len(f['dialogue']) for f in frames] == [1, 2, 3, 3, 4]
    assert frames[2]['actions'] == [choice] and frames[3]['actions'] == []
    assert frames[3]['changes'] == {'baseline_revision': 1, 'baseline_kind': 'previous-saved-step', 'unified_diff': ''}
    assert frames[3]['external_execution']['value'] == 7
    assert 'external_execution' not in frames[4] and frames[4]['reaction']['observed_revision'] == 1
    assert not loop['controls']['send_enabled']
    with pytest.raises(ValueError, match='condition'):
        student_loop(packet, sampling, 'unknown')
    attachment['reactions']['direct'] = {'sample_index':1, 'status':'error', 'model':'authored'}
    _, failed = project(report, attachment)
    assert failed['conditions'][0]['reaction']['status'] == 'error'
    assert all('reaction_frame' not in sample for sample in failed['conditions'][0]['samples'])
    with pytest.raises(ValueError, match='predetermined'):
        student_loop(packet, failed, 'direct')
    attachment['checks'] = {}
    _, pending = project(report, attachment)
    assert pending['execution_count'] == 0
    assert all('external_execution' not in sample['frame'] for sample in pending['conditions'][0]['samples'])
    attachment['comparison_sha256'] = 'c'*64
    with pytest.raises(ValueError, match='comparison'):
        project(report, attachment)


def test_policy_samples_use_their_own_tutor_and_shared_captured_work():
    shared = action.initial_task(recovered(), instruction_cells=[0], work_cell=1)
    shared['dialogue'] = shared['dialogue'][:1]
    report = {'model':'gemini-2.5-pro', 'plan_sha256':'a'*64, 'shared_task':shared,
              'scope':'One supplied tutor reply per condition; source only.', 'conditions':{}}
    for name, choice in [('direct', {'decision':'revise-work', 'text':'', 'source':'total = 7'}),
                         ('hint', {'decision':'reply', 'text':'which value?', 'source':None})]:
        task = deepcopy(shared)
        task['dialogue'].append({'role':'tutor', 'text':name+' AUTHORED REPLY'})
        report['conditions'][name] = dict(label=name, policy=name+' policy', task=task,
            records=[{'index':1, 'status':'complete', 'response':choice,
                      'raw_response':'NOT_FOR_BROWSER'}, {'index':2, 'status':'error'}],
            valid=1, failed=1, requested=30, status='complete', categories=[])
    before = deepcopy(report)
    packet, sampling = project(report)
    assert report == before
    assert 'NOT_FOR_BROWSER' not in json.dumps((packet, sampling))
    assert not packet['controls']['send_enabled']
    first, second = sampling['conditions']
    edit, reply = first['samples'][0]['frame'], second['samples'][0]['frame']
    for encounter, condition in zip(packet['encounters'], sampling['conditions']):
        assert encounter['evidence_card']['student_messages'] == 1
        assert encounter['evidence_card']['examples'][0]['text'] == 'check?'
        captured, tutor = encounter['frames']
        assert captured['dialogue'] == [{'role':'student', 'origin':'source', 'text':'check?'}]
        assert captured['work'] == tutor['work'] == shared['work']
        assert len(tutor['dialogue']) == 2 and tutor['dialogue'][1]['origin'] == 'generated'
        assert tutor['dialogue'][1]['text'] == condition['id']+' AUTHORED REPLY'
        assert condition['valid'] == condition['failed'] == 1
        for frame in [captured, tutor, *[sample['frame'] for sample in condition['samples']]]:
            assert 'reaction' not in frame and 'external_execution' not in frame
            assert frame['feedback'] is None
    assert edit['work']['source'] == 'total = 7' and edit['work']['revision'] == 1
    assert len(edit['dialogue']) == 2 and edit['dialogue'][-1]['text'] == 'direct AUTHORED REPLY'
    assert reply['work'] == shared['work']
    assert [turn['text'] for turn in reply['dialogue']] == ['check?', 'hint AUTHORED REPLY', 'which value?']
    assert '+total = 7' in edit['changes']['unified_diff']
    assert reply['changes']['unified_diff'] == ''
    assert packet['encounters'][0]['evidence_card'] == packet['encounters'][1]['evidence_card']
    contaminated = deepcopy(report)
    contaminated['shared_task']['dialogue'].append({'role':'student', 'origin':'generated', 'text':'SYNTHETIC'})
    protected, _ = project(contaminated)
    assert protected['encounters'][0]['evidence_card'] == packet['encounters'][0]['evidence_card']


def test_saved_comparison_api_is_read_only_and_redacts_changed_receipts(tmp_path):
    from apps.policy_sampling_preview import create_app
    from tests.test_notebook_policy_sampling import runner, source, raw
    module, original = runner(), source(tmp_path)
    destination = tmp_path/'comparison'
    module.prepare(destination, original)
    module.execute(destination, send=True,
        generate_tutor=lambda *_:raw({'text':'AUTHORED_TUTOR'}),
        generate_student=lambda *_:raw({'decision':'reply','text':'AUTHORED_STUDENT','source':None}))
    with pytest.raises(ValueError, match='Explicitly identify'):
        create_app(notebook_branch=original, comparison=destination, authored_demo=None)
    app = create_app(notebook_branch=original, comparison=destination, authored_demo=True)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        packet = client.get('/api/policy-sampling').json()
        assert packet['authored_demo'] is True and len(packet['conditions']) == 2
        assert all(c['valid'] == 30 for c in packet['conditions'])
        assert 'raw_response' not in json.dumps(packet)
        work = client.get('/api/workspace').json()
        assert len(work['encounters']) == 2
        assert len(work['encounters'][0]['frames'][0]['dialogue']) == 1
        assert client.get('/api/policy-sampling?condition=unknown').status_code == 400
        assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
        assert client.post('/api/continue', json={}).status_code == 404
        assert '/policy-sampling.js' in client.get('/').text
        assert "style-src 'self' 'unsafe-inline'" in client.get('/').headers['content-security-policy']
        path = destination/'tutor-direct.json'
        receipt = json.loads(path.read_text())
        receipt['response']['text'] = 'ALTERED_PRIVATE_TEXT'
        path.write_text(json.dumps(receipt))
        for endpoint in ['/api/workspace','/api/policy-sampling']:
            response = client.get(endpoint)
            assert response.status_code == 409
            assert 'ALTERED_PRIVATE_TEXT' not in response.text and 'AUTHORED_STUDENT' not in response.text


def test_optional_verified_attachment_api_redacts_changed_reactions(tmp_path):
    from apps.policy_sampling_preview import create_app
    from src.agents.notebook_student import _read, _save
    from tests.test_policy_execution import prepared_followup, raw
    module, comparison, continuation, _ = prepared_followup(tmp_path)
    module.execute(continuation)
    module.prepare_reactions(continuation)
    module.send(continuation, send=True, generate=lambda *_:raw(
        {'decision':'reply', 'text':'AUTHORED_REACTION', 'source':None}))
    app = create_app(notebook_branch=tmp_path/'source', comparison=comparison,
                     authored_demo=True, continuation=continuation)
    loop_app = create_app(notebook_branch=tmp_path/'source', comparison=comparison,
                         authored_demo=True, continuation=continuation, loop_condition='direct')
    with TestClient(loop_app, base_url='http://127.0.0.1') as client:
        packet = client.get('/api/workspace').json()
        assert len(packet['encounters']) == 1 and packet['encounters'][0]['loop_example']
        assert packet['encounters'][0]['loop_authored_demo'] is True
        assert len(packet['encounters'][0]['frames']) == 5
        assert '/student-loop.js' in client.get('/').text
        assert '/policy-sampling.js' not in client.get('/').text
        assert not any('POST' in getattr(route, 'methods', ()) for route in loop_app.routes)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        packet = client.get('/api/policy-sampling').json()
        assert packet['continuation'] is True
        assert 'raw_response' not in json.dumps(packet)
        for condition in packet['conditions']:
            first, second = condition['samples'][:2]
            assert first['reaction_frame']['dialogue'][-1]['text'] == 'AUTHORED_REACTION'
            assert 'reaction_frame' not in second
            assert first['frame']['external_execution'] == second['frame']['external_execution']
        assert client.get('/api/workspace').status_code == 200
        path = continuation/'reaction-direct.json'
        receipt = _read(path)
        receipt['response']['text'] = 'ALTERED_PRIVATE_REACTION'
        _save(path, receipt)
        for endpoint in ['/api/workspace', '/api/policy-sampling']:
            response = client.get(endpoint)
            assert response.status_code == 409
            assert 'ALTERED_PRIVATE_REACTION' not in response.text and 'AUTHORED_REACTION' not in response.text
    with TestClient(loop_app, base_url='http://127.0.0.1') as client:
        response = client.get('/api/workspace')
        assert response.status_code == 409 and 'ALTERED_PRIVATE_REACTION' not in response.text
