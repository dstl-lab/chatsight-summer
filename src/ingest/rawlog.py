"""Raw-log access. The SQL edge is fetch_conversations; everything else is pure.
Read-only: never execute anything but SELECT against the external DB."""
from datetime import datetime
from typing import Callable, Literal

from pydantic import BaseModel
from sqlalchemy import create_engine, text


class Turn(BaseModel):
    index: int
    role: Literal["student", "tutor"]
    text: str
    student_index: int | None = None
    at: datetime | None = None    # event created_at; None in old snapshots
    mode: str = ""                # "tutor" / "chatgpt" for student turns; "" for tutor turns and old snapshots


class Conversation(BaseModel):
    conv_id: str
    chatlog_id: int
    notebook: str | None
    started_at: datetime | None
    turns: list[Turn]

    @property
    def student_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.role == "student"]


def assemble_turns(rows: list[tuple[str, str | None, str | None,
                                    datetime | None, str | None]]) -> list[Turn]:
    turns: list[Turn] = []
    student_idx = 0
    seen_query = False
    for event_type, question, response, created_at, mode in rows:
        if event_type == "tutor_query" and question:
            seen_query = True
            turns.append(Turn(index=len(turns), role="student", text=question,
                              student_index=student_idx, at=created_at,
                              mode=mode or ""))
            student_idx += 1
        elif event_type == "tutor_response" and response and seen_query:
            turns.append(Turn(index=len(turns), role="tutor", text=response,
                              at=created_at))
    return turns


_CONV_SQL = """
SELECT payload->>'conversation_id' AS conv_id,
       MIN(id) AS chatlog_id,
       MAX(payload->>'notebook') AS notebook,
       MIN(created_at) AS started_at
FROM events
WHERE event_type IN ('tutor_query', 'tutor_response')
GROUP BY payload->>'conversation_id'
{having}
ORDER BY chatlog_id
"""

# Date-window filter on conversation start (2026-08-10: needed to target the
# autograder-covered window 2026-03-04..07-31; the earliest conversations
# predate autograder logging, so an undated fetch under-serves sequence
# context). HAVING because started_at is the aggregate MIN(created_at).
_HAVING_WINDOW = ("HAVING MIN(created_at) >= :since"
                  " AND MIN(created_at) < :until")

_TURNS_SQL = """
SELECT event_type, payload->>'question' AS question,
       payload->>'response' AS response, created_at,
       payload->>'mode' AS mode
FROM events
WHERE event_type IN ('tutor_query', 'tutor_response')
  AND payload->>'conversation_id' = :conv_id
ORDER BY id ASC
"""


_COUNT_SQL = (
    "SELECT COUNT(DISTINCT payload->>'conversation_id') FROM events "
    "WHERE event_type IN ('tutor_query', 'tutor_response')"
)


def count_conversations(ext_db_url: str) -> int:
    """Read-only: total distinct conversations available in the DB (no LIMIT).
    Used to compute the true excluded_conversations count for the manifest."""
    engine = create_engine(ext_db_url)
    with engine.connect() as conn:
        return conn.execute(text(_COUNT_SQL)).scalar_one()


def fetch_conversations(ext_db_url: str, limit: int | None = None,
                        on_progress: Callable[[int, int], None] | None = None,
                        since: str | None = None, until: str | None = None
                        ) -> list[Conversation]:
    """since/until (ISO dates, [since, until)) filter on conversation start;
    both or neither — a half-open window keeps the fetch reproducible."""
    if (since is None) != (until is None):
        raise ValueError("since and until must be given together")
    engine = create_engine(ext_db_url)
    having = _HAVING_WINDOW if since is not None else ""
    sql = _CONV_SQL.format(having=having)
    if limit is not None:
        sql += f"\nLIMIT {int(limit)}"
    params = ({"since": since, "until": until} if since is not None else {})
    out: list[Conversation] = []
    with engine.connect() as conn:
        heads = conn.execute(text(sql), params).mappings().all()
        for i, h in enumerate(heads):
            rows = [tuple(r) for r in conn.execute(
                text(_TURNS_SQL), {"conv_id": h["conv_id"]}
            ).fetchall()]
            turns = assemble_turns(rows)
            if turns:
                out.append(Conversation(
                    conv_id=h["conv_id"], chatlog_id=h["chatlog_id"],
                    notebook=h["notebook"], started_at=h["started_at"], turns=turns,
                ))
            if on_progress:
                on_progress(i + 1, len(heads))
    return out
