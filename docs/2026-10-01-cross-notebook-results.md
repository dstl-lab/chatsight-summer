# Cross-notebook history cards: completed comparison

**TL;DR:** Earlier-history statistics did not improve next-message form prediction
over the same current conversation alone: error was **0.430 versus 0.420**
(lower is better). Another account's statistics scored **0.545**. All 150 requests
completed, all ten withheld references were verified afterward, and the fixed
comparison is closed. Keep the current simulator default; do not promote the cards.

## What was tested

The [frozen protocol](2026-10-01-cross-notebook-cards.md) selected ten course
accounts from the 72-account richer-history subset. Every case received the same
full current conversation in three conditions: no additional history, its own
earlier-history statistics, or another account's statistics. Each condition had
five Gemini 2.5 Pro draws per case, for 150 requests total.

Matched cards summarized 12–20 earlier student queries per account, 191 total,
across 2–6 earlier notebook identities. Donor samples matched the corresponding
query count and preceded the recipient's cutoff. The ten donor assignments used
six accounts; two donors were each used three times. Cards contained aggregate
communication statistics, without historical quotations or notebook/account names.
No reference reply was included in any prompt or fetched before generation ended.

This tests whether this particular summary improves prediction. It does not test
all ways of using history or establish that these accounts have stable personas.

## Results

The primary measure is the equal-account mean **fair multicategory form Brier
score**, using five generated decisions per arm. Its twelve reply categories
combine character-length bin (0–40, 41–300, >300), newline presence and backtick
presence; explicit no-reply is a thirteenth category. Lower is better. This is a
distributional form score, not an accuracy percentage or a semantic realism score.

| Forecast | Mean form error | Role |
|---|---:|---|
| Current conversation alone | 0.420 | Primary baseline |
| Current conversation + own earlier-history card | 0.430 | Primary candidate |
| Current conversation + other account's card | 0.545 | Secondary diagnostic |
| Exact empirical distribution of own earlier queries | 0.345312 | Non-generative baseline |
| Exact empirical distribution of current-prefix student messages | 0.345445 | Non-generative baseline |

The primary matched-minus-generic difference is **+0.010**, a slightly higher
observed error. Three accounts improve, two worsen, and five tie. Matched cards
score 0.115 lower than donor cards, while donor cards score 0.125 higher than the
generic baseline. Beating another account's card does not demonstrate a benefit
over providing no card.

Both empirical baselines have lower observed mean form error than the three
generators, but they only forecast these coarse categories; they cannot produce a
coherent next reply. Their scores use exact empirical frequencies, while generated
forecasts use the five-draw correction. All means cover the same ten accounts.

| Case alias | Current conversation | Own card | Other card | Own − current | Earlier-query baseline | Current-prefix baseline |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1.000 | 1.000 | 0.800 | 0.000 | 0.137500 | 0.000000 |
| 2 | 0.300 | 0.200 | 0.800 | −0.100 | 0.002500 | 0.000000 |
| 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.810000 | 1.000000 |
| 4 | 0.800 | 1.000 | 1.000 | +0.200 | 0.040000 | 0.250000 |
| 5 | 0.050 | 0.200 | 0.450 | +0.150 | 0.277008 | 0.444444 |
| 6 | 1.000 | 1.000 | 1.000 | 0.000 | 0.547500 | 0.450000 |
| 7 | 0.150 | 0.100 | 0.300 | −0.050 | 0.902500 | 1.000000 |
| 8 | 0.000 | 0.000 | 0.000 | 0.000 | 0.422500 | 0.160000 |
| 9 | 0.800 | 0.800 | 1.000 | 0.000 | 0.202500 | 0.132231 |
| 10 | 0.100 | 0.000 | 0.100 | −0.100 | 0.111111 | 0.017778 |

Case aliases follow the frozen selection order and disclose no course identifiers.
A zero finite-sample corrected score does not prove perfect prediction.
Seven references are short, single-line messages without backticks; two are
medium-length single-line messages and one is medium-length multiline, also
without backticks. This small endpoint therefore emphasizes short, plain chat.

## Execution and verification

The user explicitly approved this exact 150-request batch after the initial
automatic-review rejection described in the
[preparation record](2026-10-01-cross-notebook-preparation.md). The earlier rejected
dispatch sent zero requests. The approved batch ran once, from 03:39:15 to 04:08:57
UTC on October 1, 2026. It produced 150 valid replies, zero no-reply decisions,
zero errors, and no pending or unattempted slots. No retries, replacement cases,
prompt changes, additional batches or new human labels were used.

All provider responses reported `gemini-2.5-pro`. Saved usage totals are 651,380
prompt tokens, 5,662 candidate tokens, 185,377 thinking tokens and 842,419 total
tokens. Cached-content counts were reported on 22 responses, totaling 115,416;
this is not an additional token total or a billing estimate.

Only after all generation ended, a read-only query fetched the exact ten frozen
reference event IDs. Account, conversation, notebook, event type, timestamp,
nonblank text, input/reference separation and query provenance all verified.
The temporary database tunnel is closed. Saved raw-response hashes, parsed
decisions, request schedule, code/input pins and completion receipts verify.
An independent calculation from the raw responses checks the reported scores.
It reparses all 150 provider outputs and reproduces every score using exact
fractions and a separate pairwise-disagreement formula. Reference retrieval began
50.66 seconds after generation completed.

Private artifacts remain ignored under `data/cross-notebook-cards-v1/`, including
approval, raw responses, references, verification and the fixed report. Public
documentation contains only aggregates and case aliases. The ten accounts remain
development-exposed and are excluded from future fresh comparisons.

Reproduction identifiers:

- Plan: `4928230f06bc9d23870f35f0d00a749bcddbd5b08fb72806c06151d636cefc11`
- Prompts: `6552b90ca415d6f5a5dbed775d2bae907b1134811dfdbabc9748135ed60c61c0`
- Explicit approval record: `e99326407d2a25b784df2cebaf90998e6b2c489a92f9d823a36d0ed6a1f4cb7a`
- Validated references: `a9bf66a9c9bc342d109610ed76ad9b0c9d648260602477ab2317add72ae86c60`
- Fixed report: `7bca00eed3a031310a4784f2ed7b4464a8cf702db14f312c34c848a26a025e8a`

## Decision and limits

Keep the current-conversation simulator as the default. Preserve the cards and
completed comparison as experimental evidence; do not tune or adopt them based
on the donor contrast. This closes the planned study without another labeling
round or generation batch.

The result narrows one implementation choice: adding a statistics card did not
improve this measured endpoint, even with richer prior histories. It does not
show that history is useless or that the existing simulator is realistic. Simple
observed-form distributions are useful benchmarks for future simulator changes,
not substitutes for contextual reasoning or notebook execution.

There are only ten history-rich accounts, five draws per arm, and one recorded
future per account. No confidence interval, significance, population-wide or
causal claim follows. The primary missing-outcome bounds collapse to
`[0.010, 0.010]` because every request completed; these are **not confidence
intervals**. Sampling uncertainty remains. Fair scoring assumes independent,
stationary draws from each fixed prompt.

This cohort is not a random sample of all DSC 10 students, and account eligibility
was not verified. Different notebook identities do not prove distinct tasks.
Reference selection conditions on a recorded return to chat, so this study cannot
validate silence probabilities. Full notebook action sequences, help-seeking
meaning, learning outcomes and tutor-policy effectiveness remain unmeasured here.
