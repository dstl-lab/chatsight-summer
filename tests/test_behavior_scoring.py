"""Hand-calculated scoring and split boundaries; all examples are invented."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

TOY = Path(__file__).parent / 'fixtures/behavior_scoring_toy.json'


def scorer():
    assert importlib.util.find_spec('src.eval.behavior_scoring'), 'Offline scoring command is missing'
    from src.eval.behavior_scoring import evaluate
    return evaluate


def test_hand_calculated_scores_keep_group_weighting_and_exclusions_visible():
    evaluate = scorer()
    result = evaluate(json.loads(TOY.read_text()))
    assert result['baseline']['probabilities'] == {'help': .75, 'code': .25}
    assert result['counts'] == {'train':5, 'train_labeled':4, 'evaluation':7,
                                'evaluation_labeled':6, 'paired_scored':3}
    assert result['prediction_status'] == {'ok':4, 'error':1, 'no-reply':1, 'unlabeled':0, 'missing':1}
    paired = result['paired']
    assert paired['encounter_mean']['model_brier'] == pytest.approx(.3)
    assert paired['encounter_mean']['baseline_brier'] == pytest.approx(11 / 24)
    assert paired['group_mean']['model_brier'] == pytest.approx(.35)
    assert paired['group_mean']['baseline_brier'] == pytest.approx(.375)
    assert paired['group_mean']['baseline_minus_model'] == pytest.approx(.025)
    assert paired['groups'] == 2
    assert paired['by_reference_label']['code']['model_brier'] == pytest.approx(.08)
    assert result['baseline']['all_labeled_evaluation']['n'] == 6
    assert result['coverage']['prediction_on_labeled'] == .5
    rows = {row['id']:row for row in result['rows']}
    assert rows['eval-error']['baseline_brier'] == 1.125
    assert rows['eval-error']['model_brier'] is None
    assert rows['eval-unknown']['reference_exclusion_reason'] == 'Invented reviewer disagreement'
    assert rows['eval-stop']['prediction_status'] == 'no-reply' and not rows['eval-stop']['scored']
    assert len(result['train_exclusions']) == 1
    assert not any(row['scored'] for row in result['rows'][3:])


def test_invalid_forecasts_and_declared_identity_leakage_fail_closed():
    evaluate = scorer()
    original = json.loads(TOY.read_text())
    mutations = [
        lambda p:p['evaluation'][0].update(conversation_id='train-conversation-1'),
        lambda p:p['evaluation'][0].update(student_id='train-student-1'),
        lambda p:p['evaluation'][-1].update(student_id='train-student-1'),
        lambda p:p['evaluation'][1].update(id='eval-1'),
        lambda p:p['predictions'].append(deepcopy(p['predictions'][0])),
        lambda p:p['predictions'][0].update(id='not-evaluation'),
        lambda p:p['predictions'][0].update(probabilities={'help':.6,'code':.6}),
        lambda p:p['predictions'][0].update(probabilities={'help':True,'code':0}),
        lambda p:p['predictions'][0].update(probabilities={'help':float('nan'),'code':.8}),
        lambda p:p['predictions'][0].update(probabilities={'help':-.2,'code':1.2}),
        lambda p:p['predictions'][0].update(probabilities={'help':1}),
        lambda p:p['predictions'][0].update(probabilities={'help':.2,'code':.8,'other':0}),
        lambda p:p['predictions'][0].update(status='error'),
        lambda p:p['evaluation'][-1].update(label='insufficient-evidence'),
        lambda p:p['evaluation'][-1].update(label=None),
        lambda p:p['evaluation'][0].update(student_id=' '),
        lambda p:p['classes'].append('help'),
        lambda p:p['classes'].append('insufficient-evidence'),
        lambda p:p['train'].clear(),
    ]
    for mutation in mutations:
        value = deepcopy(original)
        mutation(value)
        with pytest.raises(ValueError):
            evaluate(value)
    # Even excluded records participate in split checks.
    bad = deepcopy(original)
    bad['evaluation'][4]['student_id'] = 'train-student-1'
    with pytest.raises(ValueError):
        evaluate(bad)


def test_no_usable_forecasts_is_not_zero_error_and_cli_preserves_inputs(tmp_path):
    evaluate = scorer()
    value = json.loads(TOY.read_text())
    value['predictions'] = []
    result = evaluate(value)
    assert result['paired']['encounter_mean']['model_brier'] is None
    assert result['paired']['group_mean']['baseline_brier'] is None
    assert result['counts']['paired_scored'] == 0 and result['prediction_status']['missing'] == 7
    before = TOY.read_bytes()
    output = tmp_path / 'report'
    command = [sys.executable, '-m', 'src.eval.behavior_scoring', str(TOY), '--output', str(output)]
    finished = subprocess.run(command, capture_output=True, text=True)
    assert finished.returncode == 0, finished.stderr
    report = json.loads((output / 'report.json').read_text())
    assert report['paired']['encounter_mean']['model_brier'] == pytest.approx(.3)
    assert report['provenance']['input_sha256']
    assert (output / 'report.md').read_text().startswith('# Offline action scoring')
    files = {p.name:p.read_bytes() for p in output.iterdir()}
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert {p.name:p.read_bytes() for p in output.iterdir()} == files
    assert TOY.read_bytes() == before
