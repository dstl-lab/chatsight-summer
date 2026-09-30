# Does evaluator disagreement change the simulator comparison?

**Yes: choosing the saved coder instead of the saved human judgments changes
the estimated gaps and can reverse the ordering of two prompt conditions. The
large work-presence mismatch remains under either set of labels.** This offline
diagnostic reuses the completed 88-message audit. No new generation, coding,
manual review, label changes or scorer adoption occurred.

## What was compared

The closed Gemini 2.5 Flash audit used the original **help-work-v1** definitions.
Its labels were compared with the same reviewer's saved judgments, separately for
16 recorded and 72 generated unique inputs. An input is exact candidate text
plus the complete ordered visible prefix. Provenance comes from the original
private mappings; none of the unique inputs has mixed recorded/generated origins.
All 88 inputs share only 16 conversation prefixes, with no verified independent
student-account sampling.

The three original review packets contain 109 reviewed rows before deduplication.
Unique-input agreement counts each input once. Historical rate comparisons instead
retain every original draw occurrence and equal conversation weights, including
the cached comparison's two draws sharing one judgment. The retrieval review
contributes to the unique-source audit; the gap tables cover the same fixed and
cached comparisons as the preceding sensitivity analysis. Studies are not pooled.

## Where the labels differ

Here TP/FP/FN/TN take the saved human flag as the reference, **not established
ground truth**. Unclear and conflicting judgments do not become negative labels.

| Source | Flag | TP | FP | FN | TN | Outside binary comparison |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Recorded | Work | 3 | 1 | 0 | 11 | 1 model unclear |
| Generated | Work | 51 | 10 | 0 | 11 | None |
| Recorded | Help | 13 | 0 | 2 | 0 | 1 model unclear |
| Generated | Help | 18 | 0 | 49 | 4 | 1 conflicting human judgment |

Work agreement is 14/15 (93.3%) on recorded inputs and 62/72 (86.1%) on generated
inputs. More revealingly, among human work=no cases the coder labels work=yes in
1/12 decisive recorded comparisons and 10/21 generated comparisons; a thirteenth
recorded negative gets model unclear. This is a descriptive difference, not a
validated source-specific error rate or a statistically established origin effect.
Different message content and class composition can contribute to the difference.

Help agreement is 13/15 (86.7%) recorded versus 22/71 (31.0%) generated. The
reviewer often treated a generated answer as implicitly asking for checking;
the coder often labeled it as not asking for help. This interpretation follows
the earlier audit's qualitative inspection, not access to the model's reasoning.
All recorded human help flags are yes, so recorded help specificity is unmeasured.

## What happens to the work-presence gap

Gap means **generated work-present rate minus recorded work-present rate**,
in percentage points. It is one marginal message feature, not a realism score.

| Saved comparison | Human-label gap | Coder-label gap | Change in gap |
| --- | ---: | ---: | ---: |
| Sept 15: current exchange only | +71.875 | +90.625 | +18.750 |
| Sept 15: earlier dialogue | +81.250 | +87.500 | +6.250 |
| Sept 22: cached replies | +25.000 | +18.750 to +31.250 | −6.250 to +6.250 |

For Sept 15, both sources label the eight recorded messages work=no. The human
labels mark 23/32 current-exchange and 26/32 history replies work=yes; the coder
marks 29/32 and 28/32. Therefore the human labels put current exchange closer
on this marginal rate, while the coder puts history closer. This is **not** a
new Brier-score result, adoption decision or established difference in realism.
Both conditions remain well above the provisional 20-point practical resolution.

For Sept 22, the human rates are 3/8 recorded and 10/16 generated. The coder has
four recorded yes, three no and one unclear, versus 13/16 generated yes. Keeping
all eight references and resolving unclear either way gives the reported range.
That range straddles the proposed 20-point resolution; it is not a confidence
interval. The unknown is retained, not dropped or silently set to no.

For fixed binary labels, the gap shift decomposes as:

`coder gap − human gap = (coder generated rate − human generated rate)
                       − (coder recorded rate − human recorded rate)`.

The report applies the same subtraction to the full possible range when the
coder returns unclear. These ranges describe only the saved outputs, with no
population sampling or finite-generation-draw confidence claim.

## Help is more sensitive to the interpretation

| Saved comparison | Human-label help gap | Coder-label help gap |
| --- | ---: | ---: |
| Sept 15: current exchange only | −6.250 | −84.375 |
| Sept 15: earlier dialogue | 0.000 | −65.625 |
| Sept 22: cached replies | −18.750 | −62.500 to −50.000 |

The same saved conversations support radically different help-rate conclusions
under these two label sources. This reinforces the distinction between an
expressed request and an inferred request for checking. It does not tell us which
old judgment is correct. The cross-review human help conflict is excluded from
unique-input agreement, while each historical study retains its own original
human judgment. Nothing is reconciled by voting or taking the newest label.

## Research decision

1. Retain the broad finding: these saved simulations have a large work-presence
   mismatch in the fixed comparison under both label sources. The original gap
   came from human labels, so automatic-coder disagreement did not create it.
2. Do not use this coder to rank small simulator improvements. Even the ordering
   of the two fixed conditions changes with the label source. A high pooled
   agreement percentage would hide this problem.
3. Do not plug these disagreement fractions into the prior sensitivity analysis
   as defensible true-error bounds. One reviewer, exposed cases, shared contexts
   and unresolved meanings do not establish either source as truth.
4. Close this diagnostic. No additional labeling or coder tuning is queued.
   Simulator development can proceed with already-supported literal form measures
   and captured notebook events; semantic ranking remains an open measurement
   problem. The proposed student-only earlier-context comparison remains a
   separate, unrun simulator intervention, with the complete current exchange held
   fixed. This analysis does not authorize a new provider batch.

The old audit gave every candidate its complete reviewed prefix, including
candidates generated under the current-exchange-only condition. That audit input
is preserved; this is not an experiment varying evaluator context. These results
do not validate the later `content_supplied` / `expressed_request` rubric or the
subsequent evidence-backed scorer. The 20-point resolution remains a provisional
project choice, not a scientific standard or passing criterion for this audit.

## Reproduction

The new aggregate artifact is ignored by Git:
`data/evaluator-source-disagreement-v1/report.json`. The runner reparses the
closed audit, checks its saved report and closure, verifies private origin joins,
uses the existing fixed/cached readers, and verifies 409 source/code file hashes
before writing a separate create-only report. Original artifacts remain unchanged.
The report contains no message text or per-input identities.

Verification: an independent check reproduced every source count and comparison
and verified all 409 hashes; a separate offline replay was byte-identical and
refused to overwrite its output. The Python suite plus frozen audit checks passed:
1,009 passed, three skipped, with the existing Starlette/httpx deprecation warning.

```sh
PYTHONPATH=. python -P experiments/2026-09-30-evaluator-source-disagreement.py \
  data/behavioral-measurement-schema-recovery-v1 \
  /path/to/new-report.json \
  --plan-sha256 de531030846f7918c26c68a69cc1bdabc1435c382e57ef2a321a82f72bfe4c5b
```

Related evidence: [closed measurement audit](2026-09-30-behavioral-measurement-readiness.md),
[assumed-error sensitivity](2026-09-30-evaluator-error-sensitivity.md), and
[reliability contract](2026-09-30-evaluator-reliability-contract.md).
