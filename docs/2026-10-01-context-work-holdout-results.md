# Prior-code predictor did not improve the independent-account test

**TL;DR:** The frozen context rule scored **0.402980**, versus **0.251429** for
the frozen global-frequency baseline, on 21 clear judgments from 24 new course
accounts. Lower is better. The three unclear judgments cannot reverse the
direction under either possible binary assignment, holding the other judgments
fixed. The promising development result did not generalize in this test. Close
the experiment without adopting or tuning the rule.

## Fixed comparison

The [protocol](2026-10-01-context-work-holdout.md) and preparation code were
committed at `b1ad4df` before selection. Training used only the old sixteen
observations from fifteen accounts. Predictions were sealed before retrieving
the new targets; all 24 selected accounts were retained. See the
[preparation record](2026-10-01-context-work-holdout-preparation.md) for selection,
exposure exclusions, prefix retrieval recovery and limitations.

One reviewer returned all 24 judgments and reported no prior case exposure:
**3 yes, 18 no, 3 unclear**. Binary scoring coverage is **21/24 (87.5%)**.
This is a held-out-account test with the original reviewer, not an independent
second-rater study. All forecasts were available.

| Frozen forecast | Mean summed Brier on the same 21 judgments |
| --- | ---: |
| Prior-code context rule | 0.402980 |
| Global work frequency (20%) | **0.251429** |
| Constant 50/50 | 0.500000 |
| Always no work | 0.285714 |

Brier is `2*(p-y)^2`, ranging from 0 to 2; it is not an error percentage or
classification accuracy. The primary paired context-minus-frequency difference
is **+0.151552**: context has higher error. Fifteen accounts have smaller errors
and six larger errors; the larger errors outweigh the smaller improvements.
There are no ties. Compare methods within this holdout; the earlier development
scores came from different cases and training folds.

## Uncertainty and interpretation

Two unclear judgments cite language comprehension; one cites uncertainty about
whether the message contains an answer choice or substantive work/evidence.
They remain unclear, with their original notes. Considering both binary outcomes
for each gives a full-24 paired-difference range of **+0.079758 to +0.206742**.
These are unresolved-outcome bounds, not confidence intervals. They do not
account for annotation error in the 21 accepted judgments or sampling uncertainty.

The reviewer reported judging primarily the presented message rather than its
earlier context. This is compatible with the message-level outcome: context
can clarify what a message means, but cannot supply work absent from it.
Limited context use remains a measurement caveat. No translation, relabeling,
adjudication or additional review was used to change the result.

Four accounts had the prior-code cue: **three work=no, one unclear, no work=yes**.
The other twenty had **three yes, fifteen no and two unclear**. The rule assigned
73.3% work probability when the cue was present and 8.6% otherwise. This sparse
cue therefore produced substantial errors in both directions. It does not
establish a stable student persona; it records whether a literal pattern
appeared in an earlier chat message, not whether a student worked in a notebook.

## Decision and reproduction

The candidate is **not adopted**. This test closes after the single review and
report. All 24 accounts remain reserved from future independent tests. No
feature, shrinkage, probability or label was changed to improve the holdout
score. This turn made no database or provider calls and created no new labeling
queue. The live generator and authored behavior policy remain unchanged.

The preserved form, reviewer context, sealed forecasts, source bindings and
per-case contributions are private under `data/context-work-holdout-v1/`.
Only aggregate results, scorer and invented tests enter Git. Reproduce locally:

```sh
PYTHONPATH=. python -P experiments/2026-10-01-context-work-holdout-score.py verify
```

The scorer checks the frozen preparation hashes, prediction reproduction,
seal-before-target timing, packet identity, exact displayed text and account
membership. Its saved report is create-only. The focused suite passes **44
checks**. A separate rational-arithmetic calculation reproduced the primary
difference exactly as **11696/77175** and the full-set bounds as **2638/33075**
and **6838/33075**, without importing the new scorer or interpreting target text.
