# Preserve the supplied conversation example across notebook tasks

**TL;DR:** Carry the explicitly sourced recorded conversation example into later
notebook tasks, alongside the already supported simulated encounter history.
Verify the handoff offline. The failed work-presence forecast stays closed.

## Concrete gap

`notebook_example --chat-source` already copies a validated original conversation
prefix and records its hashes outside model context. `notebook_next_task` carries
observed simulated activity but deliberately excludes arbitrary initialization.
Consequently the recorded example disappears on Task 2. Keeping only simulated
history changes the supplied context during a task sequence without an explicit
research decision to remove that example.

## Bounded change

Keep `_observed` unchanged. Recover only `conversation_example` and its
`communication_scope` from the first notebook session when it declares
`provenance.communication_source`. Validate the existing prefix schema and its
recorded hash. Do not recover arbitrary initialization, generated chat continuations,
private evaluator values, source paths, identities or other metadata.

Copy that example once into each newly created task, separately from the current
task and observed simulated encounters. Bind the carried content in predecessor
provenance; verify equality with the original during lineage/replay validation.
The existing predecessor manifest hashes bind the original source provenance.
Do not require the external chat source to remain available: the initial notebook
session already captured and verified its prefix. No new model or storage layer.

Count the carried example and its scope once in the existing 64 KB shared-context
limit. Refuse oversize context rather than truncate. Preserve legacy successors
that did not carry the example; never rewrite their saved inputs or imply it was
previously delivered. A newly created successor may restore the original example
from that verified lineage. The replay must show exactly which tasks received it.

## Acceptance and stopping point

Use authored sessions to verify Tasks 1→2→3, unchanged current work/evaluator,
both agent inputs, provenance exclusion, no repeated/nested example, input-file
preservation, missing/malformed provenance, tampered carried context, the byte
limit, and old lineage compatibility. Reuse existing runtime and replay helpers.

Prepare one successor offline from the completed conversation-conditioned notebook
run, preserving its closed state and making no provider or execution calls. Save
an initial replay and provenance checks. Stop with that reproducible setup; no new
live run, manual review batch, forecast tuning or automatic adoption is queued.
This repairs input continuity. It does not establish a persistent real-student
identity, a calibrated persona, learning, or improved behavioral fidelity.

## Completed verification

The handoff now preserves the original example through Tasks 2 and 3 in both
agent inputs, while keeping arbitrary initialization and private provenance out.
The saved replay identifies which tasks actually received the example. A known
older creator hash permits genuine legacy omission; new successors reject altered
content, missing scope/hash, or complete removal of the carried example. Review
identified that final omission edge case; its regression failed before the fix
and now passes. No student/tutor engine or generation prompt changed.

All **444 tests pass**, with three optional container skips and one existing
Starlette/httpx warning. Both Marimo checks and Node navigation pass. Independent
review found no remaining issue. The completed forecast's 69 frozen files still
verify; the failed forecast and earlier human review remain closed.

An offline second exercise is saved under `data/notebook-communication-continuity/`:
find the green-row proportion using the same authored table. The prior completed
exercise remains unchanged. The new initial state has the exact 10-turn recorded
example plus the observed prior simulated encounter, fresh work and a separate
private evaluator, no current feedback or actions, and all six decisions unused.
No provider or execution call occurred. `prepare.py` repeats the verification
without regenerating the session; `verification.json` pins its source/setup/code,
and `initial.html` shows the handoff. Independent review verified all 34 pins.

This increment stops at a reproducible offline handoff. New live runs and human
reviews are not queued. Older all-source audits that pin the next-task creator or
replay renderer need their recorded revisions; keep those original pins intact.
