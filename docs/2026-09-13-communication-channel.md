# Distinguish a chat message from a notebook edit

The completed historical-context comparison preferred recorded next messages
over generated code messages in two cases, with explicit qualifications; the
third pair was equivalent. This is a development diagnostic, not an accuracy
score. A possible mechanism is ambiguity in asking for a student "contribution":
code that belongs in the notebook can instead appear as a message to the tutor.
The existing notebook-action path already separates edits from optional chat.
Test the communication prompt before changing the simulator or adding machinery.

Reuse the same three exact inputs from `evaluation-communication-v1`, cases 1,
3 and 4. Keep historical notebook cells, dialogue, unknown current work and
observation, schema and Gemini 2.5 Pro defaults unchanged. Make six fresh calls:
original/clarified for case 1, clarified/original for case 3, original/clarified
for case 4. Prior generated responses and human feedback never enter the inputs.
Case 2 remains excluded without replacement.

The clarified condition inserts only this paragraph before the unchanged JSON:

> For decision "reply", text contains only what the student would send to the tutor
> in chat. It does not represent an unsent notebook edit. Code belongs in text
> when the proposed action is sending that code to the tutor.

Code, substantive answers and no-reply remain permitted. Do not assert that the
student knows the tutor sees notebook changes, forbid repeating code, prescribe
a question number or add a brevity rule. Neither condition reconstructs silent
work, executes code or invents feedback. This remains a communication-only probe.

Use the existing continuation schema, provider adapter, atomic receipt writer
and review formatting. New private scripts and exact disclosure stay under
`data/episode-pilot/communication-channel-v1/`. Verify source hashes and identical
JSON across conditions; persist pending records before credentials or provider
creation, retain errors/retries, refuse resends and replay offline. Record the
standing grant and actual continuation instruction without fabricating exact
payload approval. Preserve any actual automatic rejection separately.

Show one case at a time with condition names hidden and exact shared context.
If the two new responses are identical, show them once while retaining both
receipts. Human review determines plausibility; reduced code length or agreement
with a recorded message is not an automatic improvement. One draw per condition
on three exposed cases cannot estimate distributions or establish a causal effect.
Keep the original production prompt unless stronger evidence warrants a change.

## Prepared comparison

All six exact requests are prepared, containing 10,242, 10,462, 8,901, 8,681,
13,301 and 13,521 characters in the declared order. The sole insertion is 220
characters including its leading newline. Baseline prompts match the previous
inputs exactly, and each pair has byte-identical JSON. All 43 preparation file
hashes verify; no current work or observation has been filled in.

The invented runner check passes with five fake provider calls and zero real
calls. It checks pairing, pending records before credentials/factories, retained
errors/retries, source drift, resend refusal and strict offline replay. The
reviewer check includes the actual runner's prompt construction, exact shared
context, hidden condition mappings, no-reply/errors, identical-candidate display
and preservation of human edits. An insertion-newline mismatch found during
review was corrected before preparation and is covered by that integration check.
Production modules and all completed experiment artifacts remain unchanged.

An independent audit confirms all 43 hashes, six exact prompts and their declared
order, the 220-character insertion, identical paired JSON, fixed schema/settings,
full disclosure and accurately scoped authorization. No prior generated answer
or human feedback entered the requests.

Automatic approval review rejected the actual send before process launch. It
requires separate approval for these six newly prepared private dialogue and
notebook payloads despite the preserved standing grant and instruction to
continue. The private `send-blocked.json` records the actual rejection, exact
approval question and six evidence hashes. That rejected attempt made no model
request and created neither results nor an execution receipt.

## Approved run and review

Minchan subsequently approved these six exact requests. The separate private
`approval-response.json` binds the reply to the unchanged preparation, disclosure,
original authorization and rejection. Approval precedes all six calls.

All six requests completed without retry notifications and selected reply.
Case 1 pairs a short acknowledgment with a complete function. Case 3 pairs the
same function with formatting differences; both omit the column-update expression
that appeared in the preceding batch. Case 4 pairs two requests to check answer
choice 2, one expressed with an assignment fragment. These remain chat messages:
no notebook state was changed, no code executed and no correctness established.

Exact offline replay passes against all 43 preparation pins, and the three review
pages render identically on repeat. Fourteen completion-file hashes bind the
results, approval, prior rejection and presentation. All new human fields remain
blank; the original prompt is retained. Formatting or a shorter response does not
establish better behavior, and this batch cannot establish a causal wording effect.
An independent audit confirmed all preparation/completion hashes, five approval
links, six rejection links, approval before every call, exact candidate mappings
and unchanged rendered outputs. No human judgment was inferred by these checks.

Begin with the new acknowledgment in case 1, shown directly in chat with the
student's language and current exchange for context. The other draw repeats the
previous function structurally, but it receives no transferred human verdict.
Keep both receipts and full context available while focusing the first question
on the new acknowledgment. Cases 3 and 4 remain available for subsequent review;
condition names stay hidden until judgment is recorded.

Minchan accepted the shown case-1 acknowledgment as plausible because the student
had asked in Chinese. The separate private `human-review-case-1.json` records
that judgment and six evidence hashes. It applies only to candidate A; candidate
B receives no comparative verdict, and no causal prompt benefit or acknowledgment
frequency is inferred. Original blank fields and completed artifacts stay intact.
Next show case 3's function once, explicitly noting the spacing differences
between its two candidates, and ask about sending it as a chat message.

Minchan accepted that shared function-sending behavior as plausible. The separate
`human-review-case-3.json` preserves the raw reply and six evidence hashes as one
grouped judgment, without a spacing or prompt-condition preference. This does not
revise the earlier conditional preference for a short check in the preceding
experiment. Case 4 is the last pending comparison; case 1 B remains unjudged.
No new model call or prompt change was made while recording this feedback.
