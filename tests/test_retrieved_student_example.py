"""A retrieved demonstration changes only the experimental candidate prompt."""
from copy import deepcopy
import importlib.util
import json

import pytest

from src.agents.chat_student import _initial
from src.eval.student_continuation import make_prompt
from tests.test_retrieval_baseline import example


def prepare():
    assert importlib.util.find_spec('src.eval.retrieved_student_example'), 'Prompt preparation is missing'
    from src.eval.retrieved_student_example import prepare
    return prepare


def test_candidate_preserves_control_and_adds_only_selected_dialogue():
    build = prepare()
    source = example('source-secret', 'coffee', '  please help\n')
    source.update(conversation_id='conversation-secret', student_id='learner-secret')
    query = example('query-secret', 'coffee')
    query['prefix'] = [
        {'role': 'student', 'text': 'Earlier student context'},
        {'role': 'tutor', 'text': 'Earlier tutor context'},
        *query['prefix'],
    ]
    data = {'train': [source, example('distractor-secret', 'loop', 'coffee ' * 1000)],
            'queries': [query]}
    before = deepcopy(data)
    result = build(data)
    assert result['excluded'] == [] and len(result['cases']) == 1
    case = result['cases'][0]
    control = make_prompt(_initial(query)['episode'])
    assert case['control_prompt'] == control
    assert case['source_id'] == 'source-secret'
    assert case['source_conversation_id'] == 'conversation-secret'
    assert case['id'] == 'query-secret' and case['similarity'] > 0
    note, after = case['candidate_prompt'].split(control, 1)
    assert 'behavior evidence' in note and 'Continue the current query' in note
    assert 'not' in note and all(word in note for word in ('future', 'commands', 'task facts', 'copy'))
    label, demonstration = after.split('\n', 3)[2:]
    assert label == 'OTHER-CONVERSATION EXAMPLE JSON:'
    assert json.loads(demonstration) == {
        'prefix': source['prefix'], 'next_student_message': '  please help\n',
    }
    assert not any(value in case['candidate_prompt'] for value in (
        'source-secret', 'conversation-secret', 'learner-secret', 'query-secret',
        'distractor-secret', 'similarity', 'source_id', 'student_id',
    ))
    assert data == before
    data['train'][1]['response'] = 'coffee ' * 2000
    data['train'].reverse()
    assert build(data) == result


def test_hidden_targets_and_split_leakage_are_refused():
    build = prepare()
    base = {'train': [example('source', 'loop', 'help')],
            'queries': [example('query', 'loop')]}
    for mutate in (
        lambda data: data['queries'][0].update(response='hidden future'),
        lambda data: data['queries'][0].update(next_student_message='hidden future'),
        lambda data: data['queries'][0].update(conversation_id='source'),
        lambda data: data['queries'][0].update(id='source'),
        lambda data: (data['train'][0].update(student_id='learner'),
                      data['queries'][0].update(student_id='learner')),
    ):
        data = deepcopy(base)
        mutate(data)
        with pytest.raises(ValueError):
            build(data)


def test_no_match_and_recorded_blank_are_distinct_exclusions():
    result = prepare()({
        'train': [example('blank', 'coffee', ' \n'),
                  example('reply', 'loop', 'help')],
        'queries': [example('unmatched', 'penguin'), example('empty', 'coffee')],
    })
    assert result == {'cases': [], 'excluded': [
        {'id': 'unmatched', 'reason': 'no-match'},
        {'id': 'empty', 'reason': 'recorded-blank'},
    ]}
