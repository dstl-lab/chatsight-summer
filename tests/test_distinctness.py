from src.labeling.distinctness import distinctness_report, overlapping_pairs
from src.labeling.draft import MessageLabels


def _row(i, **labels):
    return MessageLabels(chatlog_id=1, message_index=i,
                         labels=labels,
                         rationales={k: f"reason about thing {k}"
                                     for k in labels})


ROWS = (
    # rider: fires whenever ask fires (8/8) — J(ask, rider) = 8/10
    [_row(i, ask=True, rider=True, rare=False) for i in range(8)]
    + [_row(8, ask=True, rider=False, rare=False),
       _row(9, ask=False, rider=True, rare=False),
       _row(10, ask=False, rider=False, rare=True),
       _row(11, ask=False, rider=False, rare=False)]
)


def test_overlapping_pairs_flags_rider_only():
    pairs = overlapping_pairs(ROWS)
    assert [(a, b) for a, b, *_ in pairs] == [("ask", "rider")]
    a, b, j, both, rat = pairs[0]
    assert abs(j - 0.8) < 1e-9 and both == 8
    assert rat > 0        # identical template rationales overlap


def test_report_lists_prevalence_and_pairs():
    rep = distinctness_report(ROWS)
    assert "ask" in rep and "rare" in rep
    assert "OVERLAPPING PAIRS" in rep
    assert "ask x rider" in rep


def test_report_clean_schema_says_distinct():
    rows = [_row(0, a=True, b=False), _row(1, a=False, b=True)]
    assert "behaviorally distinct" in distinctness_report(rows)
    assert distinctness_report([]).startswith("Distinctness: no labeled")
