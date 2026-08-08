# 2026-08-07 — Phase 0 eval harness: literature-prescribed instruments

Status: **implemented** on branch `eval-harness` (`src/eval/`), per the
deep-research review (gitignored `data/research/2026-08-07-llm-labeling-
research.md`) and Minchan's distinctness/context reframing. Phase 0 is
CLAUDE.md's "START HERE" — this is its first real code.

## Modules

- **`validation.py`** — per-label table: positive-class precision/recall,
  Cohen's kappa, support, raw vs **Rogan-Gladen corrected prevalence**, a
  ceiling column (invariant 2 — prints "—" until a second annotator
  exists), and a "≈ chance — keep human-only" flag at kappa < 0.2 (LACA's
  move). Never a pooled accuracy. First real run (30-message audit vs the
  2026-08-06 snapshot) already shows the point: references-assignment-item
  reads 50% raw prevalence, 33% corrected.
- **`alttest.py`** — Calderon alt-test (ACL 2025): per-annotator advantage
  probabilities with epsilon slack, majority decision. Refuses to run with
  fewer than two annotators rather than degenerate silently.
- **`routing.py`** + `llm.gen_config(temperature=...)` — vote-entropy audit
  routing (CoAnnotating): k sampled votes at temperature 0.7, binary
  entropy per label, top-n keys become the audit's uncertainty stratum.
  Temperature exists ONLY for diagnostics; labeling runs stay at API
  default (a temperature touching snapshot verdicts would be a provenance
  input). Verbalized confidence is never used for anything.
- **`audit_sample.py`** — blind-audit composition (invariant 9): abstained
  stratum first (capped at 40% — the abstention call is a classifier too),
  high-entropy stratum when routing ran, seeded random fill; anchored keys
  excluded up front (invariant 8).

## Case-law loop (prescription #5) — process, not code

Adjudicated audit disagreements become criteria wording, as already done
for direct-answer-request (2026-08-06 pilot) and Confusion (2026-08-07
distinctness pass). Structured per-label exemplar *fields* (one positive +
one near-miss each, hash-pinned, sampler-excluded) remain deferred exactly
as the 2026-08-06 redesign memo's Option C: worth building after a real
instructor has exercised the loop, not before.

## What Phase 0 still needs (in order)

1. **A second annotator** (Sam or a TA) on a shared blind sample — unlocks
   the ceiling column and the alt-test; until then every number ships
   ceiling-less and says so.
2. **A live vote-entropy collection run** (k=5 at temp 0.7 over a snapshot
   slice) to feed `route_audit` — first real uncertainty stratum.
3. **A fresh blind audit of the layered schema** via `audit_sample` —
   current audit predates concepts/move/tightened-Confusion; `Confusion`'s
   three "why is my code wrong" survivors are queued boundary cases.
4. **Prompt-perturbation robustness check** (research prescription #3) —
   once per schema version; not yet built.
5. Admission-threshold proposal (open decision #1) once 1–3 exist — the
   original issue #6, now with its dependencies actually buildable.

## Honest limits

The single existing audit is n=30, one annotator, against a retired flat
schema; the validation table's real numbers are demonstrations of the
instrument, not measurements of the current classifier. Entropy routing is
implemented but has never run against live votes. The alt-test has run
only on synthetic fixtures.
