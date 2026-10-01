# Independent-account test of the frozen context rule

**TL;DR:** Freeze the existing predictor, select 24 previously unexposed course
accounts, save predictions before retrieving targets, then obtain one blind
human work-presence judgment per message. One test, no tuning or replacement.
Twenty-four is a review budget, not a powered validation threshold.

## Frozen training and outcome

Use all sixteen original human-reviewed observations from fifteen accounts in
`data/context-work-probe-v1/inputs.json`. Reproduce its source bindings first.
Keep the exact code cue, any-prefix student-only extraction and shrinkage from
`experiments/2026-10-01-context-work-probe.py` at commit `d3ec840`. Fit only these
old observations: cue present predicts **11/15**, cue absent **3/35**, and unknown
context **1/5**. Freeze those values and training traces before new data selection.
Comparators are the unchanged global **1/5**, **1/2**, and **0** predictions.
No holdout label enters fitting, smoothing, feature design or example selection.

Keep the original `help-work-v1` work/evidence definition verbatim. The test
concerns the next recorded message, conditional on its existence, not silence,
notebook execution, correctness, learning or a full simulated behavior sequence.
The lexical cue is a feature, never an automatic reference label.

## Account and checkpoint selection

Before fetching message content, verify the existing linkage/exposure receipts
and refresh the metadata-only local exposure union. Exclude entire previously
used accounts, including both later ten-account history cohorts, all training
accounts and any identities not resolved unambiguously. Reuse the existing
historical window and exclusions; do not investigate student eligibility.
Metadata-only availability catalogs do not by themselves constitute exposure.
This establishes no known local study use, not absence of external exposure or
provider pretraining. Document the scan's coverage and remaining limitations.

Use seed `context-work-holdout-v1-20261001`. Rank each account by SHA256 of
`seed:account:account_id`, breaking ties by ID, and take the first 24. Within
each account choose the conversation with the smallest similarly salted
`conversation` hash. No cue, length, target content or outcome-based enrichment.
If fewer than 24 remain, stop preparation; do not weaken exclusions.

Reuse the old metadata-only checkpoint query and original cutoff/salt. Each
structural checkpoint is a recorded student query immediately after a tutor
response, with at least two earlier student queries. Rank checkpoints by SHA256
of `seed:checkpoint:conversation_id:target_event_id`, breaking ties by event ID.
Retain one per selected account. Missing/changed metadata is a technical failure,
not permission to select a different account or checkpoint.

Fetch only frozen prefix event IDs, using the existing read-only content query.
The prefix is the complete nonempty chat before the selected target in its
conversation; no other conversation, later event or artificial truncation.
Validate source identity, event order, timestamps, roles and counts. This fixed
projection differs from heterogeneous historical review prefixes; report that
limitation. Store predictions and source hashes **before** requesting target text.
Retrieve only those frozen targets in a separate read-only request afterward.

## Blind review and independence

One page presents the exact prefix and one recorded target per case, in a fixed
hash-shuffled order. It contains no forecasts, cue values, account identifiers,
source identities, old judgments or suggested answers. Ask only work/evidence
present: **yes / no / unclear**, with a short reason for unclear. Preserve the
original work definition; do not ask for help-request labels.

Prefer a teammate who has not seen predictions. The original reviewer can provide
a held-out-account check but cannot establish independent-rater reliability.
Record reviewer identity and prior case exposure. No assistant/model annotations
substitute for these human references. Do not send the page to anyone without
the user's instruction. All private content and linkage stay outside Git.

## One report and stopping rule

Primary outcome is mean paired **context minus global-frequency** summed Brier,
`2*(p-y)^2`, over binary human references, with one case per account. Negative
means lower error. Report both scores, fixed comparators, coverage out of the
24 originally selected accounts, class/cue support and every case's contribution.
Show missing/unclear/technical failures explicitly; they never mean work=no.
For unresolved labels with known predictions, bound their paired differences by
evaluating both possible binary outcomes. If a prediction is unavailable, use
the conservative difference range [-2,2]. Report full-set missing-outcome bounds
separately from the complete-case estimate; these are not confidence intervals.

No post-hoc success threshold, subgroup winner, feature change, prior change,
extra cases to obtain positives, rerun or automatic adoption. A small holdout
cannot certify reliability even if its score improves. If results later inform
development, retire all these accounts from future independent tests. Stop after
one review and report; do not create an adjudication or recurring labeling queue.
