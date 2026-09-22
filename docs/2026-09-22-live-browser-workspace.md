# One live browser workspace walkthrough

## Fixed scope, before dispatch

Exercise the connected browser controls once on the fresh, wholly authored
`data/browser-workspace-example/session`. This is an operational acceptance check,
not another fidelity experiment. No private conversation, label or student profile
is supplied. Existing completed examples remain closed.

Use the visible browser controls on port 8427, the saved Gemini 2.5 Pro model and
prepared concise-hint policy, without an optional library reference. Each explicit
submission permits one student decision. Stop at six student decisions, two
generated tutor replies, no-reply, any error or ambiguous operation, whichever
applies first. The tutor ceiling is enforced by the operator. Never force a chat
turn, edit or check; do not resend or replace an outcome. Existing adapter retries
remain bounded at four per logical request, at most 32 attempts overall; actual
adapter/SDK retry counts are not recorded. At most six requested local checks can
run, each with the saved ten-second execution timeout and restricted container.

Freeze the initial manifest, prompt/schema, policy, implementation and immutable
runtime image before the first submission. The expected scalar remains outside
model/tutor inputs and the container worker request. Later exact prompts and
feedback are retained by the existing receipts. Authorization is the user's
current Continue and standing project Gemini approval for these authored inputs.

Acceptance: the browser displays each saved result, reopening reconstructs the
same sequence without sending, receipts respect the fixed limits, and original
inputs remain unchanged. A passing scalar check is not general correctness,
learning or student realism. Save scope, audit and replay in ignored
`data/browser-workspace-example/live-run/`; commit only this public summary.

## Result

**Complete and closed.** Three explicit browser submissions ran from 07:19:10 to
07:20:10 UTC on September 22, 2026, through the real Python/Gemini adapter:

1. Quietly revise the cell to divide the blue count by `swatches.shape[0]`.
2. Request a real local container check: revision 1 returns float `0.5`, pass.
3. Choose no-reply, leaving three decisions unused.

Three logical student requests, one container execution, zero generated tutor
requests and zero recorded errors. Actual retries are unrecorded; at most 12
adapter attempts were possible. The opening dialogue was authored. The prepared
tutor policy was never delivered because no student chat requested another turn.
This run therefore does not validate live tutor generation or communication fidelity.

The UI displayed request progress, revised source, the passing check and the
no-reply stop. Refresh reopened saved states without additional receipts, and
continuation was disabled at the terminal state. Existing offline replay exactly
reconstructs all three operations without changing session files. Every receipt
contains one model decision; only the requested check executes. The expected
answer is absent from actual model inputs.

All 18 frozen files matched at closure, before this result was appended. The
original advance protocol is preserved as `live-run/protocol.md`; the other 17
input/implementation files remain unchanged. Scope, dispatch, audit, final
workspace projection and HTML replay are retained locally. No simulator code,
prompt, labels, old example or decision budget changed. No reroll is queued.
An independent read-only audit confirmed these hashes, prompts, counts and exact
replay without dispatching providers or execution.

The engineering acceptance check passed for browser-driven student actions and
execution feedback. Student fidelity and matched baseline/grounded comparison
remain separate, unresolved research work.
