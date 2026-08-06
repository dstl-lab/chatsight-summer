# 2026-08-05 — Simulation-first framing: ChatSight is a distant cousin, not a sibling

## Decision

This project's outward identity is **a screening instrument for AI tutor design**:
simulated student cohorts, grounded in a full quarter of real DSC 10 tutoring logs, that
let an instructor test candidate tutor policies before any real student is exposed.
Labeling is internal machinery — the projection that turns transcripts (real or synthetic)
into a state space — not the headline and not the product.

Consequently we stop deriving this project from ChatSight in any pitch, proposal, or paper
framing. ChatSight is a distant cousin: it appears in one sentence as prior experience with
instructor-facing labeling (SIGCSE TS submission, n=2 study), and otherwise not at all. The
lineage that matters for the papers is Park et al.'s *Generative Agents*, transposed from
self-report grounding to behavioral-log grounding, with PromptDecipher as the foil
(pre-defined scenarios vs. our real-course grounding + instructor-authored metrics).

## What this changes

- **The pitch leads with the contribution.** One-liner: "narrows twenty candidate tutor
  policies to the three worth a real quarter." Labeling enters a sentence later, as
  mechanism.
- **Naming (open decision #7).** The permanent name should say simulation/screening, not
  labeling. This memo settles the direction of that choice, not the name itself.
- **Proposal documents get restructured** per the revision guide below.

## What this does NOT change

- **Every ChatSight rule in CLAUDE.md stays, and effectively strengthens.** Never modify,
  never import, and above all never compare or mix labels across the two systems. A distant
  cousin has *less* claim to label continuity than a sibling did. The one kinship that
  cannot be erased is the shared raw-log database; provenance must always state it.
- **Labeling's engineering standard.** "Means to an end" describes labeling's place in the
  story, not its quality bar. It is the compiler of this system: not the product, but a
  miscompile silently poisons every downstream claim. Admission threshold, blind
  measurement, and stratified review samples (invariants 3, 8, 9) are untouched.
- **Claim discipline.** Screening instrument; never "improves learning."

## Proposal revision guide

Applies to the current proposal draft (Status Quo / Proposed Direction / Blockers /
Proposed System). Target skeleton: **Opportunity → Proposed system → Why clustering works
now → Validation → What we will and won't claim → Positioning.**

1. **Cut "Status Quo."** Open with the screening-instrument one-liner. Delete "reframed the
   goal of labeling" — it defines the project by what it is a variation of.
2. **Reframe the blocker as the design argument.** Prior clustering attempts failed *in raw
   feature space* (reported: message time-deltas and lengths — verify with Sathvika before
   citing). This system constructs the space in which clustering is meaningful:
   instructor-defined label trajectories ("instrumental ask → got hint → re-engaged" vs.
   "→ extracted answer" vs. "→ went silent"). Past difficulty becomes the justification for
   the pipeline, not a caveat about it.
3. **Replace "good enough" with the threshold framing.** Labels need not describe
   everything; they must be reliable enough to measure with. A label enters the state space
   only if its classifier clears the admission threshold against human agreement; labels
   that miss are excluded, not diluted in.
4. **Rewrite the pipeline steps with invariants baked in:** stratified (not small random)
   review samples; a blind-labeled held-out measurement step between mass-labeling and
   clustering; 4–7 archetypes instantiated as agents, never individual students; outcomes
   reported as cohort trajectory-distribution shifts vs. the real baseline; quiet exit as a
   first-class agent action, not merely where a transcript stops; an explicit validation
   step (held-out turn prediction, distributional + transition fidelity vs. the
   human-agreement ceiling, usable-horizon curve).
5. **Add an honest-limits paragraph** (see below).
6. **One positioning sentence:** Generative Agents transposed to behavioral logs; unlike
   PromptDecipher's pre-defined scenarios, grounded in one real course's logs and evaluated
   on instructor-authored metrics.

## Honest limits

- **Stationarity is assumed, narrowly.** We claim behavior is stable enough *within one
  course iteration* for screening; model releases, course policy, and external-tool UI all
  drift semester to semester. Drift is itself measurable across snapshots — a feature of
  the snapshot discipline, not a hole in it.
- **Resolution is archetype-level.** The method cannot see per-student effects; this is an
  IRB position and an honesty position simultaneously.
- **The instrument screens; it does not conclude.** Output is "which policies merit a real
  quarter," never "which policies work."
