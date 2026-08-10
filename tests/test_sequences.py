from datetime import datetime

from src.ingest.sequences import ConversationSequence, classify, render_report


def test_autograder_run_ordering_contract():
    from src.ingest.sequences import AutograderRun
    r = AutograderRun(at=datetime(2026, 5, 1, 10, 0), grader_id="q1_1",
                      success=False)
    assert r.grader_id == "q1_1" and r.success is False


def test_merge_flags_present_true_present_false_absent():
    from src.ingest.sequences import _merge_flags
    conv_ids = ["c1", "c2", "c3"]
    rows = [("c1", True), ("c2", False)]
    flags = _merge_flags(conv_ids, rows)
    assert flags == {"c1": True, "c2": False, "c3": False}


def test_classify_covers_all_patterns():
    assert classify(None, False, False) == ("ask-first", "no-run-after")
    assert classify("false", True, True) == ("fail-then-ask", "quick-pass")
    assert classify("true", False, True) == ("pass-then-ask", "fail-after")
    assert classify("true", True, True) == ("pass-then-ask", "quick-pass")


def test_render_report_aggregates_only():
    seqs = [ConversationSequence("c1", "ask-first", "no-run-after", 3),
            ConversationSequence("c2", "fail-then-ask", "quick-pass", 5),
            ConversationSequence("c3", "fail-then-ask", "quick-pass", 2)]
    r = render_report(seqs)
    assert "conversations with student+notebook: 3" in r
    assert "fail-then-ask" in r and "(67%)" in r
    # nothing resembling an email or message text in the report
    assert "@" not in r


def test_chunks_partitioning():
    from src.ingest.sequences import _chunks
    assert _chunks(list(range(25)), 10) == [list(range(10)),
                                            list(range(10, 20)),
                                            list(range(20, 25))]
    assert _chunks([], 10) == []
