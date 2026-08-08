# 2026-08-07 — Distinctness and context-awareness as the label-quality axes

Status: **instruments implemented** on branch `distinctness-elicitation`;
findings below from smoke snapshot 20260807-d67ba530d3ee-dda99f (78 rows,
NOT for research use — all numbers are diagnostics, not measurements).

## Reframing (Minchan, 2026-08-07)

Abstention rate is a discovery channel, not a KPI — driving it down is
Goodhart-bait (a vague catch-all label zeroes abstention while worsening the
schema). The quality axes are: (a) **distinctness** — no two labels coincide
in definition or behavior; (b) **context-awareness** — verdicts use the
conversation, not surface matching.

## What the instruments found

- **`Confusion` is a rider**: co-fires with Debugging Request at J=0.71 and
  with every question-shaped label at ~0.5, with low rationale overlap
  (~0.2) — its operational meaning collapsed to "student asked a question."
- **Layer duplication**: the instructor's drafted schema re-derived the
  profile's intent layer under new names (asks-for-direct-answer ≈ Direct
  Solution Request, etc.) because `draft_schema` was blind to the layers it
  would be composed with. Four near-duplicate pairs in one 13-label run.
- **Context is load-bearing where it should be**: ablation probe (context
  window + tutor-after + latency stripped, 25 messages) flipped ≥1 verdict
  on 18/25; inference-heavy intent labels flip most (28%/20%); the only
  context-inert labels are legitimately surface constructs (paste
  detection, explicit affect). Inertness is a defect only when the
  construct requires context — the probe separates the two.

## What was built

1. **Layer-aware elicitation**: `draft_schema` receives the accepted
   profile's layers as an ALREADY-COVERED block; ELICIT and EXPLORE prompts
   carry a mutual-distinctness rule and ban "asked a question"-grade labels.
2. **Distinctness report** (`src/labeling/distinctness.py`): prevalence +
   pairwise Jaccard + rationale coincidence; printed after every CLI mass
   run; standalone against any snapshot.
3. **Context-ablation probe** (`src/labeling/ablation.py`): per-label flip
   rates with context stripped; refuses profile/snapshot mismatches
   (rule 2). Sensitivity diagnostic only — accuracy still belongs to blind
   audit (invariant 1).

## Literature grounding

Deep-research report (gitignored:
`data/research/2026-08-07-llm-labeling-research.md`) validates the
architecture (binary per-label calls beat joint prompting; separate
abstention channel; blind audit — anchoring shifts human labels without
speeding them up; turn-window context materially improves dialogue
annotation) and prescribes Phase 0 upgrades: per-label validation table
with positive-class recall, Calderon alt-test, entropy-routed audit
sampling (never verbalized confidence), prevalence correction via audit
confusion matrix, prompt-perturbation robustness check, and auditing the
abstention call itself. The "LLM hacking" result (~31% of downstream
conclusions wrong from configuration choices alone) is the standing reason
for hash-pinned vintages.

## Honest limits

All diagnostics ran on one 78-row smoke snapshot from 6 conversations; flip
rates and Jaccards at this n locate problems, they do not size them. The
distinctness thresholds (J≥0.4) and the probe's sample are conveniences,
not calibrated choices. Nothing here admits or retires a label — `Confusion`
gets tightened or retired through the tweak loop, then re-measured.
