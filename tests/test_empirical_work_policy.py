"""Hand-calculated, invented checks for the real-data baseline diagnostic."""
from copy import deepcopy
import importlib.util

import pytest


def evaluator():
    assert importlib.util.find_spec('src.eval.empirical_work_policy'), 'Empirical baseline is missing'
    from src.eval.empirical_work_policy import evaluate
    return evaluate


def observation(ident, account, value, source='fixed'):
    return {'id': ident, 'conversation_id': 'conversation-' + ident, 'account_id': account,
            'source': source, 'origin': 'recorded', 'label_origin': 'human',
            'rubric_id': 'help-work-v1', 'help_request': 'yes', 'work_present': value}


def rows():
    return [observation('a1', 'a', 'no'), observation('a2', 'a', 'no'),
            observation('a3', 'a', 'no'), observation('b1', 'b', 'yes', 'cached'),
            observation('c1', 'c', 'no')]


def test_account_fit_and_full_account_holdout_use_hand_calculated_weights():
    raw = rows()
    before = deepcopy(raw)
    result = evaluator()(raw)
    assert raw == before
    assert result['fitted']['fraction'] == '1/3'  # Message weighting would give 1/5.
    assert result['fitted']['counts']['accounts_with_work_yes'] == 1
    folds = {f['held_account']: f for f in result['leave_account_out']['folds']}
    assert folds['a']['fit']['p_work_present'] == .5
    assert folds['b']['fit']['p_work_present'] == 0
    assert folds['b']['fit']['counts']['work_yes'] == 0
    assert all(r['account_id'] != name for name, fold in folds.items() for r in fold['fit']['accounts'])
    summary = result['leave_account_out']['summary']
    assert summary['scored_accounts'] == 3 and summary['scored_messages'] == 5
    assert summary['account_mean_brier'] == {
        'frequency': 1.0, 'constant_half': .5, 'always_no': pytest.approx(2 / 3)}
    assert result['leave_account_out']['by_class']['yes']['account_mean_brier']['frequency'] == 2
    raw.reverse()
    assert evaluator()(raw) == result


def test_source_holdout_also_removes_shared_accounts():
    raw = [observation('a1', 'a', 'no', 'fixed'), observation('a2', 'a', 'yes', 'cached'),
           observation('b1', 'b', 'no', 'fixed'), observation('c1', 'c', 'yes', 'fixed'),
           observation('d1', 'd', 'no', 'cached')]
    result = evaluator()(raw)
    held = result['leave_source_out']['cached']
    assert held['excluded_accounts'] == ['a', 'd']
    assert {r['account_id'] for r in held['fit']['accounts']} == {'b', 'c'}
    assert held['fit']['p_work_present'] == .5
    assert held['summary']['scored_messages'] == 2
    assert result['leave_source_out']['fixed']['fit']['status'] == 'insufficient-evidence'
    assert result['leave_source_out']['fixed']['summary']['account_mean_brier']['frequency'] is None


def test_missing_identities_and_unclear_labels_remain_excluded():
    raw = rows() + [observation('unknown-label', 'd', 'unclear'),
                    observation('unknown-account', None, 'yes')]
    result = evaluator()(raw)
    assert result['counts']['observations'] == 7
    assert result['counts']['eligible_messages'] == 5
    assert result['fitted']['fraction'] == '1/3'
    assert {r['id'] for r in result['exclusions']} == {'unknown-label', 'unknown-account'}
    assert result['leave_account_out']['summary']['scored_messages'] == 5
    assert result['leave_account_out']['summary']['unknown_reference_messages'] == 1


def test_insufficient_support_has_no_fabricated_prediction_or_zero_error():
    result = evaluator()([observation('one', 'a', 'yes')])
    assert result['fitted']['status'] == 'insufficient-evidence'
    assert result['fitted']['p_work_present'] is None
    assert result['leave_account_out']['summary']['scored_messages'] == 0
    assert result['leave_account_out']['summary']['account_mean_brier']['frequency'] is None


@pytest.mark.parametrize('change', [
    lambda x: x[0].update(origin='generated'),
    lambda x: x[0].update(label_origin='assistant'),
    lambda x: x[0].update(rubric_id='behavior-pilot-v1'),
    lambda x: x[0].update(work_present=True),
    lambda x: x[0].update(account_id=' '),
    lambda x: x[1].update(id='a1'),
    lambda x: x[1].update(conversation_id='conversation-b1'),
])
def test_reject_mixed_origin_rubric_duplicate_or_conflicting_identity(change):
    raw = rows()
    change(raw)
    with pytest.raises(ValueError):
        evaluator()(raw)
