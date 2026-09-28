# Full-adapter reply comparison complete

The [fixed-input comparison](2026-09-28-full-adapter-replies.md) completed every
planned local request, without retries, failures or token caps. The new adapter
received the exact cached contexts, seeds and sampling settings. No tutor calls,
new labels or conversation rollout were added. Independent checks verify prompt
tokens, adapter identity, generated text, original sources and paired arithmetic.

The generated results are mixed. Repetition falls on the later fixed synthetic
histories, but the recorded-history first replies introduce a repeat. Their mean
character-count error falls slightly while median error rises, with improvements
and regressions offsetting each other. These populations remain separate; the
later result does not measure a new conversation's repetition rate.

Unblinded inspection illustrates the metric's limits: a reply can get closer to
the recorded message's length while repeating the prior student request. Other
changes replace unsupported assertions with questions, demonstrating why length
error alone cannot determine plausibility. This inspection is illustrative, not
a new scored label set or fidelity measure.

The prior prediction-loss improvement remains supported. It has not established
consistent improvement in generated behavior, so the full adapter stays separate
from the browser's existing model. Close this comparison without more training,
generation, human review or automatic adoption.

Private `data/full-adapter-replies-v1/INTERPRETATION.md` records the conclusion,
illustrative cases and a clarification of the existing empirical-quantile
convention. `REPORT.md` and `report.json` retain all cases and paired results;
`audit.json` verifies the saved requests, identities and tokens. All private
data and model artifacts remain ignored by Git.
