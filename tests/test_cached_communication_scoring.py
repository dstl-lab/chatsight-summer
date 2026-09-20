"""Authored one-output comparisons: arithmetic, coverage and strict intake."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


def scorer():
    assert importlib.util.find_spec('src.eval.cached_communication_scoring'), 'Cached scorer is missing'
    from src.eval.cached_communication_scoring import score
    return score


def example():
    packet = {'packet_id': 'authored-packet', 'rubric_id': 'help-work-v1',
              'definitions': {'help_request': 'An observable help request.',
                              'work_present': 'Observable work or diagnostic evidence.'}, 'cases': []}
    mapping = {'packet_id': packet['packet_id'], 'cases': []}
    review = {'packet_id': packet['packet_id'], 'rubric_id': packet['rubric_id'],
              'reviewer': 'Authored reviewer', 'previously_seen_cases': 'unsure', 'judgments': []}
    # Each tuple is (help, work), in reference/original/candidate order.
    flags = [(('yes', 'yes'), ('no', 'yes'), ('yes', 'no')),
             (('no', 'no'), ('yes', 'no'), ('no', 'no')),
             (('yes', 'no'), ('yes', 'yes'), ('yes', 'no')),
             (('no', 'yes'), ('no', 'no'), ('yes', 'yes'))]
    for number, messages in enumerate(flags, 1):
        ids = [f'message-{number}-{role}' for role in ('reference', 'original', 'candidate')]
        packet['cases'].append({'id': f'case-{number}', 'context_status': 'Authored dialogue.',
            'prefix': {'context': [], 'turns': [{'id': f'turn-{number}', 'role': 'tutor',
                                                'text': 'PRIVATE SOURCE CANARY'}]},
            'candidates': [{'id': identity, 'text': 'PRIVATE SOURCE CANARY'} for identity in ids]})
        mapping['cases'].append({'id': f'case-{number}', 'reference_id': ids[0], 'conditions': {
            condition: {'id': identity, 'status': 'reply'}
            for condition, identity in zip(('original', 'candidate'), ids[1:])}})
        review['judgments'].extend({'id': identity, 'help_request': help_flag,
            'work_present': work_flag, 'note': None}
            for identity, (help_flag, work_flag) in zip(ids, messages))
    return packet, mapping, review


def judgment(review, identity):
    return next(j for j in review['judgments'] if j['id'] == identity)


def absent(packet, mapping, review, index, condition, status):
    slot = mapping['cases'][index]['conditions'][condition]
    slot['status'] = status
    packet['cases'][index]['candidates'] = [c for c in packet['cases'][index]['candidates']
                                           if c['id'] != slot['id']]
    review['judgments'] = [j for j in review['judgments'] if j['id'] != slot['id']]


def test_incidence_gap_does_not_hide_disagreement_and_common_subset_is_explicit():
    inputs = example()
    before = deepcopy(inputs)
    report = scorer()(*inputs)
    primary = report['primary']
    assert primary['condition'] == 'original' and primary['flag'] == 'work_present'
    assert primary['cases'] == 4 and primary['case_ids'] == ['case-1', 'case-2', 'case-3', 'case-4']
    assert primary['table'] == {'both_yes': 1, 'neither_yes': 1, 'generated_only': 1, 'reference_only': 1}
    assert primary['reference_yes'] == primary['generated_yes'] == 2
    assert primary['count_difference'] == primary['incidence_gap_pp'] == 0
    assert primary['reference_incidence'] == primary['generated_incidence'] == .5
    assert primary['disagreements'] == 2 and primary['disagreement_fraction'] == .5
    for flag, candidate_gap in (('work_present', -25), ('help_request', 25)):
        paired = report['paired'][flag]
        assert paired['cases'] == 4
        assert paired['original']['incidence_gap_pp'] == 0
        assert paired['candidate']['incidence_gap_pp'] == candidate_gap
        assert paired['candidate']['disagreement_fraction'] == .25
        assert paired['candidate_minus_original_disagreement'] == -.25
        assert paired['candidate_minus_original_disagreement_pp'] == -25
    assert report['reference_joint']['counts'] == {'neither': 1, 'help-only': 1, 'work-only': 1, 'both': 1}
    assert report['original_joint']['cases'] == report['paired_joint']['cases'] == 4
    assert report['paired_joint']['disagreement']['original'] == {'count': 4, 'fraction': 1.0}
    assert report['paired_joint']['disagreement']['candidate'] == {'count': 2, 'fraction': .5}
    assert report['paired_joint']['candidate_minus_original_disagreement'] == -.5
    assert 'PRIVATE SOURCE CANARY' not in json.dumps(report)
    assert inputs == before


def test_unclear_flags_and_no_reply_use_separate_denominators_and_keep_reference_coverage():
    packet, mapping, review = example()
    judgment(review, 'message-1-original').update(help_request='unclear', note='Help intent is unknown.')
    judgment(review, 'message-2-reference').update(work_present='unclear', note='Work is ambiguous.')
    judgment(review, 'message-3-candidate').update(work_present='unclear', note='Work is ambiguous.')
    absent(packet, mapping, review, 3, 'candidate', 'no-reply')
    report = scorer()(packet, mapping, review)
    assert report['primary']['case_ids'] == ['case-1', 'case-3', 'case-4']
    assert report['primary']['disagreement_fraction'] == pytest.approx(2 / 3)
    assert report['original']['help_request']['case_ids'] == ['case-2', 'case-3', 'case-4']
    assert report['original']['help_request']['incidence_gap_pp'] == pytest.approx(100 / 3)
    work, help_flag = report['paired']['work_present'], report['paired']['help_request']
    assert work['case_ids'] == ['case-1'] and work['candidate_minus_original_disagreement'] == 1
    assert help_flag['case_ids'] == ['case-2', 'case-3']
    assert help_flag['candidate_minus_original_disagreement'] == -.5
    assert report['reference_joint']['cases'] == 3
    assert report['reference_joint']['counts'] == {'neither': 0, 'help-only': 1, 'work-only': 1, 'both': 1}
    assert report['original_joint']['case_ids'] == ['case-3', 'case-4']
    assert report['paired_joint']['cases'] == 0
    assert report['paired_joint']['candidate_minus_original_disagreement'] is None
    assert report['coverage']['original']['help_request']['unclear'] == 1
    assert report['coverage']['reference']['work_present']['unclear'] == 1
    assert report['coverage']['candidate']['work_present'] == {
        'yes': 0, 'no': 2, 'unclear': 1, 'missing': 0, 'no-reply': 1, 'error': 0}
    assert report['dispositions']['candidate'] == {'reply': 3, 'no-reply': 1, 'error': 0}
    assert report['counts']['cases'] == 4 and report['counts']['reviewed_messages'] == 11
    assert report['counts']['unclear_flags'] == 3 and report['counts']['missing_judgments'] == 0
    rows = report['cases']
    assert rows[0]['exclusions']['original']['help_request'] and not rows[0]['exclusions']['original']['work_present']
    assert rows[3]['conditions']['candidate']['judgment'] is None
    assert rows[3]['exclusions']['paired']['work_present']


def test_absent_outputs_never_become_negative_flags_or_zero_error():
    packet, mapping, review = example()
    packet['cases'] = packet['cases'][:1]
    mapping['cases'] = mapping['cases'][:1]
    review['judgments'] = review['judgments'][:3]
    absent(packet, mapping, review, 0, 'original', 'error')
    absent(packet, mapping, review, 0, 'candidate', 'no-reply')
    report = scorer()(packet, mapping, review)
    assert report['primary']['cases'] == 0
    assert report['primary']['incidence_gap_pp'] is None
    assert report['primary']['disagreement_fraction'] is None
    assert report['paired']['help_request']['candidate_minus_original_disagreement'] is None
    assert report['reference_joint']['cases'] == 1 and report['reference_joint']['counts']['both'] == 1
    assert report['coverage']['original']['work_present']['error'] == 1
    assert report['coverage']['original']['work_present']['no'] == 0
    assert report['coverage']['candidate']['work_present']['no-reply'] == 1
    assert report['original_joint']['cases'] == report['paired_joint']['cases'] == 0


def test_packet_mapping_and_human_intake_reject_missing_duplicate_or_ambiguous_records():
    score = scorer()
    for change in (
        lambda p, m, j: m.update(packet_id='another-packet'),
        lambda p, m, j: m.update(extra='unrecognized'),
        lambda p, m, j: m['cases'][0].update(extra='unrecognized'),
        lambda p, m, j: m['cases'][0]['conditions']['original'].update(extra='unrecognized'),
        lambda p, m, j: m['cases'][0]['conditions'].pop('candidate'),
        lambda p, m, j: m['cases'][0]['conditions'].update(other={'id': 'other', 'status': 'reply'}),
        lambda p, m, j: m['cases'][0]['conditions']['original'].update(status='no-reply'),
        lambda p, m, j: m['cases'][0]['conditions']['original'].update(status='unknown'),
        lambda p, m, j: m['cases'][0]['conditions']['original'].update(id='message-1-reference'),
        lambda p, m, j: m['cases'][1]['conditions']['candidate'].update(id='message-1-candidate'),
        lambda p, m, j: m['cases'][0].update(reference_id='message-2-reference'),
        lambda p, m, j: m['cases'].append(deepcopy(m['cases'][0])),
        lambda p, m, j: m['cases'].pop(),
        lambda p, m, j: j.update(packet_id='wrong'),
        lambda p, m, j: j.update(rubric_id='wrong'),
        lambda p, m, j: j.update(previously_seen_cases=None),
        lambda p, m, j: j.update(reviewer=' '),
        lambda p, m, j: j['judgments'].pop(),
        lambda p, m, j: j['judgments'].append(deepcopy(j['judgments'][0])),
        lambda p, m, j: j['judgments'][0].update(help_request=None),
        lambda p, m, j: j['judgments'][0].update(work_present=True),
        lambda p, m, j: j['judgments'][0].update(help_request='unclear', note=' '),
        lambda p, m, j: j['judgments'][0].update(extra='unrecognized'),
    ):
        inputs = deepcopy(example())
        change(*inputs)
        with pytest.raises(ValueError):
            score(*inputs)


def test_cli_creates_one_hashed_report_and_preserves_existing_files(tmp_path):
    scorer()
    paths = [tmp_path / name for name in ('packet.json', 'mapping.json', 'judgments.json')]
    for path, value in zip(paths, example()):
        path.write_text(json.dumps(value), encoding='utf-8')
    before = [path.read_bytes() for path in paths]
    output = tmp_path / 'report.json'
    command = [sys.executable, '-m', 'src.eval.cached_communication_scoring', *map(str, paths), str(output)]
    subprocess.run(command, check=True, capture_output=True)
    saved = output.read_bytes()
    report = json.loads(saved)
    assert report['primary']['disagreement_fraction'] == .5
    assert report['provenance'] == {
        **{name + '_sha256': sha256(raw).hexdigest()
           for name, raw in zip(('packet', 'mapping', 'judgments'), before)},
        'source_sha256': sha256(Path('src/eval/cached_communication_scoring.py').read_bytes()).hexdigest()}
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == saved and [path.read_bytes() for path in paths] == before
