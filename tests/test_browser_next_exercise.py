"""One configured notebook successor is saved offline and reopened without resends."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import sys
from threading import Event

import pytest
from fastapi.testclient import TestClient

from src.agents import browser_workspace as browser, chat_student, notebook_example, notebook_student as student
from tests.test_chat_student import QUERY
from tests.test_notebook_example import EXERCISE, IMAGE, files
from tests.test_tutor_context import choose


def setup(tmp_path, *, ended=True, **options):
    chat = tmp_path / 'chat'
    chat_student.create(chat, query=QUERY)
    chat_student.show(chat)
    source = notebook_example.create(tmp_path / 'first', image_id=IMAGE, chat_source=chat)
    student.load(source)
    if ended:
        choose(source, 'no-reply')
    exercise_file = tmp_path / 'exercise.json'
    exercise_file.write_text(json.dumps(EXERCISE))
    output = tmp_path / 'next'
    kwargs = dict(next_exercise_file=exercise_file, next_exercise_output=output, **options)
    client = TestClient(browser.create_app(source, **kwargs), base_url='http://127.0.0.1')
    return client, source, exercise_file, output, kwargs


def submission(packet):
    return {'binding':packet['encounters'][-1]['frames'][-1]['binding'],
            'exercise_sha256':packet['controls']['next_exercise']['exercise_sha256']}


def test_offline_save_preserves_source_example_and_fresh_child_then_reopens(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Setup or viewing dispatched a provider or runtime')
    monkeypatch.setattr(student.llm, 'make_generate', forbidden)
    monkeypatch.setattr(student.notebook_runtime, 'check_work', forbidden)
    client, source, _, output, kwargs = setup(tmp_path, policy='Previous task policy.')
    before = files(tmp_path)
    current = client.get('/api/workspace').json()
    control = current['controls']['next_exercise']
    assert current['exercise'] == 'current'
    assert control['status'] == 'ready' and control['reason'] is None
    assert control['task'] == EXERCISE['task']['task']
    assert client.get('/api/workspace').json() == current and files(tmp_path) == before
    response = client.post('/api/next-exercise', json=submission(current))
    assert response.status_code == 200, response.text
    child = response.json()
    assert child['exercise'] == 'next' and child['scenario_id'] is None
    assert 'next_exercise' not in child['controls']
    assert child['controls']['policy'] == EXERCISE['policy']
    assert child['controls']['send_enabled'] is False
    assert len(child['encounters']) == 2
    encounter = child['encounters'][-1]
    assert encounter['initialization']['conversation_example'] == QUERY['prefix']
    assert encounter['initialization']['previous_encounter']['status'] == 'no-reply'
    frame = encounter['frames'][0]
    assert frame['work'] == EXERCISE['task']['work']
    assert frame['status'] == 'active' and frame['decisions_remaining'] == 6
    assert frame['feedback'] is None and frame['actions'] == []
    saved = student._read(output / 'session/session.json')
    assert saved['initial']['evaluation'] == EXERCISE['evaluation']
    assert saved['initial']['activity']['image_id'] == IMAGE
    assert saved['model'] == student._read(source / 'session.json')['model']
    for secret in (str(tmp_path), 'PRIVATE_AUTHORED_PROVENANCE', '"evaluation"', 'image_id'):
        assert secret not in response.text
    after = files(tmp_path)
    assert all(after[name] == content for name, content in before.items())
    assert client.get('/api/workspace').json()['controls']['next_exercise']['status'] == 'saved'
    assert client.get('/api/workspace?exercise=next').json() == child
    assert client.post('/api/next-exercise', json=submission(current)).status_code == 409
    # A lost response or process restart recovers by reading the configured child.
    reopened = TestClient(browser.create_app(source, **kwargs), base_url='http://127.0.0.1')
    assert reopened.get('/api/workspace').json()['controls']['next_exercise']['status'] == 'saved'
    assert reopened.get('/api/workspace?exercise=next').json()['encounters'] == child['encounters']
    assert files(tmp_path) == after
    assert reopened.post('/api/continue?exercise=next', json={
        'binding':frame['binding'], 'mode':'advance'}).status_code == 403


def test_child_continuation_uses_existing_controls_and_keeps_source_unchanged(tmp_path):
    calls = []
    def generate(prompt, schema):
        calls.append(prompt)
        return schema(decision='no-reply', text='', source=None)
    client, source, _, output, _ = setup(tmp_path, send=True, generate=generate)
    original = files(source)
    saved = client.post('/api/next-exercise', json=submission(client.get('/api/workspace').json()))
    assert saved.status_code == 200 and calls == []
    binding = saved.json()['encounters'][-1]['frames'][-1]['binding']
    response = client.post('/api/continue?exercise=next', json={'binding':binding, 'mode':'advance'})
    assert response.status_code == 200, response.text
    assert response.json()['exercise'] == 'next'
    assert response.json()['encounters'][-1]['frames'][-1]['status'] == 'no-reply'
    assert len(calls) == 1 and EXERCISE['task']['task'] in calls[0]
    assert 'PRIVATE_AUTHORED_PROVENANCE' not in calls[0] and '"evaluation"' not in calls[0]
    assert client.get('/api/workspace?exercise=next').status_code == 200 and len(calls) == 1
    assert files(source) == original and (output / 'session/step-0001.json').is_file()


def test_busy_child_reads_wait_without_replaying_locked_receipts_or_resending(tmp_path):
    entered, release = Event(), Event()
    calls = []
    def generate(prompt, schema):
        calls.append(prompt)
        entered.set()
        assert release.wait(5), 'Authored test callback was not released'
        return schema(decision='no-reply', text='', source=None)
    client, source, _, _, _ = setup(tmp_path, send=True, generate=generate)
    child = client.post('/api/next-exercise', json=submission(client.get('/api/workspace').json())).json()
    body = {'binding':child['encounters'][-1]['frames'][-1]['binding'], 'mode':'advance'}
    original = files(source)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(client.post, '/api/continue?exercise=next', json=body)
        try:
            assert entered.wait(3), 'Authored continuation never started'
            for url in ('/api/workspace?exercise=next', '/api/workspace'):
                pending = client.get(url)
                assert pending.status_code == 202, pending.text
                assert pending.json()['operation']['status'] == 'running'
                assert 'encounters' not in pending.json() and 'controls' not in pending.json()
                assert str(tmp_path) not in pending.text
            assert client.post('/api/continue?exercise=next', json=body).status_code == 409
            assert len(calls) == 1
        finally:
            release.set()
        assert running.result(timeout=3).status_code == 200
    assert client.get('/api/workspace?exercise=next').json()['operation']['status'] == 'complete'
    assert client.get('/api/workspace').json()['operation']['status'] == 'idle'
    assert len(calls) == 1 and files(source) == original


def test_only_genuine_stop_can_create_and_stale_source_cannot_dispatch(tmp_path):
    client, source, _, output, _ = setup(tmp_path, ended=False)
    active = client.get('/api/workspace').json()
    assert active['controls']['next_exercise']['status'] == 'blocked'
    assert client.post('/api/next-exercise', json=submission(active)).status_code == 409
    choose(source, 'no-reply')
    assert client.post('/api/next-exercise', json=submission(active)).status_code == 409
    current = client.get('/api/workspace').json()
    assert current['controls']['next_exercise']['status'] == 'ready'
    assert not output.exists()
    assert client.post('/api/next-exercise', json=submission(current)).status_code == 200


@pytest.mark.parametrize('change', ['exercise', 'source', 'child-work', 'child-policy'])
def test_changed_inputs_and_saved_child_are_never_accepted(tmp_path, change):
    client, source, exercise_file, output, _ = setup(tmp_path)
    current = client.get('/api/workspace').json()
    if change.startswith('child'):
        assert client.post('/api/next-exercise', json=submission(current)).status_code == 200
    if change == 'exercise':
        exercise = deepcopy(EXERCISE)
        exercise['policy'] = 'Changed policy.'
        exercise_file.write_text(json.dumps(exercise))
    elif change == 'source':
        receipt_path = source / 'step-0001.json'
        receipt = student._read(receipt_path)
        receipt['result']['state']['work']['source'] = 'tampered'
        receipt_path.write_text(json.dumps(receipt))
    elif change == 'child-work':
        manifest_path = output / 'session/session.json'
        manifest = student._read(manifest_path)
        manifest['initial']['work']['source'] = 'tampered'
        manifest_path.write_text(json.dumps(manifest))
    else:
        (output / 'policy.txt').write_text('Changed saved policy.')
    before = files(tmp_path)
    assert client.post('/api/next-exercise', json=submission(current)).status_code == 409
    response = client.get('/api/workspace?exercise=next')
    assert response.status_code == 409 and str(tmp_path) not in response.text
    assert files(tmp_path) == before
    if change.startswith('child'):
        assert client.get('/api/workspace').json()['controls']['next_exercise']['status'] == 'blocked'


def test_fixed_selector_request_schema_and_origin_do_not_open_paths(tmp_path):
    client, source, _, output, _ = setup(tmp_path)
    body = submission(client.get('/api/workspace').json())
    before = files(tmp_path)
    for query in ('?exercise=current', '?exercise=next&exercise=next', '?exercise=../../other',
                  '?exercise=next&folder=/private', '?scenario=next'):
        assert client.get('/api/workspace' + query).status_code == 400
        assert client.post('/api/continue' + query, json={
            'binding':body['binding'], 'mode':'advance'}).status_code == 400
    assert client.get('/api/workspace?exercise=next').status_code == 409
    assert client.post('/api/next-exercise?exercise=next', json=body).status_code == 400
    assert client.post('/api/next-exercise', json=body | {'folder':str(output)}).status_code == 422
    assert client.post('/api/next-exercise', json=body | {'exercise_sha256':'0' * 64}).status_code == 409
    assert client.post('/api/next-exercise', json=body,
                       headers={'Origin':'http://evil.example'}).status_code == 403
    plain = TestClient(browser.create_app(source), base_url='http://127.0.0.1')
    assert plain.get('/api/workspace?exercise=next').status_code == 400
    assert plain.post('/api/next-exercise', json=body).status_code == 404
    assert files(tmp_path) == before


def test_configuration_requires_pair_standalone_notebook_and_safe_paths(tmp_path):
    _, source, exercise_file, output, _ = setup(tmp_path)
    for options in ({'next_exercise_file':exercise_file}, {'next_exercise_output':output},
                    {'next_exercise_file':exercise_file, 'next_exercise_output':output, 'chat_mode':True},
                    {'next_exercise_file':exercise_file, 'next_exercise_output':output, 'chat_sessions':True}):
        with pytest.raises(ValueError):
            browser.create_app(source, **options)
    for destination in (source / 'nested', source.parent, tmp_path):
        with pytest.raises(ValueError):
            browser.create_app(source, next_exercise_file=exercise_file, next_exercise_output=destination)
    linked = tmp_path / 'linked'
    linked.symlink_to(tmp_path / 'outside')
    with pytest.raises(ValueError):
        browser.create_app(source, next_exercise_file=exercise_file, next_exercise_output=linked)
    linked_file = tmp_path / 'linked.json'
    linked_file.symlink_to(exercise_file)
    with pytest.raises(ValueError):
        browser.create_app(source, next_exercise_file=linked_file, next_exercise_output=output)


def test_publication_failure_and_path_swap_preserve_sources_without_retrying(tmp_path, monkeypatch):
    client, source, _, output, _ = setup(tmp_path)
    current = client.get('/api/workspace').json()
    original = files(source)
    saved = student._save
    def interrupted(path, *args, **kwargs):
        if path.name == 'next-exercise.json':
            raise OSError('PRIVATE_INTERRUPTION')
        return saved(path, *args, **kwargs)
    monkeypatch.setattr(student, '_save', interrupted)
    response = client.post('/api/next-exercise', json=submission(current))
    assert response.status_code == 409 and 'PRIVATE_INTERRUPTION' not in response.text
    assert output.is_dir() and (output / 'session/session.json').is_file()
    incomplete = files(tmp_path)
    assert client.get('/api/workspace').json()['controls']['next_exercise']['status'] == 'blocked'
    assert client.get('/api/workspace?exercise=next').status_code == 409
    assert client.post('/api/next-exercise', json=submission(current)).status_code == 409
    assert files(tmp_path) == incomplete and files(source) == original
    moved = tmp_path / 'moved'
    output.rename(moved)
    output.symlink_to(moved, target_is_directory=True)
    assert client.post('/api/next-exercise', json=submission(current)).status_code == 409
    assert client.get('/api/workspace?exercise=next').status_code == 409
    assert files(source) == original


def test_cli_passes_fixed_exercise_configuration_without_creating(tmp_path, monkeypatch):
    import uvicorn
    _, source, exercise_file, output, _ = setup(tmp_path)
    requests = []
    def serve(app, **kwargs):
        requests.append(TestClient(app, base_url='http://127.0.0.1').get('/api/workspace').json())
        assert kwargs == {'host':'127.0.0.1', 'port':8450}
    monkeypatch.setattr(uvicorn, 'run', serve)
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(source), '--next-exercise-file',
        str(exercise_file), '--next-exercise-output', str(output), '--port', '8450'])
    before = files(tmp_path)
    browser.main()
    assert len(requests) == 1 and requests[0]['controls']['next_exercise']['status'] == 'ready'
    assert files(tmp_path) == before and not output.exists()
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(source), '--next-exercise-file', str(exercise_file)])
    with pytest.raises(SystemExit) as error:
        browser.main()
    assert error.value.code == 2 and len(requests) == 1
