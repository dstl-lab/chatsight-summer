"""One authored exchange verifies ordering, actual feedback and immutable parents."""
from copy import deepcopy
import json

import pytest

from src.agents import archive_tutor_continuation as continuation, archived_notebook as archive
from src.agents import notebook_student as store, notebook_tutor as tutor
from tests.test_archived_notebook import prepared, action, execution, no_execution
from tests.test_policy_execution import raw


def child(prepared):
    parent, parent_plan = prepared
    saved = archive.run(parent, send=True, generate=lambda *_:raw(
        action('revise-work', 'unique_uris = 7', 'this?')), execute=no_execution)
    reference = parent.parent/'course-context'/'course-reference.json'
    reference.parent.mkdir()
    body = {'library':'babypandas', 'library_version':'1.0.0',
            'text':'AUTHORED API REFERENCE', 'source':'Authored fixture'}
    store._save(reference, body)
    source_plan = store._read(parent.parent/'comparison'/'plan.json')['plan']
    manifest = {'version':1, 'kind':'notebook-course-reference', 'reference_sha256':store.digest(body),
        'checkpoint_sha256':source_plan['checkpoint_sha256'],
        'input_pins':archive._followup().pins([parent.parent/'source'/'checkpoint.json']),
        'runtime':{'libraries':parent_plan['runtime']['libraries'], 'image_id':parent_plan['image_id']}}
    store._save(reference.with_suffix('.manifest.json'), manifest)
    folder = parent.parent/'new-exchange'
    continuation.prepare(folder, parent_folder=parent, reference_file=reference)
    return folder, parent, saved


def test_exchange_executes_only_on_request_replays_and_preserves_parent(prepared):
    folder, parent, saved = child(prepared)
    original = {p:p.read_bytes() for p in parent.glob('*.json')}
    plan = continuation.load(folder)['plan']
    assert (plan['max_tutor_calls'], plan['max_decisions'], plan['max_checks']) == (1, 3, 2)
    choices = iter([action('request-check'), action('revise-work', 'unique_uris = 8'), action('no-reply')])
    packets, calls = [], []

    def generate(bound, prompt, schema):
        assert bound == plan
        pending = store._read(folder/'run.json')
        assert pending['status'] == pending['calls'][-1]['status'] == 'pending'
        calls.append('tutor' if schema is tutor.Reply else 'model')
        if schema is tutor.Reply:
            payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
            context = payload['context']
            assert context['work'] == saved['state']['work'] and context['feedback'] is None
            assert context['pending_message'] == 'this?' and len(context['dialogue']) == 2
            assert payload['library_reference']['text'] == 'AUTHORED API REFERENCE'
            assert all(text not in prompt for text in ('authored missing method', 'followup_folder', 'input_pins'))
            return raw({'text':'TUTOR_REPLY'})
        packet = json.loads(prompt.split('STATE JSON:\n')[1])
        packets.append(packet)
        assert 'AUTHORED API REFERENCE' not in prompt
        assert packet['dialogue'] == saved['state']['dialogue'] + [
            {'role':'student', 'text':'this?'}, {'role':'tutor', 'text':'TUTOR_REPLY'}]
        return raw(next(choices))

    def execute(binding):
        calls.append('execution')
        assert binding['revision'] == 1 and binding['request']['source'] == 'unique_uris = 7'
        return execution(binding, status='cell-error')

    with pytest.raises(ValueError, match='send'):
        continuation.run(folder, generate=generate, execute=execute)
    result = continuation.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == 'no-reply' and result['state']['work']['revision'] == 2
    assert calls == ['tutor', 'model', 'execution', 'model', 'model']
    assert packets[0]['observation'] is None and packets[0]['history'] == []
    assert packets[1]['observation']['status'] == 'cell-error'
    assert packets[2]['observation'] is None and result['state']['observation'] is None
    assert continuation.load(folder) == result
    assert all(p.read_bytes() == contents for p, contents in original.items())
    with pytest.raises(FileExistsError):
        continuation.run(folder, send=True, generate=generate, execute=execute)
    receipt = store._read(folder/'run.json')
    changed = deepcopy(receipt)
    changed['calls'][0]['response'] = raw({'text':'FORGED'})
    store._save(folder/'run.json', changed)
    with pytest.raises(ValueError):
        continuation.load(folder)
    store._save(folder/'run.json', receipt)
    envelope = store._read(folder/'plan.json')
    backdated = deepcopy(envelope['plan']) | {'created_at':'2020-01-01T00:00:00+00:00'}
    store._save(folder/'plan.json', {'plan':backdated, 'sha256':store.digest(backdated)})
    with pytest.raises(ValueError, match='timestamps'):
        continuation.load(folder)
    store._save(folder/'plan.json', envelope)
    reference = store._read(folder/'plan.json')['plan']['reference_file']
    from pathlib import Path
    Path(reference).write_text('{}')
    with pytest.raises(ValueError):
        continuation.load(folder)


@pytest.mark.parametrize('failure', ['invalid', 'provider', 'interrupted'])
def test_tutor_failure_stops_before_student_and_never_resends(prepared, failure):
    folder, _, _ = child(prepared)
    calls = []

    def generate(plan, prompt, schema):
        calls.append(schema)
        assert schema is tutor.Reply
        if failure == 'provider':
            raise RuntimeError('Authored outage')
        if failure == 'interrupted':
            raise KeyboardInterrupt()
        return raw({'text':'   '})

    if failure == 'interrupted':
        with pytest.raises(KeyboardInterrupt):
            continuation.run(folder, send=True, generate=generate, execute=no_execution)
        with pytest.raises(ValueError, match='Incomplete'):
            continuation.load(folder)
    else:
        result = continuation.run(folder, send=True, generate=generate, execute=no_execution)
        assert result['status'] == 'tutor-error' and result['state'] is result['tutor_reply'] is None
        assert continuation.load(folder) == result
    with pytest.raises(FileExistsError):
        continuation.run(folder, send=True, generate=generate, execute=no_execution)
    assert len(calls) == 1


@pytest.mark.parametrize('decision,terminal,checks', [
    ('revise-work', 'action-limit', 0), ('request-check', 'check-limit', 2), ('reply', 'awaiting-tutor', 0)])
def test_student_caps_and_message_stop(prepared, decision, terminal, checks):
    folder, _, _ = child(prepared)
    calls = []

    def generate(plan, prompt, schema):
        calls.append('tutor' if schema is tutor.Reply else 'model')
        return raw({'text':'Try this.'}) if schema is tutor.Reply else raw(action(decision,
            source='unique_uris = 2' if decision == 'revise-work' else None,
            text='help' if decision == 'reply' else ''))

    def execute(binding):
        calls.append('execution')
        return execution(binding)

    result = continuation.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == terminal
    assert calls.count('tutor') == 1 and calls.count('execution') == checks
    assert calls.count('model') == (1 if decision == 'reply' else 3)
    assert continuation.load(folder) == result
