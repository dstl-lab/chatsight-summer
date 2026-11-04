# Evidence-Preserving Timeline Compaction

## Purpose

The instructor timeline derives readable actions from bursts of related low-level
events. Compaction is a browser display transformation only. It does not replace,
delete, reorder, or mutate source events, and it is not used by reconstruction,
metrics, baselines, rankings, model analysis, or fusion.

## Current rule

Events may share one action row when all of the following hold:

- they occur in the same one-second bucket;
- they have the same before-help, help-boundary, after-help, ambiguous, or
  unpartitioned phase;
- they are notebook, execution, check, or activity observations rather than a
  student message, tutor response, inactivity gap, or question-status boundary;
- their metadata links them through a shared cell, execution, revision, request,
  check, or grader identifier; or they are repeated edit observations with no
  conflicting cell identity.

Different known cell identifiers prevent grouping. Unlinked checks and executions
remain separate. Student and tutor messages always remain separate rows. Related
events can join transitively, such as an edit linked to an execution by revision
and that execution linked to a check by execution ID.

Each compact row reports its raw event count and expands to the complete underlying
records, including exact timestamps, messages, code, metadata, source IDs and JSON
pointers. Evidence citations still target the original event reference. A cited
event highlights its containing action, and a single citation opens the matching
raw record.

Timeline filters operate on raw events before display compaction. For example, the
Checks filter shows check evidence without pulling an associated edit into that
filtered view.

## Provisional assumptions

The one-second window is a conservative interface default, not a validated semantic
definition of one student action. Real-data validation must confirm:

- source timestamp precision and whether event time or receipt time is authoritative;
- whether client sequence numbers should override timestamps;
- stability of cell, revision, execution, request, check and grader identifiers;
- whether edit bursts contain complete code revisions or incremental patches;
- whether delayed checks can share an execution ID outside the one-second window;
- whether events from concurrent notebook activity need an additional stream key.

Until those assumptions are checked, compaction should be interpreted as a readable
same-second evidence grouping, not a claim about cognitive intent or causality.

## Tests

`frontend/src/timeline-compaction.test.tsx` covers:

- a linked edit, execution and failed check in one second;
- unrelated cells at the same time;
- conversation and phase boundaries;
- later seconds;
- identifier-free edit bursts;
- uncertain ordering;
- expandable raw records and cited evidence anchors.

