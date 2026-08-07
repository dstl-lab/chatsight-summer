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
