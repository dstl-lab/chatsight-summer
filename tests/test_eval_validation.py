import math

from src.eval.validation import (AuditRow, confusion, corrected_prevalence,
                                 kappa, validation_table)
from src.labeling.draft import MessageLabels


def _model(i, **labels):
    return MessageLabels(chatlog_id=1, message_index=i, labels=labels,
                         rationales={k: "r" for k in labels})


def _audit(i, **labels):
    return AuditRow(key=(1, i), labels=labels, no_label_fits=False)


# 10 audited messages, one label "x":
#   human True on 0-3 (4), model True on 0-2 and 5-6 -> tp=3 fp=2 fn=1 tn=4
MODEL = ([_model(i, x=True) for i in (0, 1, 2, 5, 6)]
         + [_model(i, x=False) for i in (3, 4, 7, 8, 9)])
AUDIT = ([_audit(i, x=True) for i in (0, 1, 2, 3)]
         + [_audit(i, x=False) for i in (4, 5, 6, 7, 8, 9)])


def test_confusion_counts():
    c = confusion(AUDIT, MODEL, "x")
    assert (c.tp, c.fp, c.fn, c.tn) == (3, 2, 1, 4)
    assert c.support == 4
    assert math.isclose(c.precision, 3 / 5)
    assert math.isclose(c.recall, 3 / 4)
    assert math.isclose(c.specificity, 4 / 6)
    assert math.isclose(c.agreement, 7 / 10)


def test_kappa_matches_hand_computation():
    c = confusion(AUDIT, MODEL, "x")
    po = 0.7
    pyes = (5 / 10) * (4 / 10)
    pno = (5 / 10) * (6 / 10)
    pe = pyes + pno
    assert math.isclose(kappa(c), (po - pe) / (1 - pe))


def test_corrected_prevalence_rogan_gladen():
    c = confusion(AUDIT, MODEL, "x")
    raw = 5 / 10                      # model prevalence
    sens, spec = 3 / 4, 4 / 6
    expected = (raw + spec - 1) / (sens + spec - 1)
    assert math.isclose(corrected_prevalence(c), expected)
    # degenerate classifier (sens+spec == 1) -> None, never a number
    degenerate = confusion(
        [_audit(0, x=True), _audit(1, x=False)],
        [_model(0, x=False), _model(1, x=True)], "x")
    assert corrected_prevalence(degenerate) is None


def test_validation_table_renders_all_labels_and_flags_chance():
    # add a label where the model is at chance agreement with the human
    model = [r.model_copy(update={"labels": {**r.labels,
                                             "coin": r.message_index % 2 == 0}})
             for r in MODEL]
    audit = [AuditRow(key=a.key,
                      labels={**a.labels, "coin": a.key[1] < 5},
                      no_label_fits=False) for a in AUDIT]
    table = validation_table(audit, model)
    assert "x" in table and "coin" in table
    assert "recall" in table.lower()
    assert "≈ chance" in table          # LACA move: flag guessing labels
    assert "corrected prev" in table.lower()
