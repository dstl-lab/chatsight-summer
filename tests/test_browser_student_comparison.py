"""Saved student model replies open without enabling a simulator or rereading paths."""
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser
from tests.test_chat_student import files


def test_student_comparison_refuses_sending_or_unrelated_session(tmp_path):
    for options in ({'send': True}, {'folder': tmp_path}, {'chat_mode': True},
                    {'chat_sessions': True}, {'policy': 'Send a hint'}, {'reference': {}},
                    {'fidelity_comparison': tmp_path}, {'policy_workspace': tmp_path}):
        with pytest.raises(ValueError):
            browser.create_app(student_comparison=tmp_path, **options)


def test_saved_models_display_exact_replies_and_fail_closed_without_writes(tmp_path):
    from tests.test_student_reply_comparison import write_bundle

    bundle = write_bundle(tmp_path)
    before = files(tmp_path)
    viewer = TestClient(browser.create_app(student_comparison=bundle), base_url='http://127.0.0.1')
    catalog = viewer.get('/api/scenarios').json()
    assert catalog['student_comparison_available'] is True and catalog['replay_available'] is False
    assert catalog['scenarios'] == []
    response = viewer.get('/api/comparison')
    assert response.status_code == 200
    data = response.json()
    assert data['kind'] == 'saved-student-reply-comparison' and len(data['cases']) == 2
    assert str(tmp_path) not in response.text
    for case in data['cases']:
        assert [condition['id'] for condition in case['conditions']] == ['base', 'full']
        assert 'reference' not in case and 'scores' not in case
        for turns in case['prefix'].values():
            for turn in turns:
                assert ('display_html' in turn) == (turn['role'] == 'tutor')
    assert viewer.get('/api/workspace').status_code == 404
    assert viewer.post('/api/continue', json={'binding': {'session_sha256': '0' * 64,
        'state_sha256': '0' * 64}, 'mode': 'advance'}).status_code == 404
    assert viewer.post('/api/comparison', json={}).status_code == 405
    assert viewer.post('/api/comparison/run', json={}).status_code == 404
    assert viewer.get('/api/comparison?folder=elsewhere').status_code == 400
    assert viewer.get('/api/comparison', headers={'Origin': 'http://elsewhere.example'}).status_code == 403
    assert files(tmp_path) == before
    path = bundle / 'calls/case-01/full/result.json'
    path.write_bytes(path.read_bytes() + b' ')
    changed = files(tmp_path)
    failed = viewer.get('/api/comparison')
    assert failed.status_code == 409 and 'cases' not in failed.json()
    assert str(tmp_path) not in failed.text
    assert files(tmp_path) == changed


def test_student_comparison_cli_opens_saved_bundle_only(tmp_path, monkeypatch):
    import uvicorn
    from tests.test_student_reply_comparison import write_bundle

    bundle = write_bundle(tmp_path)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **_: apps.append(app))
    argv = ['browser_workspace', '--student-comparison', str(bundle)]
    monkeypatch.setattr(sys, 'argv', argv)
    browser.main()
    assert TestClient(apps[0], base_url='http://127.0.0.1').get('/api/comparison').status_code == 200
    for extra in (['--send'], ['--chat'], ['--policy-workspace', str(bundle)],
                  ['--student-model', str(bundle), '--student-python', sys.executable]):
        monkeypatch.setattr(sys, 'argv', argv + extra)
        with pytest.raises(SystemExit) as error:
            browser.main()
        assert error.value.code == 2
    assert len(apps) == 1
