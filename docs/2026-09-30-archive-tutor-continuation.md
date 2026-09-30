# One tutor exchange after the saved student message

The next increment connects the pending student message to one tutor reply, then
lets the student choose up to three actions. It tests continuity of notebook,
chat and execution feedback; it does not establish student realism or learning.

The original `data/archived-student-loop-v1` remains closed and unchanged. The
new run lives in ignored `data/archived-tutor-continuation-v1`, with plan digest
`db48c4b3b92da1fa995290a277817ba0688dc9e63ecab72a3655e49f13db09a2`.
It begins with that run's revision 1 and its exact pending message, with no
execution result. The prepared BabyPandas reference is supplied only to the tutor.
The same direct-answer policy and Gemini 2.5 Pro model are retained.

## Boundaries and implementation

`src/agents/archive_tutor_continuation.py` uses the existing tutor prompt/schema
and the unchanged archival student simulator. The existing isolated executor runs
only on `request-check`; a tutor or student edit cannot implicitly execute code.
The limits are one tutor reply, three student decisions and two local executions.
Message, no-action, error and budget stops are distinct. No automatic second
tutor, retries, replacement draws or resuming interrupted attempts are allowed.

The student receives current work, prior dialogue, the pending message and the
new tutor reply. Prior simulated activity is explicitly identified in its
initialization; action history within this new segment starts empty. The course
reference and older study's execution results are not student context. Local
feedback is attached to its exact code/revision and cleared by a new edit. There
is no correctness grader; the historical dataset bytes and kernel remain
unverified.

Preparation binds the parent plan, raw receipt, course reference and its manifest,
checkpoint, declared runtime and code dependencies. Reads replay raw tutor/student
responses and execution output against exact saved prompts. Receipt chronology
includes the parent finishing before the new plan. Every dispatch has a pending
receipt before the call; even a failed or interrupted attempt consumes the run.

```sh
PYTHONPATH=. python -P -m src.agents.archive_tutor_continuation prepare \
  data/archived-tutor-continuation-v1 \
  --parent data/archived-student-loop-v1 \
  --reference data/notebook-course-context-v1/course-reference.json
PYTHONPATH=. python -P -m src.agents.archive_tutor_continuation show \
  data/archived-tutor-continuation-v1
# Separate, explicitly authorized dispatch; show is offline.
PYTHONPATH=. python -P -m src.agents.archive_tutor_continuation run \
  data/archived-tutor-continuation-v1 --send
```

## Dispatch status

Minchan accepted the bounded continuation with “Let's do it,” then resumed the
interrupted work. The acceptance is logged in `authorization.json`. Automatic
approval review rejected the live command before process creation because it
requires specific authorization for the private notebook/chat/reference payload
to Google Gemini. `dispatch-block.json` preserves that rejection. Minchan then
answered **“Approved”** to the exact notebook/code/chat/reference and subsequent
actions/feedback transfer to Google Gemini, within the one-tutor/three-student/
two-local-execution bounds. `approval-response.json` binds that answer to the
unchanged plan and rejection before dispatch.

**The run completed with one tutor call, one student call and zero executions.**
With the course API reference, the tutor replaced the unavailable `.nunique()`
suggestion with `len(...unique())`. The student chose `revise-work`, copied that
code into revision 2, and sent the same code as a chat message. The runner stopped
at `awaiting-tutor`; no `request-check` occurred and the observation remains null.
There were no provider failures, retries or replacement draws. Total usage was
3,786 tokens: 2,250 prompt, 176 output and 1,360 thinking tokens.

The revision remains **unexecuted in this run**. Identical code succeeding in a
previous study does not supply this run's result. This establishes a working
tutor-to-student continuation, but it does not establish realistic chat behavior,
learning or student-selected execution. The student again pasted code back to the
tutor; this is an observed model choice, not a judgment that a real learner would
do so. The run is closed; unused budget does not authorize another tutor turn or
reroll.

Offline replay and independent audit verify the exact raw responses, prompts,
parent/reference/code bindings, limits and approval-before-dispatch chronology.
`completion.json` binds the run and approval receipts, counts, usage and limits.

## Validation

All 18 focused Python checks pass (seven new continuation checks and 11 existing
archive-loop checks). They cover request-only execution, feedback invalidation,
exact replay, immutable parents, tutor failures/interruption, no resend, caps,
message stopping and timestamp validation. Independent review found no remaining
runner blockers. No new manual labels are required.

## Workbench integration

The existing preview accepts `--continuation` after the new run has completed:

```sh
PYTHONPATH=. python -P apps/archive_message_preview.py \
  data/archived-student-loop-v1 --branch data/notebook-source-branch-v1/branch \
  --continuation data/archived-tutor-continuation-v1 --port 8454
```

For the current unified interface, use the consolidated command below instead.

The original three events remain intact, followed by the new tutor reply and
each student action on the same timeline. Student-requested execution output
appears below its exact code revision, and a subsequent edit removes the current
result. An attempted edit that fails before changing work retains the prior
result. The UI separates no-action, budget stops, tutor failure and action failure;
it never substitutes a successful result for an absent one. Source diffs and chat
stay beside the timeline, and the final event opens by default. Both run inputs
are verified on every reload. There are no sending endpoints.

An explicitly authored fixture in ignored `data/continuation-ui-authored` verified
the seven-event layout in the browser: tutor → requested local error → quiet edit
→ no action. These are test callbacks, not provider or container executions. The
browser confirmed keyboard navigation, one copy of each chat message, removal of
stale output, final-stage reload and exactly centered glyphs, with no console
errors. Port 8453 still displays the unchanged actual parent run.

The completed live continuation is now at <http://127.0.0.1:8454/>. Browser
inspection confirms five timeline events, one copy of each of five chat messages,
the revision-1-to-2 diff, no borrowed execution output and the final awaiting-tutor
state. The new tutor event still shows revision 1; only the following student
event introduces revision 2. No extra model or execution request was made by
opening or navigating the workbench.

Final combined verification: 31 Python checks and three Node controller checks
pass, plus JavaScript syntax and whitespace checks. The nine preview checks also
pass after removing a stale parent execution counter from continued packets;
the continued timeline reports saved local results, without guessing how many
failed execution attempts reached the executor. The shared Starlette/httpx
deprecation warning is unchanged.

## Consolidated workbench

The current page is **Student simulation**: one Run selector, one interaction
timeline, notebook on the left and chat on the right. The latest continuation
opens by default. Earlier direct-answer and guided-hint samples use the same
renderer; **Compare samples** opens the existing optional floating panel. Cycling
samples keeps that panel open and updates the run selector and timeline together.

```sh
PYTHONPATH=. python -P apps/archive_message_preview.py \
  data/archived-student-loop-v1 --branch data/notebook-source-branch-v1/branch \
  --continuation data/archived-tutor-continuation-v1 \
  --include-policy-samples --port 8454
```

The earlier comparison is derived from the parent's frozen attachment, not an
independently selected folder. Both read-only APIs revalidate the parent,
continuation and prior study; changed receipts fail closed. Three distinct
researcher checks are shared across matching source edits. Only the predetermined
first sample per policy has a saved reaction. Missing later reactions are labeled
as missing, not inferred silence. An edited reaction has no inherited output;
unchanged code may retain its previously observed result. The latest continuation
never borrows a matching-source output from the earlier comparison.

The former local listeners at 8450, 8452 and 8453 were retired. Temporary localhost
redirects send GET/HEAD requests for their roots to 8454 with 302/no-store; legacy
API paths return 410 and writes are unsupported. The redirect process serves no
research data and forwards no query strings. These redirects last only while that
local process runs; the command above is the canonical launcher. Historical
standalone adapters and all frozen artifacts remain available for reproducibility.

Validation: 32 focused Python tests and four Node controller checks pass, with
independent backend review. Browser checks covered the default latest run,
researcher feedback, unexecuted repairs, native run switching and sample cycling
with the comparison panel staying open. No new model calls, notebook executions,
manual labels or evidence of improved student realism result from consolidation.
