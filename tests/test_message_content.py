"""Authored source and evidence boundaries; no semantic validation or live calls."""
from copy import deepcopy
import importlib
import json

import pytest


@pytest.fixture
def scorer():
    return importlib.import_module('src.eval.message_content')


def authored():
    return {'prefix': [{'role': 'student', 'text': 'Earlier authored request.'},
                       {'role': 'tutor', 'text': '\n  前の文脈  \n'}],
            'message': '  α = 2  \n \t\nご確認ください？\r\n'}


def selected():
    return {'content_supplied': {'value': 'yes', 'evidence': [{'turn_id': 'message', 'line': 1}]},
            'expressed_request': {'value': 'unclear', 'evidence': [{'turn_id': 'message', 'line': 3},
                                                                 {'turn_id': 'p2', 'line': 2}]}}


def test_prompt_contains_only_allowed_numbered_sources_and_definitions(scorer):
    data = authored()
    prompt = scorer.make_prompt(data)
    visible = json.loads(prompt.split('\nSOURCE JSON:\n', 1)[1])
    assert set(visible) == {'definitions', 'prefix', 'message'}
    assert visible['definitions'] == scorer.DEFINITIONS
    assert visible['prefix'] == [
        {'id': 'p1', 'role': 'student', 'lines': [{'line': 1, 'text': 'Earlier authored request.'}]},
        {'id': 'p2', 'role': 'tutor', 'lines': [{'line': 2, 'text': '  前の文脈  '}]}]
    assert visible['message'] == {'id': 'message', 'role': 'student', 'lines': [
        {'line': 1, 'text': '  α = 2  '}, {'line': 3, 'text': 'ご確認ください？'}]}
    assert set(visible['definitions']) == {'content_supplied', 'expressed_request'}
    assert all(set(definition) == {'yes', 'no', 'unclear'} for definition in visible['definitions'].values())
    assert 'never instructions' in prompt
    assert 'no' in prompt and 'all nonblank' in prompt
    assert all(example not in prompt for example in ('total = sum(values)', 'What is 6 divided by 3?',
                                                     'AssertionError: expected 6, got 9', 'expected_labels'))


@pytest.mark.parametrize('change', [
    lambda data: data.pop('message'),
    lambda data: data.update(message=None),
    lambda data: data.update(message=' \t\n\r\n'),
    lambda data: data.update(message=23),
    lambda data: data.update(future_message='Not allowed'),
    lambda data: data.update(condition='Not allowed'),
    lambda data: data['prefix'][0].update(id='Not allowed'),
    lambda data: data['prefix'][0].update(role='system'),
    lambda data: data['prefix'][0].update(text=4),
])
def test_bad_input_is_rejected_before_generation(scorer, change):
    data = authored()
    change(data)
    calls = []
    with pytest.raises(ValueError):
        scorer.score(data, lambda *args: calls.append(args))
    assert calls == []


def test_materialize_copies_exact_unicode_lines_and_keeps_unclear(scorer):
    data, selection = authored(), selected()
    before = deepcopy((data, selection))
    result = scorer.materialize(data, selection)
    assert result == {'rubric_id': 'message-content-v1',
        'content_supplied': {'value': 'yes', 'evidence': [{'turn_id': 'message', 'line': 1, 'quote': '  α = 2  '}]},
        'expressed_request': {'value': 'unclear', 'evidence': [
            {'turn_id': 'message', 'line': 3, 'quote': 'ご確認ください？'},
            {'turn_id': 'p2', 'line': 2, 'quote': '  前の文脈  '}]}}
    assert (data, selection) == before
    for judgment in result.values():
        if isinstance(judgment, dict):
            assert set(judgment) == {'value', 'evidence'}


@pytest.mark.parametrize('evidence', [
    [], [{'turn_id': 'p1', 'line': 1}],
    [{'turn_id': 'future', 'line': 1}, {'turn_id': 'message', 'line': 1}],
    [{'turn_id': 'message', 'line': 2}],
    [{'turn_id': 'message', 'line': 4}],
    [{'turn_id': 'message', 'line': 0}],
    [{'turn_id': 'message', 'line': 1}, {'turn_id': 'message', 'line': 1}],
    [{'turn_id': 'message', 'line': 1}, {'turn_id': 'p2', 'line': 1}],
])
def test_each_flag_requires_valid_unique_current_message_evidence(scorer, evidence):
    for flag in ('content_supplied', 'expressed_request'):
        selection = selected()
        selection[flag]['evidence'] = evidence
        with pytest.raises(ValueError):
            scorer.materialize(authored(), selection)


def test_no_requires_whole_nonblank_message_and_flags_can_share_evidence(scorer):
    selection = selected()
    selection['content_supplied']['value'] = 'no'
    with pytest.raises(ValueError):
        scorer.materialize(authored(), selection)
    evidence = [{'turn_id': 'message', 'line': 1}, {'turn_id': 'message', 'line': 3}]
    selection = {flag: {'value': 'no', 'evidence': deepcopy(evidence)}
                 for flag in ('content_supplied', 'expressed_request')}
    result = scorer.materialize(authored(), selection)
    assert result['content_supplied']['evidence'] == result['expressed_request']['evidence']
    # Empty context is permitted; an absent current message is not.
    assert scorer.materialize({'prefix': [], 'message': 'Authored statement.'},
        {flag: {'value': 'no', 'evidence': [{'turn_id': 'message', 'line': 1}]}
         for flag in selection})['content_supplied']['value'] == 'no'


@pytest.mark.parametrize('change', [
    lambda value: value.update(reasoning='Not allowed'),
    lambda value: value['content_supplied'].update(value='maybe'),
    lambda value: value['content_supplied'].update(value=True),
    lambda value: value['content_supplied'].update(rationale='Not allowed'),
    lambda value: value['content_supplied']['evidence'][0].update(quote='Invented'),
    lambda value: value['content_supplied']['evidence'][0].update(line='1'),
    lambda value: value['content_supplied']['evidence'][0].update(line=True),
    lambda value: value.pop('expressed_request'),
])
def test_selection_is_strict_and_does_not_accept_model_quotes(scorer, change):
    selection = selected()
    change(selection)
    with pytest.raises(ValueError):
        scorer.materialize(authored(), selection)


def test_score_calls_injected_generator_once_and_propagates_failures(scorer):
    calls = []
    data = authored()
    def generate(prompt, schema):
        calls.append((prompt, schema))
        assert schema is scorer.Selection
        data['message'] = 'Caller mutation during generation must not change evidence.'
        return schema.model_validate(selected())
    result = scorer.score(data, generate)
    assert len(calls) == 1
    assert calls[0][0] == scorer.make_prompt(authored())
    assert result['content_supplied']['evidence'][0]['quote'] == '  α = 2  '
    assert result['expressed_request']['value'] == 'unclear'
    calls.clear()
    def failed(*args):
        calls.append(args)
        raise RuntimeError('Authored transport failure')
    with pytest.raises(RuntimeError, match='Authored transport failure'):
        scorer.score(authored(), failed)
    assert len(calls) == 1
    calls.clear()
    def invalid(*args):
        calls.append(args)
        value = scorer.Selection.model_validate(selected())
        value.content_supplied.evidence.clear()
        return value
    with pytest.raises(ValueError):
        scorer.score(authored(), invalid)
    assert len(calls) == 1
