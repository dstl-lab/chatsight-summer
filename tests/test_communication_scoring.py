"""Hand-scored mixed messages preserve exclusions and reject mismatched intake."""
from copy import deepcopy
import importlib.util
import json
import subprocess
import sys

import pytest


def test_complete_case_scores_preserve_uncertainty_dispositions_and_input_files(tmp_path):
    assert importlib.util.find_spec('src.eval.communication_scoring'), 'Communication scorer is missing'
    from src.eval.communication_scoring import score

    packet = {'packet_id': 'invented-packet', 'rubric_id': 'help-work-v1',
              'definitions': {'help_request': 'An observable request for help.',
                              'work_present': 'Submitted work or diagnostic evidence.'}, 'cases': []}
    mapping = {'packet_id': packet['packet_id'], 'cases': []}
    judgments = {'packet_id': packet['packet_id'], 'rubric_id': 'help-work-v1',
                 'reviewer': 'Invented reviewer', 'previously_seen_cases': 'unsure', 'judgments': []}
    for case_number in range(1, 9):
        case_id, reference = f'case-{case_number}', f'item-{case_number}-reference'
        case = {'id': case_id, 'prefix': {'context': [], 'turns': [
            {'id': f'{case_id}-turn-1', 'role': 'student', 'text': 'Please check my example.'},
            {'id': f'{case_id}-turn-2', 'role': 'tutor', 'text': 'What did you try?'}]},
            'context_status': 'Invented dialogue; no notebook available.',
            'candidates': [{'id': reference, 'text': '' if case_number == 8 else 'Is my answer 2 correct?'}]}
        entry = {'id': case_id, 'reference_id': reference, 'draws': []}
        judgments['judgments'].append({'id': reference, 'help_request': 'yes', 'work_present': 'yes', 'note': None})
        for condition in ('grounded', 'current-exchange'):
            for draw in range(1, 5):
                item_id = f'item-{case_number}-{condition}-{draw}'
                status = ('no-reply' if (case_number, condition, draw) == (7, 'grounded', 4) else
                          'error' if (case_number, condition, draw) == (8, 'current-exchange', 4) else 'reply')
                entry['draws'].append({'id': item_id, 'condition': condition, 'draw': draw, 'status': status})
                if status == 'reply':
                    case['candidates'].append({'id': item_id, 'text': 'Invented candidate.'})
                    judgments['judgments'].append({'id': item_id,
                        'help_request': 'yes' if condition == 'grounded' and draw <= 2 else 'no',
                        'work_present': 'yes' if draw <= (3 if condition == 'grounded' else 1) else 'no',
                        'note': None})
        packet['cases'].append(case)
        mapping['cases'].append(entry)
    uncertain = next(j for j in judgments['judgments'] if j['id'] == 'item-6-reference')
    uncertain.update(help_request='unclear', note='The intended request cannot be determined.')
    inputs = deepcopy((packet, mapping, judgments))
    report = score(packet, mapping, judgments)
    assert (packet, mapping, judgments) == inputs
    assert report['counts'] == {'cases': 8, 'scheduled_draws': 64, 'reviewed_messages': 70,
        'unclear_messages': 1, 'unclear_flags': 1, 'missing_judgments': 0, 'complete_cases': 5, 'excluded_cases': 3}
    assert report['dispositions'] == {'grounded': {'reply': 31, 'no-reply': 1, 'error': 0},
                                       'current-exchange': {'reply': 31, 'no-reply': 0, 'error': 1}}
    # Target yes/yes: grounded p=(.5,.75), baseline p=(0,.25).
    assert report['paired'] == {'cases': 5,
        'grounded': {'help_request': .25, 'work_present': .0625, 'mean_brier': .15625},
        'current-exchange': {'help_request': 1., 'work_present': .5625, 'mean_brier': .78125},
        'grounded_minus_current_exchange': -.625}
    assert len(report['cases']) == 8 and sum(len(c['draws']) for c in report['cases']) == 64
    assert all(c['scores'] is None and c['exclusion_reasons'] for c in report['cases'][5:])
    assert report['cases'][6]['draws'][-5]['status'] == 'no-reply'
    assert report['cases'][6]['draws'][-5]['judgment'] is None

    for change in (
        lambda p, m, j: m.update(packet_id='another-packet'),
        lambda p, m, j: m.update(extra='unrecognized'),
        lambda p, m, j: m['cases'][0].update(extra='unrecognized'),
        lambda p, m, j: m['cases'][0]['draws'][0].update(extra='unrecognized'),
        lambda p, m, j: m['cases'][0]['draws'][0].update(draw=True),
        lambda p, m, j: m['cases'][0]['draws'][0].update(draw=2),
        lambda p, m, j: m['cases'][0]['draws'][0].update(status='no-reply'),
        lambda p, m, j: m['cases'][0].update(reference_id='absent'),
        lambda p, m, j: m['cases'].pop(),
        lambda p, m, j: j['judgments'][0].update(help_request=None),
        lambda p, m, j: j['judgments'][0].update(help_request='unclear', note=' '),
        lambda p, m, j: j['judgments'][0].update(extra='unrecognized'),
        lambda p, m, j: j['judgments'].append(deepcopy(j['judgments'][0])),
        lambda p, m, j: j.update(previously_seen_cases=None),
        lambda p, m, j: j.update(reviewer=' '),
    ):
        invalid = deepcopy(inputs)
        change(*invalid)
        with pytest.raises(ValueError):
            score(*invalid)
    all_unclear = deepcopy(judgments)
    for judgment in all_unclear['judgments']:
        judgment.update(help_request='unclear', note='Insufficient context.')
    empty = score(packet, mapping, all_unclear)
    assert empty['paired']['cases'] == 0
    assert empty['paired']['grounded']['mean_brier'] is None
    assert empty['paired']['grounded_minus_current_exchange'] is None

    paths = [tmp_path / name for name in ('packet.json', 'mapping.json', 'judgments.json')]
    for path, value in zip(paths, inputs):
        path.write_text(json.dumps(value), encoding='utf-8')
    before = [p.read_bytes() for p in paths]
    output = tmp_path / 'report.json'
    command = [sys.executable, '-m', 'src.eval.communication_scoring', *map(str, paths), str(output)]
    subprocess.run(command, check=True, capture_output=True)
    saved = output.read_bytes()
    result = json.loads(saved)
    assert result['paired'] == report['paired']
    assert set(result['provenance']) == {'packet_sha256', 'mapping_sha256', 'judgments_sha256', 'source_sha256'}
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == saved and [p.read_bytes() for p in paths] == before
