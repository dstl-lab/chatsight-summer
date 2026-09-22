# Forecast work presentation before generating wording

**TL;DR:** Add an experimental probability forecast of whether the next recorded
student message will include substantive work. Test once against the eight
references already coded by Minchan. No new labeling, generated messages or
change to the active simulator.

## Why this increment

The [completed cached review](2026-09-22-cached-communication-results.md) found
work in 6/10 generated replies where the reference contained none, and no work
in 2/6 replies where the reference contained work. Suppressing all work would
miss the latter group. Repeating visible student history in the prompt was
already tested; it did not justify changing the generator.

This increment makes one possible communication decision measurable before
trying to realize it in prose/code. It forecasts an observable feature of a
future message, not the student's hidden intention. A probability can represent
multiple plausible outcomes instead of forcing a deterministic next action.

## Bounded implementation

Add `src/eval/work_presence_forecast.py`: one strict probability schema in [0,1]
and one prompt builder. Reuse `student_continuation.make_prompt` to exclude future
turns, then remove source identifiers. Use the unchanged help-work-v1 work
definition. Earlier dialogue and the current exchange are the only case-specific
inputs. Reference messages, labels, generated draws, reviewer notes and metadata
are never model inputs. Keep existing simulator prompts and engine pins intact.

Use the existing Gemini adapter and offline `behavior_scoring.evaluate` for the
bounded private run; do not add a second session engine, review UI or dependency.
One authored test file covers future/metadata exclusion, visible-history use and
local validation of provider probabilities. The run's authored check covers
hand-calculated scoring, incomplete forecasts and preservation of frozen inputs.

## Fixed evaluation and stopping rule

- Exactly the eight references in the completed cached review, retaining their
  original prefixes and first-next-message endpoint. All are exposed development
  cases, selected before this forecast idea, not a random or independent holdout.
- Predict `P(work_present=yes | visible prefix, another message is recorded)`.
  This does not predict whether or when the student will reply, quietly work,
  run code, learn, or finish. All eight references request help, so help prediction
  adds no useful test here and is omitted.
- One Gemini 2.5 Pro request per case, eight logical requests at most. The existing
  adapter permits four attempts per request (32 attempts maximum); retain retry
  events. Freeze exact prompts, schema, inputs, code and this protocol before
  dispatch. Standing provider approval applies subject to actual approval review.
- No model receives these eight labels, their frequencies, other reference
  messages or demonstrations. Score against the other seven reference labels'
  frequency for each held-out conversation, reusing the existing split checks.
  These are baseline folds, not model training. Unknown student identities remain
  unknown; disjoint conversations do not prove disjoint students.
- Primary measure: mean **multiclass-sum Brier**, range [0,2], over work-absent and
  work-present probabilities. Also report each reference group separately, the
  equal-group mean, coverage, all per-case dispositions, and constant forecasts
  `P(work)=0.5` and `P(work)=0`. Compute paired baselines on the same usable cases
  and all-reference baselines separately. No failures count as absent work.
- Only consider a future message-realization component if all eight forecasts
  are valid, mean error is lower than both the leave-one-conversation-out baseline
  and constant 0.5, and each work group's error is below 0.5. This is a development
  screening rule, not a significance test or production-adoption threshold.
- Close after this one batch and report the result, including failure or an
  unpromising/inconclusive result. No replacements, rerolls, prompt tuning on
  these answers, additional review queue or automatic simulator adoption.

## Honest limits

Model-stated probabilities are not verified sampling frequencies or calibration.
Eight realized messages cannot establish the full distribution of plausible
actions. The prior two-draw generation score has a different estimand; do not
report a difference from it as improvement. This single forecast condition also
cannot establish an effect of grounding. A future wording component would need
its own evidence that its generated messages actually follow the intended plan.

## Implementation checks

- [ ] Add failing authored checks; implement only the forecast helper.
- [ ] Verify prompt isolation, provider schema and existing simulator tests.
- [ ] Prepare the fixed private scope and independently check source/label joins.
- [ ] Run once if dispatch is authorized, report and close; otherwise preserve
  the prepared scope and identify the exact input still needed.
- [ ] Commit the implementation and status in the existing isolated PR worktree.
