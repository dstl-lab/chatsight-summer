"""Offline, text-free report for the frozen course-account history comparison."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory


def _module(name):
    spec = importlib.util.spec_from_file_location('course_history_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


protocol = _module('protocol')


def _average(values):
    return mean(values) if values else None


def _arm(records, reference):
    counts = Counter({'reply': 0, 'no-reply': 0, 'error': 0})
    valid, replies, errors = [], [], []
    for row in records:
        if row['status'] == 'error':
            counts['error'] += 1
            errors.append({'slot': row['slot'], 'error_type': row['error_type']})
        elif row['status'] == 'complete':
            decision = protocol.student_continuation.Continuation.model_validate(row['parsed'])
            valid.append(decision.model_dump())
            counts[decision.decision] += 1
            if decision.decision == 'reply':
                replies.append(decision.text)
        else:
            raise ValueError('Expected terminal receipts only')
    categories = Counter(protocol.form(d['text']) if d['decision'] == 'reply' else 12 for d in valid)
    return {'counts': dict(counts), 'valid_decisions': len(valid),
            'category_counts': [categories[k] for k in range(13)],
            'form_score': protocol.fair_form_score(valid, reference) if len(valid) == 5 else None,
            'reply_denominator': len(replies),
            'character_mae': _average([abs(len(text) - len(reference)) for text in replies]),
            'newline_rate': _average(['\n' in text for text in replies]),
            'backtick_rate': _average(['`' in text for text in replies]), 'errors': errors}


def summarize(plan, records, queries, references):
    """Score validated terminal slots; return numeric diagnostics without source text."""
    ids = [c['id'] for c in plan['cases']]
    query_map = {q['id']: q for q in queries}
    reference_map = {r['id']: r for r in references}
    if (len(ids) != 10 or len(set(ids)) != 10 or len(queries) != 10 or len(references) != 10
            or set(query_map) != set(ids) or set(reference_map) != set(ids)):
        raise ValueError('Expected the same ten unique cases in all inputs')
    schedule = plan['schedule']
    if (len(records) != 100 or len(schedule) != 100
            or [s['slot'] for s in schedule] != list(range(1, 101))
            or len({(s['case_id'], s['condition'], s['draw']) for s in schedule}) != 100):
        raise ValueError('Expected the fixed hundred scheduled slots')
    for row, slot in zip(records, schedule):
        if ({k: row[k] for k in ('slot', 'case_id', 'condition', 'draw')} != slot
                or slot['case_id'] not in ids or slot['condition'] not in protocol.CONDITIONS
                or slot['draw'] not in range(1, 6)):
            raise ValueError('Receipt does not match its scheduled identity')
    cases = []
    for case_id in ids:
        query, target = query_map[case_id], reference_map[case_id]
        if (target['conversation_id'] != query['conversation_id']
                or not isinstance(target['text'], str) or not target['text'].strip()):
            raise ValueError('Recorded reference does not bind to this nonblank case')
        reference = target['text']
        arms = {condition: _arm([r for r in records if r['case_id'] == case_id
                                and r['condition'] == condition], reference)
                for condition in protocol.CONDITIONS}
        scores = [arms[c]['form_score'] for c in protocol.CONDITIONS]
        student_texts = [t['text'] for t in query['prefix'] if t['role'] == 'student']
        cases.append({'id': case_id, 'reference': {'category': protocol.form(reference),
                      'characters': len(reference), 'newline': '\n' in reference, 'backtick': '`' in reference},
                      'baseline': {'visible_student_messages': len(student_texts),
                                   'form_score': protocol.empirical_form_score(student_texts, reference)},
                      'conditions': arms,
                      'history_minus_current_exchange': scores[1] - scores[0] if None not in scores else None})
    paired = [c for c in cases if c['history_minus_current_exchange'] is not None]
    primary = protocol.paired_summary([c['history_minus_current_exchange'] for c in cases])
    primary['condition_means'] = {condition: _average([c['conditions'][condition]['form_score'] for c in paired])
                                  for condition in protocol.CONDITIONS}
    primary['condition_mean_population'] = 'The same complete case pairs as the primary contrast'
    counts = {condition: {status: sum(c['conditions'][condition]['counts'][status] for c in cases)
                          for status in ('reply', 'no-reply', 'error')} for condition in protocol.CONDITIONS}
    return {'version': 1, 'population': 'Ten provisional course accounts; student eligibility unverified',
            'scheduled_requests': 100, 'counts': counts, 'primary': primary,
            'baseline': {'mean_form_score': mean(c['baseline']['form_score'] for c in cases),
                         'cases': 10, 'definition': 'Exact form-frequency distribution of all visible individual student messages'},
            'cases': cases, 'limits': [
                'Primary: finite-ensemble-corrected half-scaled categorical Brier; lower is better. '
                'Negative history-minus-current-exchange means lower literal message-form error.',
                'The correction assumes independent, stationary draws; five draws per arm remain noisy.',
                'Incomplete pairs stay in the scheduled population; missing-outcome bounds are not confidence intervals.',
                'Character error and newline/backtick rates use reply draws only; every denominator is reported.',
                'No-reply is category 12, not zero-length text. Errors are missing outcomes, not student behavior.',
                'The sample is conditional on a recorded return message and cannot measure real silence probabilities.',
                'Earlier dialogue contains task and tutor information. Literal form does not establish semantics, '
                'personalization, eligibility, overall realism or an adoption decision.',
                'The fixed batch ends here: no retries, replacements, tuning, new labels or automatic follow-up.']}


def markdown(result):
    def number(value):
        return 'unavailable' if value is None else f'{value:.4f}'
    primary = result['primary']
    bounds = primary['missing_outcome_bounds']
    lines = ['# Course-account history comparison', '', result['population'] + '.', '',
             f"Complete case pairs: {primary['complete_pairs']}/10; scheduled requests: 100.", '',
             f"All-ten history-minus-current-exchange score: {number(primary['all_ten_mean'])}.",
             f"Complete-pair contrast: {number(primary['complete_pair_mean'])}.",
             f"Missing-outcome bounds: [{number(bounds[0])}, {number(bounds[1])}] (not a confidence interval).", '',
             'Primary arm means below use the same complete pairs. Lower form error is better.', '',
             '| Condition | Mean form score | Reply | No reply | Error |',
             '| --- | ---: | ---: | ---: | ---: |']
    for condition in protocol.CONDITIONS:
        counts = result['counts'][condition]
        lines.append(f"| {condition} | {number(primary['condition_means'][condition])} | "
                     f"{counts['reply']} | {counts['no-reply']} | {counts['error']} |")
    lines.extend(['', f"Visible-student form-frequency baseline, all ten cases: {number(result['baseline']['mean_form_score'])}.", '',
                  '| Case | Current score | History score | History − current | Baseline |',
                  '| --- | ---: | ---: | ---: | ---: |'])
    for case in result['cases']:
        arms = case['conditions']
        lines.append(f"| {case['id']} | {number(arms['current-exchange']['form_score'])} | "
                     f"{number(arms['history']['form_score'])} | {number(case['history_minus_current_exchange'])} | "
                     f"{number(case['baseline']['form_score'])} |")
    lines.extend(['', 'Secondary diagnostics use reply draws only; counts include all five scheduled draws per arm.', '',
                  '| Case | Condition | Reply / no reply / error | Character MAE | Newline rate | Backtick rate | Reply denominator |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: |'])
    for case in result['cases']:
        for condition, arm in case['conditions'].items():
            count = arm['counts']
            lines.append(f"| {case['id']} | {condition} | {count['reply']} / {count['no-reply']} / {count['error']} | "
                         f"{number(arm['character_mae'])} | {number(arm['newline_rate'])} | "
                         f"{number(arm['backtick_rate'])} | {arm['reply_denominator']} |")
    if 'provider' in result:
        provider = result['provider']
        lines.extend(['', f"Saved provider responses: {provider['raw_responses']}/100; "
                      f"responses without a returned model version: {provider['missing_model_version']}.", '',
                      '| Returned model version | Responses |', '| --- | ---: |'])
        lines.extend(f'| {version} | {count} |' for version, count in provider['model_versions'].items())
        lines.extend(['', 'Usage totals cover reported top-level integer fields; missing fields are not zeros.', '',
                      '| Usage field | Total | Reporting responses |', '| --- | ---: | ---: |'])
        lines.extend(f"| {key} | {value} | {provider['usage_reporting_counts'][key]} |"
                     for key, value in provider['usage_integer_totals'].items())
    lines.extend(['', *['- ' + note for note in result['limits']], ''])
    return '\n'.join(lines)


def report(prepared, references, expected_reference_hash, out):
    """Verify a completed run, then read/hash-bind references and write one report directory."""
    prepared, references, out = Path(prepared), Path(references), Path(out)
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    plan, records = _module('run').read_receipts(prepared)
    source = Path(plan['input_path'])
    raw_references, raw_queries = references.read_bytes(), source.read_bytes()
    if (protocol.sha256(raw_references).hexdigest() != expected_reference_hash
            or protocol.sha256(raw_queries).hexdigest() != plan['input_sha256']):
        raise ValueError('Frozen scoring input hash changed')
    result = summarize(plan, records, json.loads(raw_queries), json.loads(raw_references))
    versions, usage, reported = Counter(), Counter(), Counter()
    raw_count = missing_version = 0
    for receipt in records:
        if 'raw_file' not in receipt:
            continue
        raw = (prepared / 'execution' / receipt['raw_file']).read_bytes()
        if protocol.sha256(raw).hexdigest() != receipt['raw_sha256']:
            raise ValueError('Provider response changed during reporting')
        response = json.loads(raw)
        raw_count += 1
        model_version = response.get('model_version')
        if isinstance(model_version, str) and model_version:
            versions[model_version] += 1
        else:
            missing_version += 1
        for key, value in (response.get('usage_metadata') or {}).items():
            if type(value) is int:
                usage[key] += value
                reported[key] += 1
    result['provider'] = {'raw_responses': raw_count, 'model_versions': dict(versions),
                          'missing_model_version': missing_version, 'usage_integer_totals': dict(usage),
                          'usage_reporting_counts': dict(reported)}
    result['provenance'] = {'reference_sha256': expected_reference_hash,
                            'queries_sha256': plan['input_sha256'],
                            'plan_sha256': protocol.file_hash(prepared / 'plan.json'),
                            'completed_sha256': protocol.file_hash(prepared / 'execution/completed.json'),
                            'report_source_sha256': protocol.file_hash(__file__),
                            'protocol_source_sha256': protocol.file_hash(Path(__file__).with_name('protocol.py'))}
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent, prefix='.course-history-report-') as temporary:
        staged = Path(temporary) / 'report'
        staged.mkdir()
        (staged / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        (staged / 'report.md').write_text(markdown(result))
        staged.rename(out)
    return {'json': str(out / 'report.json'), 'markdown': str(out / 'report.md'),
            'complete_pairs': result['primary']['complete_pairs']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--reference-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.prepared, args.references, args.reference_sha256, args.out), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(type(error).__name__ + ': report failed; private input details omitted')
