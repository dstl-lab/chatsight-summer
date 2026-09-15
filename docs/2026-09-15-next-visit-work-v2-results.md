# Completed next-capture work forecasts

V2 is complete: **two logical Gemini 2.5 Pro requests, two adapter attempts and
two valid forecasts**. No retries, exclusions, replacement draws, model-generated
chat or notebook executions. The earlier authored schema check was a separate
one-request/one-attempt operation and was not repeated.

Minchan explicitly answered yes to resending the same two excerpts under the new
two-request/eight-attempt cap. `explicit-approval-response.json` binds seven
unchanged artifacts and predates both dispatches. The prior inferred authorization,
V2 automatic-review rejection and failed V1 run remain unchanged.

## Prespecified mechanical comparison

All 58 and 54 initial code positions were forecastable. The prompts contained the
initial notebook sources and matched first student/tutor exchange only. Later
work, elapsed capture gap, outputs and later dialogue stayed outside the prompts.
Unlisted cells retain initial source. A changed position is a textual source
difference; all comparisons use the same fixed layout and exact non-code source.

| Fixed pair | Initial code positions | Observed changes | Forecast changes | Overlapping changed positions | Extra changes | Missed changes | Exact source matches at observed changed positions |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 | 58 | 1 | 7 | 1 | 6 | 0 | 0 |
| 3 | 54 | 4 | 1 | 1 | 0 | 3 | 1 |

The unchanged-source baseline predicts no changes. It produces zero extra changes,
misses one/four observed changes respectively, and has zero exact source matches
at the observed changed positions. No single weighted ranking against that
baseline was prespecified, so these tradeoffs remain visible rather than becoming
an invented aggregate success score.

Across the two examples, the forecasts overlap two of the five observed changed
positions, miss three, and add six source changes where no net change was recorded.
One of the five observed changed sources matches exactly. These are counts across
two notebooks, not independent trials per cell or an accuracy estimate for students.

## What the result tells us

The first completed notebook-work comparison shows uneven predictions of the
extent and location of work: more changes than observed in one example, fewer in
the other. A valid response format and a plausible edit are insufficient evidence
that a forecast matches recorded work. This is a measurable limitation worth
retaining, not a reason to quietly adjust prompts to these five known locations.

Exact source agreement is separate from correctness. Pair 2's overlapping change
is not an exact match; this does not mean the proposed code is wrong. No semantic
or correctness evaluator was run. Cell identity is positional, stored outputs are
incomplete, and the reference is the next eligible linked capture, which need not
be the student's next actual visit. We do not know intermediate actions or how
much work occurred before an unlogged visit. Actual capture gaps differ and were
not given to the model.

Both pairs were previously inspected and selected for compatible layouts. With
one draw per example, this is exposed development evidence, not a holdout, calibrated
probability estimate or generalization result. It evaluates a separate next-capture
state forecast; the existing next-action/runtime student and the earlier chat
help/work mismatch remain separate. No learning or causal teaching claim follows.

## Verification and stopping decision

Independent recomputation directly from raw initial/target cells and returned
edits matches every reported count without using the scorer. It also verifies
all code positions, unique in-range edits, exact prompt hashes, approval ordering,
source pins and preservation of V1 failures. The frozen scorer reopens identically
offline. Preparation/approval groups of 19/17/7/4 file hashes match; the prior
V1 completion's 32 files, notebook-pair audit's 20 files and help/work coding's
nine files remain unchanged. These groups overlap and are not summed as distinct
files. The explicit V2 authorization is separately pinned alongside the scorer's
historical preparation-authorization reference.

Private evidence is under `data/episode-pilot/next-visit-work-v2/`: `run.json`,
`scores.json`, `explicit-approval-response.json`, `execution-verification.json`
and the completed audit/report. Reproduce the score without another model call:

```sh
PYTHONPATH=. ../main/.venv/bin/python data/episode-pilot/next-visit-work-v2/score.py
```

Close this fixed run. Preserve both forecasts and the simple baseline; no new
labels, human plausibility review, rerolls, automatic prompt tuning or adoption
into the action simulator. A subsequent fidelity study must define its observation
boundary and held-out sampling before generation. The next research question is
how well the system predicts the amount and location of recorded work under that
boundary, with uncertainty and an explicit baseline. Keep PR #25 draft/unmerged.
