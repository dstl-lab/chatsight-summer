from src.eval.audit_sample import build_audit_sample
from src.labeling.draft import MessageLabels


def _row(i, abstained=False):
    return MessageLabels(chatlog_id=1, message_index=i,
                         labels={"x": False}, rationales={"x": "r"},
                         no_label_fits=abstained)


ROWS = [_row(i, abstained=(i < 3)) for i in range(20)]


def test_sample_composition_and_determinism():
    s1 = build_audit_sample(ROWS, n=10, seed=7)
    s2 = build_audit_sample(ROWS, n=10, seed=7)
    assert s1 == s2
    assert len(s1["keys"]) == 10
    strata = list(s1["strata"].values())
    assert strata.count("abstained") >= 1
    assert strata.count("abstained") <= 4          # 40% cap
    assert "random" in strata


def test_excludes_anchored_keys():
    s = build_audit_sample(ROWS, n=10, seed=0,
                           exclude={(1, i) for i in range(10)})
    assert all(k[1] >= 10 for k in s["keys"])


def test_label_samples_strata_and_shuffle():
    from src.eval.audit_sample import build_label_audit_samples
    rows = ([MessageLabels(chatlog_id=1, message_index=i,
                           labels={"x": i < 6, "y": False},
                           rationales={}, no_label_fits=(6 <= i < 8))
             for i in range(20)])
    s = build_label_audit_samples(rows, ["x", "y"], n_per_label=8, seed=3)
    xs = s["x"]["strata"]
    assert sum(1 for v in xs.values() if v == "model-positive") == 4
    assert "abstained-negative" in xs.values()
    assert len(s["x"]["keys"]) == 8
    # y has no positives: all-negative sample still fills the budget
    assert len(s["y"]["keys"]) == 8
    assert "model-positive" not in s["y"]["strata"].values()
    # keys are shuffled, not sorted by stratum
    x_strata_in_order = [xs[k] for k in s["x"]["keys"]]
    assert x_strata_in_order != sorted(x_strata_in_order)
    assert s == build_label_audit_samples(rows, ["x", "y"], 8, seed=3)


def test_sparse_audit_scoring_skips_unaudited_labels():
    from src.eval.validation import AuditRow, confusion
    model = [MessageLabels(chatlog_id=1, message_index=i,
                           labels={"x": True}, rationales={})
             for i in range(4)]
    audit = [AuditRow(key=(1, 0), labels={"x": True}),
             AuditRow(key=(1, 1), labels={"x": False}),
             AuditRow(key=(1, 2), labels={}),          # x not audited here
             AuditRow(key=(1, 3), labels={"other": True})]
    c = confusion(audit, model, "x")
    assert c.n == 2 and (c.tp, c.fp) == (1, 1)


def test_entropy_stratum_prioritized():
    ent = {(1, 15): {"max_entropy": 1.0}, (1, 16): {"max_entropy": 0.9},
           (1, 17): {"max_entropy": 0.0}}
    s = build_audit_sample(ROWS, n=8, seed=0, entropies=ent)
    assert s["strata"][(1, 15)] == "high-entropy"
    assert s["strata"][(1, 16)] == "high-entropy"
    assert s["strata"].get((1, 17)) != "high-entropy"   # zero entropy
