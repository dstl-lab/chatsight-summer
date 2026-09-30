"""The single boundary run must report exclusions and stop without retries."""
import importlib.util
import json
from pathlib import Path

import pytest


def test_boundary_run_preserves_abstentions_errors_and_frozen_inputs(tmp_path):
    path = Path(__file__).parents[1] / 'experiments/2026-09-30-message-content-boundaries.py'
    spec = importlib.util.spec_from_file_location('boundaries', path)
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    calls = []
    def generate(wire, prompt):
        calls.append(prompt)
        assert set(wire) == {'model', 'configuration', 'timeout_ms'}
        assert 'expected' not in prompt and 'group' not in prompt
        if len(calls) == 2:
            raise RuntimeError('Never persist exception payloads')
        judgment = {'basis': 'unresolved', 'value': 'unclear', 'evidence': [{'turn_id': 'message', 'line': 1}]}
        return {'candidates': [{'finish_reason': 'STOP', 'content': {'parts': [
            {'text': json.dumps({flag: judgment for flag in run.scorer.original.DEFINITIONS})}]}}]}
    folder = tmp_path / 'run'
    report = run.execute(folder, generate)
    assert len(calls) == 2 and report['counts'] == {'complete': 1, 'error': 1, 'unattempted': 14}
    assert not report['clean_boundary_check']
    assert report['cases'][0]['message_only_values'] == {'content_supplied': None, 'expressed_request': None}
    for flag in report['fallback'].values():
        assert flag == {'included': 0, 'excluded': 1, 'unavailable': 15, 'correct_included': 0, 'unsafe_included': 0}
    assert report['cases'][1]['error_type'] == 'RuntimeError'
    assert 'Never persist' not in json.dumps(report)
    assert json.loads((folder / 'report.json').read_text()) == report
    with pytest.raises(FileExistsError):
        run.execute(folder, generate)
    assert len(calls) == 2
