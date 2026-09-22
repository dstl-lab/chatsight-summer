"""Collection requests select one verified scenario without sharing client selection."""
from concurrent.futures import ThreadPoolExecutor
import fcntl
import sys
from threading import Event

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace as browser, chat_student as chat, notebook_student as store
from tests.test_chat_student import QUERY, files


def sessions(tmp_path):
    root = tmp_path / 'scenarios'
    root.mkdir()
    for name in ('private-a', 'private-b'):
        chat.create(root / name, query=QUERY)
        chat.show(root / name)
    return root


def client(root, **options):
    return TestClient(browser.create_app(root, chat_sessions=True, **options), base_url='http://127.0.0.1')


def selected(name, route='/api/workspace'):
    return route + '?scenario=' + store.digest(name)


def body(folder):
    return {'binding':chat.show(folder)['binding'], 'mode':'advance'}


def test_catalog_has_verified_literal_excerpts_and_reads_do_not_modify_sessions(tmp_path):
    root = sessions(tmp_path)
    (root / 'linked').symlink_to(root / 'private-a', target_is_directory=True)
    (root / 'linked-manifest').mkdir()
    (root / 'linked-manifest' / 'session.json').symlink_to(root / 'private-a' / 'session.json')
    viewer = client(root)
    before = {name:files(root / name) for name in ('private-a', 'private-b')}
    catalog = viewer.get('/api/scenarios')
    assert catalog.status_code == 200
    assert catalog.json() == {'version':1, 'workspace_id':catalog.json()['workspace_id'], 'scenarios':[
        {'id':store.digest(name), 'title':f'Conversation {index:02d}', 'summary':'how do i add them'}
        for index, name in enumerate(('private-a', 'private-b'), 1)]}
    assert len(catalog.json()['workspace_id']) == 64
    assert 'private-' not in catalog.text and str(root) not in catalog.text
    shown = viewer.get(selected('private-a')).json()
    assert shown['scenario_id'] == store.digest('private-a')
    assert shown['kind'] == 'chat' and shown['controls']['send_enabled'] is False
    assert shown['encounters'][0]['title'] == 'Conversation 01'
    assert {name:files(root / name) for name in before} == before
    chat.create(root / 'later', query=QUERY)
    assert viewer.get('/api/scenarios').json() == catalog.json()
    assert viewer.get(selected('later')).status_code == 400
    assert viewer.post(selected('private-a', '/api/continue'), json=body(root / 'private-a')).status_code == 403


def test_clients_select_independently_and_binding_cannot_cross_scenarios(tmp_path):
    root = sessions(tmp_path)
    calls = []

    def generate(_, schema):
        calls.append('student')
        return schema(decision='no-reply', text='')

    app = browser.create_app(root, chat_sessions=True, send=True, generate=generate)
    first, second = [TestClient(app, base_url='http://127.0.0.1') for _ in range(2)]
    packet_a = first.get(selected('private-a')).json()
    packet_b = second.get(selected('private-b')).json()
    request = {'binding':packet_a['encounters'][0]['frames'][-1]['binding'], 'mode':'advance'}
    assert second.post(selected('private-b', '/api/continue'), json=request).status_code == 409
    assert calls == [] and not list((root / 'private-b').glob('step-*.json'))
    sent = first.post(selected('private-a', '/api/continue'), json=request)
    assert sent.status_code == 200 and sent.json()['scenario_id'] == store.digest('private-a')
    assert sent.json()['operation']['status'] == 'complete' and calls == ['student']
    assert second.get(selected('private-b')).json() == packet_b
    assert second.get(selected('private-a')).json() == sent.json()


def test_unknown_duplicate_and_extra_selectors_never_dispatch(tmp_path):
    root = sessions(tmp_path)
    viewer = client(root, send=True, generate=lambda *_: pytest.fail('Unexpected dispatch'))
    request = body(root / 'private-a')
    for query in ('', '?scenario=', '?scenario=private-a', '?scenario=../private-a',
                  '?scenario=' + 'f' * 64, '?folder=private-a',
                  '?scenario=' + store.digest('private-a') + '&extra=1',
                  '?scenario=' + store.digest('private-a') + '&scenario=' + store.digest('private-b')):
        assert viewer.get('/api/workspace' + query).status_code == 400
        assert viewer.post('/api/continue' + query, json=request).status_code == 400
    assert viewer.get('/api/scenarios?extra=1').status_code == 400
    single = TestClient(browser.create_app(root / 'private-a', chat_mode=True), base_url='http://127.0.0.1')
    catalog = single.get('/api/scenarios').json()
    assert catalog == {'version':1, 'workspace_id':catalog['workspace_id'], 'scenarios':[]}
    assert single.get('/api/workspace').json()['scenario_id'] is None
    assert single.get(selected('private-a')).status_code == 400


@pytest.mark.parametrize('target', ['folder', 'session.json', '.lock', 'step-0001.json', 'tutor-exchanges'])
def test_replaced_symlink_is_refused_then_selection_recovers(tmp_path, target):
    root = sessions(tmp_path)
    folder = root / 'private-a'
    if target == 'step-0001.json':
        chat.step(folder, binding=chat.show(folder)['binding'],
                  generate=lambda _, schema: schema(decision='reply', text='7?'))
    if target == 'tutor-exchanges':
        (folder / target).mkdir()
    request = body(folder)
    viewer = client(root, send=True, generate=lambda *_: pytest.fail('Unexpected dispatch'))
    original = folder if target == 'folder' else folder / target
    outside = tmp_path / 'outside'
    original.rename(outside)
    original.symlink_to(outside, target_is_directory=target in ('folder', 'tutor-exchanges'))
    try:
        for response in (viewer.get(selected('private-a')),
                         viewer.post(selected('private-a', '/api/continue'), json=request)):
            assert response.status_code == 409 and str(tmp_path) not in response.text
            assert 'encounters' not in response.json()
        assert [item['summary'] for item in viewer.get('/api/scenarios').json()['scenarios']] == [
            None, 'how do i add them']
        assert viewer.get(selected('private-b')).status_code == 200
    finally:
        original.unlink()
        outside.rename(original)
    assert viewer.get(selected('private-a')).status_code == 200


def test_invalid_or_uninitialized_scenario_does_not_break_other_selection(tmp_path):
    root = sessions(tmp_path)
    chat.create(root / 'uninitialized', query=QUERY)
    manifest = root / 'private-a' / 'session.json'
    manifest.write_text('{}')
    viewer = client(root)
    before = files(root / 'uninitialized')
    assert viewer.get(selected('private-a')).status_code == 409
    assert viewer.get(selected('uninitialized')).status_code == 409
    assert files(root / 'uninitialized') == before and not (root / 'uninitialized' / '.lock').exists()
    assert viewer.get(selected('private-b')).status_code == 200
    summaries = {item['id']:item['summary'] for item in viewer.get('/api/scenarios').json()['scenarios']}
    assert summaries == {store.digest('private-a'):None, store.digest('private-b'):'how do i add them',
                         store.digest('uninitialized'):None}


def test_catalog_busy_source_does_not_hide_other_excerpts_or_touch_locks(tmp_path):
    root = sessions(tmp_path)
    viewer = client(root)
    before = files(root)
    lock = root / 'private-a' / '.lock'
    metadata = lock.stat()
    with lock.open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert [item['summary'] for item in viewer.get('/api/scenarios').json()['scenarios']] == [
            None, 'how do i add them']
    assert files(root) == before
    assert lock.stat().st_mtime_ns == metadata.st_mtime_ns
    binding = chat.show(root / 'private-a')['binding']
    question = '  does\nthis\twork ' + 'x' * 200
    chat.step(root / 'private-a', binding=binding,
              generate=lambda _, schema: schema(decision='reply', text=question))
    excerpt = viewer.get('/api/scenarios').json()['scenarios'][0]['summary']
    assert excerpt == ' '.join(question.split())[:160] + '…'


def test_pending_and_failed_operation_stay_scoped_to_requested_scenario(tmp_path):
    root = sessions(tmp_path)
    started, finish = Event(), Event()

    def fail(*_):
        started.set()
        assert finish.wait(10)
        raise RuntimeError('PRIVATE_PROVIDER_DIAGNOSTIC')

    viewer = client(root, send=True, generate=fail)
    request_a, request_b = body(root / 'private-a'), body(root / 'private-b')
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(viewer.post, selected('private-a', '/api/continue'), json=request_a)
        try:
            assert started.wait(5)
            response = viewer.get(selected('private-b'))
            assert response.status_code == 202
            assert response.json()['scenario_id'] == store.digest('private-b')
            assert response.json()['operation']['status'] == 'running'
            assert 'encounters' not in response.json()
            assert viewer.post(selected('private-b', '/api/continue'), json=request_b).status_code == 409
        finally:
            finish.set()
        result = pending.result(timeout=5)
    assert result.status_code == 200 and result.json()['operation']['status'] == 'error'
    assert 'PRIVATE_PROVIDER_DIAGNOSTIC' not in result.text
    assert viewer.get(selected('private-b')).json()['operation']['status'] == 'idle'
    assert viewer.get(selected('private-a')).json()['operation']['status'] == 'error'


def test_cli_collection_and_incompatible_options(tmp_path, monkeypatch):
    import uvicorn

    root = sessions(tmp_path)
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **options: apps.append(app))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(root), '--chat-sessions'])
    browser.main()
    viewer = TestClient(apps[0], base_url='http://127.0.0.1')
    assert len(viewer.get('/api/scenarios').json()['scenarios']) == 2
    assert viewer.get(selected('private-a')).json()['controls']['send_enabled'] is False
    for options in (['--chat'], ['--reference-file', 'does-not-exist.json']):
        monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(root), '--chat-sessions', *options])
        with pytest.raises(SystemExit) as error:
            browser.main()
        assert error.value.code == 2
    assert len(apps) == 1
    with pytest.raises(ValueError, match='chat'):
        browser.create_app(root, chat_sessions=True, chat_mode=True)
    with pytest.raises(ValueError, match='reference'):
        browser.create_app(root, chat_sessions=True, reference={})
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(ValueError, match='scenario'):
        browser.create_app(empty, chat_sessions=True)
