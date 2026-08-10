"""Behavioral-sequence extraction pilot (2026-08-09 memo follow-up).

Lives in src/ingest/ because it reads the raw-log DB through the tunnel —
rule 3 puts the live-DB boundary here; trajectories/ consumes snapshots
only. Output is aggregate pattern counts and per-conversation pattern
tuples keyed by conversation_id — never student text, never emails.

Sequence model (memo: docs/2026-08-09-behavioral-sequences-vs-message-labels.md):
for each tutor conversation (student x notebook), bracket it with the same
student's autograder events on the same notebook:

  pre-chat  : ask-first | fail-then-ask | pass-then-ask
  outcome   : quick-pass | fail-after | no-run-after

Known granularity limit: the join is notebook-level, not question-level
(tutor_query payloads carry no question id), so pass-then-ask includes
"passing q1 while asking about q3". Question-level linkage needs either
grader_id inference from chat text or new instrumentation.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy as sa

BEFORE_MIN = 45      # attempt window before the first student message
OUTCOME_MIN = 20     # outcome window after the last tutor message

_SQL = """
WITH convs AS (
  SELECT payload->>'conversation_id' AS conv_id,
         user_email,
         payload->>'notebook' AS notebook,
         min(created_at) AS t0,
         max(created_at) AS t1,
         count(*) AS n_msgs
  FROM events
  WHERE event_type = 'tutor_query'
    AND user_email IS NOT NULL
    AND payload->>'notebook' IS NOT NULL
  GROUP BY 1, 2, 3
),
before_run AS (
  SELECT c.conv_id, (
    SELECT a.payload->>'success'
    FROM events a
    WHERE a.event_type = 'autograder_info'
      AND a.user_email = c.user_email
      AND a.payload->>'notebook' = c.notebook
      AND a.created_at BETWEEN c.t0 - make_interval(mins => :before) AND c.t0
    ORDER BY a.created_at DESC LIMIT 1) AS last_before
  FROM convs c
),
after_run AS (
  SELECT c.conv_id,
    EXISTS (
      SELECT 1 FROM events a
      WHERE a.event_type = 'autograder_info'
        AND a.user_email = c.user_email
        AND a.payload->>'notebook' = c.notebook
        AND a.created_at BETWEEN c.t1 AND c.t1 + make_interval(mins => :after)
        AND a.payload->>'success' = 'true') AS passed_after,
    EXISTS (
      SELECT 1 FROM events a
      WHERE a.event_type = 'autograder_info'
        AND a.user_email = c.user_email
        AND a.payload->>'notebook' = c.notebook
        AND a.created_at BETWEEN c.t1 AND c.t1 + make_interval(mins => :after)
    ) AS any_after
  FROM convs c
)
SELECT c.conv_id, b.last_before, a.passed_after, a.any_after, c.n_msgs
FROM convs c
JOIN before_run b USING (conv_id)
JOIN after_run a USING (conv_id)
"""


@dataclass(frozen=True)
class ConversationSequence:
    conv_id: str
    pre: str        # ask-first | fail-then-ask | pass-then-ask
    outcome: str    # quick-pass | fail-after | no-run-after
    n_messages: int


def classify(last_before: str | None, passed_after: bool,
             any_after: bool) -> tuple[str, str]:
    pre = ("ask-first" if last_before is None
           else "fail-then-ask" if last_before == "false"
           else "pass-then-ask")
    outcome = ("quick-pass" if passed_after
               else "fail-after" if any_after
               else "no-run-after")
    return pre, outcome


def extract_sequences(ext_db_url: str,
                      before_min: int = BEFORE_MIN,
                      outcome_min: int = OUTCOME_MIN
                      ) -> list[ConversationSequence]:
    eng = sa.create_engine(ext_db_url)
    with eng.connect() as c:
        rows = c.execute(sa.text(_SQL), {"before": before_min,
                                         "after": outcome_min}).fetchall()
    out = []
    for conv_id, last_before, passed_after, any_after, n_msgs in rows:
        pre, outcome = classify(last_before, passed_after, any_after)
        out.append(ConversationSequence(conv_id=conv_id, pre=pre,
                                        outcome=outcome, n_messages=n_msgs))
    return out


def render_report(seqs: list[ConversationSequence]) -> str:
    n = len(seqs)
    pre = Counter(s.pre for s in seqs)
    pair = Counter((s.pre, s.outcome) for s in seqs)
    lines = [f"conversations with student+notebook: {n}",
             "", "== pre-chat pattern =="]
    for k, v in pre.most_common():
        lines.append(f"  {k:15s} {v:6d}  ({v / n:.0%})")
    lines.append("")
    lines.append("== pre-chat -> outcome ==")
    for (p, o), v in sorted(pair.items()):
        lines.append(f"  {p:15s} -> {o:12s} {v:6d}  ({v / pre[p]:.0%} of {p})")
    return "\n".join(lines)


@dataclass(frozen=True)
class AutograderRun:
    at: datetime
    grader_id: str
    success: bool


_RUNS_SQL = """
WITH convs AS (
  SELECT payload->>'conversation_id' AS conv_id, user_email,
         payload->>'notebook' AS notebook,
         min(created_at) AS t0, max(created_at) AS t1
  FROM events
  WHERE event_type = 'tutor_query'
    AND payload->>'conversation_id' = ANY(:conv_ids)
  GROUP BY 1, 2, 3
)
SELECT c.conv_id, a.created_at, a.payload->>'grader_id',
       a.payload->>'success'
FROM convs c
JOIN events a ON a.event_type = 'autograder_info'
  AND a.user_email = c.user_email
  AND a.payload->>'notebook' = c.notebook
  AND a.created_at BETWEEN c.t0 - make_interval(mins => :before)
                       AND c.t1 + make_interval(mins => :after)
ORDER BY c.conv_id, a.created_at
"""


def fetch_autograder_runs(ext_db_url: str, conversations,
                          before_min: int = BEFORE_MIN,
                          after_min: int = OUTCOME_MIN
                          ) -> dict[str, list[AutograderRun]]:
    """Autograder runs bracketing each conversation. user_email is used
    inside the SQL join only and never returned (rule 4)."""
    conv_ids = [c.conv_id for c in conversations]
    if not conv_ids:
        return {}
    eng = sa.create_engine(ext_db_url)
    out: dict[str, list[AutograderRun]] = {}
    with eng.connect() as c:
        for cid, at, gid, success in c.execute(
                sa.text(_RUNS_SQL), {"conv_ids": conv_ids,
                                     "before": before_min,
                                     "after": after_min}):
            out.setdefault(cid, []).append(AutograderRun(
                at=at, grader_id=gid or "", success=success == "true"))
    return out


_TRACEBACK_SQL = """
SELECT payload->>'conversation_id',
       payload->>'initial_notebook_json' LIKE '%Traceback%'
FROM events
WHERE event_type = 'tutor_notebook_info'
  AND payload->>'initial_notebook_json' IS NOT NULL
  AND payload->>'conversation_id' = ANY(:conv_ids)
"""


def fetch_traceback_flags(ext_db_url: str, conversations) -> dict[str, bool]:
    """Whether the at-ask snapshot shows an unresolved traceback. The
    LIKE runs server-side; notebook JSON never crosses the wire (rule 4)."""
    conv_ids = [c.conv_id for c in conversations]
    if not conv_ids:
        return {}
    eng = sa.create_engine(ext_db_url)
    with eng.connect() as c:
        return {cid: bool(flag) for cid, flag in
                c.execute(sa.text(_TRACEBACK_SQL), {"conv_ids": conv_ids})}


def main() -> None:
    from src.config import Settings
    settings = Settings.load()
    seqs = extract_sequences(settings.ext_db_url)
    print(render_report(seqs))


if __name__ == "__main__":
    main()
