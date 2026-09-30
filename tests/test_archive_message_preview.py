"""The new unexecuted message must never borrow an older matching-source result."""
from copy import deepcopy
from hashlib import sha256
import json

from fastapi.testclient import TestClient
import pytest

from apps.archive_message_preview import consolidate, create_app, project
from apps import archive_message_preview as preview
from src.agents import archive_tutor_continuation as continuation
from src.agents import archived_notebook as archive, notebook_student as store
from tests.test_archive_tutor_continuation import child
from tests.test_archive_sequence import sequence
from tests.test_archived_notebook import prepared, action, execution, no_execution
from tests.test_policy_execution import prepared_followup, raw


def sequence_result(plan):
    """Hand-authored snapshots of edit, run, chat, tutor, edit, stop; no dispatch."""
    plan = deepcopy(plan) | {'max_decisions':8, 'max_tutor_calls':3, 'max_checks':4}
    initial = plan['initial']
    frames = [{'kind':'initial', 'work':deepcopy(initial['work']),
        'dialogue':deepcopy(initial['dialogue']), 'message':None, 'observation':None,
        'status':'active', 'decisions':0, 'tutor_turns':0, 'checks':0}]

    def append(**changes):
        frame = deepcopy(frames[-1])
        frame.pop('action', None)
        frame.update(changes)
        frames.append(frame)

    append(kind='student', work={**initial['work'], 'revision':1, 'source':'unique_uris = 22'},
           decisions=1, action=action('revise-work', 'unique_uris = 22'))
    observation = {'status':'ok', 'value':22, 'success':None, 'grading':'none',
        'revision':1, 'source_sha256':sha256(b'unique_uris = 22').hexdigest(),
        'output':'AUTHORED OUTPUT', 'error':None}
    append(decisions=2, checks=1, observation=observation, action=action('request-check'))
    append(decisions=3, status='awaiting-tutor', message='this result?', action=action('reply', text='this result?'))
    append(kind='tutor', tutor_turns=1, status='active', message=None,
           dialogue=deepcopy(initial['dialogue']) + [{'role':'student', 'text':'this result?'},
                                                   {'role':'tutor', 'text':'AUTHORED NEW TUTOR'}])
    append(kind='student', decisions=4, observation=None,
           work={**initial['work'], 'revision':2, 'source':'unique_uris = 23'},
           action=action('revise-work', 'unique_uris = 23'))
    append(decisions=5, status='no-reply', action=action('no-reply'))
    return {'plan':plan, 'status':'no-reply', 'state':deepcopy(frames[-1]), 'frames':frames}


def test_sequence_projects_chat_once_and_clears_feedback_after_edit(prepared):
    _, plan = prepared
    result = sequence_result(plan)
    before = deepcopy(result)
    packet = preview.project_sequence(result)
    encounter = packet['encounters'][0]
    frames = encounter['frames']
    assert result == before
    assert encounter['archive_sequence'] and encounter['archive_continuation']
    assert encounter['model_decisions'] == 5 and encounter['tutor_calls'] == 1
    assert encounter['execution_calls'] == encounter['execution_results'] == 1
    assert len(frames) == 7
    assert frames[0]['archive_reused_tutor'] and 'saved hint' in frames[0]['label'].lower()
    assert frames[0]['dialogue'][-1]['origin'] == 'generated'
    assert frames[0]['dialogue'][0]['origin'] == 'source'
    assert [f['decisions_remaining'] for f in frames] == [8, 7, 6, 5, 5, 4, 3]
    assert [f['work']['revision'] for f in frames] == [0, 1, 1, 1, 1, 2, 2]
    assert frames[3]['pending_message'] == 'this result?'
    assert all(t['text'] != 'this result?' for t in frames[3]['dialogue'])
    for frame in frames[4:]:
        assert frame['pending_message'] is None
        assert sum(t['text'] == 'this result?' for t in frame['dialogue']) == 1
        assert frame['dialogue'][-2]['origin'] == 'generated'
    assert frames[2]['archive_observation']['value'] == 22
    assert frames[2]['archive_observation_new'] is True
    assert frames[3]['archive_observation'] == frames[4]['archive_observation'] == frames[2]['archive_observation']
    assert frames[3]['archive_observation_new'] is frames[4]['archive_observation_new'] is False
    assert all('archive_observation' not in frames[i] for i in (0, 1, 5, 6))
    assert '+unique_uris = 23' in frames[5]['changes']['unified_diff']
    assert frames[-1]['status'] == 'no-reply'
    assert all(f['feedback'] is None for f in frames)
    assert not packet['controls']['send_enabled'] and not packet['controls']['tutor_generation_enabled']
    assert 'ungraded' in encounter['saved_results_html'].lower()
    assert 'followup_folder' not in json.dumps(packet) and 'code_pins' not in json.dumps(packet)
    result['frames'][5]['observation'] = deepcopy(result['frames'][2]['observation'])
    with pytest.raises(ValueError, match='source'):
        preview.project_sequence(result)


@pytest.mark.parametrize('kind,status,message', [
    ('tutor', 'tutor-error', 'this result?'), ('student', 'error', None),
    ('student', 'action-limit', None), ('student', 'check-limit', None),
    ('student', 'tutor-limit', 'this result?')])
def test_sequence_keeps_faults_and_budget_stops_distinct(prepared, kind, status, message):
    _, plan = prepared
    result = sequence_result(plan)
    result['frames'] = result['frames'][:3]
    last = deepcopy(result['frames'][-1]) | {'kind':kind, 'status':status, 'message':message,
        'decisions':3, 'tutor_turns':int(kind == 'tutor')}
    last.pop('action')
    if status.endswith('error'):
        last['error'] = {'message':'PRIVATE_PROVIDER_DETAIL'}
    result.update(status=status, state=last, frames=result['frames'] + [last])
    encounter = preview.project_sequence(result)['encounters'][0]
    final = encounter['frames'][-1]
    assert final['status'] == encounter['terminal_status'] == status
    assert final['pending_message'] == message
    assert final['archive_observation_new'] is False
    assert encounter['execution_calls'] == encounter['execution_results'] == 1
    assert 'PRIVATE_PROVIDER_DETAIL' not in json.dumps(encounter)
    result.update(status='prepared', state=None, frames=[])
    with pytest.raises(ValueError, match='completed'):
        preview.project_sequence(result)


def test_sequence_is_appended_as_latest_and_revalidated_on_each_data_get(prepared, sequence):
    parent_folder, _ = prepared
    parent = archive.run(parent_folder, send=True, generate=lambda *_:raw(action('reply', text='OLD MESSAGE')),
                         execute=no_execution)
    module, sequence_folder, _ = sequence
    choices = iter([action('reply', text='NEW MESSAGE'), action('no-reply')])
    def generate(_, prompt, schema):
        from src.agents import notebook_tutor
        return raw({'text':'NEW TUTOR'}) if schema is notebook_tutor.Reply else raw(next(choices))

    result = module.run(sequence_folder, send=True, generate=generate, execute=no_execution)
    original, sampling = consolidate(parent)
    packet, with_sequence = consolidate(parent, sequence=result)
    assert packet['encounters'][:-1] == original['encounters']
    assert packet['encounters'][-1] == preview.project_sequence(result)['encounters'][0]
    assert sampling == with_sequence
    assert packet['encounters'][-1]['frames'][-1]['dialogue'][-2]['text'] == 'NEW MESSAGE'
    assert all(t['text'] != 'OLD MESSAGE' for t in packet['encounters'][-1]['frames'][-1]['dialogue'])
    app = create_app(parent_folder, notebook_branch=parent_folder.parent/'source',
                     include_policy_samples=True, sequence=sequence_folder)
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/workspace').json() == packet
        assert client.get('/api/policy-sampling').json() == sampling
        assert client.get('/api/workspace?sequence=other').status_code == 400
        assert client.post('/api/continue', json={}).status_code == 404
        path = sequence_folder/'run.json'
        receipt = store._read(path)
        changed = deepcopy(receipt)
        changed['calls'][0]['response'] = raw(action('reply', text='FORGED_SEQUENCE_PRIVATE'))
        store._save(path, changed)
        for endpoint in ('/api/workspace', '/api/policy-sampling'):
            response = client.get(endpoint)
            assert response.status_code == 409
            assert 'FORGED_SEQUENCE_PRIVATE' not in response.text and 'NEW MESSAGE' not in response.text
        store._save(path, receipt)
        assert client.get('/api/workspace').json() == packet
    single_app = create_app(parent_folder, notebook_branch=parent_folder.parent/'source', sequence=sequence_folder)
    with TestClient(single_app, base_url='http://127.0.0.1') as client:
        assert [c['id'] for c in client.get('/api/workspace').json()['encounters']] == [
            'archive-message', 'archive-sequence']


def test_saved_message_projection_and_read_only_fail_closed_api(prepared):
    folder, _ = prepared
    # The older authored probe has an error for this exact source. This run never executes it.
    choice = action('revise-work', 'unique_uris = 1', 'unique_uris = 1')
    result = archive.run(folder, send=True, generate=lambda *_:raw(choice), execute=no_execution)
    original = deepcopy(result)
    packet = project(result)
    assert result == original
    encounter = packet['encounters'][0]
    captured, tutor, sent = encounter['frames']
    assert encounter['archive_message'] and encounter['authored_demo']
    assert encounter['execution_calls'] == 0
    assert [f['work']['revision'] for f in encounter['frames']] == [0, 0, 1]
    assert [f['decisions_remaining'] for f in encounter['frames']] == [6, 6, 5]
    assert [len(f['dialogue']) for f in encounter['frames']] == [1, 2, 2]
    assert captured['pending_message'] is tutor['pending_message'] is None
    assert sent['pending_message'] == choice['text']
    assert sent['status'] == 'awaiting-tutor' and sent['actions'] == [choice]
    assert '+unique_uris = 1' in sent['changes']['unified_diff']
    assert all(f['feedback'] is None and 'external_execution' not in f and 'reaction' not in f for f in encounter['frames'])
    assert 'authored missing method' not in json.dumps(packet)
    assert 'code_pins' not in json.dumps(packet) and 'followup_folder' not in json.dumps(packet)
    assert encounter['evidence_card']['student_messages'] == 1
    assert not packet['controls']['send_enabled']
    for status in ('prepared', 'no-reply', 'action-limit', 'error'):
        with pytest.raises(ValueError):
            project({**result, 'status':status})
    with pytest.raises(ValueError):
        project({**result, 'state':{**result['state'], 'observation':{'status':'ok'}}})

    app = create_app(folder, notebook_branch=folder.parent/'source')
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/workspace').json() == packet
        assert client.get('/api/workspace?scenario=other').status_code == 400
        assert client.post('/api/continue', json={}).status_code == 404
        assert '/archive-message.js' in client.get('/').text
        assert '/student-loop.js' not in client.get('/').text
        assert "style-src 'self' 'unsafe-inline'" in client.get('/').headers['content-security-policy']
        assert client.get('/student-loop.css').status_code == 200
        assert client.get('/archive-message.js').status_code == 200
        path = folder/'run.json'
        saved = store._read(path)
        changed = deepcopy(saved)
        changed['calls'][0]['response']['candidates'][0]['content']['parts'][0]['text'] = 'FORGED_PRIVATE_TEXT'
        store._save(path, changed)
        response = client.get('/api/workspace')
        assert response.status_code == 409
        assert 'FORGED_PRIVATE_TEXT' not in response.text and 'unique_uris' not in response.text
        store._save(path, saved)
        assert client.get('/api/workspace').json() == packet


def continued(prepared, choices, *, failure=None, execution_status='ok'):
    """Replay authored responses through the simulator; never dispatch a provider or runtime."""
    folder, parent_folder, parent = child(prepared)
    result = continuation.load(folder)
    _, probe = archive._context(parent_folder)
    choices = iter(choices)

    def exchange(kind, request):
        if kind == failure:
            raise RuntimeError('PRIVATE_PROVIDER_DETAIL')
        if kind == 'tutor':
            return raw({'text':'AUTHORED NEW TUTOR REPLY'})
        if kind == 'model':
            return raw(next(choices))
        assert kind == 'execution'
        code, output, problem = execution(request, status=execution_status, value=22)
        return {'exit_code':code, 'output_hex':output.hex(), 'problem':problem}

    result.update(continuation._simulate(result['plan'], probe, exchange))
    return folder, parent_folder, parent, result


def test_continuation_keeps_parent_frames_and_invalidates_edited_revision(prepared):
    choices = [action('revise-work', 'unique_uris = 22'), action('request-check'),
               action('revise-work', 'unique_uris = 23')]
    _, _, parent, result = continued(prepared, choices)
    original = deepcopy((parent, result))
    baseline = project(parent)['encounters'][0]
    packet = project(parent, result)
    encounter = packet['encounters'][0]
    frames = encounter['frames']
    assert (parent, result) == original
    assert frames[:3] == baseline['frames']
    assert len(frames) == 7
    tutor, edit, checked, edited_again = frames[3:]
    assert tutor['pending_message'] is None
    assert [(turn['role'], turn['text']) for turn in tutor['dialogue'][-2:]] == [
        ('student', parent['state']['message']), ('tutor', result['tutor_reply']['text'])]
    assert tutor['dialogue'][-2]['origin'] == 'generated'
    assert all(sum(turn['text'] == parent['state']['message'] for turn in frame['dialogue']) == 1
               and frame['pending_message'] is None for frame in frames[3:])
    assert [frame['work']['revision'] for frame in frames[3:]] == [1, 2, 2, 3]
    assert [frame['decisions_remaining'] for frame in frames[3:]] == [3, 2, 1, 0]
    assert [frame['actions'] for frame in frames[4:]] == [[choice] for choice in choices]
    assert [frame['archive_stage'] for frame in frames[4:]] == [choice['decision'] for choice in choices]
    observation = checked['archive_observation']
    assert observation['status'] == 'ok' and observation['value'] == 22
    assert observation['revision'] == checked['work']['revision']
    assert observation['source_sha256'] == result['state']['history'][1]['observation']['source_sha256']
    assert observation['success'] is None and observation['grading'] == 'none'
    assert observation['dataset'] == parent['plan']['dataset']
    assert observation['image_id'] == parent['plan']['image_id']
    assert checked['archive_observation_new'] is True
    assert all(not frame.get('archive_observation') for frame in (tutor, edit, edited_again))
    assert all(frame['feedback'] is None and 'external_execution' not in frame and 'reaction' not in frame
               for frame in frames)
    assert edited_again['status'] == 'action-limit'
    assert encounter['model_decisions'] == 4 and encounter['execution_results'] == 1
    assert encounter['evidence_card'] == baseline['evidence_card']
    assert 'authored missing method' not in json.dumps(packet)
    assert 'code_pins' not in json.dumps(packet) and 'tutor_prompt' not in json.dumps(packet)
    assert not packet['controls']['send_enabled'] and not packet['controls']['tutor_generation_enabled']


@pytest.mark.parametrize('last,terminal', [(action('no-reply'), 'no-reply'),
                                         (action('reply', text='NEW STUDENT MESSAGE'), 'awaiting-tutor')])
def test_continuation_retains_observation_only_for_unchanged_work(prepared, last, terminal):
    _, _, parent, result = continued(prepared, [action('request-check'), last], execution_status='cell-error')
    encounter = project(parent, result)['encounters'][0]
    checked, final = encounter['frames'][-2:]
    assert checked['archive_observation']['status'] == 'cell-error'
    assert final['archive_observation'] == checked['archive_observation']
    assert checked['archive_observation_new'] is True and final['archive_observation_new'] is False
    assert checked['work'] == final['work']
    assert final['status'] == terminal and final['actions'] == [last]
    assert encounter['execution_results'] == 1
    assert final['pending_message'] == (last['text'] or None)
    assert all(turn['text'] != 'NEW STUDENT MESSAGE' for turn in final['dialogue'])


def test_rejected_edit_keeps_prior_observation_without_claiming_an_applied_edit(prepared):
    rejected = action('revise-work', 'x' * 20001)
    _, _, parent, result = continued(prepared, [action('request-check'), rejected])
    assert result['state']['history'][-1]['error']
    checked, failed = project(parent, result)['encounters'][0]['frames'][-2:]
    assert failed['status'] == 'error' and 'fail' in failed['label'].lower()
    assert failed['work'] == checked['work'] and failed['changes']['unified_diff'] == ''
    assert failed['archive_observation'] == checked['archive_observation']
    assert failed['archive_observation_new'] is False
    assert failed['pending_message'] is None


@pytest.mark.parametrize('failure,choices,terminal', [
    ('tutor', [], 'tutor-error'), ('model', [], 'error'),
    ('execution', [action('request-check')], 'error')])
def test_continuation_failures_are_distinct_and_do_not_expose_private_errors(prepared, failure, choices, terminal):
    _, _, parent, result = continued(prepared, choices, failure=failure)
    packet = project(parent, result)
    encounter = packet['encounters'][0]
    final = encounter['frames'][-1]
    assert final['status'] == terminal and final['status'] != 'no-reply'
    assert not final.get('archive_observation') and not final.get('archive_observation_new')
    assert final['feedback'] is None and 'reaction' not in final
    assert encounter['execution_results'] == 0
    assert 'PRIVATE_PROVIDER_DETAIL' not in json.dumps(packet)
    assert final['work'] == parent['state']['work']
    if failure == 'tutor':
        assert len(encounter['frames']) == 4 and final['archive_stage'] == 'tutor-error'
        assert final['pending_message'] == parent['state']['message']
        assert final['dialogue'] == encounter['frames'][2]['dialogue']
    elif failure == 'execution':
        assert final['actions'] == [action('request-check')]
    else:
        assert final['actions'] == [] and final['archive_stage'] == 'error'


def test_continuation_api_pins_both_inputs_and_remains_read_only(prepared, monkeypatch):
    folder, parent_folder, parent, result = continued(prepared, [action('no-reply')])
    current = deepcopy(result)
    monkeypatch.setattr(continuation, 'load', lambda _:deepcopy(current))
    app = create_app(parent_folder, notebook_branch=parent_folder.parent/'source', continuation=folder)
    packet = project(parent, result)
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/workspace').json() == packet
        assert client.get('/api/workspace?scenario=other').status_code == 400
        assert client.post('/api/continue', json={}).status_code == 404
        current['tutor_reply']['text'] = 'FORGED_CONTINUATION_PRIVATE_TEXT'
        response = client.get('/api/workspace')
        assert response.status_code == 409 and 'FORGED_CONTINUATION_PRIVATE_TEXT' not in response.text
        current = deepcopy(result)
        assert client.get('/api/workspace').json() == packet
        path = parent_folder/'run.json'
        saved = store._read(path)
        changed = deepcopy(saved)
        changed['calls'][0]['response'] = raw(action('reply', text='FORGED_PARENT_PRIVATE_TEXT'))
        store._save(path, changed)
        response = client.get('/api/workspace')
        assert response.status_code == 409 and 'FORGED_PARENT_PRIVATE_TEXT' not in response.text
        store._save(path, saved)
        assert client.get('/api/workspace').json() == packet
    changed_parent = deepcopy(parent)
    changed_parent['state']['message'] = 'OTHER PARENT'
    with pytest.raises(ValueError):
        project(changed_parent, result)


def test_unified_workspace_keeps_runs_checks_and_reactions_separate(tmp_path):
    followup, comparison, previous, _ = prepared_followup(tmp_path)
    followup.execute(previous)
    followup.prepare_reactions(previous)
    followup.send(previous, send=True, generate=lambda _, prompt:raw(
        action('revise-work', 'unique_uris = 22') if 'DIRECT_TUTOR' in prompt else action('no-reply')))
    folder = tmp_path/'archive-loop'
    archive.prepare(folder, followup_folder=previous, condition='hint', authored_demo=True)
    parent = archive.run(folder, send=True, generate=lambda *_:raw(
        action('revise-work', 'unique_uris = 1', 'unique_uris = 1')), execute=no_execution)
    original = deepcopy(parent)
    packet, sampling = consolidate(parent)
    assert parent == original
    direct, hint, latest = packet['encounters']
    assert all(c['simulation_workspace'] and c['archive_message'] for c in packet['encounters'])
    assert latest == project(parent)['encounters'][0] | {'simulation_workspace':True}
    assert latest['execution_calls'] == 0
    assert sampling['unified_workspace'] and sampling['authored_demo']
    assert sampling['execution_count'] == 3
    assert [len(c['samples']) for c in sampling['conditions']] == [30, 30]
    for encounter, condition in zip((direct, hint), sampling['conditions']):
        assert encounter['policy_sample'] and encounter['sample_index'] == 1
        assert encounter['execution_results'] == 1
        assert encounter['evidence_card']['student_messages'] == 1
        for sample in condition['samples']:
            frames = sample['timeline']
            assert len(frames) == (5 if sample['index'] == 1 else 4)
            assert all('reaction' not in f and 'external_execution' not in f for f in frames)
            assert all('archive_observation' not in f for f in frames[:3])
            check = frames[3]
            assert check['archive_stage'] == 'researcher-check' and check['actions'] == []
            assert check['archive_observation_actor'] == 'researcher' and check['archive_observation_new']
            assert check['archive_observation']['revision'] == check['work']['revision']
            assert len(frames[0]['dialogue']) == 1
            assert frames[1]['dialogue'][-1]['text'] == ('DIRECT_TUTOR' if condition['id'] == 'direct' else 'HINT_TUTOR')
    assert direct['frames'][-1]['archive_reaction']
    assert 'archive_observation' not in direct['frames'][-1]  # Repair is unexecuted.
    assert hint['frames'][-1]['archive_observation'] == hint['frames'][-2]['archive_observation']
    assert hint['frames'][-1]['archive_observation_new'] is False
    assert hint['frames'][-1]['status'] == 'no-reply'
    assert all('archive_observation' not in f for f in latest['frames'])
    assert 'code_pins' not in json.dumps((packet, sampling))

    app = create_app(folder, notebook_branch=tmp_path/'source', include_policy_samples=True)
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/workspace').json() == packet
        assert client.get('/api/policy-sampling').json() == sampling
        assert client.get('/api/policy-sampling?condition=other').status_code == 400
        assert client.post('/api/continue', json={}).status_code == 404
        html = client.get('/').text
        assert html.index('/archive-message.js') < html.index('/policy-sampling.js')
        for asset in ('archive-message.js', 'student-loop.css', 'policy-sampling.js', 'policy-sampling.css', 'next-actions.css'):
            assert client.get('/'+asset).status_code == 200
        path = previous/'reaction-direct.json'
        receipt = store._read(path)
        store._save(path, receipt | {'response':action('reply', text='FORGED_PRIVATE')})
        for endpoint in ('/api/workspace', '/api/policy-sampling'):
            response = client.get(endpoint)
            assert response.status_code == 409 and 'FORGED_PRIVATE' not in response.text
        store._save(path, receipt)
        assert client.get('/api/workspace').json() == packet


def test_optional_history_benchmark_is_pinned_read_only_and_independent(prepared, monkeypatch):
    from apps import history_benchmark
    folder, _ = prepared
    archive.run(folder, send=True, generate=lambda *_:raw(action('reply', text='AUTHORED MESSAGE')),
                execute=no_execution)
    saved = {'version':1, 'cases':[{'reference':{'text':'AUTHORED REFERENCE'}}]}
    monkeypatch.setattr(history_benchmark, 'load', lambda _:deepcopy(saved))
    app = create_app(folder, notebook_branch=folder.parent/'source', history_benchmark=folder.parent/'benchmark')
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/history-benchmark').json() == saved
        assert client.get('/api/history-benchmark?case=unknown').status_code == 400
        assert client.post('/api/history-benchmark', json={}).status_code == 405
        html = client.get('/').text
        assert html.index('/archive-message.js') < html.index('/history-benchmark.js')
        assert '/history-benchmark.css' in html
        for asset in ('history-benchmark.js', 'history-benchmark.css', 'archive-message.js'):
            assert client.get('/'+asset).status_code == 200
        saved['cases'][0]['reference']['text'] = 'CHANGED_PRIVATE_REFERENCE'
        response = client.get('/api/history-benchmark')
        assert response.status_code == 409 and 'CHANGED_PRIVATE_REFERENCE' not in response.text
        assert 'AUTHORED REFERENCE' not in response.text
        assert client.get('/api/workspace').status_code == 200
