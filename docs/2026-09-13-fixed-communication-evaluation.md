# Fixed evaluation of observable student communication

Answer one question: what communication failures and observable behavior patterns
occur across a fixed, varied set of encounters, and how much do two draws differ
within each encounter? This replaces sequential example approval with one frozen
batch and a descriptive report. It does not evaluate silent notebook work,
population fidelity, reply probability, learning or tutor-policy effects.

Use the original `student_continuation.PROMPT`, `Continuation`, Gemini 2.5 Pro and
existing provider defaults. Freeze selection, payloads, criteria, candidate order
and reporting rules before generation. No prompt tuning, better-draw selection,
case replacement or extension during the batch. Model errors and uncertain cases
are retained. The stopping point is the report after the whole review batch.

## Cases and inputs

Reuse the metadata and verified primary snapshot in `evaluation-readiness-v1`.
Exclude its 35 prior continuation conversation keys plus all four subsequently
selected recovery conversations, including the ambiguous case. This conservative
39-key exclusion leaves 43 eligible windows from 20 conversations. The available
prefix strata contain two code/error conversations, seven earlier-context and
15 concise-request conversations; strata overlap.

Select two code/error cases, then three earlier-context cases, then three concise
cases with one conversation per case. Reuse the inventory's frozen hash ranking;
earlier-context goes first because its pool overlaps concise requests. Selection
uses prefix metadata and the existence of a later contribution, never its text
or a model output. Preserve a quota shortfall rather than changing the criteria.
Save selection before extracting selected payloads or reference text.

Use only the snapshot's visible request, tutor response and at most six preceding
turns, preserving text and source line numbers while replacing IDs with local
aliases. Explicitly mark notebook work and observations unavailable. Do not
recover missing context selectively after seeing results. A reference is the
FIRST subsequent student message, not the extractor's consecutive-message block;
retain an empty first message if selected. Keep all reference text, labels,
identity metadata, previous generated replies and review feedback out of prompts.

Generate two independent draws per case: cases 1–8 for draw one, then cases 1–8
for draw two. Both receive identical inputs. Sixteen logical requests maximum,
each with the existing four-attempt adapter ceiling. Persist pending/error/retry
receipts and refuse whole-batch resends or partial resumes. No student code, DB
query or grader runs. All exact payloads, source hashes and results stay in ignored
`data/episode-pilot/fixed-communication-eval-v1/`.

## One review batch

Each case presents its exact supplied context and three candidates: the reference
and both draws, in a preassigned order with origins stored separately. Use one
Markdown packet; keep origins concealed until all judgments are recorded. This
is limited concealment, not guaranteed blinding: previous exposure and a no-reply
or generation error can reveal origin. No new interface is needed.

For each actual message, record context fit (plausible, implausible or uncertain),
the existing v7 follow-up category and the existing v7 task relationship. The same
criteria apply to references. A different continuation can be plausible; matching
the reference is not correctness. Keep the v7 substantive-work precedence and
earlier-STUDENT-code requirement for a revised-code judgment. Require a short
evidence note for implausibility, revised-code and definite task relationships.
Unknown judgments are permitted; blank means not yet reviewed, not a rejection.

Generated no-reply and model errors are separate dispositions with no inferred
message rating. An empty recorded message is a present contribution and may be
insufficient evidence; it is not a no-reply decision. References with poor fit or
uncertainty may expose missing context and must not be silently discarded.

## Report and decision

Report all 16 scheduled requests: replies, no-reply choices and errors. For each
of the eight cases, show zero, one or two human-rated plausible generated replies,
alongside implausible, uncertain, unrated, no-reply and error counts. A zero with
missing judgments is not a failure verdict. The case is the unit; two draws are
correlated and are never treated as 16 independent students.

Show v7 category counts for references and generated replies with their explicit
judged/unknown/missing denominators. Show category equality with the reference
only where both judgments are known, as a descriptive comparison, never accuracy.
Make no aggregate pass threshold or population estimate from eight cases. Report
the complete failure/uncertainty notes before considering any targeted change.
Do not pool these results with earlier qualified or relative plausibility reviews.

A pre-generation offline check must cover target isolation, unique-case selection,
quota shortfalls, identical draw inputs, retained failures, hidden origin mapping,
first-message reference selection and honest summary denominators. Replay saved
results without dispatch. Review judgments are a separate editable file; validate
all 24 case/candidate keys and allowed values without overwriting original blanks.

The existing readiness inventory documents prior exposure in every local snapshot;
these are newly selected continuation cases, not a pristine holdout or independent
learners. Reply-selected encounters cannot calibrate when students reply. Missing
linked notebook revisions and observation boundaries still prevent validation of
silent-work trajectories. Broader claims need suitable real observations and
independent human validation; no classifier is admitted by this batch.

## Implementation

Reuse snapshot extraction, dialogue projection, v7 definitions, provider adapter,
atomic receipt writer and review fencing. The private `prepare.py` selects and
freezes inputs/protocol; `run.py` sends or replays; `review.py` renders and summarizes
separate judgments. Small invented checks cover these boundaries. Production
modules and completed experiments remain unchanged. Record standing authorization
and any actual approval-review rejection separately; update draft PR 25 without
merging it.

## Prepared batch

All eight slots are filled without changing the frozen quotas. The exact prompts
contain 3,957, 8,216, 8,562, 8,323, 8,105, 7,716, 5,149 and 4,499 characters;
each is reused unchanged for its second draw. All 50 preparation hashes verify.
Replacing every selected future and adding human-feedback canaries leaves all
inputs unchanged. One source episode has eleven consecutive follow-up messages;
its reference remains only the first, as specified before extraction. The other
seven have one follow-up message each, and all selected first messages are nonempty.

The three invented checks pass, covering selection, exact preparation/runner
integration, retained retry/error receipts and review/summary behavior. The runner
check uses 19 fake provider attempts and no real calls. Summary checks preserve
reference as well as generated context-fit ratings, including uncertainty without
notes. A partial review prints pending counts and cannot write a final summary.
An independent source audit confirms the selection, local-ID projection, identical
draw inputs, exclusions and runner settings without inspecting reference wording.
Production code and completed experiments remain unchanged.

Automatic approval review initially rejected the send before process launch,
requiring authorization naming these private prefixes and the Gemini destination
despite the recorded standing grant. That rejected attempt made no model request
and created no results or execution receipt. The private `send-blocked.json`
preserves the rejection and seven evidence hashes. Minchan subsequently approved
the exact eight-prefix, sixteen-request disclosure; `approval-response.json`
records the reply and seven evidence links before every call. Preserve both
records and the original standing grant.

## Generation complete; human review pending

All sixteen requests completed and selected reply, with no errors or retry
notifications. The original prompt, paired inputs and request order stayed fixed.
No student code ran and no notebook observation was supplied. Exact offline replay
and all 50 preparation hashes verify; the eight-case review renders identically
twice. The original 24-row `review.json` remains blank, with a separate editable
`judgments.json` copy. Its initial pending summary reported 24 messages awaiting review and
72 missing ratings; it creates no final summary files. An independent audit confirms
the receipts, approval timing, all candidate mappings and first-message references.
The completion record binds 18 artifact hashes; its audit's judgment-file hash is
explicitly an initial blank snapshot, since later human edits are expected.

The private `REVIEW_START.md` explains the three judgments and links to the whole
`review.md` packet and a blank reply template. Plain-English feedback in chat is
accepted and recorded separately. Candidates retain their preassigned A/B/C order;
origins stay concealed until the whole batch is reviewed. Review may arrive in
parts, but no prompt tuning or case substitution occurs between judgments.

Successful generation supplies candidates for evaluation, not evidence that their
behavior fits students. The next milestone is the frozen descriptive report after
all eight cases have human judgments; uncertainty is a valid judgment, and missing
ratings remain missing.

## First human feedback received (2026-09-14)

Minchan commented on all eight cases. Cases 2/4/5/6/7/8 explicitly allow all three
candidates as possible; these supply 18 plausible-fit entries, without equal
probabilities. Cases 1/3 express preferences for A/C respectively; their six
absolute fit fields remain blank pending clarification. No candidate was explicitly
rejected. Keep capitalization concerns in cases 4/5, the qualified lower preference
for case 7 A and sparse-context uncertainty. Case 7's responding-trend explanation
is retained verbatim without resolving its ambiguous direction.

The exact reply and seven evidence hashes are preserved separately in
`human-review-response-1.json`; only the editable `judgments.json` receives the
supported fits and notes. No follow-up action or task-relationship judgments were
supplied, so all 48 category fields remain blank. The current pending summary has
24 incomplete rows and 54 missing ratings; no final report is produced. Relative
preference is not rejection, uncertain likelihood is not implausibility, and
assistant-inferred categories must not be passed off as human labels.

The private `review-remaining.md` groups the missing fields and permits shared
answers across candidates where applicable. Existing comments need not be repeated.
Keep candidate origins concealed, generation frozen and the original review packet
unchanged until the remaining human judgments arrive. No additional model calls,
prompt changes, behavior score or category-equality conclusion follows from this
recording step.
