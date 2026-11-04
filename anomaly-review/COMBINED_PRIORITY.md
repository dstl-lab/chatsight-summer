# Combined Metric and LLM Review Priority

## Purpose

This layer combines two review signals without treating either as ground truth:

1. Phase 3B's leave-one-out, same-question post-help metric ranking.
2. A validated structured finding produced by Gemini or an explicitly selected OpenAI model.

The output is a priority for instructor review. It is not a probability, a tutor-quality
score, a causal conclusion, or a claim that either model interpretation is correct.

## Priority rules

| Metric signal | Validated LLM signal | Evidence overlap | Priority |
| --- | --- | --- | --- |
| Strong outlier | Supported finding | Required | High |
| Strong outlier | Any other state | Not required | Medium |
| Any weaker or unavailable metric state | Supported finding | Not required | Medium |
| Moderate outlier | No supported finding, insufficient, or not analyzed | Not required | Low |
| No outlier | No supported finding | Not required | None |
| No outlier or unavailable | Insufficient or not analyzed | Not required | Insufficient data |

High priority requires overlap between the source events supporting the metric outlier and
the events cited by the LLM finding. Agreement without shared evidence remains medium.

The default metric bands are explicit preregistration candidates:

- strong composite score: at least 50 out of 100;
- strong single-metric tail score: at least 90 out of 100;
- strong contribution count: at least two metrics above their robust reference thresholds;
- moderate: at least one metric above its reference threshold without meeting a strong rule;
- no outlier: no included metric above its reference threshold.

These boundaries are not calibrated. Do not change them after viewing instructor outcomes
without recording the change as a separate analysis configuration.

## Evidence and identity requirements

The findings window and metric episode must represent the same observed session. Exact IDs
join automatically. Different IDs require a reviewed JSON mapping:

```json
{
  "review-window-id": "metric-episode-id"
}
```

The fusion pipeline rejects reused metric episodes and rejects metric evidence that is not
present in the review timeline. This prevents a high priority from combining two different
students, questions, or observation windows.

The current PR100 findings adapter does not yet produce Phase 2C question episodes. Real-data
fusion therefore requires an adapter that reconstructs metrics over the same bounded evidence
window, or a manually reviewed identity mapping plus matching source event IDs. Until then,
real findings remain model-only and receive medium or insufficient priority as appropriate.

## GPT and Gemini assessment

Both providers use the same prompt, `Assessment` schema, factual validator, saved-receipt
behavior, and no-automatic-retry rule. Provider selection is explicit from the model ID:

- `gemini-*` uses `GEMINI_API_KEY`;
- `gpt-*`, `o1*`, `o3*`, or `o4*` uses `OPENAI_API_KEY`.

No evidence is transmitted without `--send`. Use only a provider and data transfer approved
for the research dataset.

Example GPT analysis:

```bash
OPENAI_API_KEY=... uv run session-findings analyze private-data/prepared \
  --analysis private-data/prepared/analysis-openai \
  --model <OPENAI_MODEL_ID> --send \
  --output private-data/review-openai.private.json
```

## Combine saved outputs

First produce a Phase 3B ranking report and a saved review bundle. Then run:

```bash
uv run session-fuse \
  private-data/review-openai.private.json \
  private-data/question-ranking.private.json \
  --mapping private-data/session-episode-map.private.json \
  --output private-data/combined-review.private.json
```

Omit `--mapping` only when every review session ID exactly matches its Phase 3B episode ID.
Outputs are create-only and should remain outside version control.

## Output separation

Contract version 3 preserves:

- the original validated LLM analysis;
- the metric score, contributing metrics, baselines, and source event IDs;
- the deterministic combined rule and thresholds;
- shared evidence references;
- instructor review state, which remains independent of both automated signals.

The dashboard displays the combined priority, metric signal, LLM signal, and whether evidence
overlaps. Instructors can still inspect each source event and record their own judgment.

## Validation still required

- Confirm that PR100 events can be normalized into the Phase 2C schema without losing links.
- Confirm that metric and findings windows use identical boundaries.
- Measure how many sessions remain unscored because of missing question IDs or small cohorts.
- Compare metrics alone, LLM alone, and combined priority against blinded instructor labels.
- Report precision at a fixed review budget and inter-rater agreement.
- Evaluate GPT and Gemini separately. Model agreement is not human ground truth.
