# Sensitivity to assumed evaluator error

The user requested different assumed error levels and their effect on results.
This is a new offline, retrospective sensitivity analysis of saved human-coded
`help-work-v1` results. It does not relabel closed studies, validate the newer
`content_supplied` scorer, or estimate an actual evaluator error bound.

Use the existing verified readers for the fixed eight-case help/work comparison
and the separate eight-case cached communication review. Preserve the first
study's two arms and four draw slots per case, and the second's one arm and two
slots per case, including its shared judgment. Do not pool studies or treat
conversation IDs as independently identified students.

Sweep error allowances on recorded and generated labels independently through
0%, 2.5%, 5%, 10%, 15%, 20%, 25% and 30%. Keep the proposed large-gap threshold
at 20 percentage points. These are assumptions for exploration, not estimates.
No new model calls, data collection, labels, executions or prompt changes.

If a source's observed yes rate is q and the assumed erroneous label mass is e,
use the conservative rate interval [max(0,q-e), min(1,q+e)]. Subtract recorded
from generated intervals to get [L,U]. A large excess requires L > 0.20; equality
does not pass. Report direction separately: a positive range can fall short of
the large-gap threshold. All saved work flags are binary; no unclear, missing,
failed or no-reply rows are dropped. Reject changed/incomplete inputs.

Rates give each conversation equal weight and each of its draws equal weight.
Thus e bounds weighted occurrence error mass, not the fraction of unique review
forms. Continuous intervals may be wider than attainable whole-message flips;
they are conservative envelopes, not exact discrete relabeling extrema. Repeated
draws sharing one judgment remain linked; the analysis does not claim they can
be independently recoded. Source clipping prevents impossible rates below 0 or
above 1. Leave-one-conversation-out ranges are descriptive influence checks.

The intervals refer only to these fixed saved outputs and assigned labels.
No sampling margin is estimated or hidden in them. Claims about a simulator's
response distribution or a student population additionally require finite-draw
and account-sampling uncertainty. Neither the error allowances nor a confidence
level can be inferred from this sensitivity analysis.

## Results

The saved labels give work/evidence rates of 0/8 recorded versus 23/32 generated
for current exchange only, and 0/8 versus 26/32 for earlier dialogue. The separate
cached review gives 3/8 versus 10/16. The latter retains sixteen occurrences from
fifteen unique generated messages. All three comparisons have eight conversations;
learner identities and independent-account sampling are unestablished.

The table uses the same allowance on each source. Entries are generated-minus-
recorded gap ranges, in percentage points, with no sampling margin.

| Assumed error per source | Sept 15: current exchange | Sept 15: earlier dialogue | Sept 22: cached replies |
| --- | ---: | ---: | ---: |
| 0% | 71.875–71.875 | 81.250–81.250 | 25–25 |
| 2.5% | 66.875–74.375 | 76.250–83.750 | 20–30 |
| 5% | 61.875–76.875 | 71.250–86.250 | 15–35 |
| 10% | 51.875–81.875 | 61.250–91.250 | 5–45 |
| 15% | 41.875–86.875 | 51.250–96.250 | −5–55 |
| 20% | 31.875–91.875 | 41.250–100 | −15–65 |
| 25% | 21.875–96.875 | 31.250–100 | −25–75 |
| 30% | 11.875–100 | 21.250–100 | −35–85 |

For the continuous envelope, the earlier-dialogue excess stays strictly above
20 points while the two source allowances sum to less than 61.25 points;
current-exchange requires less than 51.875 points; the cached result requires
less than 5 points. Equal allowances therefore reach the respective boundary at
30.625%, 25.9375% and 2.5% per source. Equality is inconclusive under the strict
rule. This is loss of a conservative guarantee, not proof that the conclusion
actually reverses or an estimate of coding error.

An attainable discrete check illustrates the cached result's fragility: changing
one nonshared generated work=yes judgment to no changes its rate from 10/16 to
9/16 and the gap from 25 to 18.75 points. It no longer exceeds 20 points. No saved
judgment was actually changed. The 2.5% continuous bound itself does not imply
that a fraction of a message can be recoded.

Leaving out one whole conversation gives gap ranges of 67.857–75 points for
current exchange, 78.571–89.286 for earlier dialogue, and 14.286–42.857 for
cached replies. Thus the latter's large-gap conclusion also depends on which
conversation cases contribute. These ranges are influence checks, not confidence
intervals. Neither this nor the error sweep supports ranking simulator quality
across the two different studies or claiming that history caused the difference.

## Decision and reproduction

The exercise distinguishes a coarse gap that can withstand substantial assumed
label distortion from a smaller gap whose conclusion is sensitive to one label
or conversation. It does not select a defensible actual error rate. Old
`help-work-v1` labels remain untouched and are not converted to `content_supplied`.
This analysis is complete; it schedules no review, new scorer or provider batch.

Run the existing read-only verifiers and save a new report with:

```sh
mkdir -p data/evaluator-error-sensitivity-v1
PYTHONPATH=. python -P experiments/2026-09-30-evaluator-sensitivity.py \
  /Users/minchan/github/chatsight-summer/episode-pilot/data/episode-pilot/help-work-benchmark-v1 \
  /Users/minchan/github/chatsight-summer/episode-pilot/data/episode-pilot/cached-communication-review-v1 \
  data/evaluator-error-sensitivity-v1/report.json
```

The completed report is create-only and already exists; use a different output
for an explicit offline reproduction. It contains all 192 combinations (three
comparisons × eight recorded-error levels × eight generated-error levels), 19
source-file hashes and three analysis/reader code hashes. It contains aggregate
counts, never student message text. Original source files remain unchanged.

The authored arithmetic test was first observed failing before implementation,
then passed along with the existing reader tests: **39 passed**. Independent
review reproduced all 192 cells, exact source counts, case weights, clipped
intervals, strict-threshold decisions and leave-one-case-out ranges. All pins
matched and an offline reproduction was byte-identical.

An accompanying in-conversation view lets the two error allowances vary
independently. Offline JavaScript checks verified all 192 rendered decisions,
element references, state persistence and restoration. Browser visual inspection
was unavailable because its URL policy blocked the local preview; no alternate
browser access was attempted. The controls use only aggregate data and no network
requests. This is an explanation aid, not a change to the research workbench.
