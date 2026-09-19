"""Describe one saved reply per condition against a blind help/work review."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from src.eval.communication_review import _keys, _text, validate_packet


FLAGS = ('help_request', 'work_present')
CONDITIONS = ('original', 'candidate')
CATEGORIES = ('neither', 'help-only', 'work-only', 'both')


def _flag_scores(rows, condition, flag):
    pairs = [(row['reference'][flag] == 'yes',
              row['conditions'][condition]['judgment'][flag] == 'yes') for row in rows]
    table = {'both_yes': sum(reference and generated for reference, generated in pairs),
             'neither_yes': sum(not reference and not generated for reference, generated in pairs),
             'generated_only': sum(not reference and generated for reference, generated in pairs),
             'reference_only': sum(reference and not generated for reference, generated in pairs)}
    n = len(rows)
    reference_yes = table['both_yes'] + table['reference_only']
    generated_yes = table['both_yes'] + table['generated_only']
    difference = generated_yes - reference_yes
    disagreements = table['generated_only'] + table['reference_only']
    return {'cases': n, 'case_ids': [row['id'] for row in rows], 'table': table,
            'reference_yes': reference_yes, 'generated_yes': generated_yes,
            'reference_incidence': reference_yes / n if n else None,
            'generated_incidence': generated_yes / n if n else None,
            'count_difference': difference, 'incidence_gap': difference / n if n else None,
            'incidence_gap_pp': 100 * difference / n if n else None,
            'disagreements': disagreements, 'disagreement_fraction': disagreements / n if n else None}


def _category(judgment):
    if judgment is None or any(judgment[flag] == 'unclear' for flag in FLAGS):
        return None
    return CATEGORIES[int(judgment['help_request'] == 'yes') + 2 * int(judgment['work_present'] == 'yes')]


def _joint_scores(rows, conditions):
    selected = []
    for row in rows:
        categories = {'reference': _category(row['reference']), **{
            condition: _category(row['conditions'][condition]['judgment']) for condition in conditions}}
        if all(category is not None for category in categories.values()):
            selected.append((row['id'], categories))
    n = len(selected)
    counts = {role: {category: sum(values[role] == category for _, values in selected)
                     for category in CATEGORIES} for role in ('reference', *conditions)}
    disagreement = {}
    for condition in conditions:
        count = sum(values[condition] != values['reference'] for _, values in selected)
        disagreement[condition] = {'count': count, 'fraction': count / n if n else None}
    result = {'cases': n, 'case_ids': [identity for identity, _ in selected],
              'counts': counts if conditions else counts['reference'], 'disagreement': disagreement}
    if conditions == CONDITIONS:
        difference = disagreement['candidate']['count'] - disagreement['original']['count']
        result.update(candidate_minus_original_disagreement=difference / n if n else None,
                      candidate_minus_original_disagreement_pp=100 * difference / n if n else None)
    return result


def score(packet, mapping, judgments):
    validate_packet(packet)
    _keys(mapping, 'packet_id cases')
    if mapping['packet_id'] != packet['packet_id']:
        raise ValueError('Mapping belongs to a different packet.')
    if not isinstance(mapping['cases'], list):
        raise ValueError('Expected a list of mapped cases.')
    candidates = {candidate['id'] for case in packet['cases'] for candidate in case['candidates']}
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
        _keys(case, 'id reference_id conditions')
        _keys(case['conditions'], 'original candidate')
        for slot in case['conditions'].values():
            _keys(slot, 'id status')
            if slot['status'] not in ('reply', 'no-reply', 'error'):
                raise ValueError('Output disposition must be reply, no-reply or error.')
        for identity in (case['id'], case['reference_id'], *(slot['id'] for slot in case['conditions'].values())):
            _text(identity)
            if identity in used:
                raise ValueError('Mapping case and message IDs must be globally unique.')
            used.add(identity)
        mapped[case['id']] = case
    if mapped.keys() != {case['id'] for case in packet['cases']}:
        raise ValueError('Mapping must identify exactly the packet cases.')

    rows = []
    for case in packet['cases']:
        entry = mapped[case['id']]
        expected = {entry['reference_id']} | {
            slot['id'] for slot in entry['conditions'].values() if slot['status'] == 'reply'}
        if expected != {candidate['id'] for candidate in case['candidates']}:
            raise ValueError('Reference and reply slots must match the exact case candidates.')
        reference = reviewed[entry['reference_id']]
        conditions = {condition: {**slot, 'judgment': reviewed[slot['id']] if slot['status'] == 'reply' else None}
                      for condition, slot in entry['conditions'].items()}
        exclusions = {}
        for comparison, included in (('original', ('original',)), ('paired', CONDITIONS)):
            reasons = {}
            for flag in FLAGS:
                reasons[flag] = [f'Reference {flag} is unclear.'] if reference[flag] == 'unclear' else []
                for condition in included:
                    slot = conditions[condition]
                    if slot['status'] != 'reply':
                        reasons[flag].append(f'{condition}: {slot["status"]}.')
                    elif slot['judgment'][flag] == 'unclear':
                        reasons[flag].append(f'{condition} {flag} is unclear.')
            reasons['joint'] = list(dict.fromkeys(reason for flag in FLAGS for reason in reasons[flag]))
            exclusions[comparison] = reasons
        rows.append({'id': case['id'], 'reference': reference, 'conditions': conditions, 'exclusions': exclusions})

    original, paired = {}, {}
    for flag in FLAGS:
        original[flag] = _flag_scores([row for row in rows if not row['exclusions']['original'][flag]], 'original', flag)
        selected = [row for row in rows if not row['exclusions']['paired'][flag]]
        comparisons = {condition: _flag_scores(selected, condition, flag) for condition in CONDITIONS}
        difference = comparisons['candidate']['disagreements'] - comparisons['original']['disagreements']
        n = len(selected)
        paired[flag] = {'cases': n, 'case_ids': [row['id'] for row in selected], **comparisons,
                        'candidate_minus_original_disagreement': difference / n if n else None,
                        'candidate_minus_original_disagreement_pp': 100 * difference / n if n else None}
    coverage = {}
    for role in ('reference', *CONDITIONS):
        coverage[role] = {}
        for flag in FLAGS:
            states = Counter(row['reference'][flag] if role == 'reference' else
                             row['conditions'][role]['judgment'][flag] if row['conditions'][role]['status'] == 'reply'
                             else row['conditions'][role]['status'] for row in rows)
            coverage[role][flag] = {state: states[state] for state in ('yes', 'no', 'unclear', 'missing', 'no-reply', 'error')}
    return {
        'packet_id': packet['packet_id'], 'rubric_id': packet['rubric_id'],
        'reviewer': judgments['reviewer'], 'previously_seen_cases': judgments['previously_seen_cases'],
        'scope': 'Descriptive comparison of one saved output per condition with the first recorded next student message.',
        'metric': 'Incidence gap = generated yes fraction minus recorded yes fraction on the same complete pairs; '
                  'positive means more generated messages carry that flag. Disagreement is the fraction of unequal flags. '
                  'Each flag has its own denominator; paired conditions share their denominator. Missing judgments are rejected.',
        'counts': {'cases': len(rows), 'scheduled_outputs': 2 * len(rows), 'reviewed_messages': len(reviewed),
                   'unclear_messages': sum(any(judgment[flag] == 'unclear' for flag in FLAGS) for judgment in reviewed.values()),
                   'unclear_flags': sum(judgment[flag] == 'unclear' for judgment in reviewed.values() for flag in FLAGS),
                   'missing_judgments': 0},
        'dispositions': {condition: {status: sum(row['conditions'][condition]['status'] == status for row in rows)
                                    for status in ('reply', 'no-reply', 'error')} for condition in CONDITIONS},
        'coverage': coverage,
        'primary': {'condition': 'original', 'flag': 'work_present', **original['work_present']},
        'original': original, 'paired': paired,
        'reference_joint': _joint_scores(rows, ()),
        'original_joint': _joint_scores(rows, ('original',)),
        'paired_joint': _joint_scores(rows, CONDITIONS), 'cases': rows,
        'limits': [
            'One saved output per condition cannot estimate context-specific action probabilities or calibration.',
            'A zero incidence gap can hide disagreement. Disagreement with one realized message does not establish implausibility.',
            'No-reply, errors and unclear flags remain separate; flag-specific exclusions can bias the scored subset.',
            'These previously generated development cases are not a representative or student-separated holdout.',
            'Candidate comparisons change presentation of existing context; a frequency change alone is not an improvement.',
            'One reviewer supplies provisional coding; prior exposure is self-reported and reliability is unmeasured.',
            'This concerns first recorded messages, not whole contribution blocks, notebook actions, correctness, tutor effects or learning.',
            'No confidence interval, significance claim, tuning, replacement output or automatic model change follows from this report.'
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
