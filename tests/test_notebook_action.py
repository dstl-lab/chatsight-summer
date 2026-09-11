"""Invented notebook action checks; never execute source text."""
from copy import deepcopy

import pytest


def task():
    from src.eval.notebook_action import initial_task
    return initial_task({'notebook':{'recorded_at':'2026-09-01T10:02:00+00:00','cells':[
        {'index':0,'cell_type':'markdown','source':'Add 3 and 4.'},
        {'index':1,'cell_type':'code','source':'total = 3'}]},
        'exchange':[{'role':'student','text':'total?'},{'role':'tutor','text':'Include both values.'}]},
        instruction_cells=[0], work_cell=1)


def test_edit_can_be_silent_or_accompany_chat_without_implying_execution():
    from src.eval.notebook_action import Action, apply_action
    state = task(); original = deepcopy(state)
    for text in ['', 'check this']:
        result = apply_action(state, Action(decision='revise-work',text=text,source='total = 3 + 4'))
        assert result['work']['source'] == 'total = 3 + 4'
        assert result['work']['revision'] == 1
        assert result['message'] == (text or None)
        assert result['observation'] is None
        assert result['execution'] == 'not-run'
    reply = apply_action(state,Action(decision='reply',text='total = 7',source=None))
    assert reply['work'] == state['work']
    assert state == original
    assert apply_action(state,Action(decision='no-reply',text='',source=None))['message'] is None


def test_invalid_combinations_and_wrong_cell_types_are_rejected():
    from src.eval.notebook_action import Action, initial_task
    for value in [dict(decision='reply',text=' ',source=None),dict(decision='reply',text='x',source='x=1'),
                  dict(decision='revise-work',text='',source=None),dict(decision='no-reply',text='x',source=None),
                  dict(decision='request-check',text='',source=None),dict(decision='revise-work',text='',source='x',passed=True)]:
        with pytest.raises(ValueError):Action.model_validate(value)
    recovered={'notebook':{'recorded_at':'2026-09-01T10:02:00+00:00','cells':[
        {'index':0,'cell_type':'markdown','source':'A question.'}]},'exchange':[]}
    with pytest.raises(ValueError):initial_task(recovered,instruction_cells=[0],work_cell=0)
