"""Score one complete blind help/work review against its private draw mapping."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

from src.eval.communication_review import _keys, _text, validate_packet


FLAGS = ('help_request', 'work_present')
CONDITIONS = ('grounded', 'current-exchange')


def score(packet, mapping, judgments):
    validate_packet(packet)
    _keys(mapping, 'packet_id cases')
    if mapping['packet_id'] != packet['packet_id']:
        raise ValueError('Mapping belongs to a different packet.')
    if (len(packet['cases']) != 8 or not isinstance(mapping['cases'], list)
            or len(mapping['cases']) != 8):
        raise ValueError('The fixed comparison requires exactly eight cases.')
    candidates = {c['id'] for case in packet['cases'] for c in case['candidates']}
    _keys(judgments, 'packet_id rubric_id reviewer previously_seen_cases judgments')
    if any(judgments[key] != packet[key] for key in ('packet_id', 'rubric_id')):
        raise ValueError('Judgments belong to a different packet or rubric.')
    _text(judgments['reviewer'])
    if judgments['previously_seen_cases'] not in ('yes', 'no', 'unsure'):
        raise ValueError('Reviewer prior exposure must be explicit.')
    if not isinstance(judgments['judgments'], list):
        raise ValueError('Expected a list of human judgments.')
    reviewed = {}
    for judgment in judgments['judgments']:
        _keys(judgment, 'id help_request work_present note')
        _text(judgment['id'])
        if judgment['id'] in reviewed or judgment['id'] not in candidates:
            raise ValueError('Judgments must identify each packet candidate exactly once.')
        if any(judgment[flag] not in ('yes', 'no', 'unclear') for flag in FLAGS):
            raise ValueError('Every human flag must be completed; null is unfinished.')
        if judgment['note'] is not None:
            _text(judgment['note'], empty=True)
        if any(judgment[flag] == 'unclear' for flag in FLAGS):
            _text(judgment['note'])
        reviewed[judgment['id']] = dict(judgment)
    if reviewed.keys() != candidates:
        raise ValueError('All packet candidates need completed human judgments.')

    mapped, used = {}, set()
    for case in mapping['cases']:
        _keys(case, 'id reference_id draws')
        _text(case['id'])
        _text(case['reference_id'])
        if case['id'] in mapped or case['reference_id'] in used:
            raise ValueError('Mapping case and message IDs must be unique.')
        used.add(case['reference_id'])
        if not isinstance(case['draws'], list) or len(case['draws']) != 8:
            raise ValueError('Every case requires eight scheduled draws.')
        slots = set()
        for draw in case['draws']:
            _keys(draw, 'id condition draw status')
            _text(draw['id'])
            if draw['id'] in used:
                raise ValueError('Mapping message IDs must be globally unique.')
            used.add(draw['id'])
            if (draw['condition'] not in CONDITIONS or type(draw['draw']) is not int
                    or draw['draw'] not in range(1, 5)
                    or draw['status'] not in ('reply', 'no-reply', 'error')):
                raise ValueError('Invalid condition, draw number or disposition.')
            slots.add((draw['condition'], draw['draw']))
        if len(slots) != 8:
            raise ValueError('Every condition needs exactly draws one through four.')
        mapped[case['id']] = case
    if mapped.keys() != {case['id'] for case in packet['cases']}:
        raise ValueError('Mapping must identify exactly the packet cases.')

    rows, dispositions = [], {condition: Counter() for condition in CONDITIONS}
    for case in packet['cases']:
        entry = mapped[case['id']]
        expected = {entry['reference_id']} | {d['id'] for d in entry['draws'] if d['status'] == 'reply'}
        if expected != {c['id'] for c in case['candidates']}:
            raise ValueError('Reference and reply draws must match the exact case candidates.')
        reference = reviewed[entry['reference_id']]
        reasons = [f"Reference {flag} is unclear." for flag in FLAGS if reference[flag] == 'unclear']
        draws = []
        for draw in entry['draws']:
            dispositions[draw['condition']][draw['status']] += 1
            judgment = reviewed[draw['id']] if draw['status'] == 'reply' else None
            draws.append({**draw, 'judgment': judgment})
            if judgment is None:
                reasons.append(f"Draw {draw['id']}: {draw['status']}.")
            else:
                reasons.extend(f"Draw {draw['id']}: {flag} is unclear."
                               for flag in FLAGS if judgment[flag] == 'unclear')
        scores = None
        if not reasons:
            scores = {}
            for condition in CONDITIONS:
                condition_draws = [d['judgment'] for d in draws if d['condition'] == condition]
                scores[condition] = {flag: (sum(j[flag] == 'yes' for j in condition_draws) / 4
                                           - int(reference[flag] == 'yes')) ** 2 for flag in FLAGS}
                scores[condition]['mean_brier'] = mean(scores[condition].values())
            scores['grounded_minus_current_exchange'] = (scores['grounded']['mean_brier']
                                                         - scores['current-exchange']['mean_brier'])
        rows.append({'id': case['id'], 'reference_id': entry['reference_id'],
                     'reference_judgment': reference, 'draws': draws,
                     'exclusion_reasons': reasons, 'scores': scores})
    complete = [row['scores'] for row in rows if row['scores'] is not None]
    paired = {'cases': len(complete), **{condition: {
        flag: mean(s[condition][flag] for s in complete) if complete else None
        for flag in (*FLAGS, 'mean_brier')} for condition in CONDITIONS},
        'grounded_minus_current_exchange': mean(s['grounded_minus_current_exchange'] for s in complete)
                                          if complete else None}
    return {
        'packet_id': packet['packet_id'], 'rubric_id': packet['rubric_id'],
        'reviewer': judgments['reviewer'], 'previously_seen_cases': judgments['previously_seen_cases'],
        'scope': 'One fixed next-recorded-message communication comparison; single human coding pass.',
        'metric': 'Mean of two binary Brier scores (p - recorded_yes)^2, with p from four draws; range 0–1. '
                  'Negative grounded-minus-current-exchange means lower error on the complete cases.',
        'counts': {'cases': 8, 'scheduled_draws': 64, 'reviewed_messages': len(reviewed),
                   'unclear_messages': sum(any(j[f] == 'unclear' for f in FLAGS) for j in reviewed.values()),
                   'unclear_flags': sum(j[f] == 'unclear' for j in reviewed.values() for f in FLAGS),
                   'missing_judgments': 0, 'complete_cases': len(complete), 'excluded_cases': 8 - len(complete)},
        'dispositions': {c: {s: dispositions[c][s] for s in ('reply', 'no-reply', 'error')} for c in CONDITIONS},
        'paired': paired, 'cases': rows,
        'limits': [
            'Only cases with both known reference flags and eight replies with both known flags are scored. '
            'No-reply, errors and unclear labels remain excluded and counted; selection can bias this subset.',
            'Four-draw frequencies are coarse finite-ensemble estimates; equal budgets do not remove sampling noise.',
            'Cases receive equal weight; repeated draws are not independent students. No confidence interval or significance claim.',
            'One reviewer does not establish coding reliability; prior-exposure status is self-reported.',
            'Flag matching does not establish contextual appropriateness, student fidelity, notebook actions, reply probability or learning.',
            'This fixed report selects no winner and triggers no tuning, replacement draws or further batch.'
        ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packet', 'mapping', 'judgments', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raw = {key: getattr(args, key).read_bytes() for key in ('packet', 'mapping', 'judgments')}
    report = score(*(json.loads(value) for value in raw.values()))
    report['provenance'] = {key + '_sha256': sha256(value).hexdigest() for key, value in raw.items()}
    report['provenance']['source_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with args.output.open('x', encoding='utf-8') as output:
        output.write(encoded)
    print(args.output)


if __name__ == '__main__':
    main()
