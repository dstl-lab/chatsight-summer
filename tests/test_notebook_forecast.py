"""Authored next-visit forecasts; no execution, provider, or student data."""
from copy import deepcopy
import json

import pytest


def test_forecast_excludes_future_and_measures_net_edits_without_changing_inputs():
    from src.eval.notebook_forecast import Forecast, apply_forecast, compare, make_prompt

    assert 'additionalProperties' not in json.dumps(Forecast.model_json_schema())

    initial = [
        {'index': 0, 'cell_type': 'markdown', 'source': 'Update the values.'},
        {'index': 1, 'cell_type': 'code', 'source': ['x = 0\n'], 'outputs': ['PRIVATE OUTPUT']},
        {'index': 2, 'cell_type': 'code', 'source': 'y = 0'},
        {'index': 3, 'cell_type': 'code', 'source': 'z = 0'},
    ]
    recovered = {'notebook': {'cells': initial, 'recorded_at': 'PRIVATE TIME'},
                 'exchange': [{'role': 'student', 'text': 'help', 'id': 'PRIVATE ID'},
                              {'role': 'tutor', 'text': 'Try updating the values.'}],
                 'future': 'PRIVATE FUTURE', 'conversation_key': 'PRIVATE ACCOUNT'}
    original = deepcopy(recovered)
    prompt = make_prompt(recovered)
    packet = json.loads(prompt.split('INITIAL STATE JSON:\n', 1)[1])
    assert packet == {'cells': [
        {'index': 0, 'cell_type': 'markdown', 'source': 'Update the values.'},
        {'index': 1, 'cell_type': 'code', 'source': 'x = 0\n'},
        {'index': 2, 'cell_type': 'code', 'source': 'y = 0'},
        {'index': 3, 'cell_type': 'code', 'source': 'z = 0'},
    ], 'exchange': [{'role': 'student', 'text': 'help'},
                    {'role': 'tutor', 'text': 'Try updating the values.'}]}
    assert 'PRIVATE' not in prompt
    changed_metadata = deepcopy(recovered)
    changed_metadata.update(future={'cells': ['replaced future']}, changed_positions=[1])
    changed_metadata['notebook']['cells'][1]['outputs'] = ['different output']
    assert make_prompt(changed_metadata) == prompt

    target = deepcopy(initial)
    target[1]['source'] = 'x = 1\n'
    target[3]['source'] = 'z = 1'
    target_original = deepcopy(target)
    forecast = Forecast(edits=[{'index': 1, 'source': 'x = 1\n'},
                               {'index': 2, 'source': 'y = 2'}])
    applied = apply_forecast(initial, forecast)
    assert [c['source'] for c in applied] == ['Update the values.', 'x = 1\n', 'y = 2', 'z = 0']
    assert compare(initial, target, forecast) == {
        'code_cells': 3, 'reference_changed': 2, 'reference_unchanged': 1,
        'forecast': {'predicted_changed': 2, 'predicted_unchanged': 1,
                     'tp': 1, 'fp': 1, 'fn': 1, 'exact_at_reference_changed': 1},
        'unchanged_baseline': {'predicted_changed': 0, 'predicted_unchanged': 3,
                               'tp': 0, 'fp': 0, 'fn': 2, 'exact_at_reference_changed': 0},
    }
    unchanged = compare(initial, initial, {'edits': [{'index': 1, 'source': 'x = 0\n'}]})
    assert unchanged['reference_changed'] == 0
    assert unchanged['forecast'] == unchanged['unchanged_baseline']
    assert apply_forecast(initial, {'edits': [{'index': 3, 'source': ''}]})[3]['source'] == ''
    assert compare(initial, target, {'edits': [{'index': 1, 'source': 'x = 1'}]})['forecast']['exact_at_reference_changed'] == 0
    assert recovered == original and target == target_original

    for edits in [[{'index': index, 'source': 'x'}] for index in [True, '1', -1, 0, 4]] + [
        [{'index': 1, 'source': 'x'}, {'index': 1, 'source': 'y'}],
        [{'index': 1, 'source': None}], [{'index': 1, 'source': 'x', 'output': 'done'}],
    ]:
        with pytest.raises(ValueError):
            apply_forecast(initial, {'edits': edits})
    with pytest.raises(ValueError):
        apply_forecast(initial, {'edits': [], 'reasoning': 'not an output field'})
    for bad in [target[:-1], [target[0], target[2], target[1], target[3]],
                [{'index': 0, 'cell_type': 'raw', 'source': 'changed type'}, *target[1:]],
                [{'index': 0, 'cell_type': 'markdown', 'source': 'changed instructions'}, *target[1:]],
                [target[0], {'cell_type': 'code', 'source': [1]}, *target[2:]]]:
        with pytest.raises(ValueError):
            compare(initial, bad, {'edits': []})
    for exchange in [[], [{'role': 'student', 'text': 'help'}],
                     [{'role': 'student', 'text': 'help'}, {'role': 'tutor', 'text': ' '}]]:
        with pytest.raises(ValueError):
            make_prompt(recovered | {'exchange': exchange})
