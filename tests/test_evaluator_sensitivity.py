"""Authored arithmetic: boundaries, source clipping, weights and unknown labels."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path

import pytest


def test_sensitivity_bounds_and_weights():
    path = Path(__file__).parents[1] / 'experiments/2026-09-30-evaluator-sensitivity.py'
    spec = importlib.util.spec_from_file_location('sensitivity', path)
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    assert run.bounds(F(3,8), F(5,8), F(1,40), F(1,40)) == (F(1,5), F(3,10))
    assert run.decision(*run.bounds(F(3,8), F(5,8), F(1,40), F(1,40))) == 'inconclusive'
    assert run.decision(*run.bounds(0, F(26,32), F(3,10), F(3,10))) == 'large_excess'
    assert run.bounds(0, 1, 1, 1) == (-1, 1)
    assert run.decision(-F(1,10), F(1,10)) == 'within_margin'
    assert run.decision(-F(1,2), -F(1,4)) == 'large_deficit'
    assert run.rates([('no', ['yes']), ('yes', ['no', 'no', 'no'])]) == (F(1,2), F(1,2))
    for cases in ([], [('no', [])], [('unclear', ['yes'])], [('yes', ['no', None])]):
        with pytest.raises(ValueError):
            run.rates(cases)
    for error in (-.1, 1.1, float('nan')):
        with pytest.raises(ValueError):
            run.bounds(.2, .6, error, 0)
