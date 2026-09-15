"""Student-only evidence must come from the same visible prefix as the control."""
from copy import deepcopy
import importlib.util
import json

import pytest

from src.eval import student_continuation as original


def candidate():
    assert importlib.util.find_spec('src.eval.student_communication'), 'Communication candidate is missing'
    from src.eval import student_communication
    return student_communication


def episode():
    return {'id': 'private-id', 'annotation': {'hidden': 'PRIVATE_LABEL'},
            'context': [{'id': 's1', 'role': 'student', 'text': 'x = 2\n\nprint(x)'},
                        {'id': 't1', 'role': 'tutor', 'text': 'LONG TUTOR EXPLANATION'},
                        {'id': 's2', 'role': 'student', 'text': ' '},
                        {'id': 't2', 'role': 'tutor', 'text': 'SECOND TUTOR REPLY'}],
            'turns': [{'id': 's3', 'role': 'student', 'phase': 'request', 'text': 'why?'},
                      {'id': 't3', 'role': 'tutor', 'phase': 'response', 'text': 'CURRENT TUTOR REPLY'},
                      {'id': 's4', 'role': 'student', 'phase': 'followup', 'text': 'HIDDEN_FUTURE'}]}


def test_candidate_preserves_control_context_and_exposes_only_student_evidence():
    module = candidate()
    source = episode()
    before = deepcopy(source)
    control = original.make_prompt(source)
    prompt = module.make_prompt(source)
    packet = json.loads(prompt[len(module.NOTE + original.PROMPT):])
    assert packet.pop('student_communication_history') == [
        {'id': 's1', 'role': 'student', 'lines': [{'line': 1, 'text': 'x = 2'}, {'line': 3, 'text': 'print(x)'}]},
        {'id': 's2', 'role': 'student', 'lines': []},
        {'id': 's3', 'role': 'student', 'phase': 'request', 'lines': [{'line': 1, 'text': 'why?'}]}]
    assert packet == json.loads(control[len(original.PROMPT):])
    assert source == before
    changed = deepcopy(source)
    changed.update(id='different-private-id', annotation={'hidden': 'CHANGED_LABEL'})
    changed['turns'][-1]['text'] = 'CHANGED_FUTURE'
    assert module.make_prompt(changed) == prompt
    changed['context'][1]['text'] = 'CHANGED TUTOR'
    changed_packet = json.loads(module.make_prompt(changed)[len(module.NOTE + original.PROMPT):])
    assert changed_packet['student_communication_history'] == json.loads(
        prompt[len(module.NOTE + original.PROMPT):])['student_communication_history']
    assert module.make_prompt(changed) != prompt
    changed['context'][0]['text'] = 'VISIBLE STUDENT CHANGE'
    assert module.make_prompt(changed) != module.make_prompt(source)


def test_candidate_preserves_source_projection_validation():
    module = candidate()
    source = episode()
    source['turns'][0]['id'] = 's1'
    with pytest.raises(ValueError, match='Duplicate'):
        module.make_prompt(source)
