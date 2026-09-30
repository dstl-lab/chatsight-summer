"""Authored smoke must preserve errors/mismatches and never resume a batch."""
import importlib.util
import json
from pathlib import Path

import pytest


def test_smoke_stops_on_error_preserves_mismatch_and_refuses_resend(tmp_path):
    path = Path(__file__).parents[1] / 'experiments/2026-09-30-message-content-smoke.py'
    assert path.exists(), 'Authored smoke runner is missing'
    spec = importlib.util.spec_from_file_location('content_smoke', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    attempts = []

    def generate(config, prompt):
        attempts.append(prompt)
        assert set(config) == {'model', 'configuration', 'timeout_ms'}
        assert 'response_json_schema' in config['configuration']
        assert 'response_schema' not in config['configuration']
        if len(attempts) == 2:
            raise RuntimeError('Do not save exception bodies or credentials')
        # Case 1 supplies code: this valid no/no result deliberately disagrees.
        judgment = {'value': 'no', 'evidence': [{'turn_id': 'message', 'line': 1}]}
        return {'candidates': [{'finish_reason': 'STOP', 'content': {'parts': [
            {'text': json.dumps({'content_supplied': judgment, 'expressed_request': judgment})}]}}]}

    folder = tmp_path / 'smoke'
    report = smoke.execute(folder, generate)
    assert report['counts'] == {'complete': 1, 'error': 1, 'unattempted': 10}
    assert report['attempted'] == 2 and report['scheduled'] == 12
    assert report['matches'] == {'content_supplied': 0, 'expressed_request': 1, 'both': 0}
    assert report['clean_smoke'] is False
    assert report['cases'][0]['observation']['content_supplied']['evidence'][0]['quote'] == 'total = sum(values)'
    assert report['cases'][1]['error_type'] == 'RuntimeError'
    assert 'Do not save exception bodies' not in json.dumps(report)
    assert (folder / 'raw/01.json').exists()
    assert json.loads((folder / 'report.json').read_text()) == report
    with pytest.raises(FileExistsError):
        smoke.execute(folder, generate)
    assert len(attempts) == 2
