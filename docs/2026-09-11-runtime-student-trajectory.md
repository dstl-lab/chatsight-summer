# Connect student actions to declared-runtime feedback

The isolated cell checker is verified. Connect it to one new authored student
trajectory while preserving the older loops, prompts and completed traces.
Reuse the existing action schema and source-edit function; add only a small
session state transition and a runtime-aware prompt. A private experiment runner
owns bounded iteration and recorded dispatch. Do not monkeypatch or copy the old
production loop into a new general runner.

An initial state declares its branch identity, table library/version, immutable
image, supplied task/data, work revision and execution timeout before any model
choice. The prompt shows the task, library/data, work, visible feedback and
history, without internal image IDs or provenance hashes. The model chooses one
existing action: revise-work with optional chat, request-check, reply or no-reply.
Only requested checks execute source. Revisions clear current feedback; a reply
ends awaiting a separately supplied tutor. Runtime errors remain ungraded and
may inform a later choice. Environment errors and execution limits end this probe
as such, without another model call or invented student response. Reject stale
or internally inconsistent observations before installing them.

The first live probe uses entirely authored shade-counting data and Babypandas
1.0.0. Its initial method incompatibility and first requested check are scripted
by the researcher, not model actions. Compute and save that runtime-error prelude
before constructing the first model request. Under the standing Gemini approval,
allow at most three model decisions, with no tutor bridges, rerolls or forced
correction. A terminal message, no-reply, model/error condition or cap stops it.
This tests the action mechanism after actual execution feedback; it cannot
establish that real students would make or recover from this particular error.

Save pending receipts before model and container dispatch; preserve full requests,
responses/errors, origins and timestamps. Pin the exact initial prompt, schema,
inputs, prelude, authorization and all executed helper sources. Replay consumes
saved model and container observations with no provider or Docker calls, checks
current-state bindings, exact trace equality and receipt counts, and refuses
changed or incomplete evidence. The public regression uses invented inputs and
injected checks. The live artifacts and all generated text remain ignored.

## Preparation

The new `src/eval/notebook_session.py` reuses the frozen action schema and edit
function. Its transitions and runtime-aware prompt are tested; no older module
changed. Review exposed one evidence-validation gap, now fixed: matching hashes
alone cannot admit a scenario pass as executed feedback. Checked answers and
runtime errors require completed execution in the declared container runtime.

The initial preparation stopped before code execution because Docker's image
inspection timed out. Its backend log showed an idle-VM shutdown stall. Native
restart also timed out; restarting only the stalled Docker app processes restored
the engine without changing its image. The original `prelude.json` is preserved.
A separate `prepared-prelude.json`, on a separately named branch, then records
the actual Babypandas AttributeError with null success. No model call preceded
either preparation attempt; this is not a semantic reroll of student behavior.

All 25 preparation pins verify, including both attempts, the standing grant,
initial prompt, source helpers and runtime image metadata. The private runner
regression uses eight fake model calls and two fake checks, with zero provider or
Docker calls. Pending receipts, error replay, retry notifications, action cap,
environment stop and changed/incomplete/extra evidence refusal pass. The frozen
provider adapter permits up to four attempts per logical decision, including
schema-validation failures; retry notifications are retained in its pending
receipt. The full suite passes 321 tests with the existing Starlette/httpx warning.

## Live result (2026-09-12)

The fixed probe completed under standing approval with three logical Gemini
2.5 Pro decisions and no retry notifications. After the scripted runtime error,
the model silently replaced the incompatible expression with a supported distinct
count, requested its check, received an actual container result of 3 and passing
feedback, then chose no-reply. The initial error/check was scripted; the edit,
subsequent check request and no-reply were model choices. No tutor bridge or chat
message occurred. No-reply was explicitly selected, not inferred from a cap.

The requested check executed revision 1 inside the same declared Babypandas
1.0.0 image. Its completed observation binds that exact source/revision, branch,
activity, checker and timeout, with recorded Python/library versions. Revision
cleared the previous error before the new request. The next prompt received the
passing observation; no unobserved course result was supplied or asserted.

All 25 preparation pins and six execution-file hashes verify. The complete state
and requests reproduce exactly offline with zero Gemini or Docker dispatch.
Earlier notebook-runtime, notebook-check, notebook-failure and worksheet-failure
artifacts still verify/replay with 13, 31, 17 and 14 pins. The failed preparation
remains separate from this completed trace. Generated text and exact receipts
remain under ignored `data/episode-pilot/runtime-student-v1/`.

This completes one execution-backed action/state example: runtime error -> quiet
revision -> requested pass -> chosen quiet stop. It does not show that real
students would select this error, correct it immediately, or stop at this rate.
The task and dialogue are invented, and the first error was imposed. No new human
plausibility judgment, cohort fidelity, course transfer or learning claim follows.
The next research bottleneck is behavior under realistic task/work context, not
another code-execution mechanism or broader label taxonomy.
