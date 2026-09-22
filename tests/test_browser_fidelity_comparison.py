"""The fixed student benchmark is inspectable without a replay or a new request."""
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_student
from tests.test_chat_student import QUERY, files
from tests.test_fidelity_comparison import write_bundle


def client(**options):
    return TestClient(browser.create_app(**options), base_url='http://127.0.0.1')


def test_benchmark_only_is_read_only_and_has_no_unrelated_replay(tmp_path):
    benchmark = write_bundle(tmp_path)
    before = files(tmp_path)
    viewer = client(fidelity_comparison=benchmark,
                    generate=lambda *_: pytest.fail('Student dispatch'),
                    generate_tutor=lambda *_: pytest.fail('Tutor dispatch'))
    catalog = viewer.get('/api/scenarios').json()
    assert catalog == {'version': 1, 'workspace_id': catalog['workspace_id'], 'scenarios': [],
                       'comparison_available': True, 'fidelity_comparison_available': True,
                       'replay_available': False}
    assert str(tmp_path) not in str(catalog)
    response = viewer.get('/api/comparison')
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['kind'] == 'saved-student-fidelity-comparison' and len(data['cases']) == 8
    assert data['study']['counts']['scheduled_draws'] == 64
    assert all(len(condition['draws']) == 4 for case in data['cases'] for condition in case['conditions'])
    for case in data['cases']:
        for turns in case['prefix'].values():
            for turn in turns:
                if turn['role'] == 'tutor':
                    assert turn['display_html'] == browser._tutor_html(turn['text'])
                else:
                    assert 'display_html' not in turn
        assert all('tutor_html' not in condition for condition in case['conditions'])
    assert str(tmp_path) not in response.text
    assert viewer.get('/api/comparison').json() == data
    assert viewer.get('/api/workspace').status_code == 404
    assert viewer.get('/api/workspace?scenario=anything').status_code == 404
    assert viewer.post('/api/continue', json={'binding': {'session_sha256': '0' * 64,
        'state_sha256': '0' * 64}, 'mode': 'advance'}).status_code == 404
    assert viewer.post('/api/comparison', json={}).status_code == 405
    assert viewer.post('/api/comparison/run', json={}).status_code == 404
    assert viewer.get('/api/comparison?folder=elsewhere').status_code == 400
    assert viewer.get('/api/scenarios?scenario=anything').status_code == 400
    assert viewer.get('/api/comparison', headers={'Origin': 'http://evil.example'}).status_code == 403
    assert files(tmp_path) == before


def test_fidelity_companion_keeps_replay_independent_and_rejects_changed_evidence(tmp_path):
    benchmark = write_bundle(tmp_path)
    session = tmp_path / 'session'
    chat_student.create(session, query=QUERY)
    chat_student.show(session)
    legacy = client(folder=session, chat_mode=True)
    assert legacy.get('/api/scenarios').json()['workspace_id'] == browser.student.digest(
        [str(session.resolve()), None, None, None])
    viewer = client(folder=session, chat_mode=True, fidelity_comparison=benchmark)
    assert viewer.get('/api/scenarios').json()['replay_available'] is True
    replay = viewer.get('/api/workspace').json()
    assert replay['controls']['send_enabled'] is False
    assert viewer.get('/api/comparison').status_code == 200
    path = benchmark / 'inputs.json'
    original = path.read_bytes()
    path.write_bytes(original + b' ')
    before = files(tmp_path)
    response = viewer.get('/api/comparison')
    assert response.status_code == 409 and 'cases' not in response.json()
    assert str(tmp_path) not in response.text
    assert viewer.get('/api/workspace').json() == replay
    assert files(tmp_path) == before
    path.write_bytes(original)
    assert viewer.get('/api/comparison').status_code == 200


def test_configuration_requires_a_benchmark_or_session_and_one_comparison(tmp_path, monkeypatch):
    import uvicorn

    benchmark = write_bundle(tmp_path)
    with pytest.raises(ValueError, match='session folder'):
        browser.create_app()
    for options in ({'chat_mode': True}, {'chat_sessions': True}, {'send': True},
                    {'policy': 'Tutor instructions'}, {'reference': {}}):
        with pytest.raises(ValueError, match='session folder'):
            browser.create_app(fidelity_comparison=benchmark, **options)
    for name in ('comparison', 'policy_comparison', 'policy_workspace'):
        with pytest.raises(ValueError, match='one comparison'):
            browser.create_app(fidelity_comparison=benchmark, **{name: benchmark})
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **_: apps.append(app))
    command = ['browser_workspace', '--fidelity-comparison', str(benchmark)]
    monkeypatch.setattr(sys, 'argv', command)
    browser.main()
    assert TestClient(apps[0], base_url='http://127.0.0.1').get('/api/comparison').status_code == 200
    for options in (['--chat'], ['--chat-sessions'], ['--send'],
                    ['--policy-file', 'does-not-exist.txt'], ['--reference-file', 'does-not-exist.json'],
                    ['--comparison', str(benchmark)], ['--policy-comparison', str(benchmark)],
                    ['--policy-workspace', str(benchmark)]):
        monkeypatch.setattr(sys, 'argv', command + options)
        with pytest.raises(SystemExit) as exc:
            browser.main()
        assert exc.value.code == 2
    assert len(apps) == 1
