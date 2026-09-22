"""Explicit browser submissions reuse bound, durable notebook operations."""
from concurrent.futures import ThreadPoolExecutor
import json
import sys
from threading import Event

from fastapi.testclient import TestClient
import pytest

from src.agents import browser_workspace, notebook_student as student, tutor_context
from tests.test_notebook_session import ACTIVITY, TASK
from tests.test_tutor_context import choose


def session(tmp_path, *, waiting=False, budget=6):
    folder = tmp_path / 'session'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/browser-controls',
                   max_decisions=budget)
    if waiting:
        choose(folder, 'reply', text='this?')
    student.load(folder)
    return folder


def client(folder, **options):
    return TestClient(browser_workspace.create_app(folder, **options), base_url='http://127.0.0.1')


def latest(packet):
    return packet['encounters'][-1]['frames'][-1]


def request(folder, mode='advance', **options):
    return {'binding': tutor_context.snapshot(folder)['binding'], 'mode': mode} | options


def test_read_only_state_validation_stale_and_terminal_guards(tmp_path):
    folder = session(tmp_path)
    calls = []

    def generate(_, schema):
        calls.append('student')
        return schema(decision='reply', text='this?', source=None)

    body = request(folder)
    viewer = client(folder)
    shown = viewer.get('/api/workspace').json()
    assert shown['controls']['send_enabled'] is False
    assert shown['operation']['status'] == 'idle'
    assert viewer.post('/api/continue', json=body).status_code == 403
    browser = client(folder, send=True, generate=generate)
    assert browser.post('/api/continue?folder=/private', json=body).status_code == 400
    assert browser.post('/api/continue', json=body, headers={'Origin':'https://other.example'}).status_code == 403
    assert browser.post('/api/continue', json=body, headers={'Sec-Fetch-Site':'cross-site'}).status_code == 403
    assert browser.post('/api/continue', json=request(folder, 'reply', text='Hint.')).status_code == 409
    assert calls == []
    sent = browser.post('/api/continue', json=body)
    assert sent.status_code == 200, sent.text
    assert latest(sent.json())['status'] == 'awaiting-tutor'
    assert sent.json()['operation']['status'] == 'complete'
    assert calls == ['student']
    assert browser.post('/api/continue', json=body).status_code == 409
    assert browser.post('/api/continue', json=request(folder)).status_code == 409
    assert calls == ['student']
    manual = request(folder, 'reply', text='Count distinct shades.')
    stopped = client(folder, send=True,
                     generate=lambda _, schema: schema(decision='no-reply', text='', source=None))
    result = stopped.post('/api/continue', json=manual)
    assert result.status_code == 200 and latest(result.json())['status'] == 'no-reply'
    assert latest(result.json())['dialogue'][-1]['text'] == manual['text']
    assert stopped.post('/api/continue', json=request(folder)).status_code == 409


@pytest.mark.parametrize('change', [
    {'folder':'/private'}, {'reference':{}}, {'mode':'unknown'}, {'binding':{}},
    {'binding':{'session_sha256':'a'*64, 'state_sha256':'B'*64}},
    {'binding':{'session_sha256':'a'*64, 'state_sha256':'b'*64, 'extra':True}},
    {'mode':'advance','text':None}, {'mode':'advance','text':'unused'},
    {'mode':'reply'}, {'mode':'policy','text':' \n '},
    {'mode':'reply','text':5}, {'mode':'policy','text':'x'*64001},
])
def test_request_shape_refused_before_dispatch(tmp_path, change):
    folder = session(tmp_path)
    browser = client(folder, send=True, generate=lambda *_: pytest.fail('Unexpected dispatch'))
    response = browser.post('/api/continue', json=request(folder) | change)
    assert response.status_code == 422, response.text
    assert not list(folder.glob('step-*.json'))


def test_pending_get_and_concurrent_post_never_repeat_dispatch(tmp_path):
    folder = session(tmp_path)
    started, finish = Event(), Event()
    calls = []

    def generate(_, schema):
        calls.append('student')
        started.set()
        assert finish.wait(10)
        return schema(decision='reply', text='this?', source=None)

    browser = client(folder, send=True, generate=generate)
    body = request(folder)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(browser.post, '/api/continue', json=body)
        try:
            assert started.wait(5)
            shown = browser.get('/api/workspace')
            assert shown.status_code == 202 and shown.json()['operation']['status'] == 'running'
            assert 'encounters' not in shown.json()
            assert browser.post('/api/continue', json=body).status_code == 409
            assert calls == ['student']
        finally:
            finish.set()
        assert pending.result(timeout=5).status_code == 200
    shown = browser.get('/api/workspace')
    assert shown.status_code == 200 and shown.json()['operation']['status'] == 'complete'
    assert browser.post('/api/continue', json=body).status_code == 409
    assert calls == ['student']


def test_edited_policy_and_loaded_reference_reach_only_tutor(tmp_path):
    folder = session(tmp_path, waiting=True)
    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'PRIVATE_TUTOR_REFERENCE', 'source':'Authored reference'}
    edited = 'Edited teaching instructions.\nAsk one focused question.'
    calls = []

    def tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        assert payload['policy'] == edited and payload['library_reference'] == reference
        calls.append('tutor')
        return schema(text='Which shades are repeated?')

    def learner(prompt, schema):
        assert reference['text'] not in prompt
        calls.append('student')
        return schema(decision='no-reply', text='', source=None)

    browser = client(folder, send=True, policy='Loaded instructions.', reference=reference,
                     generate=learner, generate_tutor=tutor)
    shown = browser.get('/api/workspace')
    assert shown.json()['controls']['policy'] == 'Loaded instructions.'
    assert shown.json()['controls']['reference'] == {key:reference[key] for key in ('library','library_version','source')}
    assert reference['text'] not in shown.text and calls == []
    sent = browser.post('/api/continue', json=request(folder, 'policy', text=edited))
    assert sent.status_code == 200 and calls == ['tutor','student']
    receipt = student._read(next((folder/'tutor-exchanges').glob('*/receipt.json')))
    assert receipt['request']['policy'] == edited
    assert receipt['request']['library_reference'] == reference
    assert browser.get('/api/workspace').json()['controls']['policy'] == 'Loaded instructions.'


def test_failed_tutor_receipt_survives_reload_and_blocks_every_mode(tmp_path):
    folder = session(tmp_path, waiting=True)

    def fail(*_):
        raise RuntimeError('PRIVATE_PROVIDER_DIAGNOSTIC')

    browser = client(folder, send=True, generate_tutor=fail,
                     generate=lambda *_: pytest.fail('Unexpected student dispatch'))
    response = browser.post('/api/continue', json=request(folder, 'policy', text='Use a hint.'))
    assert response.status_code == 409 and 'PRIVATE_PROVIDER_DIAGNOSTIC' not in response.text
    assert browser.get('/api/workspace').json()['operation']['status'] == 'error'
    restarted = client(folder, send=True, generate_tutor=lambda *_: pytest.fail('Tutor resent'),
                       generate=lambda *_: pytest.fail('Student bypassed tutor failure'))
    shown = restarted.get('/api/workspace')
    assert shown.status_code == 200 and shown.json()['controls']['blocked_reason']
    assert 'PRIVATE_PROVIDER_DIAGNOSTIC' not in shown.text
    for mode, options in [('advance', {}), ('reply', {'text':'Manual bypass'}), ('policy', {'text':'Retry'})]:
        assert restarted.post('/api/continue', json=request(folder, mode, **options)).status_code == 409


def test_terminal_provider_failure_and_interrupted_receipt_stay_visible(tmp_path):
    folder = session(tmp_path)

    def fail(*_):
        raise RuntimeError('PRIVATE_STUDENT_ERROR')

    browser = client(folder, send=True, generate=fail)
    response = browser.post('/api/continue', json=request(folder))
    assert response.status_code == 200
    assert latest(response.json())['status'] == 'error'
    assert response.json()['operation']['status'] == 'error'
    assert 'PRIVATE_STUDENT_ERROR' not in response.text
    restarted = client(folder, send=True)
    assert latest(restarted.get('/api/workspace').json())['status'] == 'error'
    assert restarted.post('/api/continue', json=request(folder)).status_code == 409
    path = folder / 'step-0001.json'
    receipt = student._read(path)
    receipt['status'] = 'pending'
    student._save(path, receipt)
    assert restarted.get('/api/workspace').status_code == 409
    binding = {key:receipt['request'][key] for key in ('session_sha256','state_sha256')}
    assert restarted.post('/api/continue', json={'binding':binding, 'mode':'advance'}).status_code == 409


def test_bad_configuration_and_budget_do_not_send(tmp_path):
    folder = session(tmp_path, waiting=True, budget=1)
    for policy in (' ', 7):
        with pytest.raises(ValueError):
            browser_workspace.create_app(folder, policy=policy)
    with pytest.raises(ValueError):
        browser_workspace.create_app(folder, reference={'library':'babypandas'})
    browser = client(folder, send=True, generate_tutor=lambda *_: pytest.fail('Budget dispatch'))
    assert browser.post('/api/continue', json=request(folder, 'policy', text='Help.')).status_code == 409


def test_reference_mismatch_stops_before_creating_exchange(tmp_path):
    folder = session(tmp_path, waiting=True)
    reference = {'library':ACTIVITY['library'], 'library_version':'wrong',
                 'text':'Authored facts.', 'source':'Authored reference'}
    browser = client(folder, send=True, reference=reference,
                     generate_tutor=lambda *_: pytest.fail('Mismatched reference sent'))
    assert browser.post('/api/continue', json=request(folder, 'policy', text='Help.')).status_code == 409
    assert not (folder/'tutor-exchanges').exists()


def test_cli_loads_files_once_and_preserves_tutor_only_reference(tmp_path, monkeypatch):
    import uvicorn

    folder = session(tmp_path, waiting=True)
    policy_file, reference_file = tmp_path/'policy.txt', tmp_path/'reference.json'
    policy_file.write_text('Initial supplied policy.\n')
    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'PRIVATE_INITIAL_REFERENCE', 'source':'Authored reference'}
    reference_file.write_text(json.dumps(reference))
    apps = []
    monkeypatch.setattr(uvicorn, 'run', lambda app, **options: apps.append((app, options)))
    monkeypatch.setattr(sys, 'argv', ['browser_workspace', str(folder), '--send', '--port', '8499',
        '--policy-file', str(policy_file), '--reference-file', str(reference_file)])
    browser_workspace.main()
    assert apps[0][1] == {'host':'127.0.0.1','port':8499}
    policy_file.write_text('Later disk change.')
    reference_file.write_text('Invalid later disk content.')
    browser = TestClient(apps[0][0], base_url='http://127.0.0.1')
    shown = browser.get('/api/workspace')
    assert shown.json()['controls']['send_enabled'] is True
    assert shown.json()['controls']['policy'] == 'Initial supplied policy.\n'
    assert shown.json()['controls']['reference']['source'] == 'Authored reference'
    assert reference['text'] not in shown.text
    assert not (folder/'tutor-exchanges').exists()
    with pytest.raises(SystemExit) as error:
        browser_workspace.main()
    assert error.value.code == 2 and len(apps) == 1
    reference_file.write_text(json.dumps(reference))
    policy_file.write_text(' \n')
    with pytest.raises(SystemExit) as error:
        browser_workspace.main()
    assert error.value.code == 2 and len(apps) == 1


def test_tampered_predecessor_is_rejected_before_any_call(tmp_path):
    from src.agents import notebook_next_task

    previous = session(tmp_path)
    choose(previous, 'no-reply')
    folder = tmp_path / 'next'
    notebook_next_task.create(previous, folder, task=TASK, activity=ACTIVITY)
    body = request(folder)
    path = previous / 'step-0001.json'
    receipt = student._read(path)
    receipt['result']['state']['work']['source'] = 'tampered'
    student._save(path, receipt)
    browser = client(folder, send=True, generate=lambda *_: pytest.fail('Unverified lineage dispatched'))
    assert browser.post('/api/continue', json=body).status_code == 409
    assert not list(folder.glob('step-*.json'))
