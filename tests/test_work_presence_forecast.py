"""A future-message forecast must not see its answer; all examples are authored."""
from copy import deepcopy
import importlib.util
import json

import pytest


def test_forecast_uses_only_visible_dialogue_and_validates_provider_probability():
    assert importlib.util.find_spec('src.eval.work_presence_forecast'), 'Forecast helper is missing'
    from src.eval.work_presence_forecast import Forecast, PROMPT, make_prompt

    episode = {
        'id': 'PRIVATE_ID', 'annotation': {'work_present': 'HIDDEN_LABEL'},
        'context': [{'id': 'PRIVATE_HISTORY_ID', 'role': 'student', 'text': 'check this'},
                    {'id': 'PRIVATE_TUTOR_ID', 'role': 'tutor', 'text': 'Which part?'}],
        'turns': [{'id': 'PRIVATE_REQUEST_ID', 'role': 'student', 'phase': 'request', 'text': 'x = 3'},
                  {'id': 'PRIVATE_RESPONSE_ID', 'role': 'tutor', 'phase': 'response', 'text': 'Try adding two.'},
                  {'id': 'PRIVATE_FUTURE_ID', 'role': 'student', 'phase': 'followup', 'text': 'HIDDEN_ANSWER'}]}
    before = deepcopy(episode)
    prompt = make_prompt(episode)
    assert json.loads(prompt[len(PROMPT):]) == {
        'context': [{'role': 'student', 'lines': [{'line': 1, 'text': 'check this'}]},
                    {'role': 'tutor', 'lines': [{'line': 1, 'text': 'Which part?'}]}],
        'turns': [{'role': 'student', 'lines': [{'line': 1, 'text': 'x = 3'}]},
                  {'role': 'tutor', 'lines': [{'line': 1, 'text': 'Try adding two.'}]}]}
    assert episode == before
    changed = deepcopy(episode)
    changed['annotation']['work_present'] = 'CHANGED_LABEL'
    changed['turns'][-1]['text'] = 'CHANGED_FUTURE'
    changed['context'][0]['id'] = 'CHANGED_METADATA'
    assert make_prompt(changed) == prompt
    changed['context'][0]['text'] = 'Here is my calculation: 4 + 3 = 7'
    assert make_prompt(changed) != prompt
    changed['turns'][0]['id'] = changed['context'][0]['id']
    with pytest.raises(ValueError, match='Duplicate'):
        make_prompt(changed)

    for value in (0, .25, 1):
        assert Forecast.model_validate({'p_work_present': value}).p_work_present == value
    for value in (True, '0.25', None, -.1, 1.1, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            Forecast.model_validate({'p_work_present': value})
    with pytest.raises(ValueError):
        Forecast.model_validate({'p_work_present': .5, 'explanation': 'unexpected'})
    # The local strict boundary remains, but the Gemini schema must omit its
    # unsupported additionalProperties keyword (an earlier diagnostic hit this).
    schema = Forecast.model_json_schema()
    assert 'additionalProperties' not in json.dumps(schema)
    assert schema['properties']['p_work_present']['minimum'] == 0
    assert schema['properties']['p_work_present']['maximum'] == 1
