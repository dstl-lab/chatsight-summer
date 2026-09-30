"""Context provenance and selective scoring stay explicit; no provider calls."""
from copy import deepcopy
import importlib

import pytest


def test_context_contract_preserves_evidence_and_excludes_uncertain_judgments():
    scorer = importlib.import_module('src.eval.message_content_context')
    data = {'prefix': [{'role': 'tutor', 'text': 'Authored preceding line.'}],
            'message': '  authored fragment  '}
    selection = {
        'content_supplied': {'basis': 'preceding_context', 'value': 'yes', 'evidence': [
            {'turn_id': 'message', 'line': 1}, {'turn_id': 'p1', 'line': 1}]},
        'expressed_request': {'basis': 'unresolved', 'value': 'unclear', 'evidence': [
            {'turn_id': 'message', 'line': 1}]}}
    calls = []
    def generate(prompt, schema):
        calls.append(prompt)
        assert 'basis' in prompt and 'expected' not in prompt
        return schema.model_validate(selection)
    result = scorer.score(data, generate)
    assert len(calls) == 1
    assert result['content_supplied']['evidence'][0]['quote'] == '  authored fragment  '
    assert result['expressed_request']['value'] == 'unclear'
    assert scorer.message_only_values(result) == {'content_supplied': None, 'expressed_request': None}
    direct = deepcopy(selection)
    direct['content_supplied'].update(basis='message_only', evidence=[{'turn_id': 'message', 'line': 1}])
    assert scorer.message_only_values(scorer.materialize(data, direct))['content_supplied'] == 'yes'
    for flag, changes in [
        ('content_supplied', {'evidence': [{'turn_id': 'message', 'line': 1}]}),
        ('content_supplied', {'basis': 'message_only'}),
        ('content_supplied', {'basis': 'unresolved'}),
        ('expressed_request', {'basis': 'message_only'}),
        ('content_supplied', {'evidence': [{'turn_id': 'message', 'line': 1}, {'turn_id': 'p7', 'line': 1}]}),
    ]:
        invalid = deepcopy(selection)
        invalid[flag].update(changes)
        with pytest.raises(ValueError):
            scorer.materialize(data, invalid)
