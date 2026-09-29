"""Authored source-only comparison: shared input, bounded calls, and verified replay."""
import importlib.util
import json
from pathlib import Path
from threading import Event

import pytest

from src.agents import notebook_branch as branch, notebook_student as store


def runner():
    path = Path(__file__).resolve().parents[1]/'experiments/2026-09-29-notebook-policy-sampling/run.py'
    spec = importlib.util.spec_from_file_location('policy_sampling_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw(value, finish='STOP'):
    return {'candidates':[{'finish_reason':finish, 'content':{'parts':[{'text':json.dumps(value)}]}}]}


def source(tmp_path):
    folder = tmp_path/'source'
    branch.create(folder, recovered={
        'notebook':{'recorded_at':'2026-01-01T00:00:00Z', 'cells':[
            {'cell_type':'markdown', 'source':'Add both values.'},
            {'cell_type':'code', 'source':'total = 3'}]},
        'exchange':[{'role':'student', 'text':'check?'},
                    {'role':'tutor', 'text':'ORIGINAL_TUTOR_SENTINEL'}],
        'future':'FUTURE_SENTINEL'}, instruction_cells=[0], work_cell=1)
    return folder


def test_fixed_pair_reuses_only_captured_state_and_reopens_without_sending(tmp_path):
    module, original = runner(), source(tmp_path)
    frozen = (original/'checkpoint.json').read_bytes()
    destination = tmp_path/'comparison'
    plan = module.prepare(destination, original)
    assert plan['max_provider_calls'] == 62
    calls = []
    entered = {'direct':Event(), 'hint':Event()}
    def tutor(plan, prompt):
        calls.append(('tutor', prompt))
        assert (destination/'started.json').exists()
        assert any(store._read(p)['status'] == 'pending' for p in destination.glob('tutor-*.json'))
        return raw({'text':'Try adding four.' if len(calls) == 1 else 'Which value is missing?'})
    def student(plan, prompt):
        calls.append(('student', prompt))
        condition = 'direct' if 'Try adding four.' in prompt else 'hint'
        entered[condition].set()
        assert entered['hint' if condition == 'direct' else 'direct'].wait(2)
        return raw({'decision':'revise-work', 'text':'', 'source':'total = 3 + 4'})
    with pytest.raises(ValueError, match='send'):
        module.execute(destination, generate_tutor=tutor, generate_student=student)
    assert calls == []
    result = module.execute(destination, send=True, generate_tutor=tutor, generate_student=student)
    assert len(calls) == 62
    assert 'ORIGINAL_TUTOR_SENTINEL' not in str(calls) and 'FUTURE_SENTINEL' not in str(calls)
    assert all('total = 3 + 4' not in prompt for _,prompt in calls)
    assert len(set(prompt for kind,prompt in calls if kind == 'student')) == 2
    for item in result['conditions'].values():
        assert item['valid'] == 30 and item['failed'] == 0
        assert item['task']['work'] == {'cell_index':1, 'source':'total = 3', 'revision':0}
        assert item['task']['observation'] is None
        assert len(item['task']['dialogue']) == 2
    assert module.load(destination) == result
    assert (original/'checkpoint.json').read_bytes() == frozen
    with pytest.raises(FileExistsError):
        module.execute(destination, send=True, generate_tutor=tutor, generate_student=student)
    assert len(calls) == 62
    aggregate = module.aggregate(result)
    assert not any(text in json.dumps(aggregate) for text in ('total =', 'check?', 'Try adding', 'Which value'))
    receipt = destination/'report.json'
    changed = store._read(receipt)
    changed['report']['conditions']['direct']['valid'] = 29
    changed['sha256'] = store.digest(changed['report'])
    store._save(receipt, changed)
    with pytest.raises(ValueError):
        module.load(destination)


def test_failed_tutor_and_invalid_student_are_retained_without_replacement(tmp_path):
    module, original = runner(), source(tmp_path)
    destination = tmp_path/'comparison'
    module.prepare(destination, original)
    tutors, students = [], []
    def tutor(plan, prompt):
        tutors.append(prompt)
        return raw({'text':'Which number?'}, 'MAX_TOKENS' if len(tutors) == 1 else 'STOP')
    def student(plan, prompt):
        students.append(prompt)
        return raw({'decision':'no-reply', 'text':'', 'source':None},
                   'MAX_TOKENS' if len(students) == 1 else 'STOP')
    result = module.execute(destination, send=True, generate_tutor=tutor, generate_student=student)
    assert len(tutors) == 2 and len(students) == 30
    assert result['conditions']['direct']['tutor_status'] == 'error'
    assert result['conditions']['direct']['records'] == []
    assert result['conditions']['hint']['valid'] == 29 and result['conditions']['hint']['failed'] == 1
    assert module.load(destination) == result
    changed = store._read(original/'checkpoint.json')
    changed['task']['observation'] = {'value':'UNSEEN_EXECUTION'}
    changed['prompt'] = branch.action.make_prompt(changed['task'])
    store._save(original/'checkpoint.json', changed)
    with pytest.raises(ValueError):
        module.load(destination)
