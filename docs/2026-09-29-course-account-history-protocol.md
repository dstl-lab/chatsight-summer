# One prospective history comparison on ten course accounts

The ten account-separated checkpoints are frozen. Minchan approved defining the
comparison and scoring rule; this step prepares exact inputs and an offline
scorer, without generation. Student eligibility remains unverified by request.
Recorded target messages stay separate and unread during prompt/metric design.

**Question:** Does earlier dialogue improve prediction of the literal form of
the next recorded message, beyond the current exchange alone?

This is a narrow, automatic diagnostic. It does not measure semantic relevance,
help-seeking, code correctness, sentiment, personality or overall realism.
It supersedes neither the closed help/work studies nor their adoption decisions.

## Conditions and fixed budget

| Condition | Visible dialogue |
| --- | --- |
| Current exchange | Complete final contiguous student request block and final contiguous tutor response block |
| Full available history | The identical current exchange plus all earlier turns in the frozen conversation prefix |

Reuse `chat_student._initial` to preserve message blocks and the unchanged
`student_continuation` prompt and Continuation schema. Normalize visible turn IDs
so omitted-history length cannot leak through source indices. No account IDs,
future targets, labels, retrieved answers or generated earlier draws enter prompts.
Both conditions retain the existing prompt's style/communication guidance; the
baseline is **current-exchange-only**, not an unprompted or naive LLM.

Use Gemini 2.5 Pro for both arms, temperature 1.0, JSON schema output,
`max_output_tokens=8192`, 120-second timeout and one SDK/adapter attempt.
Leave top-p, top-k, seed and thinking configuration at provider defaults and
record the returned model version, raw response and usage for every future call.
The installed SDK version is pinned in preparation. The output cap can also
constrain thinking; capped/non-STOP outputs are failures, never repaired replies.

Five independent draws per arm per case: **100 requests maximum**, scheduled in
five rounds across all ten cases. Alternate which condition goes first by case
and round (25 pairs start each way); dispatch sequentially. No generated output
is fed back as context. The workspace's default 30-draw control is unchanged;
this separate, fixed diagnostic uses five draws to bound its cost.

The preparation ceiling is 65,536 Unicode code points per complete prompt, not
a claim about provider token capacity. Keep full prefixes; if a prompt exceeds
the ceiling, stop preparation rather than truncate or replace it. If the API
rejects an input, preserve the failure. All selected cases have some earlier
dialogue; one has earlier tutor context only. This intervention includes task
and tutor information, so it cannot isolate student style or personalization.
The existing projection numbers lines and omits blank lines consistently in
both conditions; exact source text remains in the frozen input artifact.

## Automatic scoring fixed before generation

Use the corpus summary's existing literal definitions: raw Python `len(text)`
(Unicode code points), length bins **0–40 / 41–300 / over 300**, whether `\n`
occurs, and whether a backtick occurs. Their Cartesian product gives twelve
message-form categories. A validated `no-reply` is a thirteenth category; an
invalid/blank reply, timeout, non-STOP result or malformed output is an error.
These indicators are not labels for code, help requests or work submission.

For each case and condition, let `c[k]` count the five valid draws in category
`k`, `r` be the recorded message's category and `n=5`. The primary score is:

```
S = 0.5 * (1 - 2*c[r]/n + sum(c[k]*(c[k]-1) for k) / (n*(n-1)))
```

Lower is better; the range is 0–1. This finite-ensemble correction estimates
the half-scaled multicategory Brier score under independent, stationary draws.
An ordinary plug-in score would additionally penalize more dispersed outputs
because only five draws were collected. The correction does not remove sampling
uncertainty or validate the categories as realism measures. See
[Ferro, Fair scores for ensemble forecasts](https://empslocal.ex.ac.uk/people/staff/ferro/Publications/ferro2013.pdf).

The primary contrast is the equal-account mean of **history minus current-exchange**
scores over the ten cases. Negative means lower message-form error for history
in this fixed comparison. Report every case, both means and the paired difference;
do not treat the 100 draws as 100 independent accounts or make a significance claim.

A zero-call sanity baseline predicts the exact empirical form distribution of
all individual student messages in the full visible prefix, including the current
request block. Score that fixed forecast with ordinary half-scaled Brier;
there is no simulated-ensemble sampling correction for this exact distribution.
This is a form-frequency baseline, not a usable generated reply or personality.

Secondary diagnostics are raw character-count absolute error among reply draws,
newline/backtick rates and reply/no-reply/error counts. Report denominators and
per-case values; do not use a favorable secondary outcome to replace the primary.
No-reply is scored in its own category, never as a zero-length message that could
artificially improve length error. This return-to-chat sample cannot estimate
real silence probabilities.

## Missing outcomes and stopping rule

Each primary case pair needs all five valid decisions in both conditions;
valid no-reply decisions remain included. If any call fails, preserve its slot,
mark that pair incomplete, and show the complete-pair result with its denominator.
The all-ten point estimate is then unavailable. For `m` incomplete pairs, report
the conservative bounds `(sum_complete_deltas - m)/10` through
`(sum_complete_deltas + m)/10`. These are missing-outcome bounds, not confidence
intervals. Never interpret an error as student behavior or silently drop it.

Stop after the fixed batch and one report, even if results are mixed or null.
No retries, extra samples, changed prompts, new labels or automatic adoption.
If dispatch is interrupted, preserve unfinished slots; no automatic restart.
Keep the current simulator unchanged. A lower score is evidence about these
literal categories only; semantic behavior would require a separately defined
and independently validated measurement, not a post-hoc label pass here.

## Preparation complete; not dispatched

The offline helper and scoring checks are in
`experiments/2026-09-29-course-account-history/protocol.py`. The private output
`data/course-account-history-v1/` contains twenty exact prompts, a fixed
100-slot schedule, configuration/schema, source pins and a preparation receipt.
Prompts range from 3,048 to 37,935 characters; all fit without truncation.
Nine cases add earlier student messages; the remaining case adds tutor context.
All ten paired payloads have identical current turns and omit account/conversation
metadata. The recorded reference file was not opened for this preparation.

Authored checks verify bin boundaries and Unicode counting, fair-score endpoints,
the finite-draw correction against an exhaustive binary example, missing-outcome
bounds, whole message-block preservation, metadata exclusion, exactly 100 unique
slots, balanced condition order and refusal to overwrite a preparation. Independent
review found a floating-point zero-boundary issue; integer-numerator evaluation
fixed it before freezing the real inputs. No application engine files changed.

No model call, new label or recorded-reference score was produced. Next execution
must consume this exact plan and preserve raw responses, returned model versions,
usage and terminal dispositions before the single predeclared report.
