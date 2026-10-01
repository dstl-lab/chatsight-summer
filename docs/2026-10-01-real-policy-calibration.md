# First real-data policy calibration: a narrow work-presence baseline

**TL;DR:** Reuse existing human judgments on recorded messages to fit an
inspectable work-presence frequency baseline. Evaluate by leaving whole accounts
out, not individual conversations. This is a retrospective development diagnostic,
not validation of the authored joint policy or calibrated DSC 10 behavior.
No LLM calls, new labels, new accounts, private-data transfer or UI changes.

## Scope fixed before computing scores

Use exactly the sixteen distinct recorded next messages already reviewed under
`help-work-v1`: eight from the September 15 fixed benchmark and eight from the
September 22 cached review. Reverify packet/review/source bindings and recover
account identities from saved linkage. These sixteen conversations link to
fifteen course accounts; one account appears in both source groups. Keep the
groups explicit. Do not inspect fresh evaluation targets or add cases.

The human observations include thirteen work=no and three work=yes; all sixteen
have help=yes. Use only **work_present** as the forecast target. Its old definition
includes substantive candidate code, answers, calculations, reasoning and actual
diagnostic output. It is not interchangeable with the prototype's separate work
and diagnostic labels. No fine assistance type, task relation, notebook action or
silence label is inferred. Single-reviewer judgments are references with unknown
error, not established ground truth. Assistant-coded pilot labels are excluded.

## Transparent calculation

For each account, compute the fraction of its eligible human-coded messages with
work=yes. The fitted baseline is the mean of those account fractions. Preserve
per-account counts and exact rational weights. Never score this fitted value on
the same rows as evidence of successful calibration.

For prediction checks, remove every row belonging to the target account, fit the
frequency using the remaining accounts, then score that account's observations.
Average error within each account, then across accounts. Compare the frequency
rule with constant 50/50 and always-no forecasts on the same rows. Reuse the
existing summed two-class Brier calculation: `2 * (probability - outcome)^2`,
range 0–2, lower better. Keep any fold with zero positive examples and report its
class support; zero positive examples are not an exclusion reason. Require two other labeled accounts
for a usable forecast, an explicit support rule rather than a reliability claim.

Report input/label/account coverage, exclusions, class support, fitted rate,
per-account prediction/error and per-source summaries. As a fixed sensitivity
check, leave each original source group out and also remove its accounts from
the remaining group before fitting. Score only that held source. If fewer than
two independent training accounts remain, report unavailable instead of guessing.

No bins, smoothed probabilities, tuned thresholds, bootstrap intervals, model
search or automatic winner. Exact-forecast reliability tables are omitted:
leave-account-out frequencies mechanically depend on the omitted outcomes and
would make a tiny table misleading. The combined fit describes a selected
development mixture; it is not a population prevalence estimate. A lower Brier
than a constant baseline alone does not establish calibration or realism.

## Implementation and stopping

Add a small pure helper `src/eval/empirical_work_policy.py` for strict human/recorded
observations, account-balanced fitting, held-account checks and the declared
source sensitivity. Add one dated offline runner to reverify existing provenance,
extract text-free observations and save a new local report. Reuse legacy source
validators and `src/eval/behavior_scoring.py`; do not change their contracts or
the authored policy's admission rule. Keep private IDs, linkage, source paths and
receipts under ignored `data/real-policy-calibration-v1/`.

Tests use invented observations to check unequal account sizes, complete account
exclusion, zero-positive training, unknown labels/identities, source overlap and
hand-calculated Brier scores. Verify the real-data report independently from its
saved counts and inputs, then document the results and commit public code/docs.
Stop after this one fixed report, including an inconclusive outcome. A richer
policy still requires qualified observations for its missing dimensions; this
calculation does not silently turn the old labels into that missing evidence.
