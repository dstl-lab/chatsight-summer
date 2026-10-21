# Phase 1: AI tutor session data feasibility

Audit date: October 10, 2026 (America/Los_Angeles).
Repository inspected: `codex/retrieval-question-forecasting`, `f6fa355`.

## Decision

**Local inspection complete; live database feasibility remains blocked.** Existing
exports support chronological conversation inspection. They do not establish
reliable student-question work sessions, active time, or post-help check outcomes.
Do not proceed to Phase 2 on the assumption that those fields are available.

No application code, production data, cluster permissions, or source snapshots
were modified. No student records were exported or sent to a model. This report
contains aggregate counts and field descriptions only. Old implementation files
were inspected for evidence of data formats, not copied into the new project.

## Access and evidence boundaries

- No local PostgreSQL listener was found on port 5432.
- The configured Kubernetes context is `nautilus`. The API responds, but the
  current identity cannot get the configured database pod in `dsc-10-llm` or
  create `pods/portforward`. The direct pod request returned `Forbidden`.
- Therefore, no live database query ran. Current schema, constraints, indexes,
  event counts, logging deployment, and database read-only grants are unverified.
- Prior documentation describes a PostgreSQL `events` table with `id`,
  `event_type`, `user_email`, `payload` (JSONB), and `created_at`. This is a
  documented schema, not a live schema inspection on this audit date.
- On October 10, Steven confirmed that all locally available data is approved
  for this study, in response to the permitted-use question including deidentified
  local exports. No additional course/date restriction was specified for that
  local data. This resolves the local-use permission question. Permission for new
  exports from the live database remains outside this confirmed local scope.

## Data verified locally

| Export | Conversations | Student / tutor turns | Valid timezone-aware turn timestamps |
| --- | ---: | ---: | ---: |
| August 7 | 6 | 78 / 74 | 152 / 152 |
| August 10 (primary) | 52 | 235 / 225 | 460 / 460 |

The two exports contain 58 distinct conversation IDs. These are conversations,
not counts of students. The primary export spans 18 notebook names; the earlier
forecasting interface's 16 notebooks described its authored-question subset.

In the primary export:

- All 408 adjacent within-conversation timestamp pairs are strictly increasing.
  Six gaps exceed 30 minutes; chat duration cannot be equated with active work.
- 47 conversations have a recorded tutor turn, with 178 additional tutor turns
  after their first. Five have no recorded tutor response. This does not establish
  failed requests, completed delivery, or complete response capture.
- All 235 label rows join to student turns. 63 have a derived question reference;
  53 have question-level sequence metadata; 182 have notebook-level metadata.
  References are extracted from message text and matched to prior checks. They
  are not explicit question IDs on raw tutor events or verified full sessions.
- Student modes are 199 `tutor` and 36 `chatgpt`. The older export has no mode
  field. Future analysis must specify mode eligibility rather than pool silently.
- There are no learner IDs, raw check attempts, notebook revisions, execution
  records, activity/idle signals, explicit question versions, request IDs,
  response-completion status, or observation-end guarantees in these exports.
- The sibling ChatSight SQLite database has zero cached messages and no raw
  `events` table. It cannot supply the missing event stream.

## Documented event relationships requiring live verification

| Event | Documented fields / relation | Limitation |
| --- | --- | --- |
| `tutor_query` | Conversation, notebook, question text, mode, server timestamp | No verified explicit assignment-question ID or request-completion link |
| `tutor_response` | Conversation, response text, server timestamp | Server logging time does not prove completed streaming or client receipt |
| `autograder_info` | Learner, notebook, `grader_id`, `success`, timestamp | Historical join uses learner + notebook + time; same question and executed revision must be established |
| `tutor_notebook_info` | Conversation, initial notebook JSON | Initial snapshot does not supply intermediate edits or current executed source |
| New request / execution logging | Prior development memo describes request IDs, cell IDs, source hashes, and execution bindings | Current deployment and collected-event coverage unknown |

A September 15 memo reports 9,442 linked conversations and 8,590 usable initial
captures in its historical window. Its six inspected captures lacked stable cell
IDs. Those figures are historical evidence, not current database measurements.

The old sequence query defines its end using tutor-query timestamps despite a
comment referring to tutor responses. Its window summaries cannot implement the
new first-completed-response boundary. Notebook-level proximity also cannot prove
that help and a subsequent check concern the same question.

## Recommended data structure and measurement rules

Use independently defined, versioned records with nullable unavailable fields:

| Record | Essential fields |
| --- | --- |
| Event | Opaque event ID, pseudonymous learner ID, course/cohort, assignment/version, notebook, question ID, question-link basis, event type, event time, received time, sequence/order certainty, conversation/request ID, source provenance |
| Tutor interaction | Request event, response events, completion status/time/basis, mode, applicable question link; retain every interaction |
| Work / check | Cell ID, source revision/hash, execution ID, grader/test ID and version, pass/fail/unknown, check scope, bound work revision |
| Question episode | Learner + assignment version + question, all work bouts and events, first completed applicable response, all later help, observation window, completion evidence, coverage gaps |
| Work bout | Episode ID, observed start/end, boundary reason, inactivity gaps, resumed-from relation |
| Metric / ranking | Value or unknown, units, pre/post-help scope, supporting event IDs, method version, eligibility, question baseline sample size, score components and reasons |
| Review / evaluation | Frozen candidate population, selection method/seed/rank, review-worthiness judgment, diagnostic category, reviewer, missing-evidence notes |

Rules incorporated before implementation:

1. Split pre/post-help at the **first completed tutor response applicable to the
   question**, not the first request. Preserve subsequent interactions and activity
   while waiting for help. Missing or ambiguous completion leaves the boundary
   unknown. Preserve tied timestamps and their uncertainty rather than invent order.
2. Treat inactivity as a bout boundary, not failure. Link later work to the same
   question episode when identity/version allows it. A passing subcheck is an
   intermediate event; retain later edits and failures. Full completion requires a
   defined question-level rule. Dataset end or missing outcome means observation
   ended with unknown completion, not failure or abandonment.
3. Keep elapsed time separate from any active-time estimate. With sufficiently
   informative activity logs, specify an idle-gap estimator and test sensitivity
   to 2/5/10-minute thresholds. Sparse chat-only timestamps do not justify it.
4. Every eventual ranking reason must identify its supporting events, metric,
   question baseline, sample size, threshold, and missingness. Unknown is not zero.
   No anomaly scores or flags are computed in Phase 1.
5. Freeze a common eligible session population, observation horizon, question
   versions, and review budget for random, total-time, and post-help rankings.
   Record exclusions and incomplete coverage; avoid completed-only selection
   silently excluding struggling sessions. Review-worthiness is separate from
   suspected tutor involvement. Hide ranking method during evaluation where possible.
6. Use study-specific opaque learner IDs or keyed pseudonyms, with keys/mappings
   separately restricted. Do not use an unsalted email hash. Remove identifiers
   from chat/code content before any approved export; pseudonyms alone do not
   anonymize free text. Retain authorized source evidence locally, outside Git.

## Remaining Phase 1 work and proposed Phase 2 gate

An administrator must provide the intended read-only access route; this audit
does not request broader production permissions. A data-owner-supplied aggregate
schema/coverage report is an alternative if direct access is unavailable.

Once access is restored, verify read-only transaction mode and inspect schema
metadata, constraints/indexes, event types, timestamp validity/order, missing and
duplicate IDs, question/version coverage, request-response completion linkage,
check-to-revision linkage, and activity logging coverage by course/date/version.
Use bounded aggregate SELECT queries with a statement timeout. No schema or index
changes. Historical chat-window exports are insufficient for full-cohort baselines:
include eligible question activity outside tutor conversation windows as permitted.

For approved local data, or live data after its export scope is confirmed, check a bounded deidentified real example
with an unambiguous question, completed help boundary, and subsequent check evidence.
Report eligible coverage across the audit window; one example alone does not prove
population feasibility. If reliable question joins or activity evidence are absent,
report the narrower supported scope and needed instrumentation.

**Proposed next implementation, only after approval:** an isolated event validator
and question-episode builder, tested on repeated bouts, partial passes, late events,
missing results, and ambiguous help boundaries. No dashboard or detector yet.

## Evidence sources

- `src/ingest/rawlog.py`, `src/ingest/sequences.py`, `src/labeling/sampler.py`.
- `docs/2026-09-15-notebook-snapshot-pairs.md`.
- `docs/2026-09-15-request-work-logging.md` (historical implementation status).
- Existing ignored snapshot JSONL files, parsed offline with aggregate-only output.
- Primary conversations SHA-256:
  `0aeaa1eeba538405413790ae2136176a912fc521d3d6df0c5010b6f3b0979529`.
- Earlier conversations SHA-256:
  `c4b8505333efcde9626dbebdea97d3cca2446e8a282f90db060f63fad9a722df`.

This report is the only newly created artifact. Phase 2 awaits user approval.
