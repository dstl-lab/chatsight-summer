# Admission threshold for the simulation state space — proposal (issue #6)

Date: 2026-08-10. Status: **proposal for Minchan + Sam** (open decision #1
in CLAUDE.md — this memo does not decide it). Phase 0's deliverable: the
rule that separates labels an agent may move through (invariant 3) from
labels that stay analytics-only.

## What the threshold gates

A label admitted to the state space becomes part of how synthetic
trajectories are generated AND scored (rule 2: same classifier both
sides). An unreliable admitted label doesn't just add noise — it
manufactures phantom dynamics that policy screening then "detects."
Poison, not dilution. The threshold is therefore conservative by design:
the cost of excluding a real-but-unreliable label is analytics-only
status; the cost of admitting a bad one is corrupted Phase 2–4 claims.

## Proposed rule (four conjunctive conditions per label)

A label is admitted iff, on a blind audit of the pinned schema vintage:

1. **Human-measurable.** Criteria within the brevity caps (desc ≤20w,
   criteria ≤25w — enforced at draft time since `brevity-caps` landed),
   and per-label positive support ≥ 25 in the audit pool, so the Wilson
   95% CI on precision is at most ±0.15. Numbers with less support are
   *provisional* and cannot admit (they can only deny early).
2. **Reliable against the ceiling, not against 100** (invariant 2):
   positive-class precision ≥ 0.80 × the two-annotator agreement ceiling
   for that label's layer, AND Cohen's κ ≥ 0.4 against the blind human.
   Rationale for the κ floor: the 2026-08-10 audits show κ collapses to
   ≈0 exactly where humans can't apply the construct — κ≥0.4 ("moderate")
   is the lowest bar at which the label demonstrably means something
   shared. The 0.80×ceiling term keeps the bar honest where humans
   themselves disagree.
3. **Alt-test pass** (Calderon et al.): the model must be exchangeable
   with a human annotator (ε=0.1) on the label's layer, measured with ≥2
   annotators. One annotator cannot admit a label.
4. **No standing red flags**: not distinctness-flagged (Jaccard ≥0.4
   co-fire with another admitted label, unresolved), no outcome-anchor
   FLAG, and — for labels whose prevalence differs by mode — reliability
   reported per mode with the WORSE mode meeting condition 2, or the
   label admitted for that mode only.

**Mechanical facets are admitted by construction** (mode, defected,
attempted, error_verified, question_ref, latency, pre_pattern): they are
logged facts with no human-judgment component. They form the state
space's free backbone — this is why the sequence work matters for the
threshold: it shrinks the set of constructs that need to clear the
human-measurement bar at all.

## What today's evidence says (illustrative, NOT admission decisions —
single annotator, support 1–4, no ceiling yet on this vintage)

Under the tightened vintage, Seeking Validation, Code Implementation
Query, concept-misapplication, outcome-focused-query would be trending
toward admission (P=1.00 at tiny n); Frustration (P=0.25) and
Conceptual Clarification (0.50) toward analytics-only; everything else
needs support. The verbose→tight swing (four labels 0.00→≥0.75) is the
cautionary tale condition 1 encodes: reliability numbers are only as
real as the human measurement behind them.

## Costs this implies

- Per admitted label: ~25 positive-support blind judgments × ≥2
  annotators. At the audit tool's measured pace (~10s/judgment), a
  12-label schema needs roughly 2×100 minutes of annotator time to
  adjudicate fully — bounded, and sequential auditing (deny early at low
  support) cuts it further.
- A per-layer double-annotated ceiling sample (~40 joint pairs) per
  schema vintage.
- Re-audit on every criteria rewording (new vintage) — brevity caps make
  this cheaper, not optional.

## Honest limits

- The 0.80×ceiling and κ≥0.4 constants are defensible-but-arbitrary;
  they should be stress-tested against the first full two-annotator
  audit rather than treated as derived quantities.
- Recall is under-measured by per-label sampling (model-negative strata
  are thin); stratum-weighted recall is still unbuilt. Until it exists,
  admission leans on precision + κ, and recall claims stay qualitative.
- The alt-test with 2 annotators at n≈8 per label is weak; it hardens
  with the support requirement, but a label can pass alt-test while
  failing everything else — it is a necessary, not sufficient, signal.
- Mode-split condition 4 currently has evidence from 96 judgments on one
  annotator; the tutor/chatgpt reliability gap (92% vs 82% post-brevity)
  may shrink or grow with support.

## Decision requested

Adopt/adjust the four conditions and constants (0.80×ceiling, κ≥0.4,
support≥25, ε=0.1), and confirm the mechanical-facet free pass. On
adoption, the first full admission audit runs on the next two-annotator
vintage (evidence-run snapshot + Steven).
