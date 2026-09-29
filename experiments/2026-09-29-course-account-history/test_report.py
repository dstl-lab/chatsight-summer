"""Authored offline report checks; never reads recorded study messages."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


def reporter():
    path = Path(__file__).with_name('report.py')
    assert path.exists(), 'Offline report is not implemented'
    spec = importlib.util.spec_from_file_location('course_account_report_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authored():
    queries = [{'id': f'case-{i:02}', 'conversation_id': f'conversation-secret-{i}',
                'student_id': f'account-secret-{i}', 'prefix': [
                    {'role': 'student', 'text': 'VISIBLE_SECRET'},
                    {'role': 'tutor', 'text': 'earlier answer'},
                    {'role': 'student', 'text': 'x' * 301},
                    {'role': 'tutor', 'text': 'current answer'}]} for i in range(10)]
    references = [{'id': q['id'], 'conversation_id': q['conversation_id'],
                   'text': 'RECORDED_SECRET'} for q in queries]
    schedule = [{'slot': 10 * i + 2 * (draw - 1) + offset + 1, 'case_id': q['id'],
                 'condition': condition, 'draw': draw}
                for i, q in enumerate(queries) for draw in range(1, 6)
                for offset, condition in enumerate(('current-exchange', 'history'))]
    plan = {'cases': [{'id': q['id']} for q in queries], 'schedule': schedule}
    records = [slot | {'status': 'complete', 'parsed':
                       {'decision': 'reply', 'text': 'ok'} if slot['condition'] == 'current-exchange'
                       else {'decision': 'no-reply', 'text': ''}} for slot in schedule]
    return plan, records, queries, references


def test_no_reply_scores_as_mismatch_and_never_zero_length_success():
    module = reporter()
    result = module.summarize(*authored())
    assert result['primary']['all_ten_mean'] == 1
    assert result['primary']['condition_means'] == {'current-exchange': 0, 'history': 1}
    assert result['primary']['missing_outcome_bounds'] == [1, 1]
    assert result['baseline']['mean_form_score'] == 0.25
    assert result['counts']['history'] == {'reply': 0, 'no-reply': 50, 'error': 0}
    current = result['cases'][0]['conditions']['current-exchange']
    history = result['cases'][0]['conditions']['history']
    assert current['character_mae'] == 13
    assert current['reply_denominator'] == 5
    assert history['character_mae'] is None and history['reply_denominator'] == 0
    encoded = json.dumps(result) + module.markdown(result)
    assert all(secret not in encoded for secret in
               ('RECORDED_SECRET', 'VISIBLE_SECRET', 'account-secret', 'conversation-secret'))


def test_error_keeps_case_missing_and_counts_all_scheduled_slots():
    module = reporter()
    plan, records, queries, references = authored()
    records[1] = plan['schedule'][1] | {'status': 'error', 'error_type': 'AuthoredError'}
    result = module.summarize(plan, records, queries, references)
    assert result['primary']['complete_pairs'] == 9
    assert result['primary']['all_ten_mean'] is None
    assert result['primary']['complete_pair_mean'] == 1
    assert result['primary']['missing_outcome_bounds'] == [0.8, 1]
    assert result['cases'][0]['conditions']['history']['form_score'] is None
    assert result['counts']['history'] == {'reply': 0, 'no-reply': 49, 'error': 1}


def test_mixed_forms_use_corrected_score_and_reply_only_secondary_rates():
    module = reporter()
    plan, records, queries, references = authored()
    for row in records:
        if row['condition'] == 'history' and row['draw'] in (1, 2):
            row['parsed'] = {'decision': 'reply', 'text': 'ok' if row['draw'] == 1 else '`\n' + 'x' * 301}
    result = module.summarize(plan, records, queries, references)
    history = result['cases'][0]['conditions']['history']
    assert history['form_score'] == 0.45
    assert result['primary']['all_ten_mean'] == pytest.approx(0.45)
    assert history['category_counts'][12] == 3
    assert history['character_mae'] == 150.5
    assert history['newline_rate'] == history['backtick_rate'] == 0.5
    assert history['reply_denominator'] == 2


@pytest.mark.parametrize('mutation', ('reference-id', 'conversation', 'blank-reference',
                                      'receipt-identity', 'duplicate-slot', 'blank-reply'))
def test_rejects_wrong_reference_or_invalid_draw_binding(mutation):
    module = reporter()
    plan, records, queries, references = deepcopy(authored())
    if mutation == 'reference-id':
        references[0]['id'] = 'other-case'
    elif mutation == 'conversation':
        references[0]['conversation_id'] = 'other-conversation'
    elif mutation == 'blank-reference':
        references[0]['text'] = ' '
    elif mutation == 'receipt-identity':
        records[0]['case_id'] = 'case-01'
    elif mutation == 'duplicate-slot':
        records[1] = records[0]
    else:
        records[0]['parsed']['text'] = ' '
    with pytest.raises(ValueError):
        module.summarize(plan, records, queries, references)


def test_completed_run_report_checks_reference_hash_and_records_usage(tmp_path):
    module = reporter()
    run = module._module('run')
    _, _, queries, references = authored()
    source, reference_file = tmp_path / 'queries.json', tmp_path / 'references.json'
    source.write_text(json.dumps(queries))
    reference_file.write_text(json.dumps(references))
    prepared = tmp_path / 'prepared'
    pins = module.protocol.prepare(source, module.protocol.file_hash(source), prepared)

    def fake(plan, prompt):
        return {'model_version': 'authored-model', 'usage_metadata': {
            'prompt_token_count': 2, 'candidates_token_count': 3, 'total_token_count': 5},
            'candidates': [{'finish_reason': 'STOP', 'content': {'parts': [
                {'text': json.dumps({'decision': 'no-reply', 'text': ''})}]}}]}

    run.execute(prepared, pins['plan_sha256'], pins['prompts_sha256'], fake, progress=False)
    out = tmp_path / 'report'
    with pytest.raises(ValueError, match='hash'):
        module.report(prepared, reference_file, '0' * 64, out)
    assert not out.exists()
    module.report(prepared, reference_file, module.protocol.file_hash(reference_file), out)
    result = json.loads((out / 'report.json').read_text())
    assert result['primary']['all_ten_mean'] == 0
    assert result['provider']['model_versions'] == {'authored-model': 100}
    assert result['provider']['usage_integer_totals']['total_token_count'] == 500
    assert result['provider']['usage_reporting_counts']['total_token_count'] == 100
    assert 'RECORDED_SECRET' not in (out / 'report.md').read_text()
    with pytest.raises(FileExistsError):
        module.report(prepared, reference_file, module.protocol.file_hash(reference_file), out)
