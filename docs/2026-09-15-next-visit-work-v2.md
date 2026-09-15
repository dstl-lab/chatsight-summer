# Validate the corrected schema, then run the fixed work forecasts

Minchan asked to continue after the failed next-capture run and offline schema
correction. First test the corrected `Forecast` schema with one entirely authored
API-format example. Only after a successful response, execute a separately bounded
V2 containing the exact two previously authorized notebook prompts. The V1 run
remains closed with its two failures/eight adapter attempts; do not rewrite or
replace any V1 artifact.

## Scope fixed before dispatch

One authored Gemini 2.5 Pro schema request, at most four adapter attempts. Ask for
one edit to an invented two-cell notebook. Require a valid response with the
specified index and source, accepted by local `apply_forecast`; record any failure
and stop before the real-data requests. This verifies this schema's live acceptance
and local handling, not student behavior or general model reliability.

If the smoke check passes, V2 has exactly two logical Gemini 2.5 Pro requests,
one for each existing pair 2/3, at most eight adapter attempts total. The entire
turn's planned provider budget is thus three logical requests/twelve adapter
attempts. The existing adapter may retry JSON/schema/network errors; no additional
logical requests, replacements, prompt changes or sampling are allowed.

Keep V1's initial contexts, inputs, targets and disclosure byte-for-byte. The only
request change is the corrected provider schema, which removes unsupported
additionalProperties while retaining strict local validation. Reuse the private
runner/scorer unchanged in a separate ignored `next-visit-work-v2/` directory.
The previously explicit approval covers the same private excerpts and destination;
record it alongside the latest continuation instruction and this separate budget.
If automatic approval requires additional specific input, preserve the rejection
and stop rather than use a different dispatch path.

All 58/54 original code positions stay in scope. The later captures are reference
outcomes only. No grader execution, new labels, reviewer work, added contexts or
behavior-prompt tuning. Preserve errors and invalid scope as unavailable forecasts,
never as predictions of unchanged work. Do not compare one immediate action with
the later notebook endpoint.

## Verification and stopping point

Before calls, pin the schema, prompt/config sources, exact inputs, source receipts
and authorization. Record pending dispatch before provider calls; an existing run
receipt blocks resending. Verify the smoke result before preparing V2 execution.
Independently check unchanged private payloads and corrected schema before dispatch.

Report per pair: observed and predicted changed positions, TP/FP/FN and exact
source matches at observed changed positions, alongside unchanged-source baseline.
Recompute directly from retained sources and responses. Text equality is not
correctness or semantic equivalence. Two exposed examples and fixed layouts remain
a development check; no population fidelity, response probability, causal tutoring
effect or learning claim follows. Freeze all results even if they are unhelpful.

Stop after the fixed run and its verified report (or failed schema gate). No
additional model batch follows automatically. Commit aggregate findings and status
in the isolated worktree and draft PR #25; keep raw data private and PR unmerged.

## Completed schema check; V2 dispatch blocked

The authored check succeeded with **one logical request and one adapter attempt**.
Gemini accepted the corrected nested schema and returned exactly the requested
edit at index 1 with source `answer = 2`. Local application accepted it; no code
was executed. This closes the specific live schema-acceptance issue. It does not
measure student behavior or guarantee acceptance of all future requests.

V2 preparation is complete. Initial contexts, inputs, targets, disclosure, runner
and scorer are byte-identical to V1. The exported schema differs only by removal
of the two unsupported `additionalProperties` fields. Strict local validation
remains in force. All 58/54 initial code positions are retained and later target
work is absent from the prompts. The prior source, error and result records remain
unchanged. Independent preparation audit and offline future/no-resend checks pass.

The new real-data dispatch was **rejected by automatic approval review before
process creation**. It stated that the earlier approval covered the exhausted
V1 run, and that the latest continuation did not explicitly authorize this new
batch. No V2 `run.json` exists: zero real-data requests, zero real-data adapter
attempts, and no student forecasts. The authored smoke result remains separate.
No alternate dispatch path or replacement request was attempted.

The preparation's `approval-response.json` records the earlier explicit payload
approval and an inference from the latest continuation. Automatic review did not
accept that inference as authorization for a fresh batch. Preserve that preparation
record and the rejection; do not rewrite them as new explicit approval. The
remaining input is authorization to resend the same two private excerpts in V2,
capped at two new logical requests/eight adapter attempts. Bind any new explicit
approval to the unchanged disclosure, inputs and experiment before dispatch.

This report therefore establishes successful schema integration and verified
preparation, not a completed student forecast comparison. No labels or human
plausibility reviews were requested. Keep PR #25 draft/unmerged.
