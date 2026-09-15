"""One generated tutor reply continues only the student state it actually saw."""
from copy import deepcopy
import importlib.util
import json

import pytest

from src.agents import notebook_student as student
from src.agents import tutor_context
from src.eval.notebook_session import Action
from tests.test_notebook_session import TASK, ACTIVITY, observation


def api():
    assert importlib.util.find_spec('src.agents.notebook_tutor'), 'Notebook tutor adapter is missing'
    from src.agents import notebook_tutor
    return notebook_tutor


def choose(folder, decision='reply', *, text='this?', source=None, tutor_reply=None):
    return student.step(folder, generate=lambda *_: Action(decision=decision, text=text, source=source),
                        check=None, tutor_reply=tutor_reply, max_actions=1)


def files(folder):
    return {path.name:path.read_bytes() for path in folder.iterdir() if path.is_file()}


def test_generated_tutor_uses_visible_context_and_continues_bound_work(tmp_path):
    tutor = api()
    folder, output = tmp_path / 'student', tmp_path / 'exchange'
    task = deepcopy(TASK)
    task.update(captured_at='PRIVATE_CAPTURE', reference_future='HIDDEN_FUTURE')
    student.create(folder, task=task, activity=ACTIVITY, branch_id='PRIVATE_BRANCH')
    choose(folder, 'revise-work', source='n_shades = 1', text='')
    choose(folder, text='PENDING_QUESTION')
    packet = tutor_context.snapshot(folder)
    exact = 'Count each distinct shade once.\nKeep the result in n_shades.\n'
    policy = 'Give one concrete next step and keep the reply brief.'
    expected_prompt = tutor.PROMPT + json.dumps({'policy':policy, 'context':{
        key:packet[key] for key in ('initialization', 'task', 'activity', 'dialogue',
                                   'pending_message', 'work', 'feedback', 'changes')}},
        ensure_ascii=False, sort_keys=True)
    choices = iter([Action(decision='revise-work', source="n_shades = len(swatches.get('shade').unique())", text=''),
                    Action(decision='request-check', source=None, text='')])
    tutor_calls, student_packets = [], []

    def generate_tutor(prompt, schema):
        tutor_calls.append(prompt)
        assert prompt == expected_prompt
        pending = student._read(output / 'receipt.json')
        assert pending['status'] == 'pending' and pending['request']['prompt'] == prompt
        assert pending['request']['schema'] == schema.model_json_schema()
        assert tutor_context.read_handoff(output / 'context.json') == packet
        assert prompt.count('PENDING_QUESTION') == 1 and 'n_shades = 1' in prompt and policy in prompt
        assert all(secret not in prompt for secret in ('PRIVATE_CAPTURE', 'PRIVATE_BRANCH', 'HIDDEN_FUTURE',
                   'image_id', packet['sha256'], *packet['binding'].values()))
        return schema(text=exact)

    def generate_student(prompt, schema):
        student_packets.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return next(choices)

    result = tutor.respond(folder, output, policy=policy, generate_tutor=generate_tutor,
        generate_student=generate_student, check=lambda *a, **kw: observation(*a, **kw, status='checked'), max_actions=2)
    assert student.load(folder) == result['state']
    assert result['state']['work']['revision'] == 2 and result['state']['observation']['success'] is True
    assert result['stop_reason'] == 'action-limit' and len(tutor_calls) == 1
    assert student_packets[0]['work'] == packet['work']
    assert student_packets[0]['dialogue'][-2:] == [
        {'role':'student', 'text':'PENDING_QUESTION', 'origin':'generated'},
        {'role':'tutor', 'text':exact, 'origin':'supplied'}]
    receipt = student._read(output / 'receipt.json')
    assert receipt['status'] == 'complete' and receipt['response'] == {'text':exact}
    assert receipt['request']['context_sha256'] == packet['sha256']
    assert receipt['request']['policy'] == policy and receipt['request']['model'] == 'gemini-2.5-pro'
    assert receipt['continuation']['status'] == 'complete' and receipt['continuation']['result'] == result
    operation = student._read(folder / 'step-0003.json')
    assert all(operation['request'][key] == value for key,value in packet['binding'].items())
    choose(folder, text='Another question')
    before, saved_output = files(folder), files(output)
    with pytest.raises((ValueError, FileExistsError)):
        tutor.respond(folder, output, policy=policy, generate_tutor=generate_tutor,
                      generate_student=generate_student, check=None)
    assert files(folder) == before and files(output) == saved_output and len(tutor_calls) == 1


def test_tutor_failure_interruption_and_changed_state_do_not_continue_student(tmp_path):
    tutor = api()
    for mode in ('error', 'interrupt', 'stale'):
        folder, output = tmp_path / mode, tmp_path / (mode + '-exchange')
        student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/' + mode)
        choose(folder)
        before, student_calls = files(folder), []

        def generate_tutor(prompt, schema):
            assert student._read(output / 'receipt.json')['status'] == 'pending'
            if mode == 'error':
                raise RuntimeError('Authored tutor outage')
            if mode == 'interrupt':
                raise KeyboardInterrupt()
            choose(folder, text='NEW question', tutor_reply='Another tutor already answered.')
            return schema(text='This answer belongs to the previous state.')

        with pytest.raises({'error':RuntimeError, 'interrupt':KeyboardInterrupt, 'stale':ValueError}[mode]):
            tutor.respond(folder, output, policy='Give a brief hint.', generate_tutor=generate_tutor,
                          generate_student=lambda *_: student_calls.append(True), check=None)
        assert student_calls == []
        receipt = student._read(output / 'receipt.json')
        if mode == 'stale':
            assert receipt['status'] == 'complete' and receipt['continuation']['status'] == 'error'
            assert student.load(folder)['message'] == 'NEW question'
            assert len(list(folder.glob('step-*.json'))) == 2
        else:
            assert files(folder) == before
            assert receipt['status'] == ('pending' if mode == 'interrupt' else 'error')
        with pytest.raises((ValueError, FileExistsError)):
            tutor.respond(folder, output, policy='Give a brief hint.', generate_tutor=lambda *_: pytest.fail('resend'),
                          generate_student=lambda *_: pytest.fail('student resend'), check=None)


def test_invalid_tutor_requests_and_reply_schema_fail_before_output_or_dispatch(tmp_path):
    tutor = api()
    for invalid in ({'text':''}, {'text':' \n '}, {'text':None}, {'text':7}, {'text':'A hint.', 'source':'code'}):
        with pytest.raises(ValueError):
            tutor.Reply.model_validate(invalid)
    for index, mode in enumerate(('active', 'terminal', 'budget', 'policy', 'nonstring-policy',
                                  'model', 'zero-actions', 'bool-actions', 'many-actions')):
        folder, output = tmp_path / str(index), tmp_path / f'{index}-exchange'
        student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/' + str(index),
                       max_decisions=1 if mode == 'budget' else 12)
        if mode == 'terminal':
            choose(folder, 'no-reply', text='')
        elif mode != 'active':
            choose(folder)
        student.load(folder)  # Establish the existing session lock before comparing persisted files.
        before = files(folder)
        options = {'policy':'A brief hint.', 'model':'gemini-2.5-pro', 'max_actions':3}
        options.update({'policy':{'policy':' \n ', 'nonstring-policy':None}.get(mode, options['policy']),
                        'model':'' if mode == 'model' else options['model'],
                        'max_actions':{'zero-actions':0, 'bool-actions':True, 'many-actions':7}.get(mode, 3)})
        with pytest.raises(ValueError):
            tutor.respond(folder, output, generate_tutor=lambda *_: pytest.fail('invalid tutor request dispatched'),
                          generate_student=lambda *_: pytest.fail('invalid student request dispatched'), check=None, **options)
        assert not output.exists() and files(folder) == before


@pytest.mark.parametrize('ending', ['no-reply', 'environment-error'])
def test_cli_requires_send_and_reports_student_failure(tmp_path, monkeypatch, capsys, ending):
    import sys
    tutor = api()
    monkeypatch.setenv('GEMINI_API_KEY', 'invented-test-key')
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Invalid input reached provider'))
    folder, output, policy = tmp_path / 'student', tmp_path / 'exchange', tmp_path / 'policy.txt'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/cli')
    choose(folder)
    policy.write_text('Offer a brief hint.\n')
    argv = ['notebook_tutor', str(folder), '--output', str(output), '--policy-file', str(policy)]
    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'Use supported column access.', 'source':'Authored CLI reference.'}
    reference_path = tmp_path / 'reference.json'
    reference_path.write_text(json.dumps(reference))
    if ending == 'no-reply':
        argv += ['--reference-file', str(reference_path)]
    monkeypatch.setattr(sys, 'argv', argv)
    with pytest.raises(SystemExit) as missing:
        tutor.main()
    assert missing.value.code == 2 and not output.exists()
    capsys.readouterr()
    if ending == 'no-reply':
        reference_path.write_text('null')
        monkeypatch.setattr(sys, 'argv', argv + ['--send'])
        with pytest.raises(ValueError):
            tutor.main()
        assert not output.exists()
        reference_path.write_text(json.dumps(reference))

    def generate(prompt, schema):
        if schema is tutor.Reply:
            return schema(text='Count distinct shades.\n')
        return schema(decision='request-check' if ending == 'environment-error' else 'no-reply', text='', source=None)

    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:generate)
    monkeypatch.setattr(student.notebook_runtime, 'check_work',
                        lambda *a, **kw:observation(*a, **kw, status='environment-error'))
    monkeypatch.setattr(sys, 'argv', argv + ['--send'])
    if ending == 'environment-error':
        with pytest.raises(SystemExit) as failed:
            tutor.main()
        assert failed.value.code == 1
    else:
        tutor.main()
    assert student.load(folder)['status'] == ending
    rendered = capsys.readouterr().out
    assert 'Tutor reply:' in rendered and 'Count distinct shades.' in rendered and ending in rendered
    assert student._read(output / 'receipt.json')['response']['text'] == 'Count distinct shades.\n'
    if ending == 'no-reply':
        assert student._read(output / 'receipt.json')['request']['library_reference'] == reference


def test_library_reference_is_recorded_exactly_and_seen_only_by_tutor(tmp_path):
    tutor = api()
    folder, output = tmp_path / 'student', tmp_path / 'exchange'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/reference')
    choose(folder)
    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'  REFERENCE_ONLY: table.get(column) selects a column.\n',
                 'source':'SOURCE_ONLY: an authored reference for this test.\n'}

    def generate_tutor(prompt, schema):
        payload = json.loads(prompt[prompt.index('{'):])
        assert payload['library_reference'] == reference
        assert student._read(output / 'receipt.json')['request']['library_reference'] == reference
        return schema(text='Select the column first.')

    def generate_student(prompt, schema):
        assert all(marker not in prompt for marker in ('REFERENCE_ONLY', 'SOURCE_ONLY', 'library_reference'))
        return schema(decision='no-reply', text='', source=None)

    result = tutor.respond(folder, output, policy='Give a brief hint.', reference=reference,
        generate_tutor=generate_tutor, generate_student=generate_student, check=None)
    assert result['state']['status'] == 'no-reply' and student.load(folder) == result['state']
    assert result['state']['dialogue'][-1]['text'] == 'Select the column first.'
    assert all(marker not in json.dumps(result['state']) for marker in ('REFERENCE_ONLY', 'SOURCE_ONLY'))


def test_invalid_library_reference_fails_before_output_or_dispatch(tmp_path):
    tutor = api()
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/reference-invalid')
    choose(folder)
    before = files(folder)
    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'Use supported column access.', 'source':'Authored reference.'}
    invalid = [reference | {'library':'another-library'}, reference | {'library_version':'0.0.0'},
               reference | {'extra':'unexpected'}, reference | {'text':1},
               {key:value for key,value in reference.items() if key != 'source'}, []]
    invalid += [reference | {key:' \n '} for key in reference]
    for index, candidate in enumerate(invalid):
        output = tmp_path / f'exchange-{index}'
        with pytest.raises(ValueError):
            tutor.respond(folder, output, policy='Give a brief hint.', reference=candidate,
                generate_tutor=lambda *_: pytest.fail('Invalid reference dispatched'),
                generate_student=lambda *_: pytest.fail('Invalid reference continued student'), check=None)
        assert not output.exists() and files(folder) == before
