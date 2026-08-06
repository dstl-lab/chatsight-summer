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
