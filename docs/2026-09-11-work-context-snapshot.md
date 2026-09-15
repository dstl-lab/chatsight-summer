# Restore context, then start from a known notebook

Continue the approved recovery using the saved read-only receipts only. Add a
pure ingestion helper and an immutable supplemental snapshot for the four reviewed
cases. Preserve existing conversation indices, labels, source snapshots and frozen
experiments. Recovered exchanges use event IDs; they do not renumber old turns.

Bind the initial notebook event to a unique earlier query and matching linked tutor
response, checking conversation membership, text fingerprints and timestamps.
Reject ambiguous or conflicting recovery. Project dated cell sources with stable
original positions; retain raw captures privately and explicitly omit outputs.
At the later reviewed cutoffs, current work remains unknown. Store post-cutoff
reference checks separately from generator context and test future isolation.

For the next work-and-chat probe, initialize one synthetic branch from a recovered
initial capture and its first tutor exchange. That is an explicit chosen starting
state, not a reconstruction of later unseen work. Use one relevant assignment
section and code cell, selected from that initial encounter alone. Allow a cell
revision with optional chat, chat without revision, or no further action. Do not
execute student code or invent grader feedback. This tests the missing action
channel before extending the course executor or building a notebook framework.

Keep exact prepared requests and provenance private. Reuse the existing Gemini
adapter and record pending/completed/failed calls. Two draws of the same fixed
initial encounter are sufficient for this development check; no semantic rerolls,
response-rate estimates or fidelity claims. User standing authorization persists;
respect any automatic review of the concrete new payload.

## Implemented and verified

`src/ingest/notebook_context.py` binds initial captures to unambiguous query and
response metadata, restores event-based turn IDs and projects dated cell sources.
The four reviewed prefixes retain their old IDs. Unknown current work and null
current observations remain explicit. Recovery is intentionally limited to a
missing initial exchange or one already present; partial/conflicting histories
fail rather than being silently merged.

The current immutable supplement is
`data/episode-pilot/work-context-v1/snapshot-v2/`: initial exchanges/cells,
generator contexts and reference-only observations are separate files. It is not
a newly labeled corpus. Mutating future query/check data or follow-up text leaves
generator context unchanged. The first preparation and exact sources are retained
with a preservation receipt: independent review found a conflicting event ID
could be hidden by a duplicate turn under another ID. An invented regression
reproduced that defect; the corrected guard passes before the second snapshot.

`src/eval/notebook_action.py` initializes a synthetic branch from one selected
captured code cell and its initial exchange. A revision replaces that cell source
and may accompany a message; a chat-only action cannot change work. The original
input is preserved. No source is executed and observations remain null. A revision
with identical source is possible; compare actual text before claiming a change.
This bounded path has no grader or multi-turn course executor.

The selected initial encounter supplies one assignment markdown cell, its code
cell and the first student/tutor exchange. It precedes the later case 4 review.
Both prepared draws use the same 3,173-character prompt. No later dialogue,
reference checks, identity metadata or notebook outputs enter it. Selection uses
the initial question and adjacent cells, not the later observed continuation.
One initial student message offers little style evidence; this remains exposed
development data and cannot establish individual or cohort fidelity.

All 311 Python tests pass, including future isolation, ambiguous/cross-conversation
recovery rejection, event-ID conflict handling, silent edits, edits with chat and
chat-only preservation. One existing Starlette/httpx warning remains. A private
invented-input check verifies persisted actions, zero-send replay, pending refusal,
source/result drift rejection, and provider failures distinct from no-reply.
The two prepared draws pin 16 files, the strict schema and source snapshot metadata.

## Automatic approval review checkpoint

Sending under the recorded standing grant was rejected before process launch.
Automatic review required permission for this exact new private notebook/code-cell
and student/tutor payload to Gemini; previous specific approval covered another
batch. No model requests were sent and no results cache exists. Keep the rejection,
standing grant, prepared inputs and exact disclosure unchanged. The private
`approval-request.json` binds the pending question, model/count, experiment and
input/disclosure hashes. This additional requirement comes from automatic review,
not a withdrawal of Minchan's standing approval. Do not retry until the specific
reply is recorded. All unaffected recovery, implementation and verification work
is complete; human behavioral review follows only after actual draws exist.

## Specific approval and completed action probe

Minchan answered “Yes” to sending the exact disclosed excerpt to Gemini 2.5 Pro
for two draws. `approval-response.json` binds that response to the question,
model/count, experiment and input/disclosure hashes. It predates both calls;
the original rejection and preparation remain intact. The unchanged runner sent
the two approved requests after checking those bindings and all 16 file pins.

Both draws returned valid source revisions with empty chat text. They replaced
the same array-method call with a length-function expression and preserved the
display line. The source actually changed; these are not no-op revisions. Their
action objects and applied states are identical, so the private `review.md`
presents the action once, explicitly noting that both draws produced it. Both
individual call receipts remain available. No further student message or tutor
turn was appended to either branch.

This establishes that the model used the separate work channel without sending
a chat message in this one prepared situation. It does not establish correctness,
successful execution, grader success, realistic response probability or behavioral
fidelity. No source was executed, observations stay null and no outcome claim was
generated. The actual later notebook change remains unobserved. Human plausibility
fields are blank; the review asks whether the proposed quiet edit fits the initial
encounter, not which of two identical candidates to prefer.

Offline cache reopening reproduces both applied states without dispatch. Review
rerendering is identical; the completion receipt binds approval, results and
presentation files, verifies temporal approval and records the pending human
judgment. The four context supplements and previous experiments are preserved.
This checkpoint changes documentation and ignored evidence only; the latest
production-code test run remains 311 passing tests with the existing warning.

## Human review received

Minchan answered “Yes” to whether changing the cell without replying was plausible.
The separate `human-review-response.json` binds that answer to both identical
draws, the displayed question and the original result/review hashes. Original
blank review fields and completed inputs remain unchanged. This accepts one
action's plausibility; it says nothing about execution, correctness, action
frequency or cohort fidelity. The next step is the limited, requested-feedback
loop in `2026-09-11-notebook-check-loop.md`.
