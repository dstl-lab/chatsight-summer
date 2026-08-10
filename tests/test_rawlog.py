# tests/test_rawlog.py  — all text is invented; never paste real student messages
from datetime import datetime, timezone

from src.ingest.rawlog import Conversation, Turn, assemble_turns, _COUNT_SQL


def _ts(minute):
    return datetime(2026, 8, 7, 10, minute, tzinfo=timezone.utc)


ROWS = [
    ("tutor_response", None, "orphan greeting", _ts(0), None),  # before first query: dropped
    ("tutor_query", "how do I sort a table?", None, _ts(1), "tutor"),
    ("tutor_response", None, "try .sort()", _ts(2), None),
    ("tutor_query", "it errored", None, _ts(5), "chatgpt"),
    ("tutor_query", "", None, _ts(6), None),                    # empty: dropped
    ("tutor_response", None, None, _ts(7), None),               # null: dropped
]


def test_assemble_turns_roles_and_indices():
    turns = assemble_turns(ROWS)
    assert [(t.role, t.index) for t in turns] == [
        ("student", 0), ("tutor", 1), ("student", 2)
    ]
    assert [t.student_index for t in turns] == [0, None, 1]
    assert turns[0].text == "how do I sort a table?"


def test_assemble_turns_carries_timestamps():
    turns = assemble_turns(ROWS)
    assert turns[0].at == _ts(1)
    assert turns[1].at == _ts(2)
    assert turns[2].at == _ts(5)


def test_turn_timestamp_defaults_for_old_snapshots():
    t = Turn(index=0, role="student", text="x", student_index=0)
    assert t.at is None


def test_count_conversations_sql_is_select_only():
    # count_conversations must never mutate the external DB: assert its SQL
    # is a single SELECT COUNT(DISTINCT ...) over the same event types used
    # by fetch_conversations, with no other statement present.
    normalized = " ".join(_COUNT_SQL.split()).upper()
    assert normalized.startswith("SELECT COUNT(DISTINCT PAYLOAD->>'CONVERSATION_ID')")
    assert "FROM EVENTS" in normalized
    assert "TUTOR_QUERY" in normalized and "TUTOR_RESPONSE" in normalized
    assert normalized.count("SELECT") == 1
    for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", ";"):
        assert forbidden not in normalized


def test_student_turns_carry_mode():
    rows = [("tutor_query", "q text", None, _ts(1), "chatgpt"),
            ("tutor_response", None, "r text", _ts(2), None)]
    turns = assemble_turns(rows)
    assert turns[0].mode == "chatgpt"
    assert turns[1].mode == ""            # tutor turns: no mode


def test_conversation_student_turns():
    conv = Conversation(
        conv_id="c1", chatlog_id=7, notebook="hw3", started_at=None,
        turns=assemble_turns(ROWS),
    )
    assert [t.text for t in conv.student_turns] == ["how do I sort a table?", "it errored"]


def test_fetch_conversations_window_args_must_pair():
    import pytest

    from src.ingest.rawlog import fetch_conversations
    with pytest.raises(ValueError, match="together"):
        fetch_conversations("postgresql://unused", since="2026-03-04",
                            until=None)


def test_conv_sql_window_renders_having():
    from src.ingest.rawlog import _CONV_SQL, _HAVING_WINDOW
    windowed = _CONV_SQL.format(having=_HAVING_WINDOW)
    assert "HAVING MIN(created_at) >= :since" in windowed
    assert windowed.index("HAVING") < windowed.index("ORDER BY")
    plain = _CONV_SQL.format(having="")
    assert "HAVING" not in plain
