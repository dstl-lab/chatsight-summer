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
