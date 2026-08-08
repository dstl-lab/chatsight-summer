# tests/test_rawlog.py  — all text is invented; never paste real student messages
from datetime import datetime, timezone

from src.ingest.rawlog import Conversation, Turn, assemble_turns, _COUNT_SQL


def _ts(minute):
    return datetime(2026, 8, 7, 10, minute, tzinfo=timezone.utc)


ROWS = [
    ("tutor_response", None, "orphan greeting", _ts(0)),  # before first query: dropped
    ("tutor_query", "how do I sort a table?", None, _ts(1)),
    ("tutor_response", None, "try .sort()", _ts(2)),
    ("tutor_query", "it errored", None, _ts(5)),
    ("tutor_query", "", None, _ts(6)),                    # empty: dropped
    ("tutor_response", None, None, _ts(7)),               # null: dropped
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


def test_conversation_student_turns():
    conv = Conversation(
        conv_id="c1", chatlog_id=7, notebook="hw3", started_at=None,
        turns=assemble_turns(ROWS),
    )
    assert [t.text for t in conv.student_turns] == ["how do I sort a table?", "it errored"]
