# 2026-08-01 — Top-down labeling moves in-repo; ChatSight becomes a sibling

## Decision

This repo is no longer downstream of ChatSight. It becomes a single project with two
subsystems:

1. **Labeling (new, instructor-facing, top-down).** The instructor states what trends they
   want to see from the data — conceptual ("which topics are students struggling with"),
   behavioral/affective ("confused, satisfied, angry"), or other. The tool pulls a sample of
   real messages, drafts labels against the instructor's stated intent, and shows the labeled
   sample. The instructor either accepts the direction (→ mass-label the corpus) or tweaks it
   by describing what they want differently (→ new prompt, new draft, review again).
2. **Simulation (unchanged in goal).** Learner agents grounded in the labeled corpus, used to
   screen tutor-policy changes. Everything in the existing phase plan from Phase 2 onward.

Data acquisition follows ChatSight's existing pattern, not its code: `kubectl port-forward`
into the Kubernetes cluster tunneling the external PostgreSQL database of raw DSC 10 tutor
logs (`dsc10_tutor_logs`), read-only.

## What this dissolves

- **The ChatSight dependency pin** (old rule 2's cross-repo mechanism) — there is no
  cross-repo classifier anymore. Parity becomes *internal*: the simulation scores synthetic
  transcripts with this repo's own classifier at a pinned prompt/config hash + schema
  version.
- **The snapshot-export mechanism from ChatSight** (old open decision #6) — replaced by this
  repo's own labeling subsystem emitting labeled-corpus snapshots into `data/snapshots/`.
  Replaced as an open item by: credentials/namespace for the k8s tunnel from this repo.
- **Phase 1 living "mostly ChatSight-side"** — the intent-compiled schema loop is now this
  repo's first instructor-facing surface.

## What survives, re-pointed

- **Snapshot immutability.** The labeling subsystem reads the raw-log DB live (as ChatSight
  does); the simulation subsystem still consumes only immutable labeled snapshots with
  manifests. The live-DB boundary moves inside the repo: `src/labeling/` + `src/ingest/` may
  touch Postgres; `src/trajectories/`, `src/agents/`, `src/replay/`, `src/eval/` never do.
- **Classifier parity.** Same classifier (prompt hash, schema version) scores real and
  synthetic transcripts within an experiment. Every results artifact records the pins.
- **Schema versioning.** Every instructor prompt-tweak iteration is a new schema version;
  provenance records which iteration was accepted, on which sample.
- **All data-safety rules.** Same course, same logs, same IRB coverage. Student data never
  enters git; `.env` holds read-only DB credentials only.
- **All research invariants**, including: evaluation ground truth is human-labeled real data;
  admission threshold gates the simulation state space; ceiling-relative reporting.

## New rules created by this decision

1. **ChatSight is a sibling, not an upstream.** Reference its conventions freely (kubectl
   tunnel pattern, backend stack); never modify it from here, never import or vendor its
   code. This repo's classifier is a deliberate reimplementation, not a fork claiming
   equivalence.
2. **No cross-tool label comparison.** Labels produced here and labels produced by ChatSight
   are never compared or mixed in any claim unless a dedicated calibration study earns it.
3. **Blind measurement, anchored drafting.** The review-and-tweak loop shows model-drafted
   labels (anchored — fine for drafting). Reliability numbers for the admission threshold
   come only from instructor labels produced *blind* (messages shown without model labels),
   on a held-out sample never used in the tweak loop. Approval of a shown label is not
   ground truth; anchoring inflates agreement.
4. **Stratified review samples.** The sample shown to the instructor is deliberately
   composed (model-uncertain cases, embedding-diverse cases, boundary cases), not the first
   N or a uniform random pull — rare behaviors (quiet exit, answer-extraction) are the point
   of the project and won't surface in a quick random sample.

## Honest limits

- Reimplementing the classifier forfeits any continuity with ChatSight's labeled corpus and
  its instructor pilots' labels. Accepted: the two tools answer different questions, and
  pretending shared lineage would be worse than declaring independence.
- "Instructor likes the direction" is a UX milestone, not a validity milestone. The loop can
  converge on a schema that feels right and still fails the blind reliability check; the
  admission threshold (open decision #1) remains the only gate into the simulation.
- Live DB access from the labeling subsystem widens the surface where raw student text is
  handled. Mitigation is the internal boundary above plus the existing git hygiene rules,
  not any new confidence.
- The repo/tool name is explicitly temporary.

## Immediately affected documents

- `CLAUDE.md` — rewritten ChatSight-relationship section, layout, phase plan, open decisions.
- `snapshots.md` — snapshots now produced by this repo's labeling subsystem, not exported.
- The two referenced day-one memos remain missing (see `docs/README.md`); this memo partially
  supersedes the direction they would have carried.
