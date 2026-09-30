"""Authored calls check a continuous sequence without Gemini or Docker."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

import pytest

from src.agents import archived_notebook as archive, notebook_student as store, notebook_tutor as tutor
from tests.test_archived_notebook import prepared, action, execution, no_execution
from tests.test_policy_execution import raw


@pytest.fixture
def sequence(prepared):
    path = Path(archive.__file__).with_name('archive_sequence.py')
    assert path.exists(), 'The bounded multi-turn archive sequence is not implemented.'
    module = importlib.import_module('src.agents.archive_sequence')
    parent, before = prepared
    reference = parent.parent/'reference.json'
    body = {'library':'babypandas', 'library_version':'1.0.0',
            'text':'TUTOR_ONLY_REFERENCE', 'source':'Authored fixture'}
    store._save(reference, body)
    comparison = store._read(parent.parent/'comparison'/'plan.json')['plan']
    store._save(reference.with_suffix('.manifest.json'), {
        'version':1, 'kind':'notebook-course-reference', 'reference_sha256':store.digest(body),
        'checkpoint_sha256':comparison['checkpoint_sha256'],
        'input_pins':archive._followup().pins([parent.parent/'source'/'checkpoint.json']),
        'runtime':{'libraries':before['runtime']['libraries'], 'image_id':before['image_id']}})
    folder = parent.parent/'sequence'
    plan = module.prepare(folder, followup_folder=before['followup_folder'],
                          reference_file=reference, authored_demo=True)
    return module, folder, plan


def test_continuous_sequence_carries_error_through_tutor_then_clears_it_on_edit(sequence):
    module, folder, plan = sequence
    choices = iter([action('request-check'), action('reply', text='why'),
                    action('revise-work', 'unique_uris = 2'), action('request-check'), action('no-reply')])
    packets, calls = [], []

    def generate(bound, prompt, schema):
        assert bound == plan
        pending = store._read(folder/'run.json')
        assert pending['status'] == pending['calls'][-1]['status'] == 'pending'
        if schema is tutor.Reply:
            calls.append('tutor')
            payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
            assert payload['library_reference']['text'] == 'TUTOR_ONLY_REFERENCE'
            assert payload['context']['feedback']['status'] == 'cell-error'
            assert payload['context']['pending_message'] == 'why'
            assert payload['context']['work']['revision'] == 0
            return raw({'text':'Use the available method.'})
        calls.append('student')
        packet = json.loads(prompt.split('STATE JSON:\n')[1])
        assert all(value not in prompt for value in ('TUTOR_ONLY_REFERENCE', 'input_pins',
            'followup_folder', 'EDIT_MESSAGE', 'unique_uris = 3'))
        packets.append(packet)
        return raw(next(choices))

    def execute(binding):
        calls.append('execution')
        return execution(binding, status='cell-error' if binding['revision'] == 0 else 'ok')

    assert module.load(folder)['status'] == 'prepared'
    with pytest.raises(ValueError, match='send'):
        module.run(folder, generate=generate, execute=execute)
    result = module.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == 'no-reply'
    assert calls == ['student', 'execution', 'student', 'tutor', 'student', 'student', 'execution', 'student']
    assert [len(packet['history']) for packet in packets] == [0, 1, 2, 3, 4]
    assert [packet['observation']['status'] if packet['observation'] else None for packet in packets] == [
        None, 'cell-error', 'cell-error', None, 'ok']
    assert packets[2]['dialogue'][-2:] == [
        {'role':'student', 'text':'why'}, {'role':'tutor', 'text':'Use the available method.'}]
    frames = result['frames']
    assert [frame['kind'] for frame in frames] == ['initial', 'student', 'student', 'tutor', 'student', 'student', 'student']
    assert [frame['work']['revision'] for frame in frames] == [0, 0, 0, 0, 1, 1, 1]
    assert all('history' not in frame for frame in frames)
    assert (frames[-1]['decisions'], frames[-1]['tutor_turns'], frames[-1]['checks']) == (5, 1, 2)
    assert frames[2]['message'] == 'why' and frames[3]['message'] is None
    assert frames[4]['observation'] is None and frames[-1]['observation']['success'] is None
    assert module.load(folder) == result
    with pytest.raises(FileExistsError):
        module.run(folder, send=True, generate=generate, execute=execute)
    receipt = store._read(folder/'run.json')
    for mutate in ('prompt', 'response', 'time', 'frame'):
        changed = deepcopy(receipt)
        if mutate == 'prompt':
            changed['calls'][0]['request']['prompt'] += 'FORGED'
        elif mutate == 'response':
            changed['calls'][3]['response'] = raw({'text':'FORGED'})
        elif mutate == 'time':
            changed['calls'][0]['started_at'] = '2000-01-01T00:00:00+00:00'
        else:
            changed['result']['frames'][1]['observation'] = None
        store._save(folder/'run.json', changed)
        with pytest.raises(ValueError):
            module.load(folder)
    store._save(folder/'run.json', receipt)
    assert module.load(folder) == result
    Path(plan['reference_file']).write_text('{}')
    with pytest.raises(ValueError):
        module.load(folder)


@pytest.mark.parametrize('decision,status,students,tutors,checks', [
    ('revise-work', 'action-limit', 8, 0, 0),
    ('reply', 'tutor-limit', 4, 3, 0),
    ('request-check', 'check-limit', 5, 0, 4)])
def test_global_caps_do_not_create_silence(sequence, decision, status, students, tutors, checks):
    module, folder, plan = sequence
    counts = {'student':0, 'tutor':0, 'execution':0}

    def generate(bound, prompt, schema):
        key = 'tutor' if schema is tutor.Reply else 'student'
        counts[key] += 1
        return raw({'text':'Next hint.'}) if schema is tutor.Reply else raw(action(decision,
            source='unique_uris = 2' if decision == 'revise-work' else None,
            text='help' if decision == 'reply' else ''))

    def execute(binding):
        counts['execution'] += 1
        return execution(binding)

    result = module.run(folder, send=True, generate=generate, execute=execute)
    assert result['status'] == result['frames'][-1]['status'] == status
    assert counts == {'student':students, 'tutor':tutors, 'execution':checks}
    assert not any(event.get('action', {}).get('decision') == 'no-reply' for event in result['state']['history'])
    assert module.load(folder) == result


@pytest.mark.parametrize('failure', ['provider', 'schema', 'tutor', 'executor', 'infrastructure', 'interrupted'])
def test_failures_stop_and_interrupted_dispatch_cannot_resume(sequence, failure):
    module, folder, plan = sequence
    calls = []

    def generate(bound, prompt, schema):
        calls.append('tutor' if schema is tutor.Reply else 'student')
        if failure == 'interrupted':
            raise KeyboardInterrupt()
        if failure == 'provider' or schema is tutor.Reply:
            raise RuntimeError('Authored outage')
        if failure == 'schema':
            return raw(action('request-check', text='invalid'))
        return raw(action('reply', text='help') if failure == 'tutor' else action('request-check'))

    def execute(binding):
        calls.append('execution')
        if failure == 'executor':
            raise RuntimeError('Authored executor outage')
        return execution(binding, status='environment-error')

    if failure == 'interrupted':
        with pytest.raises(KeyboardInterrupt):
            module.run(folder, send=True, generate=generate, execute=execute)
        with pytest.raises(ValueError, match='Incomplete'):
            module.load(folder)
    else:
        result = module.run(folder, send=True, generate=generate, execute=execute)
        assert result['status'] == ('tutor-error' if failure == 'tutor' else
                                    'environment-error' if failure == 'infrastructure' else 'error')
        assert result['frames'][-1]['status'] == result['status']
        assert module.load(folder) == result
    assert calls == (['student', 'tutor'] if failure == 'tutor' else
                     ['student', 'execution'] if failure in ('executor', 'infrastructure') else ['student'])
    with pytest.raises(FileExistsError):
        module.run(folder, send=True, generate=generate, execute=execute)


def test_provenance_and_changed_reference_prevent_dispatch(sequence):
    module, folder, plan = sequence
    for options in ({}, {'generate':lambda *_:None}, {'execute':no_execution}):
        with pytest.raises(ValueError):
            module.run(folder, send=True, **options)
        assert not (folder/'run.json').exists()
    live = folder.parent/'live-sequence'
    module.prepare(live, followup_folder=plan['followup_folder'], reference_file=plan['reference_file'])
    for options in ({'generate':lambda *_:None}, {'execute':no_execution},
                    {'generate':lambda *_:None, 'execute':no_execution}):
        with pytest.raises(ValueError):
            module.run(live, send=True, **options)
        assert not (live/'run.json').exists()
    manifest = Path(plan['reference_file']).with_suffix('.manifest.json')
    value = store._read(manifest)
    value['runtime']['image_id'] = 'sha256:' + 'f'*64
    store._save(manifest, value)
    with pytest.raises(ValueError):
        module.load(folder)
