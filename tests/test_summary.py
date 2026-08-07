"""Hermetic tests for the done-screen summary. All text invented; no student
data. Conversations get synthetic started_at dates so week binning is testable
(the shared CONVS fixture is undated on purpose)."""
from datetime import datetime, timedelta

from src.ingest.rawlog import Conversation, Turn
from src.labeling.draft import MessageLabels
from src.labeling.summary import compute_summary, sample_examples


def _conv(conv_id: str, chatlog_id: int, n_student: int,
          started_at: datetime | None) -> Conversation:
    turns = []
    for i in range(n_student):
        turns.append(Turn(index=2 * i, role="student",
                          text=f"{conv_id} q{i}", student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"{conv_id} a{i}"))
    return Conversation(conv_id=conv_id, chatlog_id=chatlog_id, notebook=None,
                        started_at=started_at, turns=turns)


T0 = datetime(2026, 4, 6)
CONVS = [
    _conv("a", 1, 2, T0),                       # week 0
    _conv("b", 2, 3, T0 + timedelta(days=8)),   # week 1
    _conv("c", 3, 2, T0 + timedelta(days=22)),  # week 3
    _conv("d", 4, 1, None),                     # undated
]


def _ml(chatlog_id: int, message_index: int, **labels: bool) -> MessageLabels:
    names = ["confused", "frustrated"]
    full = {n: labels.get(n, False) for n in names}
    return MessageLabels(chatlog_id=chatlog_id, message_index=message_index,
                        labels=full,
                        rationales={n: f"r-{n}" for n in full})


LABELED = [
    _ml(1, 0, confused=True),
    _ml(1, 2, confused=True, frustrated=True),
    _ml(2, 0),
    _ml(2, 2, frustrated=True),
    _ml(2, 4),
    _ml(3, 0, confused=True),
    _ml(3, 2),
    _ml(4, 0),
]


class FakeLabel:
    def __init__(self, name): self.name = name


class FakeSchema:
    labels = [FakeLabel("confused"), FakeLabel("frustrated")]


def test_totals():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    assert s["totals"] == {
        "messages": 8, "conversations": 4, "with_label": 4,
        "labels_per_labeled": 1.2,   # 5 applications / 4 labeled messages
    }


def test_per_label_counts_shares_and_example_shape():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    assert [p["name"] for p in s["per_label"]] == ["confused", "frustrated"]
    confused = s["per_label"][0]
    assert confused["count"] == 3
    assert confused["share"] == 3 / 8
    ex = confused["example"]
    assert set(ex) == {"text", "rationale", "conv", "week"}
    assert ex["rationale"] == "r-confused"
    assert ex["text"].endswith(("q0", "q1", "q2"))  # a real student text


def test_per_label_example_none_when_label_never_applies():
    class S:
        labels = [FakeLabel("confused"), FakeLabel("never")]
    labeled = [MessageLabels(chatlog_id=1, message_index=0,
                             labels={"confused": True, "never": False},
                             rationales={"confused": "r", "never": "r"})]
    s = compute_summary(CONVS, labeled, S(), seed=0)
    never = s["per_label"][1]
    assert never["count"] == 0 and never["example"] is None


def test_sample_examples_seeded_and_random_not_topn():
    a = sample_examples(CONVS, LABELED, "confused", n=2, seed=7)
    b = sample_examples(CONVS, LABELED, "confused", n=2, seed=7)
    c = sample_examples(CONVS, LABELED, "confused", n=2, seed=8)
    assert a == b                      # same seed -> same sample
    assert len(a) == 2
    assert a != c or sample_examples(CONVS, LABELED, "confused", n=3, seed=8) \
        != sample_examples(CONVS, LABELED, "confused", n=3, seed=7)
    # n larger than the positive pool returns all positives, no repeats
    all_ex = sample_examples(CONVS, LABELED, "confused", n=99, seed=0)
    assert len(all_ex) == 3
    assert len({e["text"] for e in all_ex}) == 3


def test_sample_examples_week_from_conversation_date():
    ex = sample_examples(CONVS, LABELED, "frustrated", n=99, seed=0)
    weeks = {e["conv"]: e["week"] for e in ex}
    assert weeks[1] == 0 and weeks[2] == 1   # chatlog 1 wk0, chatlog 2 wk1


def test_weekly_series_and_undated_count():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    w = s["weekly"]
    assert w is not None
    assert w["weeks"] == [0, 1, 3]
    assert w["undated"] == 1                      # conv d has no date
    # week 0 = conv a: 2 messages, confused on both -> share 1.0
    assert w["series"]["confused"] == [1.0, 0.0, 0.5]
    # week 1 = conv b: 3 messages, frustrated on one -> 1/3
    assert abs(w["series"]["frustrated"][1] - 1 / 3) < 1e-9


def test_weekly_none_when_span_too_short():
    convs = [_conv("a", 1, 2, T0), _conv("b", 2, 3, T0 + timedelta(days=8))]
    labeled = [r for r in LABELED if r.chatlog_id in (1, 2)]
    s = compute_summary(convs, labeled, FakeSchema(), seed=0)
    assert s["weekly"] is None and s["largest_jump"] is None


def test_top_pairs():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    assert s["top_pairs"] == [
        {"a": "confused", "b": "frustrated", "share": 1 / 8}]


def test_coverage_bins_zero_conversations_and_examples():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    cov = s["coverage"]
    # conv a: 2 labeled msgs, b: 1, c: 1, d: 0
    assert cov["bins"][0] == 1 and cov["bins"][1] == 2 and cov["bins"][2] == 1
    assert sum(cov["bins"]) == 4
    assert cov["zero_conversations"] == 1
    assert cov["zero_examples"] == [{"text": "d q0", "conv": 4}]


def test_coverage_binning_caps_at_15():
    conv = _conv("big", 9, 20, T0)
    labeled = [_ml(9, 2 * i, confused=True) for i in range(20)]
    s = compute_summary([conv], labeled, FakeSchema(), seed=0)
    assert s["coverage"]["bins"][15] == 1


def test_coverage_reports_abstained_pile():
    labeled = [
        _ml(1, 0, confused=True),
        MessageLabels(chatlog_id=1, message_index=2,
                     labels={"confused": False, "frustrated": False},
                     rationales={"confused": "r", "frustrated": "r"},
                     no_label_fits=True, coverage_note="asks about grades"),
    ]
    s = compute_summary(CONVS, labeled, FakeSchema(), seed=0)
    cov = s["coverage"]
    assert cov["abstained"] == 1
    ex = cov["abstained_examples"][0]
    assert ex == {"text": "a q1", "conv": 1, "note": "asks about grades"}


def test_largest_jump():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    # confused: [1.0, 0.0, 0.5] over weeks [0, 1, 3] -> only the 0->1
    # transition is adjacent (1->3 spans a gap and is ineligible), so the
    # biggest ELIGIBLE |delta| is week 1, -1.0.
    assert s["largest_jump"] == {"label": "confused", "week": 1, "delta": -1.0}


def test_largest_jump_skips_gap_spanning_delta_for_smaller_adjacent_one():
    """weeks = [0, 1, 4]: the raw largest delta (frustrated, week 4, +1.0,
    or confused, week 4, -0.6) spans the 1->4 gap (diff=3) and must be
    skipped; only the smaller 0->1 adjacent delta (confused, +0.1) is
    eligible, so it wins even though it is not the biggest raw change."""
    convs = [
        _conv("a", 1, 2, T0),                        # week 0
        _conv("b", 2, 5, T0 + timedelta(days=8)),    # week 1
        _conv("c", 3, 2, T0 + timedelta(days=29)),   # week 4
    ]
    labeled = [
        _ml(1, 0, confused=True),                     # wk0 confused: 1/2
        _ml(1, 2),
        _ml(2, 0, confused=True),                      # wk1 confused: 3/5
        _ml(2, 2, confused=True),
        _ml(2, 4, confused=True),
        _ml(2, 6),
        _ml(2, 8),
        _ml(3, 0, frustrated=True),                    # wk4 frustrated: 2/2
        _ml(3, 2, frustrated=True),
    ]
    s = compute_summary(convs, labeled, FakeSchema(), seed=0)
    assert s["weekly"]["weeks"] == [0, 1, 4]
    assert s["weekly"]["series"]["confused"] == [0.5, 0.6, 0.0]
    assert s["weekly"]["series"]["frustrated"] == [0.0, 0.0, 1.0]
    assert s["largest_jump"] == {
        "label": "confused", "week": 1, "delta": round(0.6 - 0.5, 4)}
