"""Authored boundaries for the frozen independent-account test."""
import importlib.util
from pathlib import Path

import pytest


def runner():
    path = Path(__file__).resolve().parents[1] / 'experiments/2026-10-01-context-work-holdout.py'
    assert path.exists(), 'Holdout preparation is missing'
    spec = importlib.util.spec_from_file_location('holdout', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selection_is_metadata_only_stable_and_account_separated():
    m = runner()
    rows = [{'conv_id': f'c{i}', 'account_ids': [a], 'eligible_checkpoints': 3}
            for i, a in enumerate(('a', 'a', 'b', 'c', 'd'))]
    result = m.choose(rows, {'b'}, count=3)
    assert {r['account_id'] for r in result} == {'a', 'c', 'd'}
    assert m.choose(list(reversed(rows)), {'b'}, count=3) == result
    with pytest.raises(ValueError):
        m.choose(rows, {'a', 'b'}, count=3)


def test_prefix_boundary_rejects_target_extra_missing_and_changed_identity():
    m = runner()
    case = {'id': 'case', 'conv_id': 'conv', 'account_id': 'account',
            'prefix_event_ids': [1, 2, 3, 4], 'target_event_id': 5, 'tutor_event_id': 4,
            'target_at': '2026-03-01T00:00:05+00:00', 'prior_queries': 2}
    rows = [{'id': i, 'conv_id': 'conv', 'account_id': 'account', 'notebook_id': 'notebook',
             'created_at': f'2026-03-01T00:00:0{i}+00:00',
             'event_type': 'tutor_query' if i % 2 else 'tutor_response',
             'text': 'answer = 2' if i == 1 else 'visible'} for i in range(1, 5)]
    assert m.prefix(case, rows)[0] == {'role': 'student', 'text': 'answer = 2'}
    target = rows[0] | {'id': 5, 'text': 'FUTURE ONLY'}
    for bad in (rows + [target], rows[:-1], [rows[0] | {'account_id': 'other'}, *rows[1:]],
                [rows[0] | {'created_at': '2026-03-02T00:00:00+00:00'}, *rows[1:]]):
        with pytest.raises(ValueError):
            m.prefix(case, bad)


def test_receipt_rejects_changed_parameters_even_when_its_hash_matches(monkeypatch):
    m = runner()
    monkeypatch.setattr(m, 'expected_params', lambda stem: {'salt': 'fixed', 'until': 'fixed', 'event_ids': '[1]'})
    monkeypatch.setattr(m, 'read', lambda path: {'salt': 'fixed', 'until': 'changed', 'event_ids': '[1]'})
    with pytest.raises(ValueError, match='Query parameters differ'):
        m.receipt('prefix', m.TEXT_SQL)
