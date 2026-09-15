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
question and five preparation-file hashes. That rejected attempt made no model
calls and created no results or execution receipt.

## Approved run and review

Minchan subsequently approved sending these exact three requests. The separate
private `approval-response.json` records the reply and binds the unchanged
experiment, input, disclosure, original authorization and rejection. Approval
precedes all three calls; the original preparation and rejected attempt remain
unchanged.

All three requests completed without retry notifications and selected a reply.
No student code was executed and no current notebook observation was supplied.
The generated messages contain no explicit claim of a new run, pass or runtime
error. Their behavioral plausibility remains for human review; these receipts
do not establish correctness, reply probabilities or learning.

Exact offline replay passes against all 35 preparation pins. The three review
pages render identically on repeat; fourteen completion-file hashes bind the
results, approval, original rejection and presentation. An independent audit
verified all hashes, five approval links, call timing, source text and candidate
origin mappings. Human judgment fields remain blank. The previous private checks
cover this unchanged runner/reviewer; no additional full-suite run is warranted.

Review cases individually, beginning with case 1. Both A and B are messages sent
to the tutor, and both may be plausible. Present the current exchange and exact
candidate text directly in chat when useful, with the full historical context
available in the private case page. Keep the origin key separate until the
judgment is recorded. Case 2 remains excluded because its initial query link is
ambiguous; do not replace it or infer a judgment for it.

Minchan tentatively preferred case 1 A over B: the tutor had already supplied the
complete function, making sending it back unnecessary. This is a relative
preference, not an explicit implausibility verdict for B or an absolute verdict
for either candidate. The separate private `human-review-case-1.json` preserves
the exact reply, qualification and six evidence hashes. Original blank review
fields and completed results remain unchanged. Cases 3 and 4 still need review;
case 3 is prepared for the same inline presentation. No model call or prompt
change was made while recording this feedback.

On September 13, Minchan preferred case 3 B conditionally: its likelihood depends
on an earlier pattern showing that the student knows the tutor can see the
notebook. The separate private `human-review-case-3.json` records the exact
qualification and seven evidence hashes, without assigning an absolute verdict
to either candidate. In the already-supplied prefix, the student refers to the
exercise without pasting code and the tutor responds about specific code. This
is consistent with shared notebook context; explicit student awareness and a
broader historical trend remain unknown. This check uses no future messages,
new source queries or model calls. Case 4 is the only remaining review, prepared
inline; all original artifacts and generator behavior remain unchanged.

Minchan judged case 4's two messages equivalent. Record no preference and no
absolute plausibility verdict; equivalence does not itself mean acceptance. The
separate `human-review-case-4.json` binds six evidence files, and
`human-review-summary.json` closes all three comparisons. With origins revealed
for analysis, the recorded message was preferred tentatively in case 1 and
conditionally in case 3; case 4's recorded and generated messages were equivalent.
No binary accuracy or acceptance count is warranted.

The generated candidates in cases 1 and 3 sent supplied solution code back as
chat. This motivates testing whether the prompt's broad word "contribution"
leaves the communication channel unclear. It does not prove that mechanism or
justify banning code, inventing notebook access or inferring student knowledge.
The [next bounded comparison](2026-09-13-communication-channel.md) keeps these
exposed inputs fixed and tests an explicit chat-only interpretation against fresh
original-prompt controls. Original review artifacts and prompts stay unchanged.
