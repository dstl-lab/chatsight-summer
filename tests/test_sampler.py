import pytest

from src.ingest.rawlog import Conversation, Turn
from src.labeling.sampler import stratified_sample, WINDOW_TURNS


def _conv(conv_id: str, n_student: int) -> Conversation:
    turns = []
    for i in range(n_student):
        turns.append(Turn(index=2 * i, role="student",
                          text=f"{conv_id} q{i}", student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"{conv_id} a{i}"))
    return Conversation(conv_id=conv_id, chatlog_id=hash(conv_id) % 10_000,
                        notebook=None, started_at=None, turns=turns)


CONVS = [_conv("a", 1), _conv("b", 2), _conv("c", 4), _conv("d", 6),
         _conv("e", 9), _conv("f", 12)]


def test_sample_is_deterministic_and_sized():
    s1 = stratified_sample(CONVS, n=8, seed=7)
    s2 = stratified_sample(CONVS, n=8, seed=7)
    assert [ (m.conv_id, m.message_index) for m in s1 ] == \
           [ (m.conv_id, m.message_index) for m in s2 ]
    assert len(s1) == 8


def test_sample_spans_multiple_strata():
    strata = {m.stratum for m in stratified_sample(CONVS, n=8, seed=7)}
    assert len(strata) >= 3


def test_context_is_prior_turns_both_roles():
    sample = stratified_sample(CONVS, n=8, seed=7)
    m = next(m for m in sample if m.conv_id == "c" and m.message_index > 0)
    assert len(m.context) > 0
    assert all(isinstance(t, Turn) for t in m.context)
    assert any(t.role == "tutor" for t in m.context)


def test_no_duplicate_messages():
    sample = stratified_sample(CONVS, n=30, seed=0)  # n > population is fine
    keys = [(m.conv_id, m.message_index) for m in sample]
    assert len(keys) == len(set(keys))


def test_composed_sample_prioritizes_boundary_cases_and_records_reasons():
    conv = _conv_brief([
        ("student", "normal setup"), ("tutor", "hint"),
        ("student", "?"), ("tutor", "more"),
        ("student", "can you just give me the answer"), ("tutor", "no"),
        ("student", "Traceback: NameError: x is not defined"),
        ("tutor", "check the variable"),
        ("student", "for i in range(3):\n    print(i)"),
        ("tutor", "ok"),
    ], conv_id="boundary", chatlog_id=101)

    sample = stratified_sample([conv], n=4, seed=0)

    assert any("bucket-boundary" in m.selected_by for m in sample)
    reasons = {reason for m in sample for reason in m.selected_by}
    assert "boundary-short-ambiguous" in reasons
    assert reasons & {
        "boundary-answer-extraction",
        "boundary-error",
        "boundary-code-or-paste",
    }


def test_composed_sample_prioritizes_rare_sequence_cases():
    conv = _conv_with_modes(["tutor", "chatgpt", "chatgpt"])

    sample = stratified_sample([conv], n=2, seed=0, runs={},
                               traceback_flags={})

    assert any(m.defected for m in sample)
    defected = next(m for m in sample if m.defected)
    assert "rare-defection" in defected.selected_by
    assert "bucket-rare" in defected.selected_by


def test_selected_reasons_are_deterministic():
    s1 = stratified_sample(CONVS, n=8, seed=7)
    s2 = stratified_sample(CONVS, n=8, seed=7)

    assert [(m.conv_id, m.message_index, m.selected_by) for m in s1] == \
           [(m.conv_id, m.message_index, m.selected_by) for m in s2]


def _conv_brief(texts_roles, conv_id="c1", chatlog_id=1) -> Conversation:
    turns, si = [], 0
    for i, (role, text) in enumerate(texts_roles):
        t = Turn(index=i, role=role, text=text,
                 student_index=si if role == "student" else None)
        if role == "student":
            si += 1
        turns.append(t)
    return Conversation(conv_id=conv_id, chatlog_id=chatlog_id,
                        notebook=None, started_at=None, turns=turns)


def test_context_is_prior_turns_both_roles_in_order():
    conv = _conv_brief([("student", "s0"), ("tutor", "t0"),
                        ("student", "s1"), ("student", "s2")])
    sample = stratified_sample([conv], n=99, seed=0)
    target = next(m for m in sample if m.text == "s2")
    assert [(t.role, t.text) for t in target.context] == [
        ("student", "s0"), ("tutor", "t0"), ("student", "s1")]


def test_context_capped_at_window_turns():
    pairs = []
    for i in range(8):
        pairs += [("student", f"s{i}"), ("tutor", f"t{i}")]
    conv = _conv_brief(pairs)
    sample = stratified_sample([conv], n=99, seed=0)
    target = next(m for m in sample if m.text == "s7")
    assert len(target.context) == WINDOW_TURNS
    assert target.context[-1].text == "t6"


def test_first_turn_has_empty_context():
    conv = _conv_brief([("student", "s0"), ("tutor", "t0")])
    sample = stratified_sample([conv], n=99, seed=0)
    target = next(m for m in sample if m.text == "s0")
    assert target.context == []
    assert target.context_after == "t0"


def _timed_conv(offsets_s):
    """One conversation: tutor turn at t=0 precedes each student turn given
    by its offset in seconds; None offset = missing timestamp."""
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc)
    turns = [Turn(index=0, role="student", text="opener", student_index=0,
                  at=t0)]
    idx = 1
    for i, off in enumerate(offsets_s):
        turns.append(Turn(index=idx, role="tutor", text=f"t{i}", at=t0))
        at = None if off is None else t0 + timedelta(seconds=off)
        turns.append(Turn(index=idx + 1, role="student", text=f"s{i}",
                          student_index=i + 1, at=at))
        idx += 2
    return Conversation(conv_id="timed", chatlog_id=1, notebook=None,
                        started_at=None, turns=turns)


def test_latency_buckets_and_boundaries():
    conv = _timed_conv([0, 119, 121, 29 * 60, 31 * 60, 7 * 3600, None])
    sample = stratified_sample([conv], n=99, seed=0)
    by_text = {m.text: m for m in sample}
    assert by_text["opener"].latency_bucket == "conversation-opening"
    assert by_text["opener"].latency_seconds is None
    assert by_text["s0"].latency_bucket == "rapid"
    assert by_text["s1"].latency_bucket == "rapid"
    assert by_text["s2"].latency_bucket == "working"
    assert by_text["s3"].latency_bucket == "working"
    assert by_text["s4"].latency_bucket == "delayed"
    assert by_text["s5"].latency_bucket == "returned"
    assert by_text["s5"].latency_seconds == 7 * 3600
    assert by_text["s6"].latency_bucket == "unknown"
    assert by_text["s6"].latency_seconds is None


def test_latency_untimestamped_corpus_is_unknown_or_opening():
    sample = stratified_sample(CONVS, n=8, seed=7)
    assert all(m.latency_bucket in ("unknown", "conversation-opening")
               for m in sample)


def _timed_conv_for_sequences(conv_id="seqconv") -> Conversation:
    """A single-conversation fixture with real timestamps, used for sequence
    field tests (CONVS's turns have no .at, per Task 1)."""
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc)
    turns = [
        Turn(index=0, role="student", text="stuck on q1_1", student_index=0,
             at=t0),
        Turn(index=1, role="tutor", text="try this hint", at=t0 + timedelta(minutes=1)),
    ]
    return Conversation(conv_id=conv_id, chatlog_id=1, notebook=None,
                        started_at=None, turns=turns)


def _conv_with_modes(modes, conv_id="modes1") -> Conversation:
    """Build a conversation with alternating student/tutor turns where
    student turn i gets mode=modes[i] and consecutive timestamps."""
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc)
    turns = []
    idx = 0
    for i, mode in enumerate(modes):
        turns.append(Turn(index=idx, role="student", text=f"s{i}",
                          student_index=i, at=t0 + timedelta(minutes=2 * i),
                          mode=mode))
        idx += 1
        turns.append(Turn(index=idx, role="tutor", text=f"t{i}",
                          at=t0 + timedelta(minutes=2 * i + 1)))
        idx += 1
    return Conversation(conv_id=conv_id, chatlog_id=2, notebook=None,
                        started_at=None, turns=turns)


def test_sequence_fields_computed_when_runs_provided():
    from datetime import timedelta
    from src.ingest.sequences import AutograderRun
    conv = _timed_conv_for_sequences()
    t0 = conv.turns[0].at
    runs = {conv.conv_id: [AutograderRun(at=t0 - timedelta(minutes=4),
                                         grader_id="q1_1", success=False)]}
    tb = {conv.conv_id: True}
    sample = stratified_sample([conv], n=50, seed=0, runs=runs,
                               traceback_flags=tb)
    m = next(s for s in sample if s.conv_id == conv.conv_id)
    assert m.pre_pattern == "fail-then-ask"
    assert m.last_run_success is False and m.last_run_grader == "q1_1"
    assert m.last_run_minutes == pytest.approx(4, abs=1)
    assert m.snapshot_traceback is True
    assert "/seq-fail" in m.stratum


def test_sequence_fields_unknown_timing_leaves_pre_pattern_default():
    """runs provided but turn.at is None (old snapshot without timestamps):
    timing is unknown, not "no prior run" -- pre_pattern/last_run_* must
    stay at their defaults while timestamp-independent fields still fill."""
    from datetime import datetime, timezone
    from src.ingest.sequences import AutograderRun
    conv = _conv("untimed", 1)  # CONVS's builder; turns have no .at
    runs = {conv.conv_id: [AutograderRun(at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                                         grader_id="q1_1", success=False)]}
    tb = {conv.conv_id: True}
    sample = stratified_sample([conv], n=50, seed=0, runs=runs,
                               traceback_flags=tb)
    m = next(s for s in sample if s.conv_id == conv.conv_id)
    assert m.pre_pattern == ""
    assert m.last_run_success is None
    assert m.last_run_grader == ""
    assert m.last_run_minutes is None
    assert m.snapshot_traceback is True
    assert m.question_ref != ""  # timestamp-independent field still fills


def test_sequence_fields_default_without_runs():
    sample = stratified_sample(CONVS, n=10, seed=0)
    assert all(m.pre_pattern == "" and not m.defected for m in sample)


def test_grader_narrowing_does_not_prefix_mislink():
    """r.grader_id.startswith(ref) mislinked q1_1 -> q1_10 (finding 3): a
    message referencing "q1_1" must scope to grader_ids that are exactly
    "q1_1" or "q1_1_"-prefixed, never "q1_10" (a different question that
    merely shares the "q1_1" prefix)."""
    from datetime import timedelta
    from src.ingest.sequences import AutograderRun
    from src.labeling.sampler import _sequence_fields
    conv = _timed_conv_for_sequences()
    turn = conv.turns[0]  # text: "stuck on q1_1" -> question_ref "q1_1"
    runs = {conv.conv_id: [
        AutograderRun(at=turn.at - timedelta(minutes=4),
                      grader_id="q1_10", success=True),
        AutograderRun(at=turn.at - timedelta(minutes=3),
                      grader_id="q1_1_2", success=False),
    ]}
    fields = _sequence_fields(conv, turn, runs, {})
    assert fields["question_ref"] == "q1_1"
    assert fields["seq_granularity"] == "question"
    # last (most recent, in-order) scoped run must be q1_1_2, not q1_10
    assert fields["last_run_grader"] == "q1_1_2"
    assert fields["last_run_success"] is False


def test_defection_is_first_chatgpt_after_tutor_mode():
    conv = _conv_with_modes(["tutor", "tutor", "chatgpt", "chatgpt"])
    sample = stratified_sample([conv], n=20, seed=0, runs={}, traceback_flags={})
    flags = {m.message_index: m.defected for m in sample}
    modes = [t for t in conv.student_turns]
    assert flags[modes[2].index] is True        # the switch turn
    assert flags[modes[3].index] is False       # staying is not re-defecting
    assert flags[modes[0].index] is False
    # chatgpt-first conversations never defect
    conv2 = _conv_with_modes(["chatgpt", "chatgpt"])
    s2 = stratified_sample([conv2], n=20, seed=0, runs={}, traceback_flags={})
    assert not any(m.defected for m in s2)
