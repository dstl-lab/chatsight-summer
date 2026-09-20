"""A UI submission must bind to the inspected state and save exactly one decision."""
import importlib.util
import json

import pytest

from src.agents import notebook_student as student, tutor_context
from tests.test_notebook_session import ACTIVITY, TASK, observation


def test_bound_intervention_saves_one_action_and_rejects_resubmission(tmp_path):
    assert importlib.util.find_spec('src.agents.student_workspace'), 'Workspace controls are missing'
    from src.agents.student_workspace import advance

    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/workspace')
    student.step(folder, generate=lambda *_: student.Action(decision='reply', source=None, text='this?'),
                 check=None, max_actions=1)
    shown = tutor_context.snapshot(folder)
    before = {p.name:p.read_bytes() for p in folder.iterdir()}
    calls = []

    def generate(prompt, schema):
        calls.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return schema(decision='revise-work', source='n_shades = 2', text='')

    for options, message in [({}, 'sending'), ({'send': True, 'binding': {}}, 'binding'),
                             ({'send': True, 'tutor_reply': ' '}, 'tutor')]:
        with pytest.raises(ValueError, match=message):
            advance(folder, **({'binding': shown['binding'], 'tutor_reply': 'Count distinct shades.',
                               'generate': generate, 'check': observation} | options))
    assert not calls and {p.name:p.read_bytes() for p in folder.iterdir()} == before

    after = advance(folder, binding=shown['binding'], tutor_reply='Count distinct shades.',
                    send=True, generate=generate, check=observation)
    assert len(calls) == 1

    assert calls[0]['dialogue'][-2:] == [
        {'role': 'student', 'text': 'this?', 'origin': 'generated'},
        {'role': 'tutor', 'text': 'Count distinct shades.', 'origin': 'supplied'}]
    assert after['work'] == {'cell_index': 1, 'source': 'n_shades = 2', 'revision': 1}
    assert after['status'] == 'active'
    assert after['decisions_remaining'] == shown['decisions_remaining'] - 1
    assert tutor_context.snapshot(folder) == after and len(calls) == 1
    with pytest.raises(ValueError, match='[Ss]tale'):
        advance(folder, binding=shown['binding'], tutor_reply='Count distinct shades.',
                send=True, generate=generate, check=observation)
    assert len(calls) == 1 and len(list(folder.glob('step-*.json'))) == 2

    stopped = advance(folder, binding=after['binding'], send=True,
                      generate=lambda *_: student.Action(decision='no-reply', source=None, text=''),
                      check=observation)
    assert stopped['status'] == 'no-reply'
    with pytest.raises(ValueError, match='terminal'):
        advance(folder, binding=stopped['binding'], send=True, generate=generate, check=observation)
    assert len(calls) == 1


def test_policy_reply_continues_once_and_retains_exact_policy(tmp_path):
    from src.agents import student_workspace as workspace
    assert hasattr(workspace, 'respond'), 'Policy continuation is missing'
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/policy')
    student.step(folder, generate=lambda *_: student.Action(decision='reply', source=None, text='this?'),
                 check=None, max_actions=1)
    shown = tutor_context.snapshot(folder)
    policy = 'Answer the current question briefly.\nUse the visible work.'
    calls = []

    def generate_tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        assert payload['policy'] == policy and payload['context']['pending_message'] == 'this?'
        assert payload['context']['work'] == shown['work']
        calls.append('tutor')
        return schema(text='Count each distinct shade once.')

    def generate_student(prompt, schema):
        state = json.loads(prompt.split('\nSTATE JSON:\n')[1])
        assert state['dialogue'][-1]['text'] == 'Count each distinct shade once.'
        calls.append('student')
        return schema(decision='reply', source=None, text='where?')

    options = dict(binding=shown['binding'], policy=policy, send=True,
                   generate_tutor=generate_tutor, generate_student=generate_student, check=observation)
    for change in ({'send': False}, {'binding': {}}, {'policy': ' '}):
        with pytest.raises(ValueError):
            workspace.respond(folder, **(options | change))
    assert calls == [] and not (folder/'tutor-exchanges').exists()
    after = workspace.respond(folder, **options)
    assert calls == ['tutor', 'student'] and after['pending_message'] == 'where?'
    assert after['decisions_remaining'] == shown['decisions_remaining'] - 1
    receipt = student._read(folder/'tutor-exchanges'/shown['binding']['state_sha256']/'receipt.json')
    assert receipt['request']['policy'] == policy
    assert receipt['continuation']['status'] == 'complete'
    assert tutor_context.snapshot(folder) == after
    with pytest.raises(ValueError, match='[Ss]tale'):
        workspace.respond(folder, **options)
    assert calls == ['tutor', 'student']


def test_policy_rechecks_prepared_context_and_blocks_interrupted_retry(tmp_path, monkeypatch):
    from src.agents import student_workspace as workspace
    assert hasattr(workspace, 'respond'), 'Policy continuation is missing'
    for mode in ('changed', 'interrupted'):
        folder = tmp_path / mode
        student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/'+mode)
        student.step(folder, generate=lambda *_: student.Action(decision='reply', source=None, text='this?'),
                     check=None, max_actions=1)
        shown = tutor_context.snapshot(folder)
        options = dict(binding=shown['binding'], policy='Brief help.', send=True,
                       generate_student=lambda *_: pytest.fail('Student must not be dispatched'), check=observation)
        if mode == 'changed':
            real_snapshot = tutor_context.snapshot
            reads = []

            def change_between_snapshots(path):
                reads.append(path)
                if len(reads) == 2:
                    student.step(folder, tutor_reply='Another intervention.', max_actions=1, check=None,
                                 generate=lambda *_: student.Action(decision='reply', source=None, text='new question'))
                return real_snapshot(path)

            with monkeypatch.context() as patch:
                patch.setattr(tutor_context, 'snapshot', change_between_snapshots)
                with pytest.raises(ValueError, match='[Ss]tale'):
                    workspace.respond(folder, generate_tutor=lambda *_: pytest.fail('Stale tutor dispatched'), **options)
            assert student.load(folder)['message'] == 'new question'
        else:
            def interrupt(*_):
                raise KeyboardInterrupt()

            with pytest.raises(KeyboardInterrupt):
                workspace.respond(folder, generate_tutor=interrupt, **options)
            with pytest.raises(FileExistsError):
                workspace.respond(folder, generate_tutor=lambda *_: pytest.fail('Interrupted request resent'), **options)
            assert tutor_context.snapshot(folder) == shown
