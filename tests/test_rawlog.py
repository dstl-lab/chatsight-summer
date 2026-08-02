# tests/test_rawlog.py  — all text is invented; never paste real student messages
from src.ingest.rawlog import Conversation, Turn, assemble_turns


ROWS = [
    ("tutor_response", None, "orphan greeting"),   # before first query: dropped
    ("tutor_query", "how do I sort a table?", None),
    ("tutor_response", None, "try .sort()"),
    ("tutor_query", "it errored", None),
    ("tutor_query", "", None),                      # empty: dropped
    ("tutor_response", None, None),                 # null: dropped
]


def test_assemble_turns_roles_and_indices():
    turns = assemble_turns(ROWS)
    assert [(t.role, t.index) for t in turns] == [
        ("student", 0), ("tutor", 1), ("student", 2)
    ]
    assert [t.student_index for t in turns] == [0, None, 1]
    assert turns[0].text == "how do I sort a table?"


def test_conversation_student_turns():
    conv = Conversation(
        conv_id="c1", chatlog_id=7, notebook="hw3", started_at=None,
        turns=assemble_turns(ROWS),
    )
    assert [t.text for t in conv.student_turns] == ["how do I sort a table?", "it errored"]
