"""Raw-log access. The SQL edge is fetch_conversations; everything else is pure.
Read-only: never execute anything but SELECT against the external DB."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import create_engine, text


class Turn(BaseModel):
    index: int
    role: Literal["student", "tutor"]
    text: str
    student_index: int | None = None


class Conversation(BaseModel):
    conv_id: str
    chatlog_id: int
    notebook: str | None
    started_at: datetime | None
    turns: list[Turn]

    @property
    def student_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.role == "student"]


def assemble_turns(rows: list[tuple[str, str | None, str | None]]) -> list[Turn]:
    turns: list[Turn] = []
    student_idx = 0
    seen_query = False
    for event_type, question, response in rows:
        if event_type == "tutor_query" and question:
            seen_query = True
            turns.append(Turn(index=len(turns), role="student", text=question,
                              student_index=student_idx))
            student_idx += 1
        elif event_type == "tutor_response" and response and seen_query:
            turns.append(Turn(index=len(turns), role="tutor", text=response))
    return turns


_CONV_SQL = """
SELECT payload->>'conversation_id' AS conv_id,
       MIN(id) AS chatlog_id,
       MAX(payload->>'notebook') AS notebook,
       MIN(created_at) AS started_at
FROM events
WHERE event_type IN ('tutor_query', 'tutor_response')
GROUP BY payload->>'conversation_id'
ORDER BY chatlog_id
"""

_TURNS_SQL = """
SELECT event_type, payload->>'question' AS question, payload->>'response' AS response
FROM events
WHERE event_type IN ('tutor_query', 'tutor_response')
  AND payload->>'conversation_id' = :conv_id
ORDER BY id ASC
"""


def fetch_conversations(ext_db_url: str, limit: int | None = None) -> list[Conversation]:
    engine = create_engine(ext_db_url)
    sql = _CONV_SQL + (f"\nLIMIT {int(limit)}" if limit is not None else "")
    out: list[Conversation] = []
    with engine.connect() as conn:
        heads = conn.execute(text(sql)).mappings().all()
        for h in heads:
            rows = [tuple(r) for r in conn.execute(
                text(_TURNS_SQL), {"conv_id": h["conv_id"]}
            ).fetchall()]
            turns = assemble_turns(rows)
            if turns:
                out.append(Conversation(
                    conv_id=h["conv_id"], chatlog_id=h["chatlog_id"],
                    notebook=h["notebook"], started_at=h["started_at"], turns=turns,
                ))
    return out
