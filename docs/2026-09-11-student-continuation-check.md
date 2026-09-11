# Frozen-prompt student continuation check

Minchan accepted the displayed revised wording and code attempt. Keep the current
style-comparison prompt, Gemini 2.5 Pro, response schema and generation settings
unchanged. Two accepted development examples do not establish a reliable student
model; the next useful check spans other conversations.

Prepare eight existing holdout windows from the same immutable snapshot, each from
a distinct conversation outside the twelve development conversations. Exclude known
prior review and model-validation exposures, including deferred D–E. Historic
message-audit exposure remains uncertain; do not call the material pristine or
learner-disjoint. Require an observed nonblank next student contribution for the
later descriptive reference comparison. This conditions the sample on a recorded
reply and cannot calibrate non-response.

Before inspecting target reply text or generating, select deterministically from
visible prefix structure: three windows containing a student code-opening cue,
two with no earlier context, and three remaining windows with earlier context.
Rank within each stratum by a fixed seed and episode ID. Code cues are retrieval
features, not behavior labels. Preserve complete eligible-pool metadata and all
exclusions. Fail preparation if the quotas cannot be met; do not silently change
the sample after viewing replies.

Prepare two stateless draws per selected window. Inputs contain only the existing
prefix projection and frozen prompt, with no future replies, labels, human feedback,
or examples from targets. Save reference contributions separately. Reuse the
experimental generation helper, its output validation and durable call cache; keep
the preparation and runner under ignored data. Preserve every generated draw and
any failures. No notebook state, trait profile, cohort, policy replay, or admitted
label state space is created.

Human review will show the full available prefix and assess each generated reply
independently: plausible, implausible, or cannot assess; an explanation is optional.
Do not rank replies for correctness or polish. Incomplete work can be plausible.
Display identical draws once while retaining their two-draw provenance. Keep the
recorded next reply hidden until judgments are saved, then compare observed actions
descriptively. A recorded reply is one possible outcome, not the only valid answer.
Report case-level findings and uncertainty across eight contexts, not an accuracy,
cohort-fidelity, learning, non-response, or causal score. If these results motivate
prompt changes, retire these cases to development use.

The earlier authorization covered twelve development prefixes sent to Gemini. This
new set lay outside that scope. Prepare the complete reviewable disclosure and
offline verification first; do not send these eight prefixes until Minchan approves
that concrete extension. This permission boundary comes from the earlier saved
disclosure scope, not from a requirement to reapprove the same development calls.

Preparation is complete in `data/episode-pilot/student-continuation-check-v1/`.
The known-exposure audit excludes 23 conversations, leaving 24 original holdout
windows; eleven have a nonblank recorded follow-up. The frozen prefix-only strata
select eight of those eleven. Their source dialogue totals 36,850 characters;
the eight full prompts total 59,974 characters and would each be used twice.
`disclosure.md` contains every exact prompt; `references.json` is separate.

Experiment `c9b0928da5f67493b4c758da3b3b9ebf0de55d2b5536e6b367da656bcf10dc2f`
pins 308 files and preserves the accepted generator unchanged. Offline checks
passed for deterministic selection, future isolation, schema/config parity,
separate caches and the approval guard. Missing approval stops the send path before
credential loading, client construction or result writes. At preparation, no request
from this set had been sent. The pending `approval-request.json` was retained as a
historical record; the subsequent explicit approval was recorded separately.

Minchan explicitly approved this prepared extension. The exact response is saved
in `approval-response.json`, bound to the unchanged approval request and its eight
prefixes. The sixteen frozen requests are now authorized. Keep the preparation
receipt unchanged as a historical record. Generate the review from inputs and
saved outputs only, retaining the actual reference replies separately until human
judgments have been recorded. Do not offer semantic judgments about these new
outputs before that review.

Generation is complete: all sixteen logical requests have saved, structurally valid
continuations; no logical requests failed. The frozen prompt and all 308 file pins
still match. Individual adapter retry attempts are not separately logged, so these
counts describe logical requests, not transport attempts.

`review.md` shows eight cases and fifteen distinct candidates: the two identical
draws in case 8 share candidate 8A. Every draw remains represented in `reviews.json`,
with all human judgments initially null. Earlier context is expandable, and recorded
follow-ups are absent from the presentation. Renderer checks cover source formatting,
duplicate provenance, failures, no-reply, incomplete batches, and preservation of
existing human answers. `completion-verification.json` records artifact hashes and
the completed-cache verification. Human plausibility review is the next step;
structural validity does not establish behavioral fidelity.

Human review is now saved in `human-review-response.json` and applied to both draws
as explicitly requested. Cases 1, 5, 7, and 8 were unqualified plausible; 2, 3, and 4
were implausible. Case 6 retains the stated plausible verdict together with the
qualification that it leans implausible and lacks prior coding evidence. It is not
an unqualified acceptance. These are eight judgments, not sixteen independent cases.

The main revision hypothesis concerns what students choose to communicate. Cases 2
and 3 were rejected for narrated reasoning or answering a tutor probe where visible
student contributions mainly submit work or ask for help. After saving the judgments,
the recorded next contributions showed a code-only answer in case 2 and a new task
question in case 3. Case 4 is a counterexample to assuming silence: the recorded
student acknowledged the tutor and requested an overall work check. Keep the human
verdict separate from this descriptive comparison. In case 6 the recorded next turn
requests a check without showing code; neither that text nor the shown prefix supplies
the missing notebook history or verifies an edit.

Continue with a single prompt insertion about communication behavior, holding the
eight prefixes, model, schema, settings, and two draws per case fixed. Reuse all cases,
including accepted code and question-answer cases as regression checks. The insertion
must not require terse replies, mistakes, or non-response; it must not turn a tutor
question into an obligation, narrate off-chat work by default, invent execution
results, or confuse delayed work with no further message. No target reply, per-case
human verdict, or prior generated answer enters the prompts. Prompt tuning cannot
recover unavailable workspace evidence. These eight cases are retired to development;
improvement here will not be a new holdout result.

The bounded comparison is prepared under `interaction-comparison/`, with the same
eight dialogue payloads, provider, model settings, schema, and sixteen planned calls.
The added generic instruction is 673 characters; all source JSON is unchanged.
The earlier exact approval receipt remains unchanged. No comparison outputs exist.

Sending under the standing continuation instruction was attempted, but automatic
approval review rejected process creation: it requires explicit approval for these
additional requests with the changed prompt. No requests were sent. Preserve that
rejection and the earlier preparation in `blocked-attempt.json`; the new
`approval-request.json` specifies the exact additional batch and disclosure. The
send path now requires a separate explicit response bound to that request before
credentials or model calls. Preparation and offline checks are complete; additional
batch approval is the only immediate dependency. After generation, stop for human
review of the new candidates before further tuning.

Minchan then explicitly approved the prepared batch and granted standing approval
for continued model runs: "Yes, you always have the approval. Make sure to log this."
The exact response is saved in `interaction-comparison/approval-response.json`, bound
to the unchanged additional-batch request. `CLAUDE.md` records the standing instruction
so routine new batches and prompt iterations in this project do not trigger repeated
approval requests. The earlier rejection and pending preparation remain historical
records; the current batch is authorized. Human plausibility judgments remain separate.

The authorized interaction comparison has completed: sixteen saved, structurally
valid continuations and zero failed logical requests. All 319 frozen pins verify;
experiment `adad8d02ee2aab8fb4a1215cb9eef7e867cafaaab41005866db480bb3ed98a7d`
is unchanged. `interaction-comparison/review.md` presents fifteen distinct candidates
across the eight cases, with every draw represented in `reviews.json` and all new
human judgments initially null. One case verdict may cover both draws when appropriate.
`completion-verification.json` records the completed cache and review provenance.
The original human review remains intact. These are development cases; the remaining
step is human plausibility review of the new outputs before any further tuning.

In-chat review has started with case 2. Minchan described A as unlikely and B as more
likely, explaining that students generally would not spell out their full reasoning.
The exact response is saved in `interaction-comparison/human-review-case-2.json`.
A is normalized as implausible with that interpretation stated; B retains a comparative
preference without an inferred unqualified acceptance. Both candidates have recorded
feedback. Case 3 was subsequently accepted with an explicit yes, saved in
`interaction-comparison/human-review-case-3.json`; its identical candidate represents
both draws. Case 4's two replies were accepted as plausible conditional on a reply,
while whether the student would actually reply remains unknown; this qualification
is preserved in `interaction-comparison/human-review-case-4.json`. Keep the first
batch's rejection unchanged and do not attribute the conditional acceptance to a
prompt effect. Case 5's two candidates were explicitly accepted as plausible,
recorded in `interaction-comparison/human-review-case-5.json`.
Case 6 received a preference for A over B because the student has been sending short
checks, recorded in `interaction-comparison/human-review-case-6.json`. Both categorical
judgments remain unset: this comparison does not establish unconditional acceptance
or rejection, resolve the missing coding history, or show a preference for code errors.
Case 7's two candidates were accepted as plausible, with a tentative slight preference
for B, recorded in `interaction-comparison/human-review-case-7.json`. No numeric
likelihood is inferred. Case 8's two candidates were accepted as plausible without
a stated preference, recorded in `interaction-comparison/human-review-case-8.json`.
Case 1's two code submissions were subsequently accepted as plausible, recorded in
`interaction-comparison/human-review-case-1.json`. All eight cases now have feedback.
There are fifteen displayed candidates representing sixteen draws: eleven categorical
plausible judgments (including the two conditional case-4 judgments), one normalized
implausible judgment, and three comparative-only judgments. These counts describe the
review records, not an accuracy or fidelity score. Preserve the comparisons and
qualifications rather than requiring another categorical confirmation.

Close this single-turn review pass and keep the current prompt frozen. The feedback
supports using visible interaction patterns as a light guide and retaining brief
checks, code submissions, and further questions; it does not support banning student
explanations or claiming the instruction caused a general improvement. Reply occurrence,
unseen notebook work, and sustained behavior remain unresolved.

The broader labeling connection is still provisional. This direct-dialogue generator
bypassed labels to test plausible student continuations; it has not implemented the
repository's label-state simulation or admitted any classifier. A next research step
should reconnect human-validated observable behavior labels to comparison of real and
generated trajectories, alongside a bounded continuity check. No cohort, production
replay, new tutor policy, or additional model run is created by closing this review.
