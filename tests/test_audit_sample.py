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


def test_entropy_stratum_prioritized():
    ent = {(1, 15): {"max_entropy": 1.0}, (1, 16): {"max_entropy": 0.9},
           (1, 17): {"max_entropy": 0.0}}
    s = build_audit_sample(ROWS, n=8, seed=0, entropies=ent)
    assert s["strata"][(1, 15)] == "high-entropy"
    assert s["strata"][(1, 16)] == "high-entropy"
    assert s["strata"].get((1, 17)) != "high-entropy"   # zero entropy
