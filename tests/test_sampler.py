from src.ingest.rawlog import Conversation, Turn
from src.labeling.sampler import stratified_sample


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


def test_context_is_adjacent_tutor_turns():
    sample = stratified_sample(CONVS, n=8, seed=7)
    m = next(m for m in sample if m.conv_id == "c" and m.message_index > 0)
    assert m.context_before is not None and m.context_before.startswith("c a")


def test_no_duplicate_messages():
    sample = stratified_sample(CONVS, n=30, seed=0)  # n > population is fine
    keys = [(m.conv_id, m.message_index) for m in sample]
    assert len(keys) == len(set(keys))
