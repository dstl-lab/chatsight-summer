"""Recorded starts must exclude targets and open offline without rewriting sources."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_student as chat
from tests.test_retrieval_baseline import example


def test_recorded_query_cli_opens_exact_prefix_without_targets(tmp_path):
    assert importlib.util.find_spec('src.agents.recorded_chat'), 'Offline recorded-query importer is missing'
    source, folder = tmp_path / 'inputs.json', tmp_path / 'chat'
    query = example('q', '  你好\n x = 2\n')
    source.write_text(json.dumps({'train': [example('a', 'work', 'SECRET TRAINING ANSWER')],
                                 'queries': [example('z', 'other'), query]}))
    before = source.read_bytes()
    # A malformed sibling deliberately proves the importer never reads hidden references.
    (tmp_path / 'references.json').write_text('not JSON: SECRET NEXT ANSWER')
    command = [sys.executable, '-m', 'src.agents.recorded_chat']
    listed = subprocess.run([*command, 'list', str(source)], text=True, capture_output=True)
    assert listed.returncode == 0, listed.stderr
    catalog = json.loads(listed.stdout)
    assert [row['id'] for row in catalog['queries']] == ['q', 'z']
    assert catalog['queries'][0]['turns'] == 2
    assert '你好' not in listed.stdout and 'SECRET' not in listed.stdout
    create = [*command, 'create', str(source), str(folder), '--query-id', 'q',
              '--input-sha256', catalog['input_sha256'], '--model', 'authored-local-model',
              '--max-decisions', '3']
    made = subprocess.run(create, text=True, capture_output=True)
    assert made.returncode == 0, made.stderr
    session = json.loads((folder / 'session.json').read_text())
    assert session['query'] == query and session['max_decisions'] == 3
    receipt = json.loads((folder / 'recorded-start.json').read_text())
    assert receipt['input_sha256'] == sha256(before).hexdigest()
    assert receipt['query_id'] == 'q' and receipt['split'] == 'queries'
    assert receipt['session_sha256'] == chat.show(folder)['binding']['session_sha256']
    assert 'SECRET' not in ''.join(p.read_text() for p in folder.iterdir() if p.is_file())
    original = {p.name: p.read_bytes() for p in folder.iterdir()}
    client = TestClient(browser.create_app(folder, chat_mode=True), base_url='http://127.0.0.1')
    response = client.get('/api/workspace')
    assert response.status_code == 200, response.text
    frame = response.json()['encounters'][0]['frames'][0]
    assert [{k: t[k] for k in ('role', 'text')} for t in frame['dialogue']] == query['prefix']
    assert client.post('/api/continue', json={'binding': frame['binding'], 'mode': 'advance'}).status_code == 403
    assert subprocess.run(create, capture_output=True).returncode != 0
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == original
    assert source.read_bytes() == before and not list(folder.glob('step-*'))


def test_import_rejects_leakage_changed_input_and_unknown_selection(tmp_path):
    from src.agents import recorded_chat as recorded
    source, folder = tmp_path / 'inputs.json', tmp_path / 'chat'
    base = {'train': [example('a', 'work', 'TARGET')], 'queries': [example('q', 'question')]}
    mutations = [
        lambda p: p['queries'][0].update(response='HIDDEN TARGET'),
        lambda p: p['queries'][0].update(conversation_id='a'),
        lambda p: p['queries'][0].update(id='a'),
        lambda p: (p['train'][0].update(student_id='s'), p['queries'][0].update(student_id='s')),
        lambda p: p['train'].append(example('a', 'other', 'TARGET')),
    ]
    for mutate in mutations:
        value = deepcopy(base)
        mutate(value)
        source.write_text(json.dumps(value))
        with pytest.raises(ValueError) as error:
            recorded.catalog(source)
        assert 'TARGET' not in str(error.value)
        with pytest.raises(ValueError):
            recorded.create(source, folder, query_id='q', input_sha256=sha256(source.read_bytes()).hexdigest(),
                            model='authored-local-model')
        assert not folder.exists()
    source.write_text(json.dumps(base))
    digest = recorded.catalog(source)['input_sha256']
    for identifier, expected_hash in [('absent', digest), ('q', '0' * 64)]:
        with pytest.raises(ValueError):
            recorded.create(source, folder, query_id=identifier, input_sha256=expected_hash,
                            model='authored-local-model')
        assert not folder.exists()
    folder.mkdir()
    with pytest.raises(FileExistsError):
        recorded.create(source, folder, query_id='q', input_sha256=digest, model='authored-local-model')
    assert list(folder.iterdir()) == []


def test_changed_source_during_preparation_leaves_no_partial_session(tmp_path, monkeypatch):
    from src.agents import recorded_chat as recorded
    source, folder = tmp_path / 'inputs.json', tmp_path / 'chat'
    source.write_text(json.dumps({'train': [example('a', 'work', 'TARGET')],
                                 'queries': [example('q', 'question')]}))
    digest = recorded.catalog(source)['input_sha256']
    show = chat.show
    def changed(path):
        result = show(path)
        source.write_text('{}')
        return result
    monkeypatch.setattr(chat, 'show', changed)
    with pytest.raises(ValueError, match='changed'):
        recorded.create(source, folder, query_id='q', input_sha256=digest, model='authored-local-model')
    assert not folder.exists() and sorted(p.name for p in tmp_path.iterdir()) == ['inputs.json']


def test_publish_reserves_destination_before_directory_replacement(tmp_path, monkeypatch):
    from pathlib import Path
    import os
    from src.agents import recorded_chat as recorded
    source, folder = tmp_path / 'inputs.json', tmp_path / 'chat'
    source.write_text(json.dumps({'train': [example('a', 'work', 'TARGET')],
                                 'queries': [example('q', 'question')]}))
    digest = recorded.catalog(source)['input_sha256']
    replace = os.replace
    competing = []
    def publish(staged, destination):
        if Path(destination) == folder and not folder.exists():
            # Another creator wins after the existence check but before publication.
            folder.mkdir()
            competing.append(folder.stat().st_ino)
        return replace(staged, destination)
    monkeypatch.setattr(Path, 'rename', publish)
    monkeypatch.setattr(os, 'replace', publish)
    try:
        recorded.create(source, folder, query_id='q', input_sha256=digest, model='authored-local-model')
    except FileExistsError:
        pass
    if competing:
        assert folder.stat().st_ino == competing[0] and list(folder.iterdir()) == []
    else:
        assert chat.show(folder)['decisions'] == 0
