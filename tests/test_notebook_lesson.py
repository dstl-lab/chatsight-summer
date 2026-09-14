"""The lesson wrapper schedules existing student and tutor transactions once."""
import importlib.util
import json
import sys

import pytest

from src.agents import notebook_student as student
from src.eval import notebook_runtime as runtime
from src.eval.notebook_session import Action
from tests.test_notebook_session import ACTIVITY, TASK, observation
from tests.test_task_evaluation import worker


def api():
    assert importlib.util.find_spec('src.agents.notebook_lesson'), 'Bounded notebook lesson is missing'
    from src.agents import notebook_lesson
    return notebook_lesson


def files(folder):
    return {str(path.relative_to(folder)):path.read_bytes() for path in folder.rglob('*') if path.is_file()}


def test_complete_lesson_reuses_private_evaluation_and_both_tutor_exchanges(tmp_path, monkeypatch):
    lesson = api()
    requests = worker(monkeypatch, 2 / 3)
    folder, evaluation = tmp_path / 'student', {'expected':2 / 3}
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/lesson',
                   evaluation=evaluation, max_decisions=8)
    choices = iter([
        Action(decision='reply', text='help', source=None),
        Action(decision='revise-work', text='', source='n_shades = 2 / 3'),
        Action(decision='request-check', text='', source=None),
        Action(decision='reply', text='is that right', source=None),
        Action(decision='no-reply', text='', source=None),
    ])
    prompts, tutor_prompts = [], []

    def generate_student(prompt, schema):
        assert student._read(folder / 'lesson/receipt.json')['status'] == 'pending'
        prompts.append(prompt)
        return next(choices)

    def generate_tutor(prompt, schema):
        assert student._read(folder / 'lesson/receipt.json')['status'] == 'pending'
        tutor_prompts.append(prompt)
        return schema(text='Consider the fraction of matching rows.')

    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'REFERENCE_ONLY: select a column with get().', 'source':'Authored test note.'}
    result = lesson.run(folder, policy='A short hint.', generate_student=generate_student,
                        generate_tutor=generate_tutor, check=runtime.check_work, reference=reference)
    assert result['stop_reason'] == 'no-reply'
    assert result['student_decisions'] == 5 and result['tutor_turns'] == 2
    assert result['state'] == student.load(folder) and result['state']['evaluation'] == evaluation
    assert result['state']['observation']['success'] is True and len(requests) == 1
    assert len(prompts) == 5 and len(tutor_prompts) == 2
    for prompt in prompts + tutor_prompts:
        assert 'evaluation' not in prompt and student.digest(evaluation) not in prompt
    assert all('REFERENCE_ONLY' not in prompt for prompt in prompts)
    assert all('REFERENCE_ONLY' in prompt for prompt in tutor_prompts)
    receipt = student._read(folder / 'lesson/receipt.json')
    assert receipt['status'] == 'complete' and receipt['result'] == result
    assert len(list((folder / 'lesson').glob('tutor-*'))) == 2
    assert len(list(folder.glob('step-*.json'))) == 5
    before = files(folder)
    with pytest.raises(FileExistsError):
        lesson.run(folder, policy='A short hint.', generate_student=None, generate_tutor=None, check=None)
    assert files(folder) == before


def test_tutor_cap_allows_remaining_quiet_work_and_preserves_pending_message(tmp_path):
    lesson = api()
    folder = tmp_path / 'capped'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/capped', max_decisions=8)
    choices = iter([
        Action(decision='reply', text='help', source=None),
        Action(decision='revise-work', text='', source='n_shades = 2'),
        Action(decision='request-check', text='', source=None),
        Action(decision='reply', text='this?', source=None),
    ])
    tutor_calls = []

    def generate_tutor(prompt, schema):
        tutor_calls.append(prompt)
        return schema(text='Check distinct values.')

    result = lesson.run(folder, policy='A hint.', max_tutor_turns=1,
        generate_student=lambda *_:next(choices), generate_tutor=generate_tutor,
        check=lambda *a, **kw:observation(*a, **kw, status='checked'))
    assert result['stop_reason'] == 'tutor-budget' and result['student_decisions'] == 4
    assert result['tutor_turns'] == len(tutor_calls) == 1
    assert result['state']['status'] == 'awaiting-tutor' and result['state']['message'] == 'this?'
    assert result['state']['work']['revision'] == 1 and result['state']['observation']['success'] is True
    assert result['state'] == student.load(folder)


def test_student_budget_terminal_and_provider_failure_are_distinct(tmp_path):
    lesson = api()
    for ending, expected in (('reply', 'student-budget'), ('revise-work', 'student-budget'),
                             ('no-reply', 'no-reply'), ('provider-error', 'error'),
                             ('environment-error', 'environment-error'), ('execution-limit', 'execution-limit')):
        folder = tmp_path / ending
        student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/' + ending, max_decisions=1)

        def generate(prompt, schema):
            if ending == 'provider-error':
                raise RuntimeError('Authored provider failure')
            decision = 'request-check' if ending in ('environment-error', 'execution-limit') else ending
            return schema(decision=decision, text='help' if decision == 'reply' else '',
                          source='n_shades = 1' if decision == 'revise-work' else None)

        result = lesson.run(folder, policy='A hint.', max_tutor_turns=0, generate_student=generate,
            generate_tutor=lambda *_:pytest.fail('Tutor called after terminal/budget stop'),
            check=lambda *a, **kw:observation(*a, **kw, status=ending))
        assert result['stop_reason'] == expected and result['student_decisions'] == 1
        assert result['tutor_turns'] == 0 and result['state'] == student.load(folder)
        if ending == 'provider-error':
            assert result['state']['history'] == []


def test_interrupted_or_failed_tutor_cannot_be_automatically_sent_again(tmp_path):
    lesson = api()
    for error, expected in ((KeyboardInterrupt, 'pending'), (RuntimeError, 'error')):
        folder = tmp_path / error.__name__
        student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/interrupted')

        def generate_tutor(prompt, schema):
            assert student._read(folder / 'lesson/tutor-0001/receipt.json')['status'] == 'pending'
            raise error('Authored interruption')

        with pytest.raises(error):
            lesson.run(folder, policy='A hint.',
                generate_student=lambda *_:Action(decision='reply', text='help', source=None),
                generate_tutor=generate_tutor, check=None)
        assert student._read(folder / 'lesson/receipt.json')['status'] == expected
        assert student.load(folder)['status'] == 'awaiting-tutor'
        before = files(folder)
        with pytest.raises(FileExistsError):
            lesson.run(folder, policy='A hint.', generate_student=None, generate_tutor=None, check=None)
        assert files(folder) == before


def test_invalid_lesson_inputs_fail_before_output_or_provider(tmp_path):
    lesson = api()
    folder = tmp_path / 'invalid'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/invalid')
    reference = {'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                 'text':'An API note.', 'source':'Authored.'}
    for options in ({'policy':''}, {'policy':None}, {'max_tutor_turns':True}, {'max_tutor_turns':-1},
                    {'max_tutor_turns':11}, {'reference':{}},
                    {'reference':reference | {'library':'wrong'}},
                    {'reference':reference | {'library_version':'wrong'}}):
        with pytest.raises(ValueError):
            lesson.run(folder, **({'policy':'A hint.'} | options),
                generate_student=lambda *_:pytest.fail('Invalid input dispatched student'),
                generate_tutor=lambda *_:pytest.fail('Invalid input dispatched tutor'), check=None)
        assert not (folder / 'lesson').exists()
    assert not list(folder.glob('step-*.json'))


def test_cli_send_and_null_guards_and_failure_exit(tmp_path, monkeypatch, capsys):
    lesson = api()
    folder, policy, reference = tmp_path / 'cli', tmp_path / 'policy.txt', tmp_path / 'reference.json'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/cli')
    policy.write_text('A short hint.')
    reference.write_text('null')
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Invalid CLI reached provider'))
    args = ['notebook_lesson', str(folder), '--policy-file', str(policy), '--reference-file', str(reference)]
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(SystemExit) as missing:
        lesson.main()
    assert missing.value.code == 2 and not (folder / 'lesson').exists()
    monkeypatch.setattr(sys, 'argv', args + ['--send'])
    with pytest.raises(ValueError):
        lesson.main()
    assert not (folder / 'lesson').exists()
    capsys.readouterr()
    reference.write_text(json.dumps({'library':ACTIVITY['library'], 'library_version':ACTIVITY['library_version'],
                                    'text':'An API note.', 'source':'Authored.'}))
    monkeypatch.setenv('GEMINI_API_KEY', 'invented-test-key')
    monkeypatch.setattr(student.llm, 'make_generate',
        lambda *a, **kw:lambda prompt, schema:schema(decision='request-check', text='', source=None))
    monkeypatch.setattr(runtime, 'check_work', lambda *a, **kw:observation(*a, **kw, status='environment-error'))
    with pytest.raises(SystemExit) as failed:
        lesson.main()
    assert failed.value.code == 1 and student.load(folder)['status'] == 'environment-error'
