# Phase 2 Session Reconstruction

## Scope

This directory is an isolated, offline analysis project. It does not import from, write to, or modify the ChatSight application. The pipeline reads a JSON export, validates it against a canonical contract, and produces question-level session records with evidence links.

## Processing order

1. `normalize.load_json` rejects duplicate JSON keys and non-finite numbers.
2. A source-specific adapter converts each input record to `Event` in `schema.py`.
3. Pydantic validation rejects unknown fields and invalid values. Rejection diagnostics do not repeat message, code, or identity values.
4. Every accepted event receives a stable `ev-*` reference and source provenance containing the input hash, JSON pointer, record hash, and adapter name.
5. Exact duplicate event IDs are collapsed while retaining every source pointer. Conflicting records with the same event ID are rejected.
6. `sessions.reconstruct` groups only events with complete session identity, a usable timestamp, and an explicit or verified question link.
7. Events with missing identity, missing time, or ambiguous question attribution remain in `unassigned`. The pipeline never guesses from nearby text.
8. Events are ordered by occurrence timestamp. Ties are ordered only when a shared source ordering stream supplies distinct sequence numbers.
9. Long gaps and explicit pause or resume events create work bouts. A resumed bout remains part of the same question episode.
10. Tutor request and response lifecycles are retained. Only a response explicitly marked completed, with completion evidence, can create a help boundary.
11. Check-to-execution links are verified using execution and revision identifiers. Unverified links remain visible with reasons.
12. Question outcome comes only from explicit question status events. Passing checks are recorded separately.

## Important behavior

- A streaming, failed, cancelled, or unknown tutor response is not completed help.
- A normal streaming-to-completed response lifecycle creates one help boundary.
- Duplicate terminal responses or request IDs spanning question scopes are marked ambiguous and cannot create a help boundary.
- A passing subcheck is intermediate evidence, not question completion.
- A passing question-level check is recovery evidence, not automatically a final completion event.
- Inactivity creates a new work bout but is not a failure.
- An export ending without a status event produces an unknown outcome, not a failed outcome.
- Source references are preserved through normalization, episodes, work bouts, help windows, checks, outcomes, and metrics.

## Assumptions requiring real JSON validation

The adapter for the unavailable production JSON cannot be implemented safely until representative deidentified records or schema documentation confirm:

- event names and payload shapes;
- timestamp units, time zones, source clocks, and ordering guarantees;
- uniqueness scope for event, request, response, execution, revision, check, learner, notebook, and question identifiers;
- how questions are identified and whether a verified notebook-cell-to-question mapping exists;
- how streaming, completed, failed, retried, and cancelled tutor responses are represented;
- whether code edits are full snapshots, diffs, or periodic state captures;
- how executions bind to code revisions and how checks bind to executions;
- whether a stable grader ID and grader version identify repeated attempts at the same check;
- which event establishes final question completion, reopening, or abandonment;
- how export coverage and missing-event guarantees are represented;
- whether inactivity, browser closure, kernel restart, and later resumption are explicit events.

Phase 2C now provides a configurable adapter and validation workflow, but no production
mapping has been verified. See `PHASE2C_VALIDATION.md`. The canonical schema remains
intentionally stricter than an assumed source schema so every conversion must be explicit.
