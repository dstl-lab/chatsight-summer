# Real-data baseline result: inspectable, but not a calibrated rich policy

**TL;DR:** The first real-data calculation uses sixteen existing human-reviewed
recorded messages from fifteen course accounts. Their account-weighted
work/evidence-presence frequency is **20%**. Leaving each whole account out gives
Brier **0.367347**, compared with **0.5** for a 50/50 forecast and **0.4** for
always predicting no work. The source groups differ substantially, so this is a
development baseline, not a universal student probability or a validated policy.
No LLM calls, new labels, fresh accounts or manual review were required.

## What is implemented

The [fixed protocol](2026-10-01-real-policy-calibration.md) is complete.
`src/eval/empirical_work_policy.py` fits an account-balanced frequency and evaluates
whole-account and whole-source exclusions with the existing Brier helper. It
retains missing identities, unresolved labels, per-account counts and weights,
class support, and unavailable predictions. The dated runner verifies source
provenance and saves text-free private inputs plus a reproducible report.

The authored joint-behavior policy remains unchanged. Old `help-work-v1` work
includes substantive code, answers, reasoning and diagnostic output; it cannot
identify the newer policy's separate material types, hint/solution choices or
task changes. All sixteen recorded references are help=yes, so these observations
cannot establish a useful help-versus-no-help predictor. Both reviews came from
the same reviewer; their saved aliases do not establish independent raters.

## Evidence and results

All sixteen references joined uniquely to their recorded first-follow-up source,
original human judgment and saved course-account linkage. One account has two
messages in different sources; fourteen accounts have one each. All three work=yes
messages belong to distinct accounts. The repeated account has two work=no
messages. Consequently the message-weighted frequency is 3/16 (18.75%), whereas
equal account weights give 3/15 (20%). No records were excluded in this run.

| Original source | Recorded messages | Accounts | Work yes | Work no | Within-source frequency |
| --- | ---: | ---: | ---: | ---: | ---: |
| September 15 fixed benchmark | 8 | 8 | 0 | 8 | 0% |
| September 22 cached review | 8 | 8 | 3 | 5 | 37.5% |

The fitted 20% describes this selected mixture. It is kept separate from the
following prediction scores: each target account's prediction uses only the
other accounts. Error is averaged within account, then across accounts.

| Scored observations | Frequency baseline | Constant 50/50 | Always no work |
| --- | ---: | ---: | ---: |
| All 15 accounts | 0.367347 | 0.500000 | 0.400000 |
| Fixed source | 0.091837 | 0.500000 | 0.000000 |
| Cached source | 0.608418 | 0.500000 | 0.750000 |
| Work yes | 1.469388 | 0.500000 | 2.000000 |
| Work no | 0.091837 | 0.500000 | 0.000000 |

This uses **summed two-class Brier**, range 0–2, not accuracy or percentage error.
The lower overall frequency error conceals poor predictions for the three
work-present observations. Class and source rows describe their own account
subsets; they are not alternate population weightings or significance tests.

The declared source sensitivity removes every account appearing in the held
source, including its messages in the other source. Each fit retains seven
accounts. Training on the fixed source predicts work at **0%** for the cached
source, with error **0.75**. Training on the cached source predicts **3/7 (42.9%)**
for the fixed source, with error **0.367347**. This exposes dependence on source
composition; a source name is not itself a behavior predictor.

## Decision and limits

Retain the helper as an inspectable real-data baseline. Do not set the simulator
to produce work 20% of the time, replace the generator, or claim calibration of
the richer behavior policy. A lower retrospective error than a constant alone
does not establish reliable probabilities, realism or benefit to instructors.

These accounts and targets were previously exposed during development; their
episodes also belong to the old historical library. The new frequency calculation
excludes the entire target account within each fold, but that does not turn the
cases into fresh research holdouts or validate old model comparisons. The selected
source mixture is not representative, human-label error is unmeasured, and only
three accounts supply the positive class. Notebook actions and silence remain
outside the measured outcome.

The next substantive requirement is qualified context-and-behavior evidence for
the policy's intended choices. The present calculation provides a baseline and
documents that gap. No additional labeling queue, model batch or tuning pass is
automatically scheduled. This fixed analysis stops here.

## Verification and artifacts

The final local report is `data/real-policy-calibration-v2/report.md`; inputs and
full per-account calculations remain in ignored JSON files. All **145 source
pins** and **4 code/protocol pins** reproduce. An independent rational-arithmetic
audit obtained overall frequency error exactly **18/49** and checked every fold,
source exclusion and per-record error. The final focused run passed **28 tests**:
eleven new baseline checks, three existing scorer checks and fourteen authored
policy regressions. The existing authored-policy demo still verifies unchanged.

The first saved receipt raced a documentation-only correction clarifying that
zero-positive training folds must be retained. Its original directory remains
untouched. V2 pins the corrected protocol; saved inputs, numerical results and
report Markdown are identical to V1. A private supersession receipt records this
repair. No observation or computation rule changed and no provider was involved.

```sh
PYTHONPATH=. python -P experiments/2026-10-01-real-policy-calibration.py \
  verify data/real-policy-calibration-v2
```

The runner requires the existing private source archive. Tests use invented
observations and can run without that archive. Public code and this memo contain
no private messages, account identifiers or linkage records.
