"""The new unexecuted message must never borrow an older matching-source result."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import pytest

from apps.archive_message_preview import create_app, project
from src.agents import archived_notebook as archive, notebook_student as store
from tests.test_archived_notebook import prepared, action, no_execution
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
