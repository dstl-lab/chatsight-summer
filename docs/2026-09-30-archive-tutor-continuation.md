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
to Google Gemini. `dispatch-block.json` preserves that rejection. A question
describing the exact payload, destination and bounds is pending. There is no run
receipt, provider call or local execution yet.

## Validation

All 18 focused Python checks pass (seven new continuation checks and 11 existing
archive-loop checks). They cover request-only execution, feedback invalidation,
exact replay, immutable parents, tutor failures/interruption, no resend, caps,
message stopping and timestamp validation. Independent review found no remaining
runner blockers. No new manual labels are required.
