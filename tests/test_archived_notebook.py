"""Authored archive-loop receipts; no submitted code, Docker or provider is run."""
from copy import deepcopy
import hashlib
import json

import pytest

from src.agents import archived_notebook as archive, notebook_student as store
from tests.test_policy_execution import prepared_followup, raw


def action(decision, source=None, text=''):
    return {'decision':decision, 'source':source, 'text':text}


def no_execution(binding):
    pytest.fail('This action must not execute code.')


def execution(binding, *, status='ok', value=2):
    result = {'execution':'completed', 'status':status, 'value':value if status == 'ok' else None,
        'error':None if status == 'ok' else {'type':'AttributeError', 'message':'authored missing method'},
        'output':'AUTHORED OUTPUT', 'runtime':{'python':'3.13', 'libraries':{'babypandas':'1.0.0'},
                                            'image_id':binding['image_id']}}
    return 0, json.dumps(result).encode(), None


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        pytest.fail('Only authored callbacks may run in this test.')
    monkeypatch.setattr(archive, '_generate', unavailable)
    monkeypatch.setattr(archive.notebook_runtime, '_local_docker', unavailable)
    monkeypatch.setattr(archive.notebook_runtime, '_execute', unavailable)
    followup, original, previous, _ = prepared_followup(tmp_path)
    followup.execute(previous)  # The fixture's fake probe only serializes authored results.
    frozen = {path:path.read_bytes() for root in (original, previous) for path in root.rglob('*.json')}
    folder = tmp_path/'archive-loop'
    plan = archive.prepare(folder, followup_folder=previous, condition='hint', authored_demo=True)
    assert archive.load(folder) == {'plan':plan, 'status':'prepared', 'state':None}
    yield folder, plan
    assert all(path.read_bytes() == contents for path, contents in frozen.items())


def test_requested_execution_feedback_invalidation_and_exact_saved_replay(prepared):
    folder, plan = prepared
    choices = [action('revise-work', 'unique_uris = 11'), action('request-check'),
               action('revise-work', 'unique_uris = 22'), action('request-check'), action('no-reply')]
    packets, bindings = [], []

    def generate(sent_plan, prompt):
        assert sent_plan == plan and sent_plan['sdk_attempts'] == 1
        pending = store._read(folder/'run.json')
        assert pending['status'] == 'pending' and pending['calls'][-1]['status'] == 'pending'
        packets.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return raw(choices[len(packets)-1])

    def execute(binding):
        pending = store._read(folder/'run.json')['calls'][-1]
        assert pending['kind'] == 'execution' and pending['status'] == 'pending'
        assert pending['request'] == binding
        bindings.append(binding)
        return execution(binding, status='cell-error' if len(bindings) == 1 else 'ok', value=22)

    with pytest.raises(ValueError, match='send'):
        archive.run(folder, generate=generate, execute=execute)
    assert not (folder/'run.json').exists() and packets == [] and bindings == []
    result = archive.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == 'no-reply'
    state = result['state']
    assert [event['action'] for event in state['history']] == choices
    assert [event['work_after']['revision'] for event in state['history']] == [1, 1, 2, 2, 2]
    assert all(event['origin'] == 'scripted' for event in state['history'])
    assert state['message'] is None and state['dialogue'] == plan['initial']['dialogue']
    assert [binding['revision'] for binding in bindings] == [1, 2]
    assert [binding['request']['source'] for binding in bindings] == ['unique_uris = 11', 'unique_uris = 22']
    for binding in bindings:
        request = binding['request']
        assert request['source_sha256'] == hashlib.sha256(request['source'].encode()).hexdigest()
        assert request['csv_sha256'] == plan['dataset']['sha256']
        assert binding['plan_sha256'] == store.digest(plan)
    assert packets[0]['observation'] is None and packets[1]['observation'] is None
    initial = packets[0]
    assert initial['work']['source'] == 'unique_uris = 0' and initial['work']['revision'] == 0
    assert initial['history'] == [] and initial['dialogue'] == plan['initial']['dialogue']
    assert set(initial) == {'initialization', 'task', 'work', 'dialogue', 'history', 'observation', 'runtime'}
    assert initial['runtime'] == {
        'table':'charts', 'result':'unique_uris', 'libraries':{'babypandas':'1.0.0'},
        'dataset':{'sha256':'a'*64, 'rows':3, 'columns':1, 'provenance':'authored fixture'},
        'grading':'none', 'namespace':'fresh per run'}  # Metadata, not table contents.
    initial_payload = json.dumps(initial)
    assert all(saved not in initial_payload for saved in (
        'EDIT_MESSAGE', 'unique_uris = 2', 'unique_uris = 3', 'authored missing method',
        'usage_metadata', 'output_hex'))  # No sampled edit, prior check, or provider receipt.
    assert packets[2]['observation']['status'] == 'cell-error'
    assert packets[2]['observation']['revision'] == 1
    assert packets[3]['observation'] is None  # Editing invalidates the current result.
    assert packets[3]['history'][1]['observation'] == packets[2]['observation']
    assert packets[4]['observation']['value'] == 22
    assert state['observation']['revision'] == 2
    assert state['observation']['success'] is None and state['observation']['grading'] == 'none'
    assert ['observation' in event for event in state['history']] == [False, True, False, True, False]

    path = folder/'run.json'
    receipt = store._read(path)
    assert [call['kind'] for call in receipt['calls']] == [
        'model', 'model', 'execution', 'model', 'model', 'execution', 'model']
    assert receipt['calls'][0]['response']['usage_metadata']['prompt_token_count'] == 7
    output = bytes.fromhex(receipt['calls'][5]['response']['output_hex'])
    assert json.loads(output)['value'] == 22
    before = path.read_bytes()
    assert archive.load(folder) == result and path.read_bytes() == before
    with pytest.raises(FileExistsError):
        archive.run(folder, send=True, generate=generate, execute=execute)
    assert len(packets) == 5 and len(bindings) == 2

    changed = deepcopy(receipt)
    changed['calls'][0]['request']['prompt'] += 'FORGED'
    store._save(path, changed)
    with pytest.raises(ValueError):
        archive.load(folder)
    changed = deepcopy(receipt)
    changed['calls'][5]['response']['output_hex'] = json.dumps({'status':'ok', 'value':'FORGED'}).encode().hex()
    store._save(path, changed)
    with pytest.raises(ValueError):
        archive.load(folder)
    store._save(path, receipt)
    assert archive.load(folder) == result


@pytest.mark.parametrize('failure', ['model-error', 'malformed', 'truncated', 'execution-error'])
def test_failed_or_invalid_calls_are_saved_without_retry_or_resend(prepared, failure):
    folder, _ = prepared
    calls = []

    def generate(plan, prompt):
        calls.append('model')
        if failure == 'model-error':
            raise RuntimeError('Authored provider outage')
        if failure == 'malformed':
            return raw(action('request-check', text='not an empty request'))
        if failure == 'truncated':
            return raw(action('no-reply'), finish='MAX_TOKENS')
        return raw(action('request-check'))

    def execute(binding):
        calls.append('execution')
        raise RuntimeError('Authored executor outage')

    result = archive.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == 'error' and result['state']['message'] is None
    assert result['state']['observation'] is None and len(result['state']['history']) == 1
    assert 'error' in result['state']['history'][0]
    assert calls == (['model', 'execution'] if failure == 'execution-error' else ['model'])
    receipt = store._read(folder/'run.json')
    assert receipt['status'] == 'complete'
    assert receipt['calls'][-1]['status'] == ('complete' if failure in ('malformed', 'truncated') else 'error')
    if failure in ('malformed', 'truncated'):
        assert receipt['calls'][0]['response']['usage_metadata']['prompt_token_count'] == 7
    assert archive.load(folder) == result
    with pytest.raises(FileExistsError):
        archive.run(folder, send=True, generate=generate, execute=execute)
    assert len(calls) == (2 if failure == 'execution-error' else 1)


def test_interrupted_pending_attempt_cannot_be_loaded_or_resent(prepared):
    folder, _ = prepared
    calls = []

    def interrupted(plan, prompt):
        calls.append(prompt)
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        archive.run(folder, send=True, generate=interrupted, execute=no_execution)
    receipt = store._read(folder/'run.json')
    assert receipt['status'] == 'pending' and receipt['calls'][0]['status'] == 'pending'
    with pytest.raises(ValueError, match='Incomplete'):
        archive.load(folder)
    with pytest.raises(FileExistsError):
        archive.run(folder, send=True, generate=interrupted, execute=no_execution)
    assert len(calls) == 1


@pytest.mark.parametrize('decision, terminal, decisions, checks', [
    ('revise-work', 'action-limit', 6, 0), ('request-check', 'check-limit', 4, 3)])
def test_fixed_budgets_stop_without_fabricating_a_no_reply(prepared, decision, terminal, decisions, checks):
    folder, plan = prepared
    model_calls, execution_calls = [], []
    assert plan['max_decisions'] == 6 and plan['max_checks'] == 3

    def generate(plan, prompt):
        model_calls.append(prompt)
        return raw(action(decision, f'unique_uris = {len(model_calls)}' if decision == 'revise-work' else None))

    def execute(binding):
        execution_calls.append(binding)
        return execution(binding)

    result = archive.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == terminal
    assert len(model_calls) == decisions and len(execution_calls) == checks
    assert [event['action']['decision'] for event in result['state']['history']] == [decision] * decisions
    assert result['state']['message'] is None
    if terminal == 'check-limit':
        assert 'observation' not in result['state']['history'][-1]
    assert archive.load(folder) == result


@pytest.mark.parametrize('choice', [action('reply', text='what now?'),
                                    action('revise-work', 'unique_uris = 5', 'this?')])
def test_a_student_message_stops_for_the_tutor_without_implicit_execution(prepared, choice):
    folder, plan = prepared
    calls = []

    def generate(plan, prompt):
        calls.append(prompt)
        return raw(choice)

    result = archive.run(folder, send=True, generate=generate, execute=no_execution)
    assert result['status'] == 'awaiting-tutor' and len(calls) == 1
    assert result['state']['message'] == choice['text']
    assert result['state']['dialogue'] == plan['initial']['dialogue']
    assert result['state']['observation'] is None
    assert result['state']['work']['revision'] == (1 if choice['decision'] == 'revise-work' else 0)
    assert archive.load(folder) == result


def test_callback_provenance_is_checked_before_an_attempt_is_saved(prepared):
    folder, plan = prepared
    generate = lambda *_: pytest.fail('Invalid provenance must not dispatch.')
    for options in ({}, {'generate':generate}, {'execute':no_execution}):
        with pytest.raises(ValueError):
            archive.run(folder, send=True, **options)
        assert not (folder/'run.json').exists()
    live = folder.parent/'live-plan-only'
    archive.prepare(live, followup_folder=plan['followup_folder'], condition='hint', authored_demo=False)
    for options in ({'generate':generate}, {'execute':no_execution},
                    {'generate':generate, 'execute':no_execution}):
        with pytest.raises(ValueError):
            archive.run(live, send=True, **options)
        assert not (live/'run.json').exists()
