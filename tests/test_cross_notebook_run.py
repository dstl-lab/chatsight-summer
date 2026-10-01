"""Authored fixtures only: bounded dispatch, replay, and three-arm scoring."""
import importlib.util
import json
from pathlib import Path

import pytest


FILE = Path(__file__).resolve().parents[1] / 'experiments/2026-10-01-cross-notebook-run.py'


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location('cross_notebook_test_runner', FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, value):
    path.write_text(json.dumps(value))


def prepared(tmp_path, runner, donors=10):
    queries = [{'id': f'case-{i}', 'conversation_id': f'conversation-{i}',
                'student_id': f'account-{i}', 'prefix': [
                    {'role': 'student', 'text': 'hi'}, {'role': 'tutor', 'text': 'try it'}]}
               for i in range(10)]
    source = tmp_path / 'inputs.json'
    save(source, {'queries': queries, 'history': {q['id']: ['ok', 'x' * 301] for q in queries},
                  'cards': {q['id']: {} for q in queries},
                  'donors': {q['id']: f'account-{(i + 1) % 10}' if i < donors else None for i, q in enumerate(queries)}})
    bank = [{'case_id': q['id'], 'condition': arm, 'prompt': f"{q['id']} {arm}"}
            for i, q in enumerate(queries)
            for arm in ('generic', 'matched', 'other-account') if arm != 'other-account' or i < donors]
    for row in bank:
        row['prompt_sha256'] = runner.protocol.sha256(row['prompt'].encode()).hexdigest()
    schedule = [{'case_id': row['case_id'], 'condition': row['condition'], 'draw': draw}
                for draw in range(1, 6) for row in bank]
    schedule = [dict(row, slot=i) for i, row in enumerate(schedule, 1)]
    plan = {'cases': [{'id': q['id']} for q in queries], 'input_path': str(source),
            'input_sha256': runner.transport.file_hash(source), 'model': 'gemini-2.5-pro',
            'sdk_version': runner.transport.version('google-genai'),
            'configuration': {'temperature': 1.0, 'max_output_tokens': 8192,
                'response_mime_type': 'application/json',
                'response_json_schema': runner.protocol.student_continuation.Continuation.model_json_schema()},
            'timeout_ms': 120000, 'workers': 1, 'sdk_attempts': 1, 'adapter_attempts': 1,
            'stopping_rule': 'One fixed batch, no retries or resume.',
            'code_pins': runner.required_pins(), 'requests': len(schedule), 'schedule': schedule,
            'prompt_hashes': {f"{r['case_id']}:{r['condition']}": r['prompt_sha256'] for r in bank}}
    save(tmp_path / 'plan.json', plan)
    save(tmp_path / 'prompts.json', bank)
    return runner.transport.file_hash(tmp_path / 'plan.json'), runner.transport.file_hash(tmp_path / 'prompts.json')


def response(decision='reply', text='ok', finish='STOP'):
    return {'candidates': [{'finish_reason': finish, 'content': {'parts': [
        {'text': json.dumps({'decision': decision, 'text': text})}]}}],
        'model_version': 'authored-test-model', 'usage_metadata': {'total_token_count': 7}}


def references(tmp_path, runner):
    path = tmp_path / 'references.json'
    save(path, [{'id': f'case-{i}', 'conversation_id': f'conversation-{i}', 'text': 'ok'} for i in range(10)])
    return path, runner.transport.file_hash(path)


def test_complete_run_scores_raw_outputs_and_cannot_send_again(tmp_path, runner):
    hashes = prepared(tmp_path, runner)
    def generate(plan, prompt):
        arm = prompt.split()[-1]
        return response('no-reply', '') if arm == 'other-account' else response(text='x' * 301 if arm == 'generic' else 'ok')
    done = runner.execute(tmp_path, *hashes, generate, progress=False)
    assert (done['scheduled'], done['complete'], done['errors']) == (150, 150, 0)
    report = runner.report(tmp_path, *references(tmp_path, runner))
    assert report['primary']['all_ten_mean'] == -1
    assert report['primary']['complete_pairs'] == 10
    assert report['history_baseline_mean'] == .25
    assert report['current_prefix_baseline_mean'] == 0
    assert report['counts']['other-account']['no-reply'] == 50
    assert report['provider']['usage_integer_totals']['total_token_count'] == 1050
    with pytest.raises(FileExistsError):
        runner.execute(tmp_path, *hashes, generate, progress=False)


def test_unavailable_donors_do_not_remove_primary_cases(tmp_path, runner):
    hashes = prepared(tmp_path, runner, donors=5)
    runner.execute(tmp_path, *hashes, lambda *_: response(), progress=False)
    result = runner.report(tmp_path, *references(tmp_path, runner))
    assert result['scheduled_requests'] == 125
    assert result['primary']['complete_pairs'] == 10
    assert result['secondary']['matched_minus_other_account']['complete_pairs'] == 5
    assert result['counts']['other-account']['reply'] == 25


@pytest.mark.parametrize('change', ['duplicate', 'extra', 'configuration', 'input'])
def test_changed_or_invalid_plan_cannot_start_dispatch(tmp_path, runner, change):
    hashes = prepared(tmp_path, runner)
    plan = json.loads((tmp_path / 'plan.json').read_text())
    if change == 'duplicate':
        plan['schedule'][1].update({k: plan['schedule'][0][k] for k in ('case_id', 'condition', 'draw')})
    elif change == 'extra':
        plan['schedule'].append(dict(plan['schedule'][0], slot=151))
        plan['requests'] = 151
    elif change == 'configuration':
        plan['configuration']['temperature'] = 0
    else:
        (tmp_path / 'inputs.json').write_text('{}')
    save(tmp_path / 'plan.json', plan)
    hashes = runner.transport.file_hash(tmp_path / 'plan.json'), hashes[1]
    with pytest.raises(ValueError):
        runner.execute(tmp_path, *hashes, lambda *_: pytest.fail('Invalid plans cannot dispatch'), progress=False)
    assert not (tmp_path / 'execution').exists()


def test_donor_failure_does_not_invalidate_primary_and_is_not_silence(tmp_path, runner):
    hashes = prepared(tmp_path, runner)
    calls = 0
    def generate(plan, prompt):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TimeoutError('private detail must not be retained')
        return response()
    runner.execute(tmp_path, *hashes, generate, progress=False)
    result = runner.report(tmp_path, *references(tmp_path, runner))
    assert calls == 150
    assert result['primary']['complete_pairs'] == 10
    assert result['secondary']['matched_minus_other_account']['complete_pairs'] == 9
    assert result['counts']['other-account']['error'] == 1
    assert result['counts']['other-account']['no-reply'] == 0
    assert 'private detail' not in (tmp_path / 'execution/receipts/003.json').read_text()


def test_interruption_is_reportable_without_resuming(tmp_path, runner):
    hashes = prepared(tmp_path, runner)
    calls = 0
    def generate(*_):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return response()
    with pytest.raises(KeyboardInterrupt):
        runner.execute(tmp_path, *hashes, generate, progress=False)
    result = runner.report(tmp_path, *references(tmp_path, runner))
    assert result['primary']['complete_pairs'] == 0
    assert result['primary']['missing_outcome_bounds'] == [-1, 1]
    assert result['counts']['matched']['pending'] == 1
    assert result['counts']['generic']['not-attempted'] == 49
    with pytest.raises(FileExistsError):
        runner.execute(tmp_path, *hashes, generate, progress=False)


def test_capped_output_is_error_and_raw_tampering_is_rejected(tmp_path, runner):
    hashes = prepared(tmp_path, runner)
    runner.execute(tmp_path, *hashes, lambda *_: response(finish='MAX_TOKENS'), progress=False)
    result = runner.report(tmp_path, *references(tmp_path, runner))
    assert result['counts']['generic']['error'] == 50
    assert result['primary']['all_ten_mean'] is None
    save(tmp_path / 'execution/raw/001.json', response())
    with pytest.raises(ValueError):
        runner.read_receipts(tmp_path)


@pytest.mark.parametrize('donor', ['account-0', 'outside-account'])
def test_invalid_donor_cannot_be_dispatched(tmp_path, runner, donor):
    hashes = prepared(tmp_path, runner)
    source = tmp_path / 'inputs.json'
    data = json.loads(source.read_text())
    data['donors']['case-0'] = donor
    save(source, data)
    plan = json.loads((tmp_path / 'plan.json').read_text())
    plan['input_sha256'] = runner.transport.file_hash(source)
    save(tmp_path / 'plan.json', plan)
    hashes = runner.transport.file_hash(tmp_path / 'plan.json'), hashes[1]
    with pytest.raises(ValueError):
        runner.execute(tmp_path, *hashes, lambda *_: pytest.fail('Self donor cannot dispatch'), progress=False)


def test_report_requires_exact_reference_hash_and_case_binding(tmp_path, runner):
    hashes = prepared(tmp_path, runner)
    runner.execute(tmp_path, *hashes, lambda *_: response(), progress=False)
    ref, digest = references(tmp_path, runner)
    with pytest.raises(ValueError):
        runner.report(tmp_path, ref, '0' * 64)
    values = json.loads(ref.read_text())
    values[0]['conversation_id'] = 'another-conversation'
    save(ref, values)
    with pytest.raises(ValueError):
        runner.report(tmp_path, ref, runner.transport.file_hash(ref))
