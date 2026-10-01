"""Offline reuse of sixteen recorded, human-reviewed messages; no model or database calls."""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

from src.eval import fidelity_comparison, saved_comparison
from src.labeling.episodes import _hash, _source_lines

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'episode-pilot/data/episode-pilot'
AUDIT = ROOT / 'data/behavioral-measurement-v1'
LINKAGE = ROOT / 'data/learner-linkage-recovery-v1'
DISPATCH_SHA = 'f3c651a3fa4a39a536515621e9b1838f0e2b5b83e9bbd12de66d0f2f8205fbbb'
LINKAGE_SUMMARY_SHA = '4df71eaf5834e3ec6ffd3bfde02e1b7a1cfd984b07b5d4b8f3446736b1ca5259'


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def module(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def collect():
    """Reconstruct text-free observations, retaining original human labels and account linkage."""
    pins = {}

    def check(path, expected=None):
        path = Path(path).resolve(strict=True)
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError('An original evidence or source binding changed.')
        if str(path) in pins and pins[str(path)] != actual:
            raise ValueError('Evidence changed during collection.')
        pins[str(path)] = actual
        return read(path) if path.suffix == '.json' else None

    dispatch = check(AUDIT / 'dispatch/plan.json', DISPATCH_SHA)
    # Hash legacy files without importing their runners, which can write on import.
    for path, expected in dispatch['legacy_verification']['files'].items():
        if digest(path) != expected:
            raise ValueError('Legacy evidence no longer matches the closed audit.')
        pins[path] = expected
    audit = module(ROOT / 'experiments/2026-09-30-help-work-measurement/audit.py')
    check(AUDIT / 'plan.json', dispatch['audit_plan_sha256'])
    saved = audit.load(AUDIT)
    for name in ('prompts.json', 'references.json', 'summary.json'):
        check(AUDIT / name)
    pins.update(saved['plan']['code_pins'])
    origin = module(ROOT / 'experiments/2026-09-30-evaluator-source-disagreement.py')
    source_paths = [Path(source['packet']['path']) for source in saved['plan']['sources']]
    mapping_paths = [p.with_name('private-mapping.json') for p in source_paths[:2]]
    mapping_paths.append(source_paths[2].parent.parent / 'private-review-mapping.json')
    mappings = [check(p, pins[str(p)]) for p in mapping_paths]
    origins = origin.origins(saved['references'], mappings)
    fidelity_comparison.load_comparison(source_paths[0].parent)
    saved_comparison.load_comparison(source_paths[1].parent)

    summary = check(LINKAGE / 'summary.json', LINKAGE_SUMMARY_SHA)
    for path, expected in summary['source_sha256'].items():
        check(path, expected)
    receipt = read(LINKAGE / 'linkage.json')
    if receipt['read_only'] is not True:
        raise ValueError('Expected the saved read-only account linkage.')
    for suffix, field in (('.sql', 'query_sha256'), ('-params.json', 'params_sha256')):
        path = LINKAGE / ('linkage' + suffix)
        if digest(path) != receipt[field]:
            raise ValueError('Account linkage query binding changed.')
    probe = BASE / 'notebook-context-v1/ingestion_probe.py'
    if digest(probe) != receipt['probe_sha256']:
        raise ValueError('Account linkage probe binding changed.')
    pins[str(probe)] = receipt['probe_sha256']
    split = check(LINKAGE / 'existing-split-linkage.json')
    legacy = read(BASE / 'historical-response-baseline-v1/inputs.json')
    old_receipt = read(BASE / 'historical-response-baseline-v1/receipt.json')
    if digest(BASE / 'historical-response-baseline-v1/inputs.json') != old_receipt['inputs.json']:
        raise ValueError('Historical input binding changed.')
    metadata = {_hash(r['conv_id'])[:16]: r for r in receipt['rows']}
    if len(metadata) != len(receipt['rows']):
        raise ValueError('Ambiguous conversation aliases.')
    # Only already-exposed historical-library rows are joined; no new target content.
    rebuilt = {name: [{'id': r['id'], 'conversation_id': r['conversation_id'],
                      'account_id': metadata[r['conversation_id']]['account_ids'][0]}
                     for r in legacy[name]] for name in ('train', 'queries')}
    if split != rebuilt:
        raise ValueError('Derived account linkage does not reproduce.')
    linked = {r['id']: r for rows in split.values() for r in rows}
    occurrence = {tuple(o[k] for k in ('source_index', 'packet_id', 'case_id', 'candidate_id')): identity
                  for identity, r in saved['references'].items() for o in r['occurrences']}
    observations = []
    for index, source in enumerate(('fixed', 'cached')):
        folder = source_paths[index].parent
        packet = check(source_paths[index], pins[str(source_paths[index])])
        episodes_path = BASE / ('help-work-benchmark-v1' if index == 0 else 'fixed-communication-eval-v1') / 'episodes.json'
        episodes = check(episodes_path, pins[str(episodes_path)])
        mapping = {c['id']: c for c in mappings[index]['cases']}
        if index == 0:
            by_case = {c['id']: ep for c, ep in zip(packet['cases'], episodes, strict=True)}
        else:
            plan_path = folder / 'blind-plan.json'
            plan = check(plan_path, pins[str(plan_path)])
            by_case = {c['id']: episodes[c['source_case'] - 1] for c in plan['cases']}
            records_path = BASE / 'fidelity-coding-readiness-v1/source-records.json'
            records = check(records_path, pins[str(records_path)])
            records = {c['id']: records[c['source_case'] - 1] for c in plan['cases']}
        for case in packet['cases']:
            episode, entry = by_case[case['id']], mapping[case['id']]
            identity = occurrence[index, packet['packet_id'], case['id'], entry['reference_id']]
            target = next(t for t in episode['turns'] if (t['role'], t['phase']) == ('student', 'followup'))
            candidate = next(c for c in case['candidates'] if c['id'] == entry['reference_id'])
            if candidate['text'] != target['text'] or origins[identity] != 'recorded':
                raise ValueError('Reference must be the first recorded student follow-up.')
            if index == 1:
                record = records[case['id']]
                prefix = {g: [{'role': t['role'], 'lines': [l for l in _source_lines(t['text']) if l['text'].strip()]}
                              for t in case['prefix'][g]] for g in ('context', 'turns')}
                expected = {g: [{'role': t['role'], 'lines': t['lines']} for t in record['prefix'][g]]
                            for g in ('context', 'turns')}
                if (record['episode_id'] != episode['id'] or record['reference_turn_id'] != target['id']
                        or record['recorded_message'] != target['text'] or prefix != expected):
                    raise ValueError('Cached packet no longer matches its recorded episode.')
            account = linked[episode['id']]
            meta = metadata[episode['conversation_key']]
            if (account['conversation_id'] != episode['conversation_key'] or not meta['locally_exposed']
                    or meta['missing_identity_events'] or meta['account_ids'] != [account['account_id']]):
                raise ValueError('Expected unambiguous previously exposed account linkage.')
            observations.append({'id': identity, 'conversation_id': episode['conversation_key'],
                'account_id': account['account_id'], 'source': source, 'origin': 'recorded',
                'label_origin': 'human', 'rubric_id': packet['rubric_id'], **saved['references'][identity]['human']})
    if len(observations) != 16 or {o['id'] for o in observations} != {k for k, v in origins.items() if v == 'recorded'}:
        raise ValueError('Keep exactly the sixteen distinct human-reviewed recorded messages.')
    for path in (Path(__file__), Path(audit.__file__), Path(origin.__file__),
                 Path(fidelity_comparison.__file__), Path(saved_comparison.__file__),
                 ROOT / 'src/labeling/episodes.py'):
        pins[str(path)] = digest(path)
    if any(digest(path) != expected for path, expected in pins.items()):
        raise ValueError('Source evidence changed during collection.')
    return {'observations': sorted(observations, key=lambda r: r['id']), 'provenance': {
        'source_sha256': pins, 'source_validation': 'Original packet/review bindings, recorded first follow-ups, canonical audit IDs and read-only account linkage reverified.',
        'limits': ['Single-reviewer development judgments; unknown annotation error.',
                   'Course accounts are not verified persons. No new labels or data collected.']}}


def encoded(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'


def report(inputs):
    from src.eval import behavior_scoring, empirical_work_policy
    paths = [Path(__file__), Path(empirical_work_policy.__file__), Path(behavior_scoring.__file__),
             ROOT / 'docs/2026-10-01-real-policy-calibration.md']
    return {'input_sha256': sha256(encoded(inputs).encode()).hexdigest(),
        'code_and_protocol_sha256': {str(p): digest(p) for p in paths},
        'observation_schema': empirical_work_policy.Observation.model_json_schema(),
        'result': empirical_work_policy.evaluate(inputs['observations'])}


def markdown(saved):
    result = saved['result']
    counts, fit = result['counts'], result['fitted']
    lines = ['# Recorded-message frequency diagnostic', '',
        '**Retrospective development evidence; no LLM calls or new labels.**', '', result['scope'], '',
        f"{counts['observations']} recorded messages; {counts['linked_accounts']} linked course accounts; "
        f"{counts['eligible_messages']} eligible and {counts['excluded_messages']} excluded messages.", '',
        f"Fitted account-weighted work-presence rate: **{fit['p_work_present']:.1%}** ({fit['fraction']}). "
        'This describes the selected mixture; it is not a population estimate or a calibration guarantee.', '',
        '| Source | Messages | Accounts | Work yes | Work no | Fitted rate |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name, source in result['sources'].items():
        fitted = source['fitted']; c = fitted['counts']
        lines.append(f"| {name} | {c['input_messages']} | {c['accounts']} | {c['work_yes']} | "
                     f"{c['work_no']} | {fitted['p_work_present']:.1%} |")
    lines += ['', '## Predictions with the entire target account excluded', '', result['metric'], '',
              '| Scored group | Messages | Accounts | Frequency | Constant 50/50 | Always no |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']

    def row(name, summary):
        errors = summary['account_mean_brier']
        values = ['unavailable' if errors[k] is None else f'{errors[k]:.6f}'
                  for k in ('frequency', 'constant_half', 'always_no')]
        return f"| {name} | {summary['scored_messages']} | {summary['scored_accounts']} | " + ' | '.join(values) + ' |'

    held = result['leave_account_out']
    lines.append(row('All', held['summary']))
    lines.extend(row(name, summary) for name, summary in held['by_source'].items())
    lines.extend(row('Work ' + name, summary) for name, summary in held['by_class'].items())
    lines += ['', '## Source-group sensitivity', '',
        'Hold out one original source and remove its accounts from the training source.', '',
        '| Held source | Training accounts | Training work yes / no | Predicted work rate | Frequency Brier |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name, check in result['leave_source_out'].items():
        train, score = check['fit'], check['summary']['account_mean_brier']['frequency']
        c = train['counts']; p = train['p_work_present']
        probability = 'unavailable' if p is None else f'{p:.1%}'
        error = 'unavailable' if score is None else f'{score:.6f}'
        lines.append(f"| {name} | {c['accounts']} | {c['work_yes']} / {c['work_no']} | {probability} | {error} |")
    lines += ['', '## Limits', '', *('- ' + limitation for limitation in result['limits']), '',
        'The saved JSON retains exact account weights, fold exclusions and source hashes. '
        'No simulator default or authored-policy admission rule changed.', '']
    return '\n'.join(lines)


def run(folder):
    folder = Path(folder)
    if folder.exists():
        raise FileExistsError('Choose a new output directory; existing results are immutable.')
    inputs = collect()
    saved = report(inputs)
    rendered = markdown(saved)
    folder.mkdir(parents=True, exist_ok=False)
    for name, text in (('inputs.json', encoded(inputs)), ('report.json', encoded(saved)), ('report.md', rendered)):
        with (folder / name).open('x', encoding='utf-8') as target:
            target.write(text)
    return saved


def verify(folder):
    folder = Path(folder)
    inputs = collect()
    saved = report(inputs)
    for name, expected in (('inputs.json', encoded(inputs)), ('report.json', encoded(saved)),
                           ('report.md', markdown(saved))):
        if (folder / name).read_text(encoding='utf-8') != expected:
            raise ValueError('Saved inputs, source bindings, calculation or report changed.')
    return saved


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify'))
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    saved = (run if args.command == 'run' else verify)(args.folder)
    print(encoded({'status': args.command + '-complete', 'counts': saved['result']['counts'],
                   'account_holdout': saved['result']['leave_account_out']['summary']}))
