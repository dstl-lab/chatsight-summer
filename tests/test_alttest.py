import pytest

from src.eval.alttest import alt_test
from src.eval.validation import AuditRow
from src.labeling.draft import MessageLabels


def _model(i, v):
    return MessageLabels(chatlog_id=1, message_index=i, labels={"x": v},
                         rationales={"x": "r"})


def _ann(values):
    return [AuditRow(key=(1, i), labels={"x": v}, no_label_fits=False)
            for i, v in enumerate(values)]


def test_single_annotator_refuses():
    with pytest.raises(ValueError, match=">= 2"):
        alt_test([_ann([True])], [_model(0, True)])


def test_llm_matching_pool_passes():
    truth = [True, False, True, False, True, False]
    ann1, ann2 = _ann(truth), _ann(truth)
    model = [_model(i, v) for i, v in enumerate(truth)]
    res = alt_test([ann1, ann2], model)
    assert res["passes"] is True
    assert all(a["advantage_prob"] == 1.0 for a in res["per_annotator"])


def test_llm_contradicting_pool_fails():
    truth = [True, False, True, False, True, False]
    ann1, ann2 = _ann(truth), _ann(truth)
    model = [_model(i, not v) for i, v in enumerate(truth)]
    res = alt_test([ann1, ann2], model)
    assert res["passes"] is False
    assert all(a["advantage_prob"] == 0.0 for a in res["per_annotator"])
