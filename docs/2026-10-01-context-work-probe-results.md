# Prior code cue: lower development error, still limited support

**TL;DR:** One fixed, transparent context rule reduced account-held-out Brier from
**0.367347 to 0.193358**, a **47.4% relative reduction** on the same sixteen
human-reviewed messages from fifteen course accounts. Fourteen accounts improved;
one worsened. No LLM calls, new labels or parameter search were used. The signal
comes from only two cue-positive accounts, so this is a promising development
predictor, not a validated replacement simulator.

## What changed

The [frozen protocol](2026-10-01-context-work-probe.md) adds one observable feature:
whether an earlier student message matches our existing literal code-opening
pattern. A small conditional frequency calculation uses that feature, retaining
account weights and shrinking each estimate toward the training fold's global
rate by one account-equivalent. No LLM extracts state or chooses probabilities.

Protocol, code and authored checks were committed at `d3ec840` before deriving
the feature/outcome association. The rule was evaluated once. The human labels
and accounts had been exposed in earlier development; freezing this comparison
does not turn them into fresh research holdouts. All sixteen observations were
scored, with no unknown features, exclusions or account-holdout fallbacks.

## Results

Scores use summed two-class Brier, `2*(p-y)^2`, ranging from 0 to 2; lower is
better. They are not accuracy percentages. Average within each account, then
give each account equal weight. Every prediction excludes its entire account.

| Scored group | Accounts | Frequency baseline | Context rule |
| --- | ---: | ---: | ---: |
| All | 15 | 0.367347 | **0.193358** |
| Work present | 3 | 1.469388 | 0.896993 |
| Work absent | 12 | 0.091837 | 0.017450 |
| Fixed source | 8 | 0.091837 | 0.017450 |
| Cached source | 8 | 0.608418 | 0.347278 |

The unchanged 50/50 and always-no baselines score 0.5 and 0.4 overall. The
context improvement is **0.173989 Brier units**, not 47.4 percentage points of
accuracy. The source rows overlap by one account and are not additive.

Only two messages from two accounts have the cue; both have human work=yes.
The other fourteen messages, from thirteen accounts, have one work=yes and
thirteen work=no. For each cue-positive held account, the remaining cue-positive
evidence therefore comes from **just one account**. Its prediction moves from
14.3% to 57.1%. This is sparse support, not an established population tendency.

The third work-present case has no prior cue. Its prediction gets worse:
14.3% falls to **1.1%**, and its error rises from 1.469388 to 1.956285. This
counterexample matters: students can send work without previously matching our
literal pattern. Absence of the cue must not be treated as inability or refusal
to contribute work.

## Source sensitivity and decision

| Held source | Frequency baseline | Context rule |
| --- | ---: | ---: |
| Cached | 0.750000 | 0.750000 |
| Fixed | 0.367347 | 0.113379 |

Each source fit removes every account found in the target source, leaving seven
training accounts. Holding out cached leaves no positive training labels, so
both rules still predict zero. Two cached cases also have an unseen cue bucket
and fall back to that global rate. Context cannot recover behavior absent from
its training evidence. Source sensitivity remains a substantial limitation.

Retain the frozen rule as a candidate predictor. It supports investigating
observable behavioral history, but does not establish stable personas, causal
effects, calibrated probabilities, notebook-action realism or tutor-policy
benefit. The cue can match prose or quoted/starter code and miss other work;
longer prefixes have more opportunities to match. The old semantic work labels
also have unmeasured annotation error.

The experiment stops here without tuning away the missed positive or creating
another labeling queue. The next evidence requirement is independent coverage
of both work-present and work-absent behavior, including accounts without this
cue. Lowering the score further on these same sixteen exposed cases would not
establish that requirement. The live generator and authored policy stay unchanged.

## Reproduction

Private, text-free inputs, prefix hashes and full prediction traces are saved in
`data/context-work-probe-v1/`. Original source text remains in its pinned archive.
The code reuses the previous baseline's validation, folds and scoring and checks
the canonical visible-prefix bindings before feature extraction.

```sh
PYTHONPATH=. python -P experiments/2026-10-01-context-work-probe.py \
  verify data/context-work-probe-v1
```

The focused test set passes **31 checks**, covering the new cue/weighting/holdout
logic and existing baseline, scorer and authored-policy regressions. No historical
experiment code or saved result was replaced.

An independent rational-arithmetic audit reproduced every forecast, exclusion and
score, obtaining overall context error exactly **8006/41405**. It also verified
all sixteen prefix features, **146 source pins** and **7 code/protocol pins**.
