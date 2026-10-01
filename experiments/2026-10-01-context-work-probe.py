"""One frozen, offline context comparison over existing human work-presence judgments."""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import importlib.util
from pathlib import Path
import re

from src.agents.notebook_student import digest as value_digest
from src.eval import empirical_work_policy as baseline
from src.eval.behavior_scoring import _brier
from src.eval.retrieval_baseline import Turn

ROOT = Path(__file__).resolve().parents[1]
CODE_CUE = re.compile(r'(?m)^\s*(?:def\s+|for\s+|[A-Za-z_]\w*\s*=(?!=))')
spec = importlib.util.spec_from_file_location('calibration', ROOT / 'experiments/2026-10-01-real-policy-calibration.py')
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


def feature(prefix):
    students = [turn.text for raw in prefix if (turn := Turn.model_validate(raw)).role == 'student']
    # ponytail: reuse a literal historical cue; prose can match and many code forms are missed.
    return any(CODE_CUE.search(text) for text in students) if students else None


def forecast(rows, features, target):
    rows = [baseline.Observation.model_validate(r) for r in rows]
    fit = baseline._fit(rows)
    eligible = [r for r in rows if baseline._reason(r) is None]
    counts = Counter(r.account_id for r in eligible)
    members = [r for r in eligible if target is not None and features[r.id] == target]
    mass = sum((Fraction(1, counts[r.account_id]) for r in members), Fraction())
    positive = sum((Fraction(1, counts[r.account_id]) for r in members if r.work_present == 'yes'), Fraction())
    global_rate = Fraction(fit['fraction']) if fit['fraction'] is not None else None
    p = (positive + global_rate) / (mass + 1) if global_rate is not None else None
    reason = ('insufficient-training-accounts' if p is None else 'unknown-feature' if target is None
              else 'empty-bucket' if not members else None)
    return {'p': float(p) if p is not None else None, 'fraction': str(p) if p is not None else None,
            'global_fraction': fit['fraction'], 'cue': target, 'reason': reason,
            'bucket_mass': str(mass), 'positive_mass': str(positive),
            'matching_accounts': len({r.account_id for r in members}),
            'training_ids': sorted(r.id for r in eligible),
            'training_weights': {r.id: str(Fraction(1, counts[r.account_id])) for r in eligible},
            'matching_ids': sorted(r.id for r in members)}


def summary(predictions):
    result = baseline._summary(predictions)
    contextual = [r | {'brier': r['brier'] | {'frequency': r['brier']['context']}} for r in predictions]
    result['account_mean_brier']['context'] = baseline._summary(contextual)['account_mean_brier']['frequency']
    result['context_fallbacks'] = dict(Counter(r['context']['reason'] for r in predictions if r['context']['reason']))
    return result


def evaluate(rows, features):
    result = baseline.evaluate(rows)
    if set(features) != {r['id'] for r in rows} or any(v is not None and type(v) is not bool for v in features.values()):
        raise ValueError('Supply exactly one boolean or unknown prefix feature per observation.')

    def enrich(fold):
        training_ids = {identity for a in fold['fit']['accounts'] for identity in a['observation_ids']}
        train = [r for r in rows if r['id'] in training_ids]
        for row in fold['predictions']:
            row['context'] = forecast(train, features, features[row['id']])
            p = row['context']['p']
            row['brier']['context'] = _brier({'yes': p, 'no': 1-p}, row['work_present']) if row['scored'] else None
        fold['summary'] = summary(fold['predictions'])

    held = result['leave_account_out']
    for fold in held['folds']:
        enrich(fold)
    for fold in result['leave_source_out'].values():
        enrich(fold)
    predictions = [r for fold in held['folds'] for r in fold['predictions']]
    # Keep unlinked observations in coverage, exactly as the baseline does.
    unlinked = baseline._predict(baseline._fit([]), [baseline.Observation.model_validate(r) for r in rows if r['account_id'] is None])
    for row in unlinked:
        row['context'] = forecast([], features, features[row['id']])
        row['brier']['context'] = None
    predictions += unlinked
    held['summary'] = summary(predictions)
    held['by_class'] = {label: summary([r for r in predictions if r['work_present'] == label]) for label in ('yes', 'no')}
    held['by_source'] = {source: summary([r for r in predictions if r['source'] == source]) for source in result['sources']}
    changes = [f['summary']['account_mean_brier'] for f in held['folds'] if f['summary']['scored_accounts']]
    held['account_comparison'] = dict(Counter('tie' if abs(s['context']-s['frequency']) < 1e-12 else
            'better' if s['context'] < s['frequency'] else 'worse' for s in changes))
    result['kind'] = 'retrospective-single-cue-work-presence-probe'
    result['weighting'] = 'Equal training account mass, divided among its eligible messages before conditioning; context uses one-account-equivalent shrinkage. Scores average within account, then across accounts.'
    result['feature_support'] = {str(value): {'messages': len(selected),
        'accounts': len({r['account_id'] for r in selected if r['account_id'] is not None})}
        for value in (True, False, None) for selected in [[r for r in rows if features[r['id']] is value]]}
    result['limits'] += ['One previously used lexical cue, not semantic work labels; alpha fixed at one account-equivalent.',
                        'Exposed development comparison; no feature search, deployment or claim of calibrated probabilities.']
    return result


def collect():
    calibration.verify(ROOT / 'data/real-policy-calibration-v2')
    inputs = calibration.read(ROOT / 'data/real-policy-calibration-v2/inputs.json')
    pins = inputs['provenance']['source_sha256']
    audit = calibration.module(ROOT / 'experiments/2026-09-30-help-work-measurement/audit.py')
    saved = audit.load(calibration.AUDIT)
    selected = {r['id'] for r in inputs['observations']}
    prefixes = {identity: payload['prefix'] for identity, payload in zip(saved['plan']['ids'], saved['prompts'], strict=True) if identity in selected}
    if prefixes.keys() != selected or any(value_digest(prefix) != saved['references'][identity]['prefix_sha256']
                                         for identity, prefix in prefixes.items()):
        raise ValueError('Every selected prefix must match its original canonical audit binding.')
    if any(not prefix or prefix[-1]['role'] != 'tutor' or not any(t['role'] == 'student' for t in prefix) for prefix in prefixes.values()):
        raise ValueError('Expected a student contribution followed by the visible tutor response.')
    cue_source = calibration.BASE / 'student-continuation-check-v1/run.py'
    if "CODE_CUE = re.compile(r'" + CODE_CUE.pattern + "')" not in cue_source.read_text():
        raise ValueError('The reused historical cue changed.')
    pins[str(cue_source)] = calibration.digest(cue_source)
    inputs['features'] = {key: feature(prefix) for key, prefix in prefixes.items()}
    inputs['prefix_sha256'] = {key: value_digest(prefix) for key, prefix in prefixes.items()}
    return inputs


def report(inputs):
    paths = [Path(__file__), Path(baseline.__file__), Path(calibration.__file__),
             ROOT / 'src/eval/behavior_scoring.py', ROOT / 'src/eval/retrieval_baseline.py',
             ROOT / 'src/agents/notebook_student.py', ROOT / 'docs/2026-10-01-context-work-probe.md']
    return {'input_sha256': sha256(calibration.encoded(inputs).encode()).hexdigest(),
            'code_and_protocol_sha256': {str(p): calibration.digest(p) for p in paths},
            'result': evaluate(inputs['observations'], inputs['features'])}


def run(folder, verify=False):
    folder = Path(folder)
    if not verify and folder.exists():
        raise FileExistsError('Choose a new output directory; existing evidence is immutable.')
    inputs = collect()
    saved = report(inputs)
    files = {'inputs.json': calibration.encoded(inputs), 'report.json': calibration.encoded(saved)}
    if verify:
        if any((folder / name).read_text() != text for name, text in files.items()):
            raise ValueError('Saved inputs, features, calculation or source bindings changed.')
    else:
        folder.mkdir(parents=True, exist_ok=False)
        for name, text in files.items():
            with (folder / name).open('x', encoding='utf-8') as stream:
                stream.write(text)
    return saved


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify'))
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    result = run(args.folder, args.command == 'verify')['result']
    print(calibration.encoded({'status': args.command + '-complete', 'counts': result['counts'],
        'feature_support': result['feature_support'], 'account_holdout': result['leave_account_out']['summary'],
        'account_comparison': result['leave_account_out']['account_comparison']}))
