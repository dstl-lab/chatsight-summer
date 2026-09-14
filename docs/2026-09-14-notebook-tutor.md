# Connect one tutor reply to the saved student

The saved student and tutor context already support a supplied reply. This bounded
addition supplies that reply from Gemini under a researcher-written teaching policy,
then resumes the same student through the existing state-bound `step` transaction.
It enables an actual tutor–student exchange without manually copying response files.

The tutor sees the selected task, dialogue, pending message, work, net source changes
and current feedback. It receives no hidden student state, reference future, engine
hashes or decision budget. Its output is one nonblank message, not code execution or
a student action. A policy is an instruction to the tutor, not a new learner label.

Accept only an awaiting-tutor session with remaining student budget. Create a new
output directory and save the exact context, policy, prompt, schema and model before
requesting the tutor response. Save the response before student dispatch and pass
both original context bindings into `notebook_student.step`. A concurrent state
change must prevent applying the reply. Provider errors and interrupted operations
retain their receipts; existing output directories cannot automatically resend.

Reuse the existing provider adapter, JSON writes, student transaction and checker.
Leave pinned student modules unchanged. One command makes at most one logical tutor
request and one bounded student step; it does not introduce an autonomous teaching
loop, new memory architecture or policy taxonomy. The existing provider may retry
each logical request up to four times. Tutor policy compliance is prompted, not
enforced or measured by this change.

Verify continuity, failure, interrupted dispatch and stale-state refusal offline.
Then retain at most one new authored live session: up to six student decisions and
one tutor request, stopping on the existing terminal states or budget. Send only
invented task/dialogue and generated continuation under the recorded standing Gemini
authorization. A tutor responds only if the generated student actually asks; do not
manufacture a question or reroll a quiet ending to make the demonstration work.

Completion is a runnable command and recorded integration outcome, with the saved
student replaying offline. This establishes interaction mechanics, not realistic
student probabilities, learning or an advantage of one tutor policy over another.
The earlier labeling-review loop, history ablation and game interface stay paused.

## Use the tutor

For a saved student whose status is `awaiting-tutor`, put the teaching policy in
a UTF-8 text file and choose a new output directory:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_tutor data/my-student --policy-file policy.txt --output data/tutor-exchange-1 --send --max-actions 3
```

The command prints the generated tutor reply and the resulting student context.
It uses the student's configured Gemini model for both roles, with separate
prompts and no shared provider conversation. `context.json` retains the exact
export; `receipt.json` contains the tutor request/response and continuation status.
The student's original operation receipts remain the source for offline replay.

An active student can continue quiet work with the existing `notebook_student step`
command. A new pending question can receive another explicit tutor command with
a fresh output directory. Each invocation permits only one tutor reply. This does
not impose a project-wide cap on tutor commands; the recorded live example below
has its own one-tutor cap. Do not change output paths to bypass an interrupted run.
Inspect both receipts first: a student operation may have begun even if the tutor
continuation record was not finalized. Infrastructure failures produce a nonzero
CLI exit status. `notebook_student show` and `tutor_context` inspect offline.

## Completed implementation and live result

`src/agents/notebook_tutor.py` now supplies this command. Five new offline test cases
cover successful continuation with exact tutor text and preserved work, context
isolation, create-only output, invalid requests, provider errors, interruption,
concurrent state changes, CLI send gating and infrastructure exit status. The
related suites pass **36 tests, with 1 container integration test skipped**. An
independent review also exercised interruption during student generation: the
completed tutor response remained saved while both continuation records stayed
pending, preventing an automatic resend. Existing student/runtime modules are
unchanged, so their saved source pins remain valid.

The new live trace is retained in ignored `data/episode-pilot/notebook-tutor-v1/`.
Its exact scope, authored inputs and standing authorization were recorded before
dispatch. A separate preflight executed known authored code successfully in the
existing immutable Babypandas 1.0.0 container. Then the following occurred:

1. The generated student answered the supplied opening tutor question by asking
   for help counting distinct values.
2. The generated tutor supplied a concise hint suggesting `nunique()`. That method
   is unavailable in the declared Babypandas library.
3. The student quietly revised the cell to use bracket column access and that
   method, then requested a check. Actual execution raised an indexing error.
4. The student switched to `get()` column access and requested another check.
   Execution raised an attribute error for the unavailable method.
5. The student revised the method to `unique()`. The fixed six-decision student
   budget ended before another check. The final code obtains distinct values but
   does not yet count them; it remains unexecuted and ungraded.

The run contains six logical student decisions, one logical tutor decision and
two student-requested executions. The separate setup check is not a student action.
There was no generated no-reply, second tutor request, replacement run or human
plausibility review. The final student remains active at revision 3 with no current
feedback; an action limit is not student silence or completion.

The whole saved student replays exactly without external calls or file changes.
The tutor's saved context and exact reply match the bound continuation operation;
the initial input/source hashes still match. `trajectory.md` gives a readable
view, while `run-summary.json` binds it to the retained receipts.

This completes the bounded interaction milestone and exposes a concrete current
limitation: the tutor can recommend an incompatible API even when its context
declares the library. Neither policy compliance nor tutor correctness is enforced
by the message schema. Actual checks make that error observable; this one trace
does not establish realistic novice recovery, learning or policy quality. Preserve
the result rather than changing prompts or retrying until the lesson succeeds.
