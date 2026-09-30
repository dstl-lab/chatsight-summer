"""Read-only benchmark projection checks using the frozen study's authored data."""
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def module(path):
    spec = importlib.util.spec_from_file_location('history_projection_test_' + path.stem, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@pytest.fixture
def saved_history(tmp_path):
    authored = module(ROOT / 'experiments/2026-09-29-course-account-history/test_report.py')
    report = authored.reporter()
    _, _, queries, references = authored.authored()
    source = tmp_path / 'checkpoints/inputs/queries.json'
    reference = tmp_path / 'checkpoints/references/recorded-next.json'
    source.parent.mkdir(parents=True)
    reference.parent.mkdir(parents=True)
    source.write_text(json.dumps(queries))
    references[1]['text'] = '  RECORDED_SECRET  '
    reference.write_text(json.dumps(references))
    folder = tmp_path / 'saved'
    pins = report.protocol.prepare(source, report.protocol.file_hash(source), folder)
    plan = json.loads((folder / 'plan.json').read_text())
    calls = iter(plan['schedule'])

    def fake(_plan, _prompt):
        slot = next(calls)
        if slot['case_id'] == 'case-00' and slot['condition'] == 'history' and slot['draw'] == 1:
            raise TimeoutError('PRIVATE_PROVIDER_DETAIL')
        choice = ({'decision': 'reply', 'text': '  ok  '} if slot['condition'] == 'current-exchange'
                  else {'decision': 'no-reply', 'text': ''})
        return {'candidates': [{'finish_reason': 'STOP', 'content': {'parts': [
            {'text': 'PRIVATE_PROVIDER_THOUGHT', 'thought': True}, {'text': json.dumps(choice)}]}}]}

    report._module('run').execute(folder, pins['plan_sha256'], pins['prompts_sha256'], fake, progress=False)
    report.report(folder, reference, report.protocol.file_hash(reference), folder / 'report')
    return folder, source, reference


def projection():
    path = ROOT / 'apps/history_benchmark.py'
    assert path.exists(), 'Saved benchmark projection is not implemented'
    return module(path)


def test_retains_all_draws_exact_text_and_scores_without_polluting_prefix(saved_history):
    folder, source, reference = saved_history
    paths = [p for p in folder.rglob('*') if p.is_file()] + [source, reference]
    before = {p: p.read_bytes() for p in paths}
    result = projection().load(folder)
    assert {p: p.read_bytes() for p in paths} == before
    assert result['version'] == 1 and result['model'] == 'gemini-2.5-pro'
    assert result['draws_per_condition'] == 5
    assert [c['id'] for c in result['cases']] == [f'course-account-v1-{i:02}' for i in range(1, 11)]
    assert [c['number'] for c in result['cases']] == list(range(1, 11))
    study = result['study']
    assert study['scheduled_requests'] == 100 and study['primary']['complete_pairs'] == 9
    assert study['primary']['condition_means'] == {'current-exchange': 0, 'history': 1}
    assert study['primary']['all_ten_mean'] is None
    assert study['baseline']['mean_form_score'] == 0.25
    assert study['counts']['history'] == {'reply': 0, 'no-reply': 49, 'error': 1}
    assert result['limits'] == study['limits']
    first = result['cases'][0]
    assert first['current_start'] == 2 and len(first['prefix']) == 4
    assert first['prefix'][0] == {'role': 'student', 'text': 'VISIBLE_SECRET'}
    assert all('RECORDED_SECRET' not in json.dumps(case['prefix']) for case in result['cases'])
    assert first['reference'] == {'text': 'RECORDED_SECRET', 'category': 0,
                                 'characters': 15, 'newline': False, 'backtick': False}
    assert result['cases'][1]['reference']['text'] == '  RECORDED_SECRET  '
    assert first['baseline']['category_counts'] == [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
    assert first['baseline']['category_probabilities'] == [.5, 0, 0, 0, 0, 0, 0, 0, .5, 0, 0, 0, 0]
    current, history = first['conditions']
    assert [c['id'] for c in first['conditions']] == ['current-exchange', 'history']
    assert current['form_score'] == 0 and current['character_mae'] == 9
    assert history['form_score'] is None and history['reply_denominator'] == 0
    assert history['draws'][0] == {'slot': 2, 'draw': 1, 'status': 'error', 'decision': None,
                                   'text': None, 'form': None, 'error_type': 'TimeoutError'}
    assert current['draws'][0]['text'] == '  ok  '
    assert current['draws'][0]['form'] == {'category': 0, 'characters': 6, 'newline': False, 'backtick': False}
    assert history['draws'][1]['decision'] == 'no-reply' and history['draws'][1]['text'] == ''
    assert history['draws'][1]['form'] == {'category': 12, 'characters': None, 'newline': None, 'backtick': None}
    assert all([d['draw'] for d in arm['draws']] == [1, 2, 3, 4, 5]
               for case in result['cases'] for arm in case['conditions'])
    assert sorted(d['slot'] for c in result['cases'] for arm in c['conditions'] for d in arm['draws']) == list(range(1, 101))
    encoded = json.dumps(result, allow_nan=False)
    assert all(secret not in encoded for secret in ('account-secret', 'conversation-secret',
        'PRIVATE_PROVIDER', str(folder), str(source), 'input_path', 'raw_file', 'prompt_sha256'))


@pytest.mark.parametrize('target', ['source', 'reference', 'plan.json', 'prompts.json',
    'execution/receipts/001.json', 'execution/raw/001.json', 'execution/completed.json',
    'report/report.json', 'provenance'])
def test_frozen_artifact_changes_fail_closed(saved_history, target):
    folder, source, reference = saved_history
    path = {'source': source, 'reference': reference, 'provenance': folder / 'report/report.json'}.get(target, folder / target)
    value = json.loads(path.read_text())
    if target in ('source', 'reference'):
        value[0]['text' if target == 'reference' else 'student_id'] = 'TAMPERED_PRIVATE_VALUE'
    elif target == 'report/report.json':
        value['primary']['complete_pairs'] = 10
    elif target == 'provenance':
        value['provenance']['reference_sha256'] = '0' * 64
    else:
        value = {'forged': 'TAMPERED_PRIVATE_VALUE'}
    path.write_text(json.dumps(value))
    with pytest.raises((ValueError, KeyError, TypeError)):
        projection().load(folder)


def test_rejects_symlinked_reference(saved_history):
    folder, _, reference = saved_history
    other = reference.with_suffix('.original')
    reference.rename(other)
    reference.symlink_to(other)
    with pytest.raises(ValueError):
        projection().load(folder)
