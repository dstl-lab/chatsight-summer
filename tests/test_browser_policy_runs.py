"""Policy setup and execution reuse frozen pairs without resending saved requests."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import shutil
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_demo, chat_policy_pair as pair
from tests.test_chat_student import files


def setup(tmp_path, *, send=False, generate=None, generate_tutor=None):
    chat_demo.create(tmp_path / 'demo')
    source, workspace = tmp_path / 'demo' / 'source', tmp_path / 'runs'
    app = browser.create_app(source, chat_mode=True, policy_workspace=workspace,
                             send=send, generate=generate, generate_tutor=generate_tutor)
    return source, workspace, TestClient(app, base_url='http://127.0.0.1')


def draft(viewer):
    source = viewer.get('/api/comparison').json()['controls']['sources'][0]
    return {'source_id':source['id'], 'binding':source['binding'],
            'current_policy':'Give one hint.', 'proposed_policy':'Give the answer.'}


def save(viewer):
    response = viewer.post('/api/comparison', json=draft(viewer))
    assert response.status_code == 200, response.text
    result = response.json()
    case = next(case for case in result['cases'] if case['id'] == result['selected_id'])
    return {'comparison_id':case['id'], 'comparison_sha256':case['comparison_sha256']}


def scripted(calls):
    def tutor(_, schema):
        calls.append('tutor')
        return schema(text='Use **count**.')

    def student(_, schema):
        calls.append('student')
        return schema(decision='reply', text='count?')

    return tutor, student


def test_offline_save_pins_same_start_without_sending_or_touching_source(tmp_path):
    source, workspace, viewer = setup(tmp_path)
    before = files(tmp_path)
    catalog = viewer.get('/api/scenarios').json()
    assert catalog['policy_workspace_available'] is True and catalog['comparison_available'] is True
    packet = viewer.get('/api/comparison').json()
    assert packet['cases'] == [] and packet['controls']['send_enabled'] is False
    assert packet['controls']['sources'][0]['prefix']['turns'][0]['text'] == 'how do i count that'
    assert packet['controls']['sources'][0]['summary'] == 'how do i count that'
    assert files(tmp_path) == before and not workspace.exists()
    original = files(source)
    payload = draft(viewer)
    result = viewer.post('/api/comparison', json=payload)
    assert result.status_code == 200
    case = result.json()['cases'][0]
    assert len(case['comparison_sha256']) == 64
    original_source = packet['controls']['sources'][0]
    assert case['source'] == {key:original_source[key] for key in ('id', 'title', 'summary', 'binding')}
    assert case['summary'] == 'how do i count that' and case['reuse_unavailable_reason'] is None
    assert all(condition['status'] == 'ready' for condition in case['conditions'])
    assert result.json()['operation']['comparison_id'] == case['id']
    assert viewer.get('/api/comparison').json()['operation']['status'] == 'complete'
    assert str(tmp_path) not in result.text
    assert files(source) == original
    run = {'comparison_id':case['id'], 'comparison_sha256':case['comparison_sha256']}
    assert viewer.post('/api/comparison/run', json=run).status_code == 403
    before = files(tmp_path)
    duplicate = viewer.post('/api/comparison', json=payload)
    assert duplicate.status_code == 409 and 'already saved' in duplicate.json()['detail']
    assert files(tmp_path) == before


def test_run_once_records_four_requests_and_rejects_completed_retry(tmp_path):
    calls = []
    tutor, student = scripted(calls)
    source, _, viewer = setup(tmp_path, send=True, generate=student, generate_tutor=tutor)
    original = files(source)
    run = save(viewer)
    response = viewer.post('/api/comparison/run', json=run)
    assert response.status_code == 200
    result = response.json()
    assert result['operation']['status'] == 'complete'
    assert all(condition['status'] == 'student-replied' for condition in result['cases'][0]['conditions'])
    assert '<strong>count</strong>' in result['cases'][0]['conditions'][0]['tutor_html']
    assert calls == ['tutor', 'student', 'tutor', 'student']
    before = files(tmp_path)
    assert viewer.post('/api/comparison/run', json=run).status_code == 409
    assert files(tmp_path) == before and files(source) == original
    assert len(calls) == 4


@pytest.mark.parametrize('stage', ['tutor-failed', 'tutor-pending', 'student-pending'])
def test_saved_failed_or_incomplete_arm_is_not_retried_but_peer_can_finish(tmp_path, stage):
    calls = []
    tutor, student = scripted(calls)
    source, workspace, viewer = setup(tmp_path, send=True, generate=student, generate_tutor=tutor)
    run = save(viewer)
    destination = workspace / 'run-0001'
    binding = pair.show(destination)['conditions']['a']['snapshot']['binding']

    def stop(*_):
        if stage == 'tutor-failed':
            raise RuntimeError('PRIVATE /local/saved-path')
        raise KeyboardInterrupt()

    with pytest.raises(RuntimeError if stage == 'tutor-failed' else KeyboardInterrupt):
        pair.respond(destination, 'a', binding=binding, send=True,
                     generate_tutor=tutor if stage == 'student-pending' else stop,
                     generate_student=stop)
    calls.clear()
    original = files(source)
    response = viewer.post('/api/comparison/run', json=run)
    assert response.status_code == 200
    result = response.json()
    assert result['operation']['status'] == 'error'
    assert result['cases'][0]['conditions'][0]['status'] == ('failed' if stage == 'tutor-failed' else 'incomplete')
    assert result['cases'][0]['conditions'][1]['status'] == 'student-replied'
    assert 'PRIVATE' not in response.text and '/local/saved-path' not in response.text
    assert calls == ['tutor', 'student'] and files(source) == original
    assert viewer.post('/api/comparison/run', json=run).status_code == 409
    assert calls == ['tutor', 'student']


def test_failure_during_run_is_saved_and_peer_still_runs(tmp_path):
    calls = []
    _, student = scripted(calls)

    def tutor(_, schema):
        calls.append('tutor')
        if len(calls) == 1:
            raise RuntimeError('PRIVATE PROVIDER DIAGNOSTIC')
        return schema(text='Try count.')

    _, _, viewer = setup(tmp_path, send=True, generate=student, generate_tutor=tutor)
    run = save(viewer)
    response = viewer.post('/api/comparison/run', json=run)
    assert response.status_code == 200
    assert response.json()['operation']['status'] == 'error'
    assert [item['status'] for item in response.json()['cases'][0]['conditions']] == ['failed', 'student-replied']
    assert 'PRIVATE' not in response.text and calls == ['tutor', 'tutor', 'student']


@pytest.mark.parametrize('target', ['source-binding', 'source-content', 'source-lock', 'run-pin', 'run-manifest', 'run-symlink', 'workspace-symlink', 'extra-run'])
def test_stale_or_changed_paths_never_send_or_overwrite(tmp_path, target):
    calls = []
    tutor, student = scripted(calls)
    source, workspace, viewer = setup(tmp_path, send=True, generate=student, generate_tutor=tutor)
    payload = draft(viewer)
    run = save(viewer)
    if target == 'source-binding':
        payload['binding']['state_sha256'] = '0' * 64
    elif target == 'source-content':
        (source / 'step-0001.json').write_text('{}')
    elif target == 'source-lock':
        path = source / '.lock'
        path.unlink()
        path.symlink_to(tmp_path / 'outside')
    elif target == 'run-pin':
        run['comparison_sha256'] = '0' * 64
    elif target == 'run-manifest':
        path = workspace / 'run-0001' / 'comparison.json'
        path.write_bytes(path.read_bytes() + b' ')
    elif target == 'run-symlink':
        path = workspace / 'run-0001'
        path.rename(tmp_path / 'moved')
        path.symlink_to(tmp_path / 'moved', target_is_directory=True)
    elif target == 'workspace-symlink':
        workspace.rename(tmp_path / 'moved')
        workspace.symlink_to(tmp_path / 'moved', target_is_directory=True)
    else:
        (workspace / 'run-0002').mkdir()
    before = files(tmp_path)
    response = viewer.post('/api/comparison' if target.startswith('source-') else '/api/comparison/run',
                           json=payload if target.startswith('source-') else run)
    assert response.status_code == 409
    assert calls == [] and files(tmp_path) == before and str(tmp_path) not in response.text


def test_source_changes_do_not_block_frozen_outcomes(tmp_path):
    calls = []
    tutor, student = scripted(calls)
    source, _, viewer = setup(tmp_path, send=True, generate=student, generate_tutor=tutor)
    run = save(viewer)
    (source / 'step-0001.json').write_text('{}')
    packet = viewer.get('/api/comparison').json()
    assert packet['controls']['sources'] == [] and len(packet['cases']) == 1
    assert packet['cases'][0]['source'] is None
    assert 'no longer eligible' in packet['cases'][0]['reuse_unavailable_reason']
    assert viewer.post('/api/comparison/run', json=run).status_code == 200
    assert len(calls) == 4


def test_mutations_share_one_lock_and_polling_does_not_resend(tmp_path):
    entered, release = Event(), Event()
    calls = []
    _, student = scripted(calls)

    def tutor(_, schema):
        calls.append('tutor')
        entered.set()
        assert release.wait(10)
        return schema(text='Use count.')

    _, _, viewer = setup(tmp_path, send=True, generate=student, generate_tutor=tutor)
    payload = draft(viewer)
    run = save(viewer)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(viewer.post, '/api/comparison/run', json=run)
        try:
            assert entered.wait(10)
            pending = viewer.get('/api/comparison')
            assert pending.status_code == 202
            assert pending.json()['operation']['comparison_id'] == run['comparison_id']
            assert pending.json()['operation']['status'] == 'running'
            assert viewer.get('/api/workspace').status_code == 202
            assert viewer.post('/api/comparison/run', json=run).status_code == 409
            assert viewer.post('/api/comparison', json=payload).status_code == 409
            assert viewer.post('/api/continue', json={'binding':payload['binding'], 'mode':'reply', 'text':'hint'}).status_code == 409
            assert calls == ['tutor']
        finally:
            release.set()
        assert future.result().status_code == 200
    assert calls == ['tutor', 'student', 'tutor', 'student']


def test_unsaved_failure_is_reported_honestly(tmp_path, monkeypatch):
    _, _, viewer = setup(tmp_path, send=True)
    run = save(viewer)

    def fail(*_, **__):
        raise OSError('PRIVATE /local/path')

    monkeypatch.setattr(browser.policy_comparison_setup, 'run_both', fail)
    response = viewer.post('/api/comparison/run', json=run)
    assert response.status_code == 409 and 'PRIVATE' not in response.text
    packet = viewer.get('/api/comparison').json()
    assert packet['operation']['status'] == 'error'
    assert all(condition['status'] == 'ready' for condition in packet['cases'][0]['conditions'])


def test_startup_registration_strict_inputs_and_collection_catalog(tmp_path):
    source, workspace, viewer = setup(tmp_path)
    run = save(viewer)
    viewer = TestClient(browser.create_app(source.parent, chat_sessions=True, policy_workspace=workspace),
                        base_url='http://127.0.0.1')
    packet = viewer.get('/api/comparison').json()
    assert packet['cases'][0]['id'] == run['comparison_id']
    assert len(packet['controls']['sources']) == 1
    assert packet['controls']['sources'][0]['id'] in {item['id'] for item in viewer.get('/api/scenarios').json()['scenarios']}
    assert packet['cases'][0]['source']['id'] == packet['controls']['sources'][0]['id']
    payload = draft(viewer)
    assert viewer.post('/api/comparison', json=payload | {'folder':'private'}).status_code == 422
    assert viewer.post('/api/comparison', json=payload | {'source_id':'0' * 64}).status_code == 400
    assert viewer.post('/api/comparison', json=payload | {'proposed_policy':payload['current_policy']}).status_code == 422
    assert viewer.post('/api/comparison?scenario=x', json=payload).status_code == 400
    assert viewer.post('/api/comparison', json=payload, headers={'Origin':'https://other.invalid'}).status_code == 403
    assert viewer.get('/api/comparison?folder=private').status_code == 400


def test_reuse_requires_unique_exact_source_identity_and_workspace_drafts_are_scoped(tmp_path):
    source, workspace, viewer = setup(tmp_path)
    save(viewer)
    first_id = viewer.get('/api/scenarios').json()['workspace_id']
    reopened = TestClient(browser.create_app(source, chat_mode=True, policy_workspace=workspace),
                          base_url='http://127.0.0.1')
    assert reopened.get('/api/scenarios').json()['workspace_id'] == first_id
    different = TestClient(browser.create_app(source, chat_mode=True, policy_workspace=tmp_path / 'other'),
                           base_url='http://127.0.0.1')
    assert different.get('/api/scenarios').json()['workspace_id'] != first_id
    # Same visible question in a different session must never stand in for the original.
    chat_demo.create(tmp_path / 'unrelated')
    unrelated = TestClient(browser.create_app(tmp_path / 'unrelated' / 'source', chat_mode=True,
                           policy_workspace=workspace), base_url='http://127.0.0.1')
    case = unrelated.get('/api/comparison').json()['cases'][0]
    assert case['source'] is None and 'no longer eligible' in case['reuse_unavailable_reason']
    # Two byte-identical copies are ambiguous, even though their bindings match.
    shutil.copytree(source, source.parent / 'duplicate')
    ambiguous = TestClient(browser.create_app(source.parent, chat_sessions=True, policy_workspace=workspace),
                           base_url='http://127.0.0.1')
    before = files(tmp_path)
    response = ambiguous.get('/api/comparison')
    assert response.json()['cases'][0]['source'] is None
    assert 'Several saved starts' in response.json()['cases'][0]['reuse_unavailable_reason']
    assert str(tmp_path) not in response.text and files(tmp_path) == before


def test_cli_mode_is_explicit_and_mutually_exclusive(tmp_path, monkeypatch):
    import uvicorn

    source, workspace, _ = setup(tmp_path)
    with pytest.raises(ValueError, match='requires a chat'):
        browser.create_app(source, policy_workspace=workspace)
    with pytest.raises(ValueError, match='one comparison'):
        browser.create_app(source, chat_mode=True, policy_workspace=workspace, policy_comparison=workspace)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **_: apps.append(app))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(source), '--chat', '--policy-workspace', str(workspace)])
    browser.main()
    viewer = TestClient(apps[0], base_url='http://127.0.0.1')
    assert viewer.get('/api/comparison').json()['controls']['send_enabled'] is False
