# Run a bounded student–tutor encounter

The saved student can act on different scalar tasks, but a caller still has to
alternate student steps and tutor replies manually. Minchan directed continuation
after the task-portability increment. Add one thin command that performs that
alternation using the existing saved student, tutor and runtime. This is an
execution convenience, not a new student model or a fidelity benchmark.

When the student is active, request one existing student action. When awaiting a
tutor, generate one existing state-bound tutor reply and one student action. Stop
on a terminal student state, the session's cumulative student-decision budget,
or a separate tutor-reply cap when another tutor reply is needed. Quiet work may
continue after the tutor cap. A passing check does not itself end the encounter;
the student can continue, communicate or choose no-reply. Budget pauses remain
separate from that choice. Use the session's declared model for both agents.

Keep all dispatch and replay handling in the current APIs. The runner writes one
create-only `lesson/` directory inside the session, with its inputs/source hashes,
pending/completed/error status, tutor exchange receipts and final summary. A
second invocation for that session refuses to resend, including after interrupted
tutor generation. There is no automatic resume, output-directory override or new
scheduler. Explicit continuation remains available through the existing student
and tutor commands after inspecting the receipts. Validate the policy, cap and
optional matching library reference before creating output or spending calls.

Check the complete alternation, both budgets, failure/interruption boundaries,
answer isolation and CLI with injected adapters. Then run one fresh, authored
category-proportion task with at most six student decisions and two tutor replies.
Only student-requested checks execute code. No rerolls, prompt changes during the
run, or human plausibility-review batch. Record whichever stop occurs, including
no requested tutor turn. Standing project model authorization applies; the
existing provider's retry policy remains unchanged.

This increment does not add cross-task memory, latent skill estimates, personas,
learning dynamics or another course runtime. It makes the existing mechanism
usable as one bounded interaction. Earlier source-pinned modules and completed
experiments remain unchanged; all live inputs and receipts stay in ignored data.

## Run the existing student automatically

After creating a saved student with its task, activity, optional evaluation and
cumulative `--max-decisions` budget:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_lesson data/my-student --policy-file data/policy.txt --max-tutor-turns 2 --send
```

Supply `--reference-file data/reference.json` for the same library/version-matched
API note accepted by the tutor command. Without `--send`, the command makes no
provider calls. Use `notebook_student show` or `tutor_context` for offline replay
and inspection. Both agents use the saved session's model; a lazy provider is
created only if a decision is actually requested.

The command records `data/my-student/lesson/receipt.json` before dispatch and
stores tutor exchanges beneath that directory. Existing student operations stay
at the session root. It can run once per session; repeated invocation refuses to
resend even if the preceding call was interrupted. There is no output-path option
to bypass that protection. Existing explicit student/tutor commands remain
available for a deliberate continuation after inspecting prior records.

`student-budget` and `tutor-budget` are runner stops; the saved student can still
be active or awaiting a tutor. `no-reply` is a generated terminal action. Errors
and execution limits remain separate, and the CLI exits unsuccessfully for those
failures. A successful CLI exit or passing local check is not a learning result.
The tutor cap accepts zero to ten replies; zero still permits quiet student work.

## Offline validation

Six focused tests cover two consecutive tutor exchanges, private evaluation and
reference isolation, quiet work after the tutor cap, continued action after a
passing check, cumulative student usage (including failed model requests),
terminal/error distinctions, interrupted tutor refusal and input/CLI guards.
The related suite reports **50 passed, 2 skipped**. The two optional container
integrations were not rerun for this scheduling-only change. Independent code
review found no actionable issue. The existing student engine, tutor, prompts,
runtime worker and legacy source pins are unchanged.

## Completed live encounter

One fresh authored category-proportion session used Gemini 2.5 Pro with a maximum
of six student decisions and two tutor replies. It completed five decisions:

1. A quiet source revision selected matching rows and attempted a proportion.
2. A requested container check raised `TypeError`: the Babypandas DataFrame did
   not support the submitted length operation. Correctness remained ungraded.
3. A quiet revision changed the row-count operation.
4. A requested check returned `0.5` with passing scalar feedback.
5. The student chose no-reply, with one decision still available.

The selected cell ended at revision two. There was no generated chat and therefore
no generated tutor reply or delivery of the optional tutor API note. The runner
did not manufacture a tutor turn or repeat the run to exercise that path. Offline
tests cover two tutor exchanges; this live trace establishes the autonomous quiet
work/check/stop path on the new task. The supplied initial tutor turn remains
authored context. No claim about realistic student frequencies, learned ability
or teaching effects follows from this result.

The five logical student generations and two requested checks are retained in
`data/episode-pilot/notebook-lesson-v1/`, alongside the pre-dispatch plan, exact
authored inputs, source hashes, readable trajectory and run summary. No real
student data was sent and no human plausibility review was requested. The provider
retained its existing retry policy; receipts count logical calls rather than
independently recording every transport attempt.

The final state replays exactly without external calls or changed session files.
All prepared input/source pins match, both original saved sessions still replay,
and all eight prior live-tutor artifact hashes verify. This increment is complete;
the earlier generated traces and fixed budgets remain intact.
