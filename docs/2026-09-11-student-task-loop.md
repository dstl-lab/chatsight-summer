# Make the student act on its own work before returning to the game

Minchan explicitly prioritized functioning simulated students over end-product
design. Preserve the coaching storyboard; pause interface work. The current
continuation helper can generate chat, and the grader gate can check caller-owned
code, but the student cannot revise its own task state. Free-form messages have
also reported unsupported results. A longer chat alone does not fix either gap.

Build one bounded, invented rate-comparison encounter in `src/eval/student_task.py`.
The model chooses a message, terminal no-reply, a worksheet revision, or a check.
Revisions install structured answers without sending a chat message. Checks compute
feedback locally against those answers; they do not ask the model for the outcome.
Every revision invalidates the current observation. Old checks remain in history
with their revision, never masquerading as current feedback. The student may
continue without reporting a check to the tutor. Do not solicit hidden reasoning,
biographies, ability scores or a personality type.

Reuse the existing generator, visible-dialogue projection, continuation schema,
branch helper and communication guidance. Use full short-episode history as memory.
Keep worksheet state separate from the notebook-specific grader gate. This is a
single task, not a general task-adapter or memory framework. Two supplied tutor
bridges support branching after student messages; exhausting them means awaiting
tutor input. Six student decisions cap a run; that cap is not no-reply or failure.
Messages never install work, trigger a check or establish a result by themselves.

First test wrong work → check → revision → unknown current result → fresh check,
retained dialogue without historical future leakage, no-reply and invalid actions.
Then run two predetermined Gemini 2.5 Pro rollouts from the same wholly authored
situation, with at most six decisions each. Keep all actions, failures, prompts,
schemas and results. Save a pending receipt before each generator call; do not
automatically resubmit interrupted runs. Reuse the existing adapter's retry policy
and document that it does not retain raw rejected provider responses. No private
student text, identity, human judgments, DB access or course assets are required.
Standing model-run approval covers this experiment. Preserve all 370 earlier pins.

Assess whether the loop functions and inspect unsupported outcome reports against
its recorded work/check history. Free-form chat is still capable of inventing
events, so structured state does not guarantee semantic grounding. A run that
solves this small task is not evidence of plausible novice behavior. These invented
traces are engineering probes, not a fidelity evaluation set or estimates of
learning, response probability, course transfer or tutor-policy effects. The
pending real/generated behavior comparison remains separate and unscored.

## Implemented and exercised

The CLI now saves exact per-call prompts/schemas, source hashes, pending/completed
or failed receipts, and every action/check. Each invocation requires a new output
directory. Offline replay checks the same inputs and reproduces the saved result
without dispatch. A review found that terminal provider failures initially could
not replay; a regression reproduced that bug and the fix now preserves the saved
failure type/message. Pending/interrupted calls still cannot be resubmitted by replay.

The two predetermined runs completed under standing approval, using no private
student text. Seven logical requests returned valid actions, with no failed logical
requests; individual adapter attempts are not separately recorded. Both traces
reproduce offline. Exact artifacts remain ignored under
`data/episode-pilot/student-task-loop-v1/`.

| Draw | Retained sequence | What was actually established |
|---|---|---|
| 01 | revise work → request check → no-reply | The installed answers pass the local worksheet checker; no student chat followed |
| 02 | revise work → request check → reply → authored tutor bridge → no-reply | The same correct revision/check, followed by an acknowledgment and the two rate values |

Both models immediately changed the initial total-based answers to the correct
rates. This confirms action/state mechanics on this task, not a realistic novice
policy. The live traces never recover from a failed check; that path currently
has an offline regression only. There is just one generated chat exchange.
Draw 02's acknowledgment is a generated claim about understanding, not
an observation of understanding. Neither trace reports a result unsupported by
the local work/check evidence; two traces cannot establish a general grounding
guarantee. The fixed tutor bridge repeats a procedure after a correct answer;
it is intentionally a limited scaffold, not an adaptive tutor under evaluation.
Early exits are model decisions within this authored scenario, not estimates of
student response probability or observed abandonment. Both draws share one initial
situation and do not supply two independent real contexts.

Validation: 301 Python tests pass, including four focused regressions for work
state, termination/invalid actions, successful/pending replay, and failed-provider
replay. The existing Starlette/httpx deprecation warning remains. All 370 earlier
experiment pins still verify (358 through the original archive mapping and 350
unchanged live parent pins). No existing frozen generator was edited.

From the worktree root, replay a saved trace without an API request:

```sh
uv run python -m src.eval.student_task --replay --output data/episode-pilot/student-task-loop-v1/draw-01
```

For a deliberately new authored draw, use `--send` and a new ignored output
directory. The CLI uses the existing Gemini 2.5 Pro adapter and `.env` convention.
It does not start a UI, access the database, infer an archetype or execute arbitrary
student code. The next research step is testing action choice and continuity
against real student behavior, including imperfect work and selective reporting;
more immediate correct solutions would not resolve that requirement.
