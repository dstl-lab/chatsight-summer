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
receipts and refuse whole-batch resends or partial resumes. No code, DB or grader
runs. All exact payloads, source hashes and results stay in ignored
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
