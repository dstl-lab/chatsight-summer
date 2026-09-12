# Compare communication with recovered historical context

Use the fixed evaluation candidates after context recovery. Cases 1, 3 and 4
have aligned initial context; case 2 has two matching unlinked initial queries
and stays excluded. Do not replace it. This development sample was selected
conditional on a recorded next contribution, with prior corpus exposure. It
cannot estimate whether or when students reply, or count silent notebook actions.

Make one fresh Gemini 2.5 Pro request per recovered case under Minchan's standing
model-run authorization and explicit instruction to continue until review is
needed. Reuse the frozen student_continuation PROMPT, Continuation schema and
provider defaults. Preserve its reply/no-reply choice; do not force an answer or
infer that a generated no-reply contradicts a logged contribution. The new input
is the recovered visible dialogue plus an explicitly historical notebook excerpt,
with current notebook work and current observation null. Tutor claims about
correctness or errors remain dialogue, not execution evidence.

Select cells using only the visible prefix: case 1 cells 59/60; case 3 cells
139/140/144/145; case 4 cells 66/67/85/86/88/89. These cover the referenced
assignments, captured code and, where relevant, the next question already
introduced by the current tutor. Preserve source text and capture date. Omit
outputs, CSV contents and unrelated cells. A code excerpt pasted in a later
student message stays in that message; it does not update the historical capture.

Keep reference next messages and all post-response check records outside the
generator input. Mutation checks must confirm this separation. Hash the exact
augmented prompt sent to Gemini; the ordinary dialogue-only review helper's
recomputed prompt is not its provenance. Pin direct source/config/input files,
retain pending and error/retry receipts, refuse resends and replay offline.
All private prompts, generated replies, reference text and reviews stay ignored
under `data/episode-pilot/evaluation-communication-v1/`. No production helper or
completed experiment changes.

Show one case at a time with the same visible dialogue and historical context
for both recorded and generated candidates. Hide candidate origin in the first
view, preserve the key separately, and leave all human fields blank. Ask whether
each message is plausible, implausible or uncertain; both may be plausible.
Generated no-reply is presented separately as a synthetic branch ending, without
invented student text or a reply-rate score. This is an exposed developmental
comparison of communication, not classifier admission, a fidelity score, a
learning outcome or a simulated full student trajectory.

## Prepared comparison

The three exact prompts contain 10,242, 8,681 and 13,301 characters. Historical
cell sources and capture dates are preserved; later submitted code remains in
dialogue. Raw event identifiers are replaced by local sequential turn aliases
without changing wording or line numbers. Current work and observation remain
null, and no reference followup or check records enter the payloads.

All 35 preparation pins verify, including recovered context, the original prompt,
schema, provider settings, standing authorization and exact disclosure. The
private runner check passes with two fake provider calls and no real calls; it
checks input projection, exclusion, pending receipts before credentials, factory
errors, retry retention, replay and refusal to resend or accept changed sources.
The separate invented reviewer check covers supplied history/code, origin mapping,
blank judgments, no-reply/errors, robust fences and immutable rerendering. No
production module changed and no full-suite rerun was needed for this preparation.

An independent audit confirmed all 35 pins, exact selected sources/dates,
unchanged dialogue apart from local aliases, disclosure equality and exclusion
of future observations and source identities from the requests.

Automatic approval review then rejected dispatch before process creation. It
requires approval of these exact private student dialogue/code payloads going to
Gemini, despite the standing authorization and latest instruction to continue.
The private `send-blocked.json` preserves the actual rejection, exact approval
question and five preparation-file hashes. No model calls occurred and no
results or execution receipt was created. All preparation and checks are complete;
the next required user action is this specific send approval. Keep the rejection
and original authorization unchanged, record any later explicit reply separately,
and do not reroute or retry the blocked send without it.
