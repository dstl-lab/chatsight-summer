"""The new unexecuted message must never borrow an older matching-source result."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from apps.archive_message_preview import create_app, project
from src.agents import archive_tutor_continuation as continuation
from src.agents import archived_notebook as archive, notebook_student as store
from tests.test_archive_tutor_continuation import child
from tests.test_archived_notebook import prepared, action, execution, no_execution
from tests.test_policy_execution import raw


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
