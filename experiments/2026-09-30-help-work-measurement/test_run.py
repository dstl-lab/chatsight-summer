"""Authored provider responses; no credentials, network or course data."""
import importlib.util
import json
from pathlib import Path

import pytest


def module(name):
    path = Path(__file__).with_name(name + '.py')
    spec = importlib.util.spec_from_file_location('test_measurement_' + name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def prepared(tmp_path):
    cases, judgments = [], []
    for c in range(11):
        candidates = [{'id': f'm-{c}-{i}', 'text': f'Authored message {c}-{i}'} for i in range(8)]
        cases.append({'id': f'case-{c}', 'context_status': 'Authored',
            'prefix': {'context': [], 'turns': [{'id': f't-{c}', 'role': 'student', 'text': f'Authored context {c}'}]},
            'candidates': candidates})
        judgments.extend({'id': row['id'], 'help_request': 'yes', 'work_present': 'no', 'note': None}
                         for row in candidates)
    packet = {'packet_id': 'authored-packet', 'rubric_id': 'help-work-v1',
        'definitions': {'help_request': 'Authored help definition.', 'work_present': 'Authored work definition.'},
        'cases': cases}
    form = {'packet_id': packet['packet_id'], 'rubric_id': packet['rubric_id'], 'reviewer': 'authored',
        'previously_seen_cases': 'no', 'judgments': judgments}
    paths = {key: tmp_path / (key + '.json') for key in ('packet', 'review')}
    paths['packet'].write_text(json.dumps(packet))
    paths['review'].write_text(json.dumps(form))
    folder = tmp_path / 'audit'
    module('audit').prepare(folder, [paths])
    runner = module('run')
    verification = {'verified': True, 'files': {str(path): runner.file_hash(path) for path in paths.values()}}
    frozen = runner.freeze(folder, verification)
    return runner, folder, frozen['dispatch_plan_sha256']


def response(value, finish='STOP'):
    return {'model_version': 'authored', 'candidates': [{'finish_reason': finish,
        'content': {'parts': [{'thought': True, 'text': 'IGNORED_PROVIDER_THOUGHT'},
                              {'text': json.dumps(value)}]}}]}


def test_once_only_audit_preserves_failures_replays_and_rejects_tampering(tmp_path):
    runner, folder, expected = prepared(tmp_path)
    calls = []
    def generate(plan, prompt):
        calls.append(prompt)
        assert plan['requests'] == 88 and plan['sdk_attempts'] == 1
        assert 'authored-packet' not in prompt and 'previously_seen_cases' not in prompt
        if len(calls) == 1:
            raise TimeoutError('PRIVATE_EXCEPTION_DETAIL')
        return response({'help_request': 'unclear' if len(calls) == 3 else 'yes', 'work_present': 'no'},
                        'MAX_TOKENS' if len(calls) == 2 else 'STOP')
    runner.execute(folder, expected, generate, progress=False)
    result = runner.report(folder, expected)
    assert len(calls) == 88
    assert result['outcomes'] == {'complete': 86, 'error': 2, 'missing': 0}
    assert result['flags']['help_request']['outcomes_on_eligible'] == {
        'binary': 85, 'unclear': 1, 'error': 2, 'missing': 0}
    assert result['flags']['work_present']['confusion'] == {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 86}
    assert 'PRIVATE_EXCEPTION_DETAIL' not in (folder / 'execution/receipts/001.json').read_text()
    assert 'IGNORED_PROVIDER_THOUGHT' not in json.dumps(result)
    with pytest.raises(FileExistsError):
        runner.execute(folder, expected, generate, progress=False)
    assert len(calls) == 88
    path = folder / 'execution/raw/004.json'
    path.write_text(json.dumps(response({'help_request': 'no', 'work_present': 'yes'})))
    with pytest.raises(ValueError, match='response changed'):
        runner.report(folder, expected)


def test_interruption_stays_missing_and_cannot_resume(tmp_path):
    runner, folder, expected = prepared(tmp_path)
    def interrupt(*_):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        runner.execute(folder, expected, interrupt, progress=False)
    result = runner.report(folder, expected)
    assert result['outcomes'] == {'complete': 0, 'error': 0, 'missing': 88}
    assert result['flags']['work_present']['specificity']['estimate'] is None
    with pytest.raises(FileExistsError):
        runner.execute(folder, expected, interrupt, progress=False)
    payloads = folder / 'dispatch/payloads.json'
    payloads.write_text('[]')
    with pytest.raises(ValueError, match='inputs or fixed schedule'):
        runner.inputs(folder, expected)
