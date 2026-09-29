"""Authored source-only comparison: no inherited fix, output, or original tutor."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from apps.policy_sampling_preview import project
from src.agents.notebook_branch import action
from tests.test_notebook_branch import recovered


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
