"""A new task carries observed experience without reopening its predecessor."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from src.agents import notebook_student as student, notebook_tutor as tutor, tutor_context
from src.eval import notebook_runtime as runtime, notebook_session as session
from tests.test_notebook_lesson import files
from tests.test_notebook_session import ACTIVITY, TASK
from tests.test_task_evaluation import worker


def api():
    assert importlib.util.find_spec('src.agents.notebook_next_task'), 'Next-task initialization is missing'
    from src.agents import notebook_next_task
    return notebook_next_task


def finished(folder, *, task=TASK, evaluation=None, check=None):
    student.create(folder, task=task, activity=ACTIVITY, evaluation=evaluation,
                   branch_id='authored/previous', model='authored-model', max_decisions=4)
    actions = ([session.Action(decision='request-check', text='', source=None)] if check else [])
    actions.append(session.Action(decision='no-reply', text='', source=None))
    choices = iter(actions)
    return student.step(folder, generate=lambda *_:next(choices), check=check, max_actions=len(actions))['state']


def test_new_task_keeps_observed_history_separate_from_current_state_and_provenance(tmp_path, monkeypatch):
    next_task = api()
    worker(monkeypatch, 2)
    previous, folder = tmp_path / 'PRIVATE_PARENT_PATH', tmp_path / 'next'
    old_task = deepcopy(TASK)
    old_task['initialization'] = {'previous_encounter':'OLDER_ENCOUNTER_SENTINEL'}
    old_state = finished(previous, task=old_task, evaluation={'expected':2}, check=runtime.check_work)
    old_manifest = student._read(previous / 'session.json')
    before = files(previous)
    task = deepcopy(TASK)
    task.update(initialization='A separately authored next encounter.', task='Find a category proportion.')
    task['work'] = {'cell_index':5, 'source':'fraction = 0', 'revision':0}
    activity = ACTIVITY | {'result':'fraction'}
    evaluation = {'expected':'PRIVATE_NEW_EXPECTED'}
    next_task.create(previous, folder, task=task, activity=activity, evaluation=evaluation, max_decisions=3)
    state = student.load(folder)
    manifest = student._read(folder / 'session.json')
    assert state['status'] == 'active' and state['message'] is None
    assert state['work'] == task['work'] and state['activity'] == activity
    assert state['evaluation'] == evaluation and state['observation'] is None and state['history'] == []
    assert state['dialogue'] == task['dialogue']
    assert manifest['model'] == 'authored-model' and manifest['max_decisions'] == 3
    assert state['branch_id'] != old_state['branch_id']
    packet = json.loads(session.make_prompt(state).split('\nSTATE JSON:\n')[1])
    assert packet['initialization']['current_task'] == task['initialization']
    memory = packet['initialization']['previous_encounter']
    assert memory['task'] == old_task['task'] and memory['work'] == old_state['work']
    assert memory['dialogue'] == old_state['dialogue'] and memory['status'] == 'no-reply'
    assert memory['observation']['success'] is True and memory['observation']['value'] == 2
    assert memory['history'][0]['observation']['success'] is True
    assert memory['history'][-1]['action']['decision'] == 'no-reply'
    provenance = json.dumps(manifest['provenance']['previous_encounter'])
    for value in (str(previous.resolve()), student.digest(old_manifest), student.digest(old_state),
                  student.digest(Path(next_task.__file__).read_text())):
        assert value in provenance
    assert not list(folder.glob('step-*.json'))
    prompts = [session.make_prompt(state), json.dumps(tutor_context.snapshot(folder))]
    student.step(folder, generate=lambda *_:session.Action(decision='reply', text='help', source=None),
                 check=None, max_actions=1)

    def generate_tutor(prompt, schema):
        prompts.append(prompt)
        return schema(text='Consider the fraction of matching rows.')

    tutor.respond(folder, tmp_path / 'exchange', policy='A short hint.', generate_tutor=generate_tutor,
                  generate_student=lambda *_:session.Action(decision='no-reply', text='', source=None),
                  check=None, max_actions=1)
    for prompt in prompts:
        for secret in ('PRIVATE_NEW_EXPECTED', str(previous.resolve()), 'OLDER_ENCOUNTER_SENTINEL',
                       'evaluation', 'image_id', student.digest({'expected':2}), student.digest(evaluation)):
            assert secret not in prompt
    assert student.load(previous) == old_state and files(previous) == before
    sibling = next_task.create(previous, tmp_path / 'another' / folder.name, task=task, activity=activity)
    assert sibling['branch_id'] != state['branch_id']
    with pytest.raises(ValueError, match='terminal'):
        student.step(previous, generate=None, check=None)
    assert files(previous) == before


def test_private_old_evaluator_is_excluded_even_when_its_check_failed(tmp_path, monkeypatch):
    next_task = api()
    worker(monkeypatch, 'public attempt')
    previous, folder = tmp_path / 'previous', tmp_path / 'next'
    old = finished(previous, evaluation={'expected':'PRIVATE_OLD_EXPECTED'}, check=runtime.check_work)
    assert old['observation']['success'] is False
    next_task.create(previous, folder, task=TASK, activity=ACTIVITY)
    state = student.load(folder)
    for prompt in (session.make_prompt(state), json.dumps(tutor_context.snapshot(folder))):
        assert 'PRIVATE_OLD_EXPECTED' not in prompt and 'evaluation' not in prompt
        assert 'public attempt' in prompt
    assert state['observation'] is None


def test_unfinished_failed_and_authored_stops_cannot_create_a_follow_on(tmp_path):
    next_task = api()
    for ending in ('active', 'awaiting-tutor', 'budget', 'error', 'scripted-stop'):
        previous, folder = tmp_path / ending, tmp_path / (ending + '-next')
        student.create(previous, task=TASK, activity=ACTIVITY, branch_id='authored/' + ending,
                       max_decisions=1 if ending == 'budget' else 4)
        if ending == 'awaiting-tutor':
            student.step(previous, generate=lambda *_:session.Action(decision='reply', text='help', source=None), check=None)
        elif ending == 'budget':
            student.step(previous, generate=lambda *_:session.Action(decision='revise-work', text='', source='n_shades = 0'),
                         check=None, max_actions=1)
        elif ending == 'error':
            def fail(*_):
                raise RuntimeError('Authored provider error')
            student.step(previous, generate=fail, check=None)
        elif ending == 'scripted-stop':
            manifest = student._read(previous / 'session.json')
            manifest['initial'] = session.advance(manifest['initial'],
                session.Action(decision='no-reply', text='', source=None), check=None, origin='scripted')
            student._save(previous / 'session.json', manifest)
        student.load(previous)
        before = files(previous)
        with pytest.raises(ValueError):
            next_task.create(previous, folder, task=TASK, activity=ACTIVITY)
        assert not folder.exists() and files(previous) == before


def test_utf8_limit_rejects_oversized_context(tmp_path):
    next_task = api()
    previous, folder = tmp_path / 'large', tmp_path / 'next'
    task = deepcopy(TASK)
    task['task'] = '가' * 22000  # Under 64k characters, over 64k UTF-8 bytes.
    finished(previous, task=task)
    before = files(previous)
    with pytest.raises(ValueError):
        next_task.create(previous, folder, task=TASK, activity=ACTIVITY)
    assert not folder.exists() and files(previous) == before


def test_cli_initializes_without_provider_and_rejects_explicit_null(tmp_path, monkeypatch, capsys):
    next_task = api()
    previous, folder = tmp_path / 'previous', tmp_path / 'cli'
    finished(previous)
    task, activity, evaluation = (tmp_path / name for name in ('task.json', 'activity.json', 'evaluation.json'))
    task.write_text(json.dumps(TASK))
    activity.write_text(json.dumps(ACTIVITY))
    evaluation.write_text('null')
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Initialization dispatched a provider'))
    args = ['notebook_next_task', str(previous), str(folder), '--task', str(task), '--activity', str(activity),
            '--evaluation-file', str(evaluation), '--max-decisions', '2']
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(ValueError):
        next_task.main()
    assert not folder.exists()
    evaluation.write_text(json.dumps({'expected':2 / 3}))
    next_task.main()
    capsys.readouterr()
    assert student.load(folder)['evaluation'] == {'expected':2 / 3}
    assert student._read(folder / 'session.json')['max_decisions'] == 2
    assert not list(folder.glob('step-*.json'))


def test_interrupted_provenance_write_never_publishes_a_runnable_child(tmp_path, monkeypatch):
    next_task = api()
    previous, folder = tmp_path / 'previous', tmp_path / 'next'
    finished(previous)
    save = student._save
    interrupted = []

    def interrupt_provenance(path, value, **kwargs):
        if 'previous_encounter' in value.get('provenance', {}):
            interrupted.append(path)
            assert not (folder / 'session.json').exists(), 'Child published before provenance was saved'
            raise KeyboardInterrupt('Authored interruption while saving provenance')
        return save(path, value, **kwargs)

    monkeypatch.setattr(student, '_save', interrupt_provenance)
    with pytest.raises(KeyboardInterrupt):
        next_task.create(previous, folder, task=TASK, activity=ACTIVITY)
    assert len(interrupted) == 1 and not (folder / 'session.json').exists()
    with pytest.raises((OSError, ValueError)):
        student.load(folder)
    with pytest.raises((OSError, ValueError)):
        student.step(folder, generate=lambda *_:pytest.fail('Interrupted child reached provider'), check=None)


def test_multiple_tasks_keep_flat_verified_history_in_both_agents_and_replay(tmp_path, monkeypatch):
    from src.eval import notebook_replay

    next_task = api()
    worker(monkeypatch, 'FIRST_OBSERVED_VALUE')
    first = tmp_path / 'first'
    task = deepcopy(TASK)
    task.update(task='First task', initialization={'earlier_encounters':'UNVERIFIED_INITIALIZATION'})
    finished(first, task=task, evaluation={'expected':'PRIVATE_FIRST_EXPECTED'}, check=runtime.check_work)
    folders, states = [first], [student.load(first)]
    for number in (2, 3, 4):
        folder = tmp_path / str(number)
        task = deepcopy(TASK)
        task.update(task=f'Task {number}', initialization='Fresh supplied context')
        before = [files(path) for path in folders]
        initial = next_task.create(folders[-1], folder, task=task, activity=ACTIVITY,
                                   evaluation={'expected':'PRIVATE_CURRENT_EXPECTED'}, max_decisions=2)
        assert [files(path) for path in folders] == before
        assert initial['observation'] is None and initial['history'] == []
        assert initial['branch_id'] not in [state['branch_id'] for state in states]
        packet = json.loads(session.make_prompt(initial).split('\nSTATE JSON:\n')[1])
        memory = packet['initialization']
        records = memory['earlier_encounters'] + [memory['previous_encounter']]
        assert [record['task'] for record in records] == [state['task'] for state in states]
        assert all('initialization' not in record for record in records)
        assert records[0]['observation']['value'] == 'FIRST_OBSERVED_VALUE'
        assert tutor_context.snapshot(folder)['initialization'] == memory
        for private in ('PRIVATE_FIRST_EXPECTED', 'PRIVATE_CURRENT_EXPECTED', 'UNVERIFIED_INITIALIZATION',
                        str(first), 'image_id', 'evaluation', 'session_sha256', 'branch_id'):
            assert private not in json.dumps(memory)
        choose = lambda *_:session.Action(decision='no-reply', text='', source=None)
        states.append(student.step(folder, generate=choose, check=None, max_actions=1)['state'])
        folders.append(folder)

    before = [files(path) for path in folders]
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Unexpected provider'))
    destination = tmp_path / 'four-tasks.html'
    notebook_replay.export(folders[-1], destination)
    page = destination.read_text()
    assert all(state['task'] in page for state in states)
    assert 'FIRST_OBSERVED_VALUE' in page and 'PRIVATE_FIRST_EXPECTED' not in page
    assert 'FIRST_OBSERVED_VALUE' not in page.split('<section id="current">')[1]
    assert [files(path) for path in folders] == before
    with pytest.raises(ValueError, match='[Ii]nput session'):
        notebook_replay.export(folders[-1], first / 'should-not-write.html')

    # Even a fresh, replayable child cannot falsely claim a changed or unrelated history.
    fresh = tmp_path / 'fresh'
    next_task.create(folders[-1], fresh, task=TASK, activity=ACTIVITY)
    manifest_path = fresh / 'session.json'
    manifest = student._read(manifest_path)
    manifest['initial']['initialization']['earlier_encounters'][0]['task'] = 'FORGED'
    student._save(manifest_path, manifest)
    student.step(fresh, generate=choose, check=None, max_actions=1)
    with pytest.raises(ValueError, match='[Aa]ncestry'):
        next_task.create(fresh, tmp_path / 'rejected', task=TASK, activity=ACTIVITY)
    with pytest.raises(ValueError, match='[Aa]ncestry'):
        notebook_replay.export(fresh, tmp_path / 'rejected.html')
    assert not (tmp_path / 'rejected').exists() and not (tmp_path / 'rejected.html').exists()

    # Each record fits independently, but their total exceeds the shared-history ceiling.
    large_task = deepcopy(TASK)
    large_task['task'] = '가' * 11000
    large = tmp_path / 'large'
    finished(large, task=large_task)
    second_large = tmp_path / 'second-large'
    next_task.create(large, second_large, task=large_task, activity=ACTIVITY)
    student.step(second_large, generate=choose, check=None, max_actions=1)
    with pytest.raises(ValueError, match='64000'):
        next_task.create(second_large, tmp_path / 'too-large', task=TASK, activity=ACTIVITY)
    assert not (tmp_path / 'too-large').exists()
    assert [files(path) for path in folders] == before
