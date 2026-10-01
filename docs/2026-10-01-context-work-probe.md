# One context-conditioned work-presence comparison

**TL;DR:** Test whether an existing literal code-opening cue in earlier student
messages improves the 0.367347 frequency baseline. One offline development
comparison; no LLM calls, new labels, parameter search or simulator adoption.

## Fixed question and inputs

The user requested improvement over the frequency baseline. Reuse its exact
sixteen recorded, human-reviewed observations and fifteen course accounts under
`help-work-v1`. Preserve the original target, outcome labels, exclusions, account
weighting and source provenance. These are previously exposed, selected cases,
not new validation data. Earlier research motivates checking code-pasting habits.

The single feature is whether **any student message in the originally supplied
prefix** matches the existing historical code-opening cue:

```python
re.compile(r'(?m)^\s*(?:def\s+|for\s+|[A-Za-z_]\w*\s*=(?!=))')
```

Reuse that exact pattern from `student-continuation-check-v1/run.py`; verify and
pin its source without importing the private runner. This deliberately narrow
lexical feature can match prose beginning with “for”, starter code or quoted
questions; it misses many other code forms. It is not a semantic work label,
student authorship judgment, ability or persona. False means no cue detected,
not no previous work. Missing student context remains unknown.
Longer supplied prefixes offer more chances for this cue to appear; availability
can differ across source groups and is not a stable student characteristic.

Use the canonical audit payload's prefix, checked against its recorded prefix
hash. Pass only student text to feature extraction; exclude tutor text, target
text, labels, source names and identifiers. Keep private text and linkage local.
Freeze this protocol and extractor before deriving feature/outcome associations.

## Fixed estimator and evaluation

In each training fold, assign each eligible row weight `1 / n_a`, where `n_a`
is the number of eligible messages from that row's account. The global rate `g`
is unchanged from the account-balanced baseline. For the query's feature bucket,
let `M` be the sum of row weights and `S` the sum of weights with work=yes:

```
p(work | cue) = (S + g) / (M + 1)
```

The fixed shrinkage strength is **one account-equivalent**, an engineering choice,
not a fitted prior or reliability guarantee. Preserve account weights before
conditioning; do not give accounts a new weight after filtering to the bucket.
An empty bucket or unknown feature falls back to `g`. Fewer than two eligible
training accounts remains insufficient evidence, as in the original baseline.
Zero-positive training folds stay zero; do not add a positive prior afterward.

Repeat the same whole-account holdouts and both source holdouts. Source holdouts
also remove all accounts shared with their targets. Recompute rates and weights
using training rows only. Record training IDs, weights, bucket support, probability
and fallback reason. Never fit a threshold, use source as a predictor, or treat
the feature as a replacement human outcome.

Compare paired account-average summed two-class Brier, `2*(p-y)^2` (range 0–2),
against the unchanged frequency, 50/50 and always-no baselines. Report full
coverage, class/source errors, feature support and account-level wins/ties/losses.
No significance, calibration or overall-realism claim follows from this sample.

## Stopping rule

Run this one frozen rule once on the sixteen observations, verify its calculation,
and report the result whether better, worse or uninformative. No new cue, lookback
window, shrinkage value or follow-up batch is selected from these outcomes.
Keep the old report and policy unchanged. A positive result supports only a
candidate predictor for further evaluation; it does not justify deployment.
