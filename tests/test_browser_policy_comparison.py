"""Authored policy pairs share Compare without changing their saved evidence."""
import json
import sys
import fcntl

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_demo, chat_policy_pair as pair
from tests.test_chat_student import files


def setup_pair(tmp_path, *, completed=True):
    chat_demo.create(tmp_path / 'demo')
    source = tmp_path / 'demo' / 'source'
    destination = tmp_path / 'demo' / 'comparison'
    if not completed:
        destination = tmp_path / 'ready'
        pair.create(destination, source=source, policies={'a':'Give a hint.', 'b':'Give the answer.'})
    return source, destination


@pytest.mark.parametrize('completed', [False, True])
def test_policy_pair_is_read_only_and_distinguishes_cached_start_from_result(tmp_path, completed):
    source, destination = setup_pair(tmp_path, completed=completed)
    before = files(tmp_path)
    viewer = TestClient(browser.create_app(source, chat_mode=True, policy_comparison=destination),
                        base_url='http://127.0.0.1')
    assert viewer.get('/api/scenarios').json()['comparison_available'] is True
    response = viewer.get('/api/comparison')
    assert response.status_code == 200
    assert response.json()['kind'] == 'saved-policy-comparison'
    case = response.json()['cases'][0]
    assert case['prefix']['turns'] == [
        {'role':'student', 'text':'how do i count that', 'origin':'generated'}]
    assert case['conditions'][0]['status'] == ('student-replied' if completed else 'ready')
    assert case['conditions'][1]['status'] == ('no-follow-up' if completed else 'ready')
    if completed:
        assert case['conditions'][0]['student_reply'] == "colors.count('teal')?"
        assert case['conditions'][1]['student_reply'] is None
        assert 'count method' in case['conditions'][0]['tutor_reply']
    else:
        assert all(c['student_reply'] is None and c['tutor_reply'] is None for c in case['conditions'])
    assert str(tmp_path) not in response.text
    assert viewer.post('/api/comparison', json={}).status_code == 405
    assert viewer.get('/api/comparison?folder=elsewhere').status_code == 400
    assert viewer.get('/api/workspace').json()['controls']['send_enabled'] is False
    assert files(tmp_path) == before


def test_failed_tutor_retains_shared_start_and_peer_without_exposing_diagnostics(tmp_path):
    source, destination = setup_pair(tmp_path, completed=False)
    binding = pair.show(destination)['conditions']['a']['snapshot']['binding']

    def fail(*_):
        raise RuntimeError('PRIVATE DIAGNOSTIC /private/local/path')

    with pytest.raises(RuntimeError):
        pair.respond(destination, 'a', binding=binding, send=True, generate_tutor=fail)
    before = files(tmp_path)
    viewer = TestClient(browser.create_app(source, chat_mode=True, policy_comparison=destination),
                        base_url='http://127.0.0.1')
    response = viewer.get('/api/comparison')
    assert response.status_code == 200
    case = response.json()['cases'][0]
    assert case['conditions'][0]['status'] == 'failed'
    assert case['conditions'][1]['status'] == 'ready'
    assert case['prefix']['turns'][0]['text'] == 'how do i count that'
    assert 'PRIVATE DIAGNOSTIC' not in response.text and '/private/local/path' not in response.text
    assert files(tmp_path) == before


@pytest.mark.parametrize('stage', ['tutor', 'student'])
def test_unfinished_request_is_not_silence_and_busy_reads_do_not_write(tmp_path, stage):
    source, destination = setup_pair(tmp_path, completed=False)
    binding = pair.show(destination)['conditions']['a']['snapshot']['binding']

    def interrupted(*_):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        pair.respond(destination, 'a', binding=binding, send=True,
                     generate_tutor=interrupted if stage == 'tutor' else lambda _, schema: schema(text='Saved hint.'),
                     generate_student=interrupted)
    viewer = TestClient(browser.create_app(source, chat_mode=True, policy_comparison=destination),
                        base_url='http://127.0.0.1')
    before = files(tmp_path)
    response = viewer.get('/api/comparison')
    assert response.status_code == 200
    condition = response.json()['cases'][0]['conditions'][0]
    assert condition['status'] == 'incomplete' and condition['student_reply'] is None
    assert condition['tutor_reply'] == ('Saved hint.' if stage == 'student' else None)
    with (destination / 'sessions' / 'a' / '.lock').open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert viewer.get('/api/comparison').status_code == 409
    assert files(tmp_path) == before


@pytest.mark.parametrize('change', ['manifest', 'prompt', 'symlink', 'missing-lock', 'binding-path'])
def test_changed_policy_evidence_is_hidden_without_writes_or_path_traversal(tmp_path, change):
    source, destination = setup_pair(tmp_path)
    viewer = TestClient(browser.create_app(source, chat_mode=True, policy_comparison=destination),
                        base_url='http://127.0.0.1')
    assert viewer.get('/api/comparison').status_code == 200
    child = destination / 'sessions' / 'a'
    if change == 'manifest':
        path = destination / 'comparison.json'
        path.write_bytes(path.read_bytes() + b' ')
    elif change in ('prompt', 'binding-path'):
        path = child / 'step-0002.json'
        receipt = json.loads(path.read_text())
        if change == 'prompt':
            receipt['request']['prompt'] = 'tampered'
        else:
            receipt['request']['binding']['state_sha256'] = '../../outside'
        path.write_text(json.dumps(receipt))
    elif change == 'missing-lock':
        (child / '.lock').unlink()
    else:
        path = child / 'step-0002.json'
        outside = tmp_path / 'outside.json'
        path.rename(outside)
        path.symlink_to(outside)
    before = files(tmp_path)
    response = viewer.get('/api/comparison')
    assert response.status_code == 409 and 'cases' not in response.json()
    assert str(tmp_path) not in response.text
    assert files(tmp_path) == before


def test_policy_pair_cli_is_explicit_and_mutually_exclusive(tmp_path, monkeypatch):
    import uvicorn

    source, destination = setup_pair(tmp_path)
    with pytest.raises(ValueError, match='one comparison'):
        browser.create_app(source, chat_mode=True, policy_comparison=destination, comparison=destination)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **_: apps.append(app))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(source), '--chat',
                                    '--policy-comparison', str(destination)])
    browser.main()
    viewer = TestClient(apps[0], base_url='http://127.0.0.1')
    assert viewer.get('/api/comparison').json()['kind'] == 'saved-policy-comparison'
    assert viewer.get('/api/workspace').json()['controls']['send_enabled'] is False
