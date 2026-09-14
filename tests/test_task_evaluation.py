"""Private scalar evaluators reuse the notebook action loop without entering prompts."""
from copy import deepcopy
import json
import os
import sys

import pytest

from src.agents import notebook_student as student, notebook_tutor as tutor, tutor_context
from src.eval import notebook_runtime as runtime, notebook_session as session
from tests.test_notebook_session import ACTIVITY, TASK


def worker(monkeypatch, value):
    """A protocol double, never a Docker or model invocation."""
    requests = []
    monkeypatch.setattr(runtime, '_local_docker', lambda _: ['authored-docker-double'])

    def execute(command, image, request, timeout):
        requests.append(deepcopy(request))
        header = {'kind':'runtime', 'python':'authored', 'library':request['library'],
                  'libraries':{request['library']:request['library_version']}}
        response = {'kind':'value', 'value':value, 'output':''}
        return 0, (json.dumps(header) + '\n' + json.dumps(response) + '\n').encode(), None

    monkeypatch.setattr(runtime, '_execute', execute)
    return requests


def test_evaluation_accepts_only_one_finite_scalar_without_coercion():
    assert hasattr(runtime, 'Evaluation'), 'Private task evaluation is not implemented'
    for expected in ('answer', '', 2, 2.0, True, False):
        actual = runtime.Evaluation.model_validate({'expected':expected}).expected
        assert type(actual) is type(expected) and actual == expected
    for invalid in (None, {}, {'expected':None}, {'expected':[]}, {'expected':{}},
                    {'expected':float('nan')}, {'expected':float('inf')},
                    {'expected':-float('inf')}, {'expected':2, 'extra':'hidden'}):
        with pytest.raises(ValueError):
            runtime.Evaluation.model_validate(invalid)


def test_private_scalar_grades_are_typed_and_not_sent_to_worker(monkeypatch):
    assert hasattr(runtime, 'Evaluation'), 'Private task evaluation is not implemented'
    work = {'source':'n_shades = 0', 'revision':0}
    for expected, actual, passed in (
            (2, 2, True), (2, 3, False), (2, 2.0, False), (1, True, False),
            (True, True, True), (False, 0, False), ('2', '2', True), ('2', 2, False),
            (2 / 3, 2 / 3, True), (2 / 3, 0.5, False), (2.0, 2, False)):
        requests = worker(monkeypatch, actual)
        observation = runtime.check_work(work, branch_id='authored/scalar', activity=ACTIVITY,
                                         evaluation={'expected':expected})
        assert observation['status'] == 'checked' and observation['success'] is passed
        assert observation['value'] == actual
        assert requests == [{key:value for key,value in ACTIVITY.items() if key != 'image_id'}
                            | {'source':work['source']}]
    worker(monkeypatch, 2)
    legacy = runtime.check_work(work, branch_id='authored/legacy', activity=ACTIVITY)
    assert legacy['success'] is True and 'evaluation_sha256' not in legacy['binding']
    legacy['binding']['checker_sha256'] = runtime.DISTINCT_COUNT_SOURCE
    runtime.require_current(legacy, work, branch_id='authored/legacy', activity=ACTIVITY)
    with pytest.raises(ValueError):
        runtime.require_current(legacy, work, branch_id='authored/legacy', activity=ACTIVITY,
                                evaluation={'expected':2})
    legacy['binding']['checker_sha256'] = 'unknown'
    with pytest.raises(ValueError):
        runtime.require_current(legacy, work, branch_id='authored/legacy', activity=ACTIVITY)


def test_feedback_binds_the_private_evaluation_and_rejects_swaps(monkeypatch):
    assert hasattr(runtime, 'Evaluation'), 'Private task evaluation is not implemented'
    worker(monkeypatch, 2 / 3)
    work, evaluation = {'source':'n_shades = 2 / 3', 'revision':1}, {'expected':2 / 3}
    options = {'branch_id':'authored/fraction', 'activity':ACTIVITY}
    observed = runtime.check_work(work, evaluation=evaluation, **options)
    assert observed['binding']['evaluation_sha256'] == student.digest(evaluation)
    assert runtime._binding(work, options['branch_id'], runtime.Activity.model_validate(ACTIVITY),
                            10, evaluation=evaluation) == observed['binding']
    runtime.require_current(observed, work, evaluation=evaluation, **options)
    old_checker = deepcopy(observed)
    old_checker['binding']['checker_sha256'] = runtime.DISTINCT_COUNT_SOURCE
    with pytest.raises(ValueError):
        runtime.require_current(old_checker, work, evaluation=evaluation, **options)
    for changed in (None, {'expected':0.5}, {'expected':'0.6666666666666666'}):
        with pytest.raises(ValueError):
            runtime.require_current(observed, work, evaluation=changed, **options)
    with pytest.raises(ValueError):
        runtime.require_current(observed, work | {'revision':2}, evaluation=evaluation, **options)
    with pytest.raises(ValueError):
        runtime.check_work(work, evaluation={'expected':None}, **options)


def test_saved_evaluation_stays_out_of_student_and_tutor_inputs_and_edits_clear_feedback(tmp_path, monkeypatch):
    assert hasattr(runtime, 'Evaluation'), 'Private task evaluation is not implemented'
    worker(monkeypatch, 'public attempt')
    evaluation = {'expected':'PRIVATE_EXPECTED_SENTINEL'}
    folder, exchange = tmp_path / 'student', tmp_path / 'tutor'
    initial = session.initial_state(TASK, activity=ACTIVITY, branch_id='authored/private', evaluation=evaluation)
    assert initial['evaluation'] == evaluation
    assert 'evaluation' not in session.initial_state(TASK, activity=ACTIVITY, branch_id='authored/legacy')
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/private', evaluation=evaluation)
    inputs = []

    def choose(decision, text='', source=None):
        def generate(prompt, schema):
            inputs.append(prompt)
            return schema(decision=decision, text=text, source=source)
        return generate

    checked = student.step(folder, generate=choose('request-check'), check=runtime.check_work, max_actions=1)
    assert checked['state']['observation']['success'] is False
    assert student.load(folder) == checked['state']
    student.step(folder, generate=choose('reply', text='still stuck'), check=runtime.check_work, max_actions=1)
    packet = tutor_context.snapshot(folder)
    assert packet['feedback']['success'] is False and 'evaluation' not in packet

    def generate_tutor(prompt, schema):
        inputs.append(prompt)
        return schema(text='Try revising the selected cell.')

    revised = tutor.respond(folder, exchange, policy='Give a brief hint.', generate_tutor=generate_tutor,
        generate_student=choose('revise-work', source='n_shades = 0'), check=runtime.check_work, max_actions=1)
    assert revised['state']['observation'] is None and revised['state']['work']['revision'] == 1
    assert revised['state']['history'][0]['observation']['success'] is False
    assert revised['state']['evaluation'] == evaluation and student.load(folder) == revised['state']
    for prompt in inputs:
        assert all(secret not in prompt for secret in ('PRIVATE_EXPECTED_SENTINEL', 'evaluation', student.digest(evaluation)))
    assert 'evaluation' not in json.dumps(student._read(exchange / 'context.json'))
    assert student._read(folder / 'session.json')['initial']['evaluation'] == evaluation
    assert student._read(folder / 'step-0001.json')['calls'][1]['request']['evaluation'] == evaluation


def test_cli_evaluation_is_create_only_and_explicit_null_is_invalid(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('CLI validation dispatched provider'))
    task_path, activity_path, evaluation_path = (tmp_path / name for name in ('task.json', 'activity.json', 'evaluation.json'))
    task_path.write_text(json.dumps(TASK))
    activity_path.write_text(json.dumps(ACTIVITY))
    evaluation_path.write_text('null')
    folder = tmp_path / 'invalid'
    args = ['notebook_student', 'create', str(folder), '--task', str(task_path), '--activity', str(activity_path),
            '--evaluation-file', str(evaluation_path)]
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(ValueError):
        student.main()
    assert not folder.exists()
    evaluation = {'expected':2 / 3}
    evaluation_path.write_text(json.dumps(evaluation))
    folder = tmp_path / 'valid'
    args[2] = str(folder)
    monkeypatch.setattr(sys, 'argv', args)
    student.main()
    assert student.load(folder)['evaluation'] == evaluation
    capsys.readouterr()
    before = {path.name:path.read_bytes() for path in folder.iterdir()}
    for command in ('show', 'step'):
        monkeypatch.setattr(sys, 'argv', ['notebook_student', command, str(folder),
                                       '--evaluation-file', str(evaluation_path)])
        with pytest.raises(SystemExit) as rejected:
            student.main()
        assert rejected.value.code == 2
    assert {path.name:path.read_bytes() for path in folder.iterdir()} == before


@pytest.mark.skipif(not os.environ.get('NOTEBOOK_RUNTIME_IMAGE'), reason='Explicit local container image required')
def test_same_executor_checks_distinct_count_and_category_fraction():
    activity = ACTIVITY | {'image_id':os.environ['NOTEBOOK_RUNTIME_IMAGE']}
    count = runtime.check_work({'source':"n_shades = len(swatches.get('shade').unique())", 'revision':0},
                               branch_id='authored/count', activity=activity)
    fraction = runtime.check_work({'source':"n_shades = (swatches.get('shade') == 'red').sum() / len(swatches.get('shade'))", 'revision':0},
                                  branch_id='authored/fraction', activity=activity, evaluation={'expected':2 / 3})
    assert count['status'] == fraction['status'] == 'checked'
    assert count['success'] is True and count['value'] == 2
    assert fraction['success'] is True and fraction['value'] == 2 / 3
