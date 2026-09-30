"""Offline source split of the closed help-work-v1 audit; no new labels or calls."""
import argparse
from collections import Counter
from fractions import Fraction as F
import importlib.util
from pathlib import Path

from src.agents import notebook_student as store
from src.eval import fidelity_comparison, saved_comparison


def origins(references, mappings):
    """Join original private identities, never infer provenance from message text."""
    index = {}
    for source, mapping in enumerate(mappings):
        slots = []
        if 'cases' in mapping:
            for case in mapping['cases']:
                slots.append((case['id'], case['reference_id'], 'recorded'))
                slots.extend((case['id'], draw['id'], 'generated') for draw in case['draws'])
        else:
            slots.extend((row['case_id'], row['candidate_id'], 'generated')
                         for row in mapping['occurrences'])
        for case, candidate, origin in slots:
            key = source, mapping['packet_id'], case, candidate
            if key in index and index[key] != origin:
                raise ValueError('A reviewed occurrence has conflicting origins.')
            index[key] = origin
    result, used = {}, set()
    for identity, reference in references.items():
        values = set()
        for row in reference['occurrences']:
            key = tuple(row[k] for k in ('source_index', 'packet_id', 'case_id', 'candidate_id'))
            if key not in index:
                raise ValueError('A reviewed occurrence has no verified origin.')
            values.add(index[key])
            used.add(key)
        if len(values) != 1:
            raise ValueError('Unique input has mixed origins; do not duplicate it across groups.')
        result[identity] = values.pop()
    if used != index.keys():
        raise ValueError('The origin mapping has unreviewed occurrences.')
    return result


def compare(cases):
    """Equal case weights, original draw slots; model unclear ranges over [0,1]."""
    if not cases or any(not row['generated'] for row in cases):
        raise ValueError('Every comparison needs recorded messages and generated draws.')
    result, exact = {}, {}
    for origin in ('recorded', 'generated'):
        human_rate, lower, upper = F(0), F(0), F(0)
        outcomes = Counter()
        for case in cases:
            pairs = [case['recorded']] if origin == 'recorded' else case['generated']
            weight = F(1, len(cases) * len(pairs))
            for human, model in pairs:
                if human not in ('yes', 'no') or model not in ('yes', 'no', 'unclear'):
                    raise ValueError('Keep binary historical judgments and explicit model unclear.')
                outcomes[model] += 1
                human_rate += weight * (human == 'yes')
                lower += weight * (model == 'yes')
                upper += weight * (model != 'no')
        exact[origin] = human_rate, lower, upper
        result[origin] = {'occurrences': sum(outcomes.values()),
            'outcomes': {value: outcomes[value] for value in ('yes', 'no', 'unclear')},
            'human_rate': float(human_rate), 'model_rate_range': list(map(float, (lower, upper))),
            'rate_shift_range': list(map(float, (lower - human_rate, upper - human_rate)))}
    rh, rl, ru = exact['recorded']
    gh, gl, gu = exact['generated']
    result.update(cases=len(cases), human_gap=float(gh-rh),
        model_gap_range=list(map(float, (gl-ru, gu-rl))),
        gap_shift_range=list(map(float, (gl-ru-gh+rh, gu-rl-gh+rh))))
    return result


def execute(folder, expected, output):
    folder = Path(folder).resolve()
    spec = importlib.util.spec_from_file_location('measurement_run',
        Path(__file__).with_name('2026-09-30-help-work-measurement') / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    audit, plan, _ = runner.inputs(folder, expected)
    reproduced = runner.report(folder, expected)
    if reproduced != store._read(folder / 'report.json'):
        raise ValueError('Closed audit report does not reproduce.')
    closure = store._read(folder / 'closure.json')
    if (closure['dispatch_plan_sha256'] != expected
            or closure['report_sha256'] != runner.file_hash(folder / 'report.json')
            or reproduced['outcomes'] != {'complete': 88, 'error': 0, 'missing': 0}):
        raise ValueError('This diagnostic requires the completed, closed recovery audit.')
    saved = audit.load(folder)
    predictions = {job['id']: store._read(folder / 'execution/receipts' / f"{job['slot']:03}.json")
                   for job in plan['schedule']}
    source_paths = [Path(source['packet']['path']) for source in saved['plan']['sources']]
    mapping_paths = [source_paths[0].with_name('private-mapping.json'),
                     source_paths[1].with_name('private-mapping.json'),
                     source_paths[2].parent.parent / 'private-review-mapping.json']
    pins = dict(plan['legacy_verification']['files'])
    pins.update({str(path): runner.file_hash(path) for path in folder.rglob('*') if path.is_file()})
    pins.update({str(Path(path).resolve()): runner.file_hash(path) for path in
                 (__file__, runner.__file__, audit.__file__, fidelity_comparison.__file__, saved_comparison.__file__)})
    if any(pins.get(str(path)) != runner.file_hash(path) for path in mapping_paths):
        raise ValueError('Original private mapping is not bound to the audit.')
    by_origin = origins(saved['references'], [store._read(path) for path in mapping_paths])
    groups = {}
    for origin in ('recorded', 'generated'):
        refs = {key: row for key, row in saved['references'].items() if by_origin[key] == origin}
        groups[origin] = {'unique_inputs': len(refs),
            'unique_prefixes': len({row['prefix_sha256'] for row in refs.values()}), 'flags': {}}
        for flag in audit.FLAGS:
            # Reuse frozen confusion handling, but omit independence-based intervals.
            metric = audit._flag_report(refs, predictions, flag)
            groups[origin]['flags'][flag] = {key: metric[key] for key in
                ('human', 'eligible_binary', 'outcomes_on_eligible', 'confusion')}

    fixed = fidelity_comparison.load_comparison(source_paths[0].parent)
    cached = saved_comparison.load_comparison(source_paths[1].parent)
    if fixed['definitions'] != cached['definitions'] or cached['rubric_id'] != 'help-work-v1':
        raise ValueError('Historical definitions must remain identical.')

    def pair(case, message, flag):
        prefix = [{key: turn[key] for key in ('role', 'text')}
                  for turn in case['prefix']['context'] + case['prefix']['turns']]
        identity = store.digest({'prefix': prefix, 'candidate': message['text']})
        if identity not in predictions:
            raise ValueError('Exact message and complete prefix missing from the saved audit.')
        # Original per-study judgments remain unchanged even if another review conflicts.
        return message['review'][flag], predictions[identity]['labels'][flag]

    comparisons = []
    arms = [('September 15: ' + title, fixed['cases'], condition)
            for condition, title in fidelity_comparison.CONDITIONS]
    arms.append(('September 22: Cached replies', cached['cases'], None))
    for name, cases, condition in arms:
        flags = {}
        for flag in audit.FLAGS:
            rows = []
            for case in cases:
                draws = case['draws'] if condition is None else next(
                    arm['draws'] for arm in case['conditions'] if arm['id'] == condition)
                rows.append({'recorded': pair(case, case['reference'], flag),
                             'generated': [pair(case, draw, flag) for draw in draws]})
            flags[flag] = compare(rows)
        comparisons.append({'name': name, 'flags': flags})
    if any(runner.file_hash(path) != checksum for path, checksum in pins.items()):
        raise ValueError('Saved source evidence changed during analysis.')
    result = {'kind': 'retrospective-evaluator-source-disagreement', 'rubric_id': 'help-work-v1',
        'dispatch_plan_sha256': expected, 'unique_source_groups': groups, 'comparisons': comparisons,
        'source_and_code_sha256': pins,
        'limits': ['Disagreement with one saved reviewer is not known true classification error.',
            'Source groups count each exact input once; comparisons retain original draw occurrences and case weights.',
            'The help conflict is excluded only in unique-input agreement; historical studies retain their own judgments.',
            'Ranges resolve model unclear in either direction on fixed outputs; they are not confidence intervals.',
            'Three historical review sources inform the source split; gap diagnostics cover only the fixed and cached studies.',
            'No pooled cross-study gap, new-rubric labels, scorer adoption, population generalization or new calls.']}
    store._save(output, result, exclusive=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    result = execute(args.folder, args.plan_sha256, args.output)
    print('Verified source groups:', {k: v['unique_inputs'] for k, v in result['unique_source_groups'].items()})
    for comparison in result['comparisons']:
        print(comparison['name'], comparison['flags'])
