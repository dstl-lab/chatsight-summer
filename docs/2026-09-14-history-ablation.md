# Does available earlier dialogue change the next student action?

**Paused before preparation or dispatch (2026-09-14).** Minchan requested a
project-level reassessment of the repeated review loop and a team meeting update.
The protocol below remains a proposal. Private implementation drafts exist, but
integration verification is incomplete; no frozen experiment, generated results,
or model requests exist for this comparison. Do not resume it automatically.
See [the research reassessment](2026-09-14-research-reassessment.md).

The completed communication batch found that plausible generated replies had a
different primary action mix from recorded next messages. This diagnostic tests
one possible contributor: the additional earlier dialogue supplied to the model.
It does not change the original continuation prompt or try to force more help
requests. Minchan requested continuation after the completed report proposed this
comparison; the standing authorization to continue remains in force.

## Frozen comparison

Use all six previous cases with at least one earlier student message: cases 2–7
of `fixed-communication-eval-v1`. Selection uses only the saved input prefixes,
not their reference categories or the new outputs. Cases 1/8 have empty earlier
context and are excluded without replacement; they cannot supply this treatment.
These are exposed development cases, not a new holdout or independent students.

For each case, compare `with-history` with `without-history`. The former is byte
identical to its old input prompt. The latter changes only the JSON `context`
array to `[]`; the current student request, tutor reply, original prompt, local
IDs and explicit unknown work/observation fields stay fixed. The existing
context-status wording permits zero to six earlier turns and stays unchanged.
The omitted dialogue contains both student and tutor turns. Current exchanges may
refer to earlier work even after this removal: this tests the additional supplied
dialogue, not absence of all historical information or student-style memory alone.

Make two fresh requests per condition per case: 24 logical requests total, Gemini
2.5 Pro, original schema and provider defaults, at most four adapter attempts per
request. Do not reuse the earlier generated replies as a condition. Iterate draw
1 then draw 2, cases 2–7 within each draw; with-history comes first when
`(case + draw) % 2 == 0`, otherwise without-history. Reverse it for the next draw.
Counterbalancing limits order imbalance; it does not create matched random seeds.
Each condition's two prompts are identical and neither includes the other draw.

No recorded next message, label, prior generated reply, human feedback, inferred
notebook revision or execution result enters an input. Use saved prefixes only;
no additional database query, source recovery, student-code execution or grading.
Keep all exact prompts, results and private scripts in ignored
`data/episode-pilot/history-ablation-v1/`. Completed experiments stay unchanged.

## One review, fixed before sending

Present four fresh candidates A–D per case with condition/draw mappings concealed
in a separately saved, preassigned order. Show the same available full prefix for
every candidate. Judge whether each could fit that situation, regardless of what
its generating condition saw. This separates review context from model input.
Do not add the previously reviewed reference as a fifth candidate or transfer any
old verdict to a new draw. Prior exposure prevents guaranteed blinding.

Record fit (plausible/implausible/uncertain) and the unchanged v7 primary follow-up
action. This diagnostic does not repeat the largely unobservable task-relationship
rating. Code/work takes precedence over an attached checking request; a proposed
numerical answer can be submitted-work despite question wording. Revised-code
requires a visible change from earlier STUDENT code. A short note is required for
implausibility or revised-code; retain mixed-function and ambiguous-message notes,
using insufficient-evidence when the primary function cannot be determined.
Labels describe messages, not verified notebook actions or correctness.

Keep original review fields blank and collect judgments separately. Any assistant
label suggestions must be kept separate until human confirmation and recorded as
assisted review. No automatic model judge supplies missing human ratings. Error
and no-reply slots have no message ratings and stay in the condition denominator.
Explicit uncertainty is a judgment; a blank field is not. Review the whole batch
before revealing conditions or drawing conclusions.

## Report and stopping rule

Report all 12 scheduled requests per condition, including errors/no-reply; fit and
primary action counts with known/unknown/missing denominators; both draws per
case/condition; and complete notes. Compare primary help/checking, code, revisions,
other work and acknowledgment without interpreting category counts as all speech
acts. Preserve mixed-function qualifications. Describe within-case variability;
do not treat 24 draws as independent learners or invent a significance threshold.

The comparison can suggest that additional dialogue changes sampled outputs. It
cannot isolate student habits from tutor/task information, validate a learned
persona, establish a population frequency or prove that a difference is beneficial.
Sparse/truncated history, selection conditioned on a recorded reply and only two
draws per condition limit interpretation. No reply-rate, silent-work, learning,
task-drift or classifier-admission claim follows.

Generate once, retain every terminal receipt, complete one review batch and report
before any tuning. No replacement, better-draw selection, extension, old-result
pooling, forced help quota or generator adoption. Preserve actual approval-review
rejections separately from the standing grant; do not preemptively request another
approval unless a real external-send block requires it.

## Implementation and verification

- `prepare.py` selects from the old saved prefixes, freezes the protocol and 24
  inputs, records authorization/disclosure and verifies their hashes. Its
  `verify()` returns `(experiment, inputs)`; `make_jobs(prior_inputs)` is the pure
  transformation shared with checks.
- `run.py` reuses the existing receipt/provider pattern: pending persisted before
  credentials, all terminal replies/no-reply/errors retained, bounded retries,
  exclusive creation and offline exact replay. No resume or implicit resend.
- `review.py` reuses existing fencing and v7 definitions for deterministic A–D
  rendering and the summary of separate judgments. A partial review cannot write
  a final summary.
- Focused offline checks cover the actual preparation/runner/reviewer seam,
  context-only removal, unchanged current exchange, counterbalanced order,
  future/feedback isolation, same review context, all candidate mappings,
  preserved failures and missing/unknown denominators. Independent review checks
  the frozen sources and experiment limits before dispatch.

All work stays in the existing `codex/episode-pilot` worktree and draft PR 25.
Production modules remain frozen; no new interface, dependency or framework.
