# Two-annotator audit round — snapshot 20260810-b975dcfde38c-927c22

Date: 2026-08-10. Annotators: Steven and Austin, both blind, remote
(wormhole-transferred snapshot), same sample (seed 0, 48 messages, 96
judgments each, identical judged-label sets per message — verified).
Model side: schema b975dcfde38c, classifier 927c22cf2d0f, profile
821784c1258d. This is the first vintage with a measured human-agreement
ceiling and a defined alt-test (both required ≥2 annotators).

## Headline: the ceiling is now the binding constraint

On the 96 jointly judged (message, label) pairs:

| agreement | value |
|---|---|
| human–human (the ceiling) | **68%** |
| model–Steven | 79% |
| model–Austin | 64% |

The classifier agrees with each human about as much as — and with Steven,
*more* than — the humans agree with each other. Invariant 2 says this is
near the achievable maximum **for this schema as humans can currently
apply it**. Further model tuning cannot be measured until human agreement
improves; criteria work now pays through the ceiling, not the model.

Per-layer ceiling (pooled judgments): intent 73%, concept 72%,
**affect 44%** (n=16). Frustration's ceiling is 38% with κ=−0.25 —
Steven and Austin systematically disagree about what frustration looks
like in terse messages. Confusion: 50%, S+5 vs A+1. The affect layer, as
written, does not yet describe a shared construct.

## Alt-test: PASS — after fixing a harness bug

`alt_test` scored agreement over all 12 schema labels per message, but
the audit judges only ~2 labels per message: both humans' unjudged slots
default False and agree trivially, while the model was graded on labels
nobody audited. That artifact produced advantage 0.12/0.17 (fail).
Restricted to labels actually judged per message (fix in
`src/eval/alttest.py`, regression-tested):

- vs Steven: advantage 0.79 — wins
- vs Austin: advantage 0.81 — wins
- **PASSES** (ε=0.1, Calderon decision rule, 2 annotators)

The model is statistically exchangeable with either annotator on this
task, per the proposal's condition 3 — with the standing caveat that a
2-annotator alt-test is the weakest defined form.

## Per-label admission check (2026-08-10 proposal)

Pooled human judgments (support = human positives; all support < 25, so
**nothing can admit this round** — condition 1; the round can only deny
early):

| label | P | recall | κ | ceiling | support | trend |
|---|---|---|---|---|---|---|
| Seeking Validation | 0.75 | 1.00 | 0.75 | 0.75 | 6 | toward admission |
| bare-assignment-reference | 0.75 | 0.86 | 0.62 | 0.62 | 7 | toward admission |
| Conceptual Clarification | 0.62 | 1.00 | 0.62 | 0.62 | 5 | toward admission |
| Debugging Request | 0.62 | 0.71 | 0.38 | 0.62 | 7 | κ just under 0.4 |
| Frustration | 0.62 | 0.71 | 0.38 | 0.38 | 7 | ceiling too low to admit |
| Alternative Method Query | 0.50 | 1.00 | 0.50 | 1.00 | 4 | P below 0.80×ceiling |
| Direct Solution Request | 0.50 | 1.00 | 0.50 | 0.75 | 4 | P below bar |
| Code Implementation Query | 0.38 | 1.00 | 0.38 | 0.62 | 3 | deny-early |
| explicit-concept-mention | 0.38 | 1.00 | 0.38 | 0.88 | 3 | deny-early |
| assignment-prompt-paste | 0.38 | 1.00 | 0.38 | 0.62 | 3 | deny-early |
| Confusion | 0.38 | 0.50 | 0.00 | 0.50 | 6 | deny-early (κ≈0) |
| code-completion-request | 0.17 | 0.50 | 0.08 | 0.75 | 2 | deny-early (κ≈0) |

Mode split, pooled: tutor 71% (n=146), chatgpt 74% (n=46) — the
single-annotator tutor/chatgpt gap (92/82) did not replicate; treat the
gap as unresolved, not established.

## Attacks on these numbers before believing them

- **Per-label ceilings sit on n=8 joint pairs each.** A 0.80×ceiling bar
  multiplied against an n=8 estimate is arithmetic on noise; the proposal
  itself said the constants must be stress-tested here. Stress-test
  result: per-label ceilings need the ~40-pair joint sample the proposal
  budgets before any admit/deny is final. Layer-level ceilings (n=16–48)
  are the citable ones this round.
- **Model–Steven (79%) > human–human (68%)** admits two readings: the
  model genuinely tracks the criteria, or Steven and the model share a
  literalist reading that Austin doesn't. Distinguishing needs annotator
  3 or an adjudication pass on the 31 human-disagreement pairs.
- **Austin's sparse positives** (0 assignment-prompt-paste vs Steven's 3;
  1 Confusion vs Steven's 5) could be construct disagreement or
  differing default-no thresholds — the annotator-guide practice effect
  is uncontrolled for both first-time annotators.
- Raw prevalence is 50% by sample construction (balanced per-label
  passes); corrected-prevalence columns from this round say nothing
  about the corpus.

## What this round decides

1. **Affect layer (Frustration, Confusion) stays analytics-only** for
   now — humans cannot agree on it (ceiling 38–50%, κ≤0.16); no model
   number on these labels is meaningful until the constructs are
   rewritten or judged at conversation level instead of message level.
2. Confusion, code-completion-request: deny-early under the proposal
   (κ≈0 against pooled humans on top of the low ceiling).
3. Seeking Validation, bare-assignment-reference, Conceptual
   Clarification: the admission candidates worth buying support≥25 for.
4. Alt-test condition of the proposal is met on this vintage; the
   support condition is the sole blocker for the candidates above.

Next instruments, in order: adjudication pass on the 31 disagreement
pairs (cheap, sharpens the ceiling), a support-targeted round (~25
positives on the three candidates only, not all 12 labels), affect-layer
construct rewrite as a new vintage.
