"""Authored provider responses exercise durable bounded sampling; no network calls."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from threading import Event, Thread
import time
from uuid import uuid4

import pytest

from src.agents import notebook_student as store
from src.eval.notebook_action import Action


def prepared():
    prompt = 'Authored fixed notebook context.'
    return {'model':'gemini-2.5-pro', 'prompt':prompt,
            'prompt_sha256':sha256(prompt.encode()).hexdigest(),
            'schema':Action.model_json_schema(), 'task':{'work':{'source':'total = 3'}}}


def raw(decision='no-reply'):
    return {'candidates':[{'finish_reason':'STOP', 'content':{'parts':[{'text':json.dumps(
        {'decision':decision, 'text':'Which value?' if decision == 'reply' else '', 'source':None})}]}}],
        'usage_metadata':{'total_token_count':12}}


def wait(jobs, batch_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = jobs.snapshot(batch_id)
        if result['status'] != 'running':
            return result
        time.sleep(.005)
    raise AssertionError('Authored job did not stop.')


def manager(root, data, generate):
    module = importlib.import_module('src.agents.next_action_sampling')
    return module.SamplingJobs(root, lambda:deepcopy(data), generate=generate)


def test_durable_samples_include_failed_raw_and_do_not_retry(tmp_path):
    data = prepared()
    calls = []
    partial = {'candidates':[{'finish_reason':'MAX_TOKENS', 'content':{'parts':[{'text':'{"decision"'}]}}]}
    def generate(plan, prompt):
        calls.append(prompt)
        assert plan['model'] == 'gemini-2.5-pro' and plan['sdk_attempts'] == 1
        assert plan['generation_config'] == {'response_mime_type':'application/json', 'response_schema':data['schema']}
        if len(calls) == 2:
            return partial
        if len(calls) == 3:
            raise RuntimeError('PRIVATE PROVIDER DETAIL')
        return raw()
    jobs = manager(tmp_path/'jobs', data, generate)
    request_id = str(uuid4())
    batch = jobs.start(request_id, 4, store.digest(data))
    result = wait(jobs, batch['id'])
    assert (result['status'], result['requested'], result['finished'], result['valid'], result['failed']) == ('complete',4,4,2,2)
    assert calls == [data['prompt']]*4
    assert result['records'][1]['raw_response'] == partial
    assert result['records'][2]['error'] == {'type':'RuntimeError'}
    assert 'PRIVATE PROVIDER DETAIL' not in json.dumps(result)
    quiet = next(c for c in result['categories'] if c['decision'] == 'no-reply')
    assert quiet['count'] == 2 and quiet['proportion'] == 1
    assert quiet['interval'][0] == pytest.approx(.3423802275)
    assert 'prepared' not in jobs.list()[0] and 'records' not in jobs.list()[0]
    assert jobs.start(request_id, 4, store.digest(data))['id'] == batch['id']
    with pytest.raises(ValueError):
        jobs.start(request_id, 5, store.digest(data))
    jobs.close()
    reopened = manager(tmp_path/'jobs', data, lambda *_:pytest.fail('Reopening sent a request.'))
    assert reopened.snapshot(batch['id']) == result
    assert reopened.start(request_id, 4, store.digest(data))['status'] == 'complete'
    assert reopened.list()[0]['request_id'] == request_id
    reopened.close()


def test_cancel_finishes_inflight_then_stops_and_single_owner_blocks(tmp_path):
    data, entered, release = prepared(), Event(), Event()
    def generate(*_):
        entered.set()
        assert release.wait(5)
        return raw('reply')
    jobs = manager(tmp_path/'jobs', data, generate)
    try:
        request_id = str(uuid4())
        batch = jobs.start(request_id, 30, store.digest(data))
        assert entered.wait(5)
        assert jobs.snapshot(batch['id'])['finished'] == 0
        assert jobs.start(request_id, 30, store.digest(data))['id'] == batch['id']
        with pytest.raises(RuntimeError):
            jobs.start(str(uuid4()), 1, store.digest(data))
        with pytest.raises((RuntimeError, ValueError)):
            manager(tmp_path/'jobs', data, generate)
        assert jobs.cancel(batch['id'])['cancel_requested'] is True
        assert jobs.cancel(batch['id'])['cancel_requested'] is True
        release.set()
        result = wait(jobs, batch['id'])
        assert (result['status'],result['finished'],result['valid'],result['failed']) == ('cancelled',1,1,0)
        assert len(result['records']) == 1 and result['records'][0]['response']['decision'] == 'reply'
    finally:
        release.set()
        jobs.close()


@pytest.mark.parametrize('runs', [True, False, 0, -1, 101, 1.0, '30', None])
def test_invalid_count_never_creates_receipt(tmp_path, runs):
    data = prepared()
    jobs = manager(tmp_path/'jobs', data, lambda *_:pytest.fail('Invalid start sent.'))
    with pytest.raises(ValueError):
        jobs.start(str(uuid4()), runs, store.digest(data))
    assert jobs.list() == []
    jobs.close()


def test_invalid_identifiers_and_input_binding_never_send(tmp_path):
    data = prepared()
    jobs = manager(tmp_path/'jobs', data, lambda *_:pytest.fail('Invalid start sent.'))
    for request_id in ('../escape', 'not-uuid', '', None):
        with pytest.raises(ValueError):
            jobs.start(request_id, 1, store.digest(data))
    with pytest.raises(ValueError):
        jobs.start(str(uuid4()), 1, '0'*64)
    assert jobs.list() == []
    jobs.close()


def test_input_changed_between_draws_stops_without_replacement(tmp_path):
    data = prepared()
    def generate(*_):
        data['task']['work']['source'] = 'CHANGED INPUT'
        return raw()
    jobs = manager(tmp_path/'jobs', data, generate)
    batch = jobs.start(str(uuid4()), 3, store.digest(data))
    result = wait(jobs, batch['id'])
    assert (result['status'],result['finished'],result['valid'],result['failed']) == ('error',1,1,0)
    assert len(result['records']) == 1
    jobs.close()


def test_code_pin_changed_between_draws_stops_before_next_send(tmp_path, monkeypatch):
    module = importlib.import_module('src.agents.next_action_sampling')
    data = prepared()
    def generate(*_):
        monkeypatch.setattr(module, '_pins', lambda:{'changed':'0'*64})
        return raw()
    jobs = manager(tmp_path/'jobs', data, generate)
    batch = jobs.start(str(uuid4()), 3, store.digest(data))
    result = wait(jobs, batch['id'])
    assert (result['status'],result['finished'],result['valid']) == ('error',1,1)
    jobs.close()


def test_largest_batch_has_exactly_the_requested_samples(tmp_path):
    data = prepared()
    jobs = manager(tmp_path/'jobs', data, lambda *_:raw())
    batch = jobs.start(str(uuid4()), 100, store.digest(data))
    result = wait(jobs, batch['id'])
    assert (result['status'],result['finished'],result['valid']) == ('complete',100,100)
    assert [record['index'] for record in result['records']] == list(range(1,101))
    jobs.close()


def test_missing_provider_key_does_not_consume_request(tmp_path, monkeypatch):
    module = importlib.import_module('src.agents.next_action_sampling')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    data = prepared()
    jobs = module.SamplingJobs(tmp_path/'jobs', lambda:data)
    with pytest.raises(ValueError, match='GEMINI_API_KEY'):
        jobs.start(str(uuid4()), 1, store.digest(data))
    assert jobs.list() == []
    jobs.close()


def test_storage_failure_after_raw_response_does_not_schedule_more(tmp_path, monkeypatch):
    module = importlib.import_module('src.agents.next_action_sampling')
    data, entered, release = prepared(), Event(), Event()
    save = module.store._save
    def generate(*_):
        entered.set()
        assert release.wait(5)
        return raw()
    jobs = manager(tmp_path/'jobs', data, generate)
    try:
        batch = jobs.start(str(uuid4()), 3, store.digest(data))
        assert entered.wait(5)
        failed = False
        def disk_failure(path, envelope, **kwargs):
            nonlocal failed
            if not failed and 'raw_response' in envelope['batch']['records'][-1]:
                failed = True
                raise OSError('Authored full disk')
            return save(path, envelope, **kwargs)
        monkeypatch.setattr(module.store, '_save', disk_failure)
        release.set()
        result = wait(jobs, batch['id'])
        assert result['status'] == 'error' and result['finished'] == 0
        assert len(result['records']) == 1
    finally:
        release.set()
        jobs.close()


def test_restart_interrupts_pending_receipt_and_preserves_completed_samples(tmp_path):
    data = prepared()
    root = tmp_path/'jobs'
    jobs = manager(root, data, lambda *_:raw())
    batch = jobs.start(str(uuid4()), 2, store.digest(data))
    result = wait(jobs, batch['id'])
    jobs.close()
    path = root/f'{batch["id"]}.json'
    envelope = json.loads(path.read_text())
    saved = envelope['batch']
    saved['status'] = 'running'
    saved['records'][1] = {'index':2, 'status':'pending', 'started_at':result['created_at'],
                           'prompt_sha256':data['prompt_sha256'],
                           'raw_response':{'candidates':[{'finish_reason':'MAX_TOKENS'}]}}
    store._save(path, {'sha256':store.digest(saved), 'batch':saved})
    reopened = manager(root, data, lambda *_:pytest.fail('Restart sent.'))
    interrupted = reopened.snapshot(batch['id'])
    assert (interrupted['status'],interrupted['finished'],interrupted['valid'],interrupted['failed']) == ('interrupted',1,1,0)
    assert interrupted['records'][0] == result['records'][0]
    assert interrupted['records'][1]['raw_response']['candidates'][0]['finish_reason'] == 'MAX_TOKENS'
    assert reopened.start(batch['id'], 2, store.digest(data))['status'] == 'interrupted'
    reopened.close()


@pytest.mark.parametrize('changed', ['record-prompt', 'plan', 'input', 'complete-count'])
def test_rehashed_receipts_must_keep_input_plan_and_lifecycle_binding(tmp_path, changed):
    data = prepared()
    root = tmp_path/'jobs'
    jobs = manager(root, data, lambda *_:raw())
    batch = jobs.start(str(uuid4()), 1, store.digest(data))
    wait(jobs, batch['id'])
    jobs.close()
    path = root/f'{batch["id"]}.json'
    saved = json.loads(path.read_text())['batch']
    if changed == 'record-prompt':
        saved['records'][0]['prompt_sha256'] = '0'*64
    elif changed == 'plan':
        saved['plan']['code_pins'] = {'changed':'0'*64}
    elif changed == 'input':
        saved['prepared']['task']['work']['source'] = 'OTHER INPUT'
        saved['input_sha256'] = store.digest(saved['prepared'])
    else:
        saved['requested'] = 2
    store._save(path, {'sha256':store.digest(saved), 'batch':saved})
    with pytest.raises(ValueError):
        manager(root, data, lambda *_:pytest.fail('Reopening sent.'))


def test_tampered_receipt_and_symlink_root_fail_closed(tmp_path):
    data = prepared()
    root = tmp_path/'jobs'
    jobs = manager(root, data, lambda *_:raw())
    batch = jobs.start(str(uuid4()), 1, store.digest(data))
    wait(jobs, batch['id'])
    path = root/f'{batch["id"]}.json'
    envelope = json.loads(path.read_text())
    envelope['batch']['records'][0]['response']['decision'] = 'reply'
    store._save(path, envelope)
    with pytest.raises(ValueError):
        jobs.snapshot(batch['id'])
    jobs.close()
    link = tmp_path/'linked'
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError):
        manager(link, data, lambda *_:raw())


def test_shutdown_releases_owner_even_when_inflight_receipt_is_damaged(tmp_path):
    data, entered, release = prepared(), Event(), Event()
    def generate(*_):
        entered.set()
        assert release.wait(5)
        return raw()
    root = tmp_path/'jobs'
    jobs = manager(root, data, generate)
    batch = jobs.start(str(uuid4()), 3, store.digest(data))
    assert entered.wait(5)
    path = root/f'{batch["id"]}.json'
    path.write_text('{}')
    errors = []
    def close():
        try:
            jobs.close()
        except (KeyError, ValueError) as exc:
            errors.append(type(exc).__name__)
    closer = Thread(target=close)
    closer.start()
    release.set()
    closer.join(5)
    assert not closer.is_alive()
    path.unlink()
    reopened = manager(root, data, lambda *_:pytest.fail('Shutdown sent.'))
    assert reopened.list() == []
    reopened.close()
