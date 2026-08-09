# Sequence pilot — first numbers (same day as the position memo)

Date: 2026-08-09. Follow-up to
`docs/2026-08-09-behavioral-sequences-vs-message-labels.md`. Code:
`src/ingest/sequences.py` (read-only, aggregates only). One session of
read-only exploration overturned the ingested memo's central factual
premise and the ingest-cost section of the tensions memo.

## Finding 1: the sequence data already exists

The memo assumed the attempt→error→chat→code-change→test-result sequence
required new Jupyter instrumentation. It does not — `dsc10_tutor_logs`'s
single `events` table already carries, joined by a top-level `user_email`
column on every row:

| Sequence element | Event type | Volume | Notes |
|---|---|---|---|
| Attempt (notebook state at ask) | `tutor_notebook_info` | 36,803 | full notebook JSON + the student message it accompanied |
| Error / test result | `autograder_info` | 281,882 (41,486 failures) | per-question `grader_id` (q1_1…), success bool, output, timestamp |
| Tutor conversation | `tutor_query`/`tutor_response` | 45,652 / 42,727 | as already ingested |
| Code change | successive `tutor_notebook_info` snapshots | — | diffable across a conversation; no keystroke telemetry, but before/after state exists |
| Session context | `session_start` | 25,841 | cell counts per notebook open |

Coverage: autograder 2026-03-04..07-31; chat 2026-02-09..08-06 — the
spring+summer quarters overlap almost fully. No new instrumentation, no
new IRB data category, no tutor-surface cooperation needed for a
historical analysis. (The tensions memo's cost section stands only for
*keystroke-granularity* telemetry and for question-level chat linkage.)

## Finding 2: first sequence distribution (n = 7,782 conversations)

Every tutor conversation with a student and notebook attached, bracketed
by that student's autograder events on the same notebook (attempt window
45 min before first message; outcome window 20 min after last):

```
pre-chat pattern                          outcome (share of that pattern)
  pass-then-ask   4,360 (56%)   -> quick-pass 85% · no-run-after 14% · fail-after 1%
  ask-first       2,069 (27%)   -> no-run-after 84% · quick-pass 15% · fail-after 0%
  fail-then-ask   1,353 (17%)   -> quick-pass 87% · no-run-after 11% · fail-after 3%
```

Three immediate reads, each with its honest limit:

1. **fail-then-ask → quick-pass = 87%.** Post-failure chats almost always
   end in a pass within 20 minutes. The sequence alone cannot say whether
   that is guided debugging or answer extraction — *that distinction is
   exactly what the message labels measure* (pastes-error, direct-answer-
   request, answer-extraction). This is the labels×sequences join in one
   row.
2. **ask-first is 27% of conversations, and 84% of those never run the
   autograder afterward.** The memo's "asking before attempting" pattern
   is real and large — though "never ran within 20 min" conflates quiet
   exit, conceptual questions with nothing to grade, and logistics
   questions. Labels again disambiguate.
3. **56% of conversations happen while the student's tests already
   pass.** Most tutor use is invisible to the autograder. Caveat: the
   join is **notebook-level** — a student passing q1 while stuck on q3
   counts as pass-then-ask. Question-level linkage (grader_id ↔ chat
   topic) is the single highest-value refinement and likely needs the
   concept facet or chat-text question-number extraction (students cite
   "3.2"-style references — `reference_conventions` in the course
   profile).

## Methodological caveats (attack list for next session)

- Window sensitivity: 45m/20m are unvalidated choices; sweep them.
- Notebook-level join (above) inflates pass-then-ask.
- `user_email` is direct PII: it never leaves the SQL join; outputs are
  conversation-id-keyed patterns and aggregates only. Any snapshot
  emission must hash it (rule 4 review before any sequence snapshot).
- Autograder `check_all`/`citations` grader_ids are not per-question;
  currently counted like any run.
- Survivorship: conversations without user_email (~?) are excluded;
  quantify.

## Status

Pilot only — supports option (b) of the position memo's decision
(sequences *join* the label state space rather than replace it): the
sequence machine-classifies the arc, the labels give the arc its meaning.
Decision still open with Minchan and Sam; nothing downstream consumes
sequences yet.
