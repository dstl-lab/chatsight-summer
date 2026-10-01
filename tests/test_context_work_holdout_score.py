"""Invented checks for the predeclared paired score and unresolved-outcome bounds."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


def scorer():
    path = Path(__file__).resolve().parents[1] / 'experiments/2026-10-01-context-work-holdout-score.py'
    assert path.exists(), 'Holdout scorer is missing'
    spec = importlib.util.spec_from_file_location('holdout_score', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs():
    forecasts = [{'id': 'a', 'cue': True, 'p': .75, 'baselines': {'frequency': .25, 'constant_half': .5, 'always_no': 0.}},
                 {'id': 'b', 'cue': False, 'p': .1, 'baselines': {'frequency': .25, 'constant_half': .5, 'always_no': 0.}}]
    form = {'packet_id': 'invented', 'rubric_id': 'help-work-v1', 'reviewer': 'fixture', 'previously_seen_cases': 'no',
            'judgments': [{'id': 'b-message', 'work_present': 'unclear', 'note': 'Ambiguous.'},
                          {'id': 'a-message', 'work_present': 'yes', 'note': None}]}
    return forecasts, form


def test_paired_score_and_bounds_share_the_same_unresolved_outcome():
    predictions, form = inputs()
    result = scorer().evaluate(predictions, form, 'invented')
    assert result['coverage']['binary_scored'] == 1
    assert result['paired']['mean_brier'] == {'context': .125, 'frequency': 1.125, 'constant_half': .5, 'always_no': 2.}
    assert result['paired']['context_minus_frequency'] == -1
    # Unknown b: delta(no)=-.105, delta(yes)=.495; include a's known delta=-1.
    assert result['full_set_delta_bounds'] == pytest.approx({'lower': -.5525, 'upper': -.2525})
    assert result['rows'][1]['work_present'] == 'unclear'
    assert result['rows'][1]['brier'] is None
    assert result['paired']['account_comparison'] == {'better': 1, 'tie': 0, 'worse': 0}
    assert scorer().evaluate(list(reversed(predictions)), form, 'invented') == result


def test_missing_forecast_and_all_unclear_preserve_coverage():
    predictions, form = inputs()
    predictions[0]['p'] = None
    result = scorer().evaluate(predictions, form, 'invented')
    assert result['coverage']['binary_scored'] == 0
    assert result['coverage']['missing_predictions'] == 1
    assert result['paired']['mean_brier']['context'] is None
    assert result['full_set_delta_bounds'] == pytest.approx({'lower': (-2-.105)/2, 'upper': (2+.495)/2})
    predictions, form = inputs()
    for row in form['judgments']:
        row.update(work_present='unclear', note='Unknown.')
    assert scorer().evaluate(predictions, form, 'invented')['coverage']['binary_scored'] == 0


@pytest.mark.parametrize('change', [
    lambda f: f.update(packet_id='other'),
    lambda f: f.update(rubric_id='other'),
    lambda f: f['judgments'][0].update(note=None),
    lambda f: f['judgments'][0].update(id='a-message'),
    lambda f: f['judgments'][1].update(work_present=True),
    lambda f: f['judgments'][1].update(help_request='yes'),
])
def test_wrong_binding_or_invalid_review_is_rejected(change):
    predictions, original = inputs()
    form = deepcopy(original); change(form)
    with pytest.raises(ValueError):
        scorer().evaluate(predictions, form, 'invented')
