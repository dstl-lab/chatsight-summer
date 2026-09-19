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
