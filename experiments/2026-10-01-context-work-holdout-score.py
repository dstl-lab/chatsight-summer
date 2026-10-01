"""Close the frozen held-out-account work-presence test without refitting or relabeling."""
import argparse
from collections import Counter
import importlib.util
import math
from pathlib import Path
from statistics import mean

from src.eval.behavior_scoring import _brier
from src.eval.communication_review import _keys, _text, validate_packet

METHODS = ('context', 'frequency', 'constant_half', 'always_no')


def aggregate(rows):
    paired = [r for r in rows if r['brier'] is not None]
    changes = [r['delta'] for r in paired]
    return {'cases': len(rows), 'scored': len(paired),
        'mean_brier': {name: mean(r['brier'][name] for r in paired) if paired else None for name in METHODS},
        'context_minus_frequency': mean(changes) if changes else None,
        'account_comparison': {'better': sum(d < -1e-12 for d in changes),
                              'tie': sum(abs(d) <= 1e-12 for d in changes),
                              'worse': sum(d > 1e-12 for d in changes)}}


def evaluate(predictions, form, packet_id):
    _keys(form, 'packet_id rubric_id reviewer previously_seen_cases judgments')
    if form['packet_id'] != packet_id or form['rubric_id'] != 'help-work-v1':
        raise ValueError('Review belongs to a different packet or rubric.')
    _text(form['reviewer'])
    if form['previously_seen_cases'] not in ('yes', 'no', 'unsure') or not isinstance(form['judgments'], list):
        raise ValueError('Expected reviewer exposure and a judgment list.')
    if not isinstance(predictions, list) or not predictions:
        raise ValueError('Expected frozen predictions.')
    ids = []
    for p in predictions:
        _keys(p, 'id cue p baselines'); _text(p['id'])
        _keys(p['baselines'], 'frequency constant_half always_no')
        if p['cue'] is not None and type(p['cue']) is not bool:
            raise ValueError('Cue must be boolean or unknown.')
        for value in list(p['baselines'].values()) + ([] if p['p'] is None else [p['p']]):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Expected finite probabilities in [0,1].')
        ids.append(p['id'] + '-message')
    judgments = {}
    for j in form['judgments']:
        _keys(j, 'id work_present note'); _text(j['id'])
        if j['id'] in judgments or j['work_present'] not in ('yes', 'no', 'unclear', None):
            raise ValueError('Repeated or invalid judgment.')
        if j['note'] is not None:
            _text(j['note'], empty=True)
        if j['work_present'] == 'unclear':
            _text(j['note'])
        judgments[j['id']] = j
    if len(set(ids)) != len(ids) or set(ids) != set(judgments):
        raise ValueError('Exactly one judgment, including unresolved entries, is needed per frozen case.')
    rows = []
    for p in sorted(predictions, key=lambda p: p['id']):
        j = judgments[p['id'] + '-message']
        known = j['work_present'] in ('yes', 'no')
        probabilities = {'context': p['p'], **p['baselines']}
        errors = {k: _brier({'yes': v, 'no': 1-v}, j['work_present']) for k, v in probabilities.items()} if known and p['p'] is not None else None
        delta = errors['context'] - errors['frequency'] if errors is not None else None
        if p['p'] is None:
            bounds = [-2., 2.]
        elif known:
            bounds = [delta, delta]
        else:
            possibilities = [_brier({'yes': p['p'], 'no': 1-p['p']}, label) -
                _brier({'yes': p['baselines']['frequency'], 'no': 1-p['baselines']['frequency']}, label) for label in ('no', 'yes')]
            bounds = [min(possibilities), max(possibilities)]
        rows.append({'id': p['id'], 'cue': p['cue'], 'work_present': j['work_present'],
                     'probabilities': probabilities, 'brier': errors, 'delta': delta, 'delta_bounds': bounds})
    counts = Counter(j['work_present'] for j in judgments.values())
    return {'metric': 'Summed two-class Brier = 2*(p-y)^2; lower is better, range 0–2.',
        'primary': 'Paired mean context-minus-frequency error; negative favors context.',
        'coverage': {'selected': len(rows), 'returned_judgments': len(judgments),
            'yes': counts['yes'], 'no': counts['no'], 'unclear': counts['unclear'], 'missing_labels': counts[None],
            'missing_predictions': sum(p['p'] is None for p in predictions),
            'binary_scored': sum(r['brier'] is not None for r in rows)},
        'paired': aggregate(rows),
        'full_set_delta_bounds': {'lower': mean(r['delta_bounds'][0] for r in rows),
                                 'upper': mean(r['delta_bounds'][1] for r in rows)},
        'by_class': {label: aggregate([r for r in rows if r['work_present'] == label]) for label in ('yes', 'no', 'unclear')},
        'by_cue': {str(cue): {'labels': dict(Counter(r['work_present'] or 'missing' for r in rows if r['cue'] is cue)),
            **aggregate([r for r in rows if r['cue'] is cue])} for cue in (True, False, None)},
        'rows': rows,
        'limits': ['Single-reviewer, held-out-account test; not independent-rater reliability.',
            'Bounds concern unresolved outcomes only, not annotation error or sampling uncertainty.',
            'Limited context use was reported by the reviewer; no labels were changed.',
            'No training update, translation/adjudication, parameter selection or automatic adoption.']}


def report():
    path = Path(__file__).with_name('2026-10-01-context-work-holdout.py')
    spec = importlib.util.spec_from_file_location('holdout', path)
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    folder = h.OUT
    preparation = h.read(folder / 'preparation.json')
    h.helpers.checked_pins(preparation['source_sha256'])
    predictions = h.read(folder / 'predictions.json')
    if {k: v for k, v in predictions.items() if k != 'sealed_at_utc'} != h.predictions():
        raise ValueError('Frozen prediction inputs or values changed.')
    launch, targets = h.read(folder / 'targets-dispatch.json'), h.read(folder / 'targets.json')
    if not h.stamp(predictions['sealed_at_utc']) < h.stamp(launch['started_at_utc']) <= h.stamp(targets['queried_at_utc']):
        raise ValueError('Targets were not retrieved after prediction sealing.')
    packet, form = h.read(folder / 'review-packet.json'), h.read(folder / 'received/review.json')
    validate_packet(packet)
    body = {k: v for k, v in packet.items() if k != 'packet_id'}
    if packet['packet_id'] != 'packet_' + h.probe.value_digest(body):
        raise ValueError('Blind packet binding changed.')
    cases = predictions['cases']
    if len(cases) != 24 or len({c['account_id'] for c in cases}) != 24 or len(packet['cases']) != 24:
        raise ValueError('Keep all twenty-four distinct selected accounts.')
    if {c['id'] for c in cases} != {c['id'] for c in packet['cases']}:
        raise ValueError('Review cases differ from the selected accounts.')
    target_rows = h.receipt('targets', h.TEXT_SQL)
    if sorted(r['id'] for r in target_rows) != sorted(c['target_event_id'] for c in cases):
        raise ValueError('Target event membership changed.')
    for c in cases:
        shown = next(item for item in packet['cases'] if item['id'] == c['id'])
        target = next(r for r in target_rows if r['id'] == c['target_event_id'])
        if (shown['candidates'] != [{'id': c['id'] + '-message', 'text': target['text']}]
                or [{k: t[k] for k in ('role', 'text')} for group in ('context', 'turns') for t in shown['prefix'][group]] != c['prefix']):
            raise ValueError('Reviewed text differs from the selected prefix/target.')
    inputs = [{k: c[k] for k in ('id', 'cue', 'p', 'baselines')} for c in cases]
    files = [Path(__file__), path, h.ROOT / 'src/eval/behavior_scoring.py',
             h.ROOT / 'src/eval/communication_review.py', h.ROOT / 'docs/2026-10-01-context-work-holdout.md',
             *[folder / n for n in ('preparation.json', 'predictions.json', 'review-packet.json',
                                   'received/review.json', 'received/context.json')]]
    return {'status': 'closed-single-review-pass', 'rubric_id': packet['rubric_id'],
            'reviewer': form['reviewer'], 'previously_seen_cases': form['previously_seen_cases'],
            'review_context': h.read(folder / 'received/context.json'),
            'source_sha256': h.helpers.pins(files), 'result': evaluate(inputs, form, packet['packet_id'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify'))
    args = parser.parse_args()
    import json
    output = Path(__file__).resolve().parents[1] / 'data/context-work-holdout-v1/scored-report.json'
    if args.command == 'run' and output.exists():
        raise FileExistsError('Preserve the completed test report.')
    saved = report()
    encoded = json.dumps(saved, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'
    if args.command == 'verify':
        if output.read_text() != encoded:
            raise ValueError('Saved report no longer reproduces.')
    else:
        with output.open('x', encoding='utf-8') as stream:
            stream.write(encoded)
    print(json.dumps({k: saved['result'][k] for k in ('coverage', 'paired', 'full_set_delta_bounds')}, indent=2))
