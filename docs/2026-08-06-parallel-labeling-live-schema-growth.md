# 2026-08-06 — Parallel mass-labeling and live schema growth from the abstention pile

Status: **adopted direction, phased.** Phase 1 (parallel executor + live abstention
surfacing) on branch `parallelize-labeling` (issue #1). Phase 2 (mid-run label proposal,
approval, single-label backfill passes, composite provenance) is a follow-up branch;
its design is fixed here so the split is planned, not accidental.

## Problem

Two, and they compound:

1. **Mass labeling is sequential.** `draft_labels` (src/labeling/draft.py) makes one
   Gemini call per student message, one at a time. The first real snapshot was 2,745
   turns; at sequential Flash latency that is the slowest step of the whole loop, and
   it is embarrassingly parallel — no call depends on any other.
2. **The abstention pile is write-only during mass runs.** The 2026-08-06 prompt
   redesign gave the classifier an abstention channel (`no_label_fits`) precisely so
   acts the schema misses would surface. The review loop shows abstentions
   (summary.py), but a *mass* run writes them silently into the snapshot. The comment
   in draft.py promises "feeds the instructor's coverage pile"; after a mass run,
   nothing feeds anything. Meanwhile the instructor sits idle watching a progress bar
   — exactly the person who could be deciding what the missing labels are.

Issue #1's original text (filed 2026-08-04, before the prompt redesign) asked for
ChatSight-style single-label fanout for *all* labels. That part is superseded: the
redesign memo deliberately adopted one-call-per-message with all labels in a block, and
the abstention channel only makes sense when one call sees the whole label set. This
memo keeps that architecture for the base pass and revives single-label calls only
where they are the right tool: backfilling a label that did not exist when the base
pass started.

## Design

**Base pass (Phase 1).** The schema is frozen for the duration of a run. `draft_labels`
gains a bounded worker pool (`workers`, default 8, configurable): each message's
classify call is submitted to a thread pool; results are collected back into input
order; `on_result`/`on_progress` fire as calls complete (the webapp already locks and
keys results by `(chatlog_id, message_index)`, so arrival order is immaterial). First
failure after retries stops new submissions, lets in-flight calls land, and re-raises —
same abort-but-keep-finished-work semantics as today. Concurrency is not a provenance
input; `classifier_hash` is untouched.

**Live abstention feed (Phase 1).** During `mass_labeling`, the webapp shows a running
abstention count and the abstained messages as they accumulate, and the done screen
carries a coverage report: N messages (X%) showed acts no label captures. The CLI
prints the same summary. The pile stops being write-only.

**Label proposal (Phase 2).** Periodically during a mass run, a separate aggregation
step reads the abstained pile and drafts candidate labels (name, description,
positive/negative criteria — the same shape the tweak loop produces). This does not
breach the redesign's "the classifier may never name a new label" rule: that rule
binds the per-message classifier, whose abstention stays a bare flag. The proposal
step is the existing schema-drafting step made incremental — aggregation over the
pile, shown to the instructor while the run proceeds.

**Approval → backfill (Phase 2).** If the instructor approves a candidate, the schema
grows append-only to vN+1 and a *single-label* parallel pass launches for that label
over the **entire** message list (binary verdict + rationale per message). Declined
candidates stay in the coverage report. Snapshot emission waits for the base pass and
every approved label's pass, so every message in the snapshot is judged against every
label in the final schema — no vintage mixing (invariant 6) even though labels were
born mid-run.

## Why mid-run label creation must be backfill, not append-from-here

If a label appeared at message 1,500 of 2,745 and only later messages were judged
against it, the snapshot would mix label vintages — invariant 6 and rule 2 both fall.
Sequential labeling at least has a coherent "when did the label exist" ordering; a
worker pool does not even have that. Freezing the schema per pass and backfilling new
labels over the full list is what makes the run parallelizable *and* the snapshot
coherent. The two problems solve each other.

## Provenance under Phase 2 (rule 2)

Original labels are judged by the multi-label prompt; approved labels by a
single-label prompt. One snapshot, two templates. The manifest therefore records
provenance **per label**: which prompt template and hash judged it. `src/scoring/`
pins the composite, so Phase 3 synthetic transcripts are scored label-for-label
identically. Pretending one hash covers both templates would be the actual rule-2
violation; per-label hashes are more bookkeeping but truthful bookkeeping.

## Honest limits

- **Single-label verdicts are not multi-label verdicts.** A label judged in isolation
  sees no cross-label context; the same label re-judged under the multi-label prompt
  in the next full schema revision may score differently. Within a snapshot each
  label is internally consistent; across snapshots the numbers are not comparable
  (standard invariant-6 discipline, now with a sharper edge).
- **Abstention flags go stale.** `no_label_fits` was judged against the base label
  set; an approved label may retroactively cover an abstained message. The flag stays
  as recorded — it is a model judgment at a point in time — and the coverage report
  notes which abstained messages the new labels' backfill ended up claiming.
- **Mid-run approval is anchored drafting.** The instructor approves a model-drafted
  label after seeing model-selected evidence (invariant 8's anchoring, squarely).
  Fine for drafting; no reliability number may ever come from it. Admission of a
  Phase-2-born label to the simulation state space still goes through the blind
  Phase 0 gate like any other label.
- **Throughput is bounded by the API tier.** Default `workers=8` assumes a paid-tier
  rate limit; `with_retries` absorbs stray 429s, but a free-tier key should run
  `workers=1..2` or the pool just converts rate limit into retry storms.

## Relation to open work

The abstained pile plus proposal candidates is an obvious input to stratified review
sampling (issue #10, invariant 9) — rare uncaptured acts are exactly what a review
sample should over-weight. Not built here; noted so #10 picks it up.
