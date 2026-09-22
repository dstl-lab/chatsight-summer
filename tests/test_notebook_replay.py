"""Invented saved encounters exercise the read-only HTML replay boundary."""
from copy import deepcopy
import importlib.util
import json
import sys

import pytest

from src.agents import notebook_next_task, notebook_student as student
from src.eval import notebook_runtime as runtime
from tests.test_notebook_lesson import files
from tests.test_notebook_session import ACTIVITY, TASK, observation
from tests.test_task_evaluation import worker
from tests.test_tutor_context import choose


def test_replay_preserves_saved_evidence_and_keeps_ancestry_feedback_and_html_safe(tmp_path, monkeypatch, capsys):
    assert importlib.util.find_spec('src.eval.notebook_replay'), 'Saved notebook HTML replay is missing'
    from src.eval import notebook_replay

    previous, current = tmp_path / 'PRIVATE_PARENT_PATH', tmp_path / 'current'
    old_task = deepcopy(TASK)
    old_task['task'] = 'An authored first task.'
    old_task['captured_at'] = 'PRIVATE_PROVENANCE_SENTINEL'
    student.create(previous, task=old_task, activity=ACTIVITY, branch_id='authored/previous',
                   evaluation={'expected':'PRIVATE_EXPECTED_SENTINEL'})
    choose(previous, 'revise-work', source='n_shades = 0')
    worker(monkeypatch, 'OLD_OBSERVED_VALUE')
    choose(previous, 'request-check', check=runtime.check_work)
    choose(previous, 'no-reply')
    hostile = '<script>alert("saved text")</script><img src=x onerror=alert(1)>'
    task = deepcopy(TASK)
    task.update(task='An authored second task.', initialization='A fresh task supplied by the researcher.')
    task['dialogue'][0]['text'] = hostile
    notebook_next_task.create(previous, current, task=task, activity=ACTIVITY,
                              evaluation={'expected':2}, max_decisions=6)
    choose(current, 'reply', text='A generated question.')
    choose(current, 'revise-work', source='# ' + hostile + '\nn_shades = 2',
           tutor_reply='A supplied tutor hint.')
    worker(monkeypatch, 2)
    choose(current, 'request-check', check=runtime.check_work)
    choose(current, 'revise-work', source='n_shades = 3')
    choose(current, 'no-reply')
    before = files(previous), files(current)
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Replay dispatched a model'))
    monkeypatch.setattr(runtime, 'check_work', lambda *a, **kw:pytest.fail('Replay executed code'))
    replay = notebook_replay.load_replay(current, previous=previous)
    assert replay['version'] == 1 and replay['contains_private_content'] is True
    assert replay['linked'] is True
    assert [task['title'] for task in replay['tasks']] == ['Task 1', 'Task 2']
    first, second = replay['tasks']
    assert first['task'] == 'An authored first task.'
    assert second['task'] == 'An authored second task.'
    assert second['initialization'] == 'A fresh task supplied by the researcher.'
    assert len(second['shared_history']) == 1
    assert [event['kind'] for event in second['events']] == [
        'student-action', 'tutor-intervention', 'student-action',
        'student-action', 'student-action', 'student-action']
    assert second['events'][1] == {'sequence':2, 'kind':'tutor-intervention',
                                   'origin':'supplied', 'text':'A supplied tutor hint.'}
    actions = [event for event in second['events'] if event['kind'] == 'student-action']
    assert [event['number'] for event in actions] == [1, 2, 3, 4, 5]
    assert [event['action']['decision'] for event in actions] == [
        'reply', 'revise-work', 'request-check', 'revise-work', 'no-reply']
    assert actions[0]['action']['text'] == 'A generated question.' and actions[0]['code_diff'] == ''
    assert '--- revision 0' in actions[1]['code_diff'] and '+++ revision 1' in actions[1]['code_diff']
    assert '+n_shades = 2' in actions[1]['code_diff']
    assert actions[2]['feedback']['status'] == 'checked' and actions[2]['feedback']['success'] is True
    assert actions[2]['feedback']['value'] == 2 and actions[2]['code_diff'] == ''
    assert '--- revision 1' in actions[3]['code_diff'] and '+++ revision 2' in actions[3]['code_diff']
    assert '+n_shades = 3' in actions[3]['code_diff']
    assert second['final'] == {'status':'no-reply', 'disposition':'no-reply',
        'decisions_used':5, 'max_decisions':6,
        'work':{'cell_index':1, 'source':'n_shades = 3', 'revision':2}, 'feedback':None}
    assert first['events'][1]['feedback']['success'] is False
    assert first['events'][1]['feedback']['value'] == 'OLD_OBSERVED_VALUE'
    serialized = json.dumps(replay)
    for private in ('PRIVATE_EXPECTED_SENTINEL', 'PRIVATE_PROVENANCE_SENTINEL', str(previous),
                    'evaluation_sha256', 'session_sha256', 'state_sha256', 'image_id'):
        assert private not in serialized
    assert (files(previous), files(current)) == before
    destination = tmp_path / 'replay.html'
    monkeypatch.setattr(sys, 'argv', ['notebook_replay', str(current), '--previous', str(previous),
                                    '--output', str(destination)])
    notebook_replay.main()
    capsys.readouterr()
    rendered = destination.read_text()
    assert 'Verified linked continuation' in rendered
    assert 'An authored first task.' in rendered and 'An authored second task.' in rendered
    assert 'A generated question.' in rendered and 'A supplied tutor hint.' in rendered
    assert 'Origin: model' in rendered and 'Origin: supplied' in rendered
    assert 'request-check' in rendered and 'no-reply' in rendered
    assert 'OLD_OBSERVED_VALUE' in rendered and 'Checked: pass' in rendered and 'Checked: fail' in rendered
    current_html = rendered.split('<section id="current">', 1)[1]
    assert 'OLD_OBSERVED_VALUE' not in current_html
    assert 'No check feedback for this revision.' in current_html
    assert hostile not in rendered and '&lt;script&gt;' in rendered
    for private in ('PRIVATE_EXPECTED_SENTINEL', 'PRIVATE_PROVENANCE_SENTINEL', str(previous),
                    'evaluation_sha256', 'session_sha256', 'state_sha256', 'image_id'):
        assert private not in rendered
    assert (files(previous), files(current)) == before
    with pytest.raises(FileExistsError):
        notebook_replay.export(current, destination, previous=previous)
    assert destination.read_text() == rendered
    linked_output = tmp_path / 'existing-link.html'
    linked_target = tmp_path / 'missing-target.html'
    linked_output.symlink_to(linked_target)
    with pytest.raises(FileExistsError):
        notebook_replay.export(current, linked_output, previous=previous)
    assert linked_output.is_symlink() and not linked_target.exists()
    automatic = tmp_path / 'automatic.html'
    assert notebook_replay.export(current, automatic) == automatic
    assert automatic.read_text() == rendered
    with pytest.raises(ValueError, match='[Ii]nput session'):
        notebook_replay.export(current, current / 'replay.html', previous=previous)
    with pytest.raises(ValueError, match='[Ii]nput session'):
        notebook_replay.export(current, previous / 'nested' / 'replay.html', previous=previous)
    assert (files(previous), files(current)) == before
    # A real, replayable but different predecessor must not be called an ancestor.
    unrelated = tmp_path / 'unrelated'
    student.create(unrelated, task=TASK, activity=ACTIVITY, branch_id='authored/unrelated')
    choose(unrelated, 'no-reply')
    rejected = tmp_path / 'rejected.html'
    with pytest.raises(ValueError, match='[Aa]ncestry'):
        notebook_replay.export(current, rejected, previous=unrelated)
    assert not rejected.exists() and (files(previous), files(current)) == before
    # Hash-valid session loading alone does not validate its inherited shared record.
    manifest_path = current / 'session.json'
    original = manifest_path.read_bytes()
    manifest = student._read(manifest_path)
    manifest['provenance']['previous_encounter']['history_sha256'] = '0' * 64
    # Use the untouched fresh initialization to isolate ancestry from step bindings.
    empty = tmp_path / 'altered'
    empty.mkdir()
    student._save(empty / 'session.json', manifest)
    (empty / '.lock').touch()
    with pytest.raises(ValueError, match='[Aa]ncestry'):
        notebook_replay.export(empty, rejected, previous=previous)
    assert not rejected.exists() and manifest_path.read_bytes() == original
    assert (files(previous), files(current)) == before


def test_replay_data_redacts_environment_diagnostics_without_changing_session(tmp_path, monkeypatch):
    from src.eval import notebook_replay

    folder = tmp_path / 'environment-error'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/environment-error')
    choose(folder, 'request-check', check=lambda *args, **kwargs:
        {**observation(*args, **kwargs, status='environment-error'),
            'error':{'type':'CalledProcessError', 'message':'PRIVATE_DOCKER_COMMAND'}})
    before = files(folder)
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Replay dispatched a model'))
    monkeypatch.setattr(runtime, 'check_work', lambda *a, **kw:pytest.fail('Replay executed code'))

    replay = notebook_replay.load_replay(folder)

    feedback = replay['tasks'][0]['events'][0]['feedback']
    assert feedback['status'] == 'environment-error' and feedback['success'] is None
    assert feedback['error'] == {'message':'Local execution was unavailable; this work is ungraded. '
                                           'The operation receipt retains the diagnostic.'}
    assert feedback['output'] == '' and replay['tasks'][0]['final']['feedback'] == feedback
    assert 'PRIVATE_DOCKER_COMMAND' not in json.dumps(replay)
    assert files(folder) == before


def test_replay_data_flattens_one_multi_action_receipt_without_duplicates(tmp_path, monkeypatch):
    from src.eval import notebook_replay

    folder = tmp_path / 'multi-action'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/multi-action', max_decisions=3)
    actions = iter([
        student.Action(decision='revise-work', source='n_shades = 2', text=''),
        student.Action(decision='request-check', source=None, text=''),
        student.Action(decision='no-reply', source=None, text=''),
    ])
    student.step(folder, generate=lambda *_:next(actions),
                 check=lambda *args, **kwargs:observation(*args, **kwargs, status='checked'),
                 max_actions=3)
    before = files(folder)
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:pytest.fail('Replay dispatched a model'))
    monkeypatch.setattr(runtime, 'check_work', lambda *a, **kw:pytest.fail('Replay executed code'))

    task = notebook_replay.load_replay(folder)['tasks'][0]

    assert [event['number'] for event in task['events']] == [1, 2, 3]
    assert [event['action']['decision'] for event in task['events']] == [
        'revise-work', 'request-check', 'no-reply']
    assert '+n_shades = 2' in task['events'][0]['code_diff']
    assert task['events'][1]['feedback']['success'] is True
    assert task['final']['disposition'] == 'no-reply'
    assert task['final']['decisions_used'] == task['final']['max_decisions'] == 3
    assert files(folder) == before


def test_replay_data_distinguishes_budget_pause_from_student_silence(tmp_path):
    from src.eval import notebook_replay

    folder = tmp_path / 'budget-pause'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/budget', max_decisions=1)
    student.step(folder, generate=lambda *_:student.Action(decision='reply', source=None, text='One question.'),
                 check=None, max_actions=1)

    final = notebook_replay.load_replay(folder)['tasks'][0]['final']

    assert final['status'] == 'awaiting-tutor'
    assert final['disposition'] == 'budget-exhausted'
    assert final['decisions_used'] == final['max_decisions'] == 1
