"""Invented checks for one frozen context diagnostic, not student fidelity."""
import importlib.util
from pathlib import Path

import pytest


def probe():
    path = Path(__file__).resolve().parents[1] / 'experiments/2026-10-01-context-work-probe.py'
    assert path.exists(), 'Context probe is missing'
    spec = importlib.util.spec_from_file_location('context_work_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(ident, account, label, source='fixed'):
    return {'id': ident, 'conversation_id': 'conversation-' + ident, 'account_id': account,
            'source': source, 'origin': 'recorded', 'label_origin': 'human',
            'rubric_id': 'help-work-v1', 'help_request': 'yes', 'work_present': label}


def test_literal_feature_uses_student_prefix_only_and_keeps_its_known_limits():
    cue = probe().feature
    assert cue([{'role': 'student', 'text': 'help'}, {'role': 'tutor', 'text': 'x = 2'}]) is False
    assert cue([{'role': 'student', 'text': 'x = 2\nhelp'}, {'role': 'tutor', 'text': 'ok'}]) is True
    assert cue([{'role': 'student', 'text': 'for this question?'}]) is True  # Known lexical false positive.
    assert cue([{'role': 'student', 'text': 'print(2)'}]) is False  # Known missed code form.
    assert cue([{'role': 'student', 'text': 'x == 2'}]) is False
    assert cue([{'role': 'tutor', 'text': 'x = 2'}]) is None
    with pytest.raises(ValueError):
        cue([{'role': 'student', 'text': 'help', 'target': 'x = 2'}])


def test_account_weights_are_preserved_before_conditioning_and_fallback_is_global():
    mod = probe()
    rows = [row('a1', 'a', 'yes'), row('a2', 'a', 'no'), row('b', 'b', 'no')]
    features = {'a1': True, 'a2': False, 'b': False}
    # Global=.25; matching mass=.5, positive mass=.5 -> (.5+.25)/1.5=.5.
    result = mod.forecast(rows, features, True)
    assert result['fraction'] == '1/2'
    assert result['bucket_mass'] == '1/2' and result['positive_mass'] == '1/2'
    assert mod.forecast(rows, features, None)['fraction'] == '1/4'
    assert mod.forecast(rows, dict.fromkeys(features, False), True)['fraction'] == '1/4'
    assert mod.forecast(rows[:2], features, True)['p'] is None


def test_holdouts_remove_whole_accounts_and_never_use_the_target_label():
    mod = probe()
    rows = [row('a1', 'a', 'no'), row('a2', 'a', 'no', 'cached'),
            row('b', 'b', 'yes'), row('c', 'c', 'no'), row('d', 'd', 'yes', 'cached')]
    features = {'a1': True, 'a2': False, 'b': True, 'c': False, 'd': True}
    result = mod.evaluate(rows, features)
    fold = next(f for f in result['leave_account_out']['folds'] if f['held_account'] == 'a')
    assert all(set(p['context']['training_ids']) == {'b', 'c', 'd'} for p in fold['predictions'])
    changed = [r | {'work_present': 'yes'} if r['account_id'] == 'a' else r for r in rows]
    other = next(f for f in mod.evaluate(changed, features)['leave_account_out']['folds'] if f['held_account'] == 'a')
    assert [p['context'] for p in fold['predictions']] == [p['context'] for p in other['predictions']]
    source = result['leave_source_out']['cached']
    assert all(set(p['context']['training_ids']) == {'b', 'c'} for p in source['predictions'])
    with pytest.raises(ValueError):
        mod.evaluate(rows, features | {'unbound': True})
