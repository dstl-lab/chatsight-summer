"""Recorded observations use the existing browser shell without simulation actions."""
from hashlib import sha256
import json

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace, notebook_student
from src.eval import notebook_runtime
from tests.test_notebook_replay import recorded_projection


def test_recorded_browser_preserves_prefixes_and_readonly_boundary(tmp_path, monkeypatch):
    replay = recorded_projection()
    replay['events'][1]['tutor_reply'] = '**Try** <script>unsafe()</script>'
    path = tmp_path / 'private.json'
    raw = json.dumps(replay).encode()
    path.write_bytes(raw)
    options = dict(recorded_replay=path, recorded_sha256=sha256(raw).hexdigest())
    monkeypatch.setattr(notebook_student.llm, 'make_generate', lambda *a, **k: pytest.fail('Model dispatch'))
    monkeypatch.setattr(notebook_runtime, 'check_work', lambda *a, **k: pytest.fail('Code execution'))
    monkeypatch.setattr(browser_workspace, 'snapshot', lambda *a, **k: pytest.fail('Synthetic snapshot'))
    app = browser_workspace.create_app(**options)
    browser = TestClient(app, base_url='http://127.0.0.1')
    assert browser.get('/').status_code == browser.get('/workspace.js').status_code == 200
    assert browser.get('/api/scenarios').json()['scenarios'] == []
    response = browser.get('/api/workspace')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    packet = response.json()
    assert packet['kind'] == 'recorded-notebook' and packet['default_step'] == 3
    frames = packet['encounters'][0]['frames']
    assert len(frames) == 7 and packet['recorded_summary']['boundary_sequence'] == 2
    frame = frames[3]
    assert frame['recorded']['event']['diff'] == '-x = 1\n+x = 2'
    assert frame['recorded']['notebook_capture']['cells'][0]['source'] == 'x = 1'
    assert frame['recorded']['execution']['source'] == 'x = 2'
    assert frame['recorded']['execution_result'] is None
    assert 'FUTURE_' not in json.dumps(frame)
    assert frames[4]['recorded']['execution_result']['output'] == '2'
    assert all(turn['origin'] == 'source' for turn in frame['dialogue'])
    assert '<strong>Try</strong>' in frame['dialogue'][1]['display_html']
    assert '<script>' not in frame['dialogue'][1]['display_html']
    assert not {'work', 'binding', 'decisions_remaining', 'feedback'} & frame.keys()
    assert packet['controls']['send_enabled'] is False
    assert not any('POST' in getattr(route, 'methods', ()) for route in app.routes)
    assert browser.post('/api/continue', json={}).status_code == 404
    assert browser.get('/api/workspace?scenario=elsewhere').status_code == 400
    assert browser.get('/api/workspace', headers={'Origin': 'https://elsewhere.invalid'}).status_code == 403
    assert path.read_bytes() == raw
    # No diff falls back to the prediction cutoff, not the final evidence.
    del replay['events'][3]['diff']
    assert browser_workspace._recorded_snapshot(replay)['default_step'] == 1
    for extra in ({'send': True}, {'chat_mode': True}, {'folder': tmp_path},
                  {'policy': 'hint'}, {'generate': lambda: None}, {'comparison': tmp_path}):
        with pytest.raises(ValueError, match='read-only'):
            browser_workspace.create_app(**options, **extra)
    with pytest.raises(ValueError, match='both'):
        browser_workspace.create_app(recorded_replay=path)
    path.write_bytes(raw + b' ')
    failed = browser.get('/api/workspace')
    assert failed.status_code == 409 and str(path) not in failed.text
    assert 'unsafe' not in failed.text
