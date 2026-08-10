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
| Code change | successive `tutor_notebook_info` snapshots | — | one snapshot per conversation (turn 1 only — see appendix); diffable across *consecutive conversations*, not within one |
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

## Appendix: cluster inventory (read-only, 2026-08-09)

Namespace `dsc-10-llm` on Nautilus holds the entire data surface:

- **`dsc10-tutor-logs-prod`** (Spilo/Patroni Postgres, primary+replica,
  20Gi): one database `dsc10_tutor_logs` (470 MB), one table
  `public.events` (~485k rows). Everything this project can historically
  analyze lives in that table — there is no second data source to find.
- **`dsc10-tutor-logs-dev`** (2Gi): dev twin, presumably test data; not
  probed (separate credentials/tunnel).
- **`dsc10-tutor-logging-api-prod`** (2 replicas, healthy): the write
  path. Image `gitlab-registry.nrp-nautilus.io/samlau95/dsc10-tutor-logger/api`
  — **the logging surface is Sam Lau's `dsc10-tutor-logger` GitLab
  project**, which substantially answers open decision #5's "who owns the
  tutor's logging surface" (the *prompt/policy* surface may still differ —
  confirm with Sam). The dev API pod is crashlooping (866 restarts) —
  worth mentioning to Sam, prod unaffected.

Implication for the sequence work: any new sequence element (question-id
on tutor_query, richer cell telemetry) is one event type away — a change
to Sam's logger API, not new infrastructure.

## Appendix 2: snapshot anatomy and the ChatGPT toggle (2026-08-09)

Two run-downs of the notebook-snapshot surface:

**1. The "unparseable snapshots" were nulls, not corruption.**
`initial_notebook_json` is captured exactly once per conversation, on
turn 1 (100% of non-null snapshots are their conversation's first
`tutor_notebook_info` row; 8,608 of 8,609 conversations have exactly one).
Rows for later turns carry the field as null. Consequences:

- Valid snapshots are clean: full notebooks (typically 21+ cells), cell
  outputs captured including tracebacks — a rich at-ask error signal.
- **Within-conversation code-change diffing is impossible** (the earlier
  "76% diffable" figure counted rows, not non-null snapshots — wrong).
- **Across-conversation diffing works**: same student + notebook,
  consecutive conversations' initial snapshots show code evolution
  between chats, which brackets "what changed after the tutor's advice"
  at conversation granularity. Copy-detection (tutor response text vs
  next snapshot's diff) survives in this coarser form.

**2. `toggle_mode: chatgpt` is an in-tool ChatGPT mode — defection is
partially observable.** The tutor UI has a toggle: `tutor` mode runs
`prompt_mode=append` (tutor system prompt), `chatgpt` mode runs
`prompt_mode=override` (raw assistant, no tutor persona). It is heavily
used — 9,513 of 45,652 tutor_query turns (~21%) are `mode=chatgpt`,
present every month Feb–Jul, fully logged (question, response,
conversation_id, user_email). Implications:

- Invariant 7's "quiet exit to ChatGPT" is not entirely invisible:
  in-tool mode-switching is a logged, per-turn observable. A
  tutor→chatgpt toggle mid-conversation is a directly measurable
  defection event (external ChatGPT use remains invisible).
- Policy-relevant natural experiment: the same student population, same
  assignments, two tutor personas, logged side by side — a comparison
  cohort for "what does the tutor persona change" that the replay agenda
  (Phase 4) could baseline against.
- Sequence pilot caveat: the pilot's 7,782 conversations mix both modes;
  the pre/outcome distributions should be re-cut by mode next.

## First sequence-grounded labeling run (2026-08-09, smoke test)

The five-upgrade implementation (spec `docs/superpowers/specs/2026-08-09-
sequence-grounded-labeling-design.md`) passed its live smoke: 10 recent
conversations, 89 messages, 4-label instructor schema, throwaway snapshot
(deleted after; provenance verified then discarded).

- **Plumbing verified end-to-end**: manifest recorded
  `sequence_context {before_min 45, outcome_min 20, enabled true}` and the
  new classifier hash; every label row carried mode/pre_pattern/attempted/
  question_ref/defected facets; review strata showed `seq-askfirst`
  suffixes; the distinctness report printed its by-mode section
  (e.g. solution-seeking: tutor=16, chatgpt=6).
- **Fetcher correctness**: `fetch_autograder_runs` matched a direct SQL
  join exactly (456 runs over 10 May conversations) — the ANY() binding
  works; traceback flags fire on real data (2/10).
- **Coverage caveat**: recent (August) conversations sit past the
  autograder stream's 2026-07-31 end, so the smoke sample was 100%
  ask-first. Runs over the covered window (Mar–Jul) are where the
  fail-then-ask / pass-then-ask context lines will actually vary.
- **Facet stats on the smoke sample**: mode 79 tutor / 10 chatgpt;
  question_ref on 24/89 messages (27%); 2 in-tool defection events.
- **Sequence ablation** (20-message probe): 4/20 messages changed at
  least one verdict when sequence facts were stripped — conceptual-
  difficulty 10%, assignment-context 5%, solution-seeking 5%,
  code-error-debugging sequence-inert. Even "no autograder run" + mode
  alone moves verdicts; a Mar–Jul sample with real fail/pass context is
  the next measurement.
