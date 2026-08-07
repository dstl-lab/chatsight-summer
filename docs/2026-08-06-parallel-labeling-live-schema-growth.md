# 2026-08-06 — Single-label parallel labeling and live schema growth from the abstention pile

Status: **adopted direction, phased.** Phase 1 (single-label call architecture +
parallel executor + live abstention surfacing) on branch `parallelize-labeling`
(issue #1). Phase 2 (mid-run label proposal, approval, backfill passes) is a follow-up
branch; its design is fixed here so the split is planned, not accidental.

Supersedes one aspect of the 2026-08-06 classifier-prompt-redesign memo: the
one-call-per-message / all-labels-in-a-block packaging. Everything else in that memo —
CourseProfile grounding, the turn-window context, the judgment rules, abstention as a
bare flag the classifier may raise but never name — survives unchanged and is carried
into the new prompts.

## Problem

Two, and they compound:

1. **Mass labeling is sequential.** `draft_labels` (src/labeling/draft.py) makes one
   Gemini call per student message, one at a time. The first real snapshot was 2,745
   turns; at sequential Flash latency that is the slowest step of the whole loop, and
   it is embarrassingly parallel — no call depends on any other.
2. **The abstention pile is write-only during mass runs.** The prompt redesign gave
   the classifier an abstention channel (`no_label_fits`) precisely so acts the schema
   misses would surface. The review loop shows abstentions (summary.py), but a *mass*
   run writes them silently into the snapshot. The comment in draft.py promises "feeds
   the instructor's coverage pile"; after a mass run, nothing feeds anything.
   Meanwhile the instructor sits idle watching a progress bar — exactly the person who
   could be deciding what the missing labels are.

## Design

**Single-label calls (Phase 1).** The multi-label block is dropped. Each label is
judged by its own call: one message + context window + *one* label's definition →
binary verdict + one-sentence rationale. A separate **coverage call** per message sees
all label definitions and returns only `no_label_fits` (plus a one-sentence note
describing the uncaptured act when abstaining — it describes, never names, so the
redesign memo's "the classifier may never name a new label" rule stands). The coverage
call runs for every message, not only all-false ones: a message can be partially
captured — one act labeled, another uncaptured — and conditional firing would miss
exactly those.

Why: uniformity with mid-run growth. When a label can be born mid-run (Phase 2), a
block architecture forces new labels through a *different* prompt than the ones that
shipped with the run — two templates in one snapshot, composite provenance, verdicts
that are not like-for-like. With single-label calls, a new label is just one more
label pass through the same template as every other label, ever. Isolation also
removes cross-label interference from verdicts, and per-label Phase 0 eval maps
one-to-one onto how labeling actually ran.

**Parallel executor (Phase 1).** The schema is frozen for the duration of a pass. The
unit of work is one call — (message, label) verdicts plus (message) coverage — fanned
out on a bounded worker pool (`workers`, default 8, configurable). A message's results
reassemble into one record when all its calls land; downstream contracts
(`on_result` per message, resume keyed by `(chatlog_id, message_index)`) are
unchanged. First failure after retries stops new submissions, lets in-flight calls
land, and re-raises — abort, but finished messages survive and the run resumes from
them.

**Live abstention feed (Phase 1).** During `mass_labeling`, the webapp shows a running
abstention count and the abstained messages (with their coverage notes) as they
accumulate; the done screen carries a coverage report: N messages (X%) showed acts no
label captures. The CLI prints the same summary. The pile stops being write-only.

**Label proposal (Phase 2).** Periodically during a mass run, an aggregation step
reads the abstained pile (messages + coverage notes) and drafts candidate labels
(name, description, positive/negative criteria — the same shape the tweak loop
produces). This is the existing schema-drafting step made incremental — aggregation
over the pile, shown to the instructor while the run proceeds. The per-message
classifier still never names labels.

The likely mechanism is embedding clustering: embed the abstained messages, cluster,
and draft one candidate label per coherent cluster (with the cluster's messages as
its evidence), rather than asking a model to eyeball the whole pile at once — the
same idiom as invariant 9's embedding-diverse review sampling. Decided at
implementation time in Phase 2, not binding here. One embedding use is explicitly
**rejected**: routing — skipping a label's calls for messages whose embeddings sit
far from that label's examples — because it silently trades recall for cost and
falsifies "every message was judged against every label." If cost ever forces triage,
embeddings may *order* work, never skip it.

**Approval → backfill (Phase 2).** If the instructor approves a candidate, the schema
grows append-only to vN+1 and a backfill pass launches for that label over the
**entire** message list — mechanically identical to any other label's pass. Declined
candidates stay in the coverage report. Snapshot emission waits for the base pass and
every approved label's pass, so every message in the snapshot is judged against every
label in the final schema — no vintage mixing (invariant 6) even though labels were
born mid-run.

## Why mid-run label creation must be backfill, not append-from-here

If a label appeared at message 1,500 of 2,745 and only later messages were judged
against it, the snapshot would mix label vintages — invariant 6 and rule 2 both fall.
A worker pool does not even have a coherent "when did the label exist" ordering.
Freezing the label set per pass and backfilling new labels over the full list is what
makes the run parallelizable *and* the snapshot coherent.

## Provenance (rule 2)

One template judges every label, so provenance stays per-label *uniform*:
`label_hash(label)` = hash of (single-label template, that label's canonical
definition, model, profile, context-window parameters), and a `coverage_hash` over
(coverage template, the full label set the coverage pass saw, model, profile, window).
Phase 1 freezes the schema, so the manifest can carry one run-level `classifier_hash`
folding all of these; Phase 2 records per-label hashes so a backfilled label's
provenance is exact. A label's verdicts do not depend on what other labels exist —
append-only growth leaves existing labels' provenance untouched. `scoring/` pins the
same hashes so Phase 3 synthetic transcripts are scored label-for-label identically.

## Honest limits

- **Cost multiplies.** ~(N+1) calls per message (N labels + coverage), each
  re-sending the context window. Parallelism absorbs the latency, not the spend.
  Output per call is small; input tokens dominate. If this bites, Gemini context
  caching over the shared window is the obvious lever — not built here.
- **No cross-label calibration.** A label judged in isolation cannot be traded off
  against a better-fitting sibling; whether isolation helps or hurts accuracy is an
  empirical question the Phase 0 eval arbitrates, per label, against the ceiling.
- **Verdicts are not comparable to block-era snapshots.** The template change is a
  new `classifier_hash`; numbers from snapshot 20260803-… and any single-label
  snapshot are different-vintage by construction (invariant 6 discipline).
- **Abstention flags go stale under growth.** `no_label_fits` was judged against the
  label set the coverage pass saw; an approved label may retroactively cover an
  abstained message. The flag stays as recorded, and the coverage report notes which
  abstained messages the new labels' backfill ended up claiming.
- **Mid-run approval is anchored drafting.** The instructor approves a model-drafted
  label after seeing model-selected evidence (invariant 8's anchoring, squarely).
  Fine for drafting; no reliability number may ever come from it. Admission of a
  Phase-2-born label to the simulation state space still goes through the blind
  Phase 0 gate like any other label.
- **Throughput is bounded by the API tier.** Default `workers=8` assumes a paid-tier
  rate limit; `with_retries` absorbs stray 429s, but a free-tier key should run
  `workers=1..2` or the pool just converts rate limit into retry storms.

## Relation to open work

The abstained pile plus coverage notes is an obvious input to stratified review
sampling (issue #10, invariant 9) — rare uncaptured acts are exactly what a review
sample should over-weight. Not built here; noted so #10 picks it up.
