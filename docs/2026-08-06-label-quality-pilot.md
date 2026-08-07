# 2026-08-06 — Label-quality pilot: blind mini-audit + architecture diff

Status: **findings memo.** One-evening pilot run against the smoke-test
snapshot `20260806-003cb322c943-2aa40b` (19 conversations, 299 student
messages, 6-label schema `003cb322c943`, single-label classifier
`2aa40bd1d96e`, branch `parallelize-labeling` @ 065f899). Artifacts in
`data/audit/20260806-003cb322c943-2aa40b/` (gitignored). No number here is a
Phase 0 measurement; every claim carries its limits below.

## Setup

Two probes, run the same evening the single-label parallel labeler first ran
end-to-end:

- **A. Blind mini-audit.** 30 stratified messages (review-loop sample
  excluded per invariant 8), labeled blind by Minchan in a throwaway
  localhost tool, scored against the classifier per label.
- **B. Architecture diff.** The retired all-labels-in-one-call classifier
  (main @ 6fca6ac) rerun over the same 299 messages; per-label agreement with
  the single-label classifier; the human audit used as tiebreak on the
  overlap.

## Findings

**1. Well-defined labels sit at 0.83–0.93 blind agreement** (paste-detection
1.00 precision at support 14; assignment-reference 1.00 recall at support 10).
The frustration label never occurred in the audit sample (support 0 — rare
labels need targeted sampling, invariant 9).

**2. The weak label was weak because its criteria were contested, not
because the classifier misread messages.** `direct-answer-request` scored
P=0.44/R=0.57 against the raw audit — but every disagreement was one of two
boundary patterns: (a) a pasted assignment prompt as the whole message, in a
conversation where the tutor answers such pastes with full solutions; (b)
"how to solve [item]"-style approach questions. The instructor then ruled
(a) counts and (b) does not — i.e. **the classifier had inferred both
rulings already**; rescored against ruling-corrected truth the *old* labels
were P=1.00/R=0.90. This is criteria drift in the EvalGen sense, caught by a
30-message audit.

**3. Encoding the rulings explicitly** (schema `147356de4392`, deterministic
criteria surgery, parent-chained) made the classifier apply the
pasted-prompt rule *more* consistently than the partially-corrected ground
truth, surfacing further audit marks inconsistent with the instructor's own
ruling. Reconciled: revised ≈ P 0.92 / R 0.92 vs old 1.00 / 0.75 — the
revision trades precision for recall in favor of ruling-consistency.

**4. Ground-truth self-consistency is the current bottleneck.** The single
annotator's 30 blind marks disagreed with his own subsequent rulings on ~11
messages ("my answers might slightly be inconsistent" — confirmed). Further
classifier tuning on this label is unmeasurable until the ground truth
stabilizes: second annotator, adjudication round, ceiling (#5).

**5. The two architectures agree 89–99% per label**; divergence concentrates
exactly on the contested boundary (single-label applies
`direct-answer-request` 29 more times out of 299 — the pasted-prompt
inferences). Human tiebreak on the 9 disagreeing (message,label) pairs in
the audit: 4 single-label / 5 block. **No evidence the architecture change
moved accuracy either way.**

**6. The abstention channels are different instruments.** Dedicated coverage
call: 32/299 abstentions; block prompt's inline flag: 78/299. Neither is
validated; treat abstention rates as channel-specific, never comparable
across the architecture boundary.

## What was changed on the strength of this

- Schema `147356de4392` (rulings encoded in `direct-answer-request`
  criteria) — saved, not yet used for a mass snapshot.
- Message-form facet (redesign memo Option B) adopted: list-valued `forms`
  on the coverage call, since the largest divergence sits precisely on the
  pasted-prompt surface form the facet makes mechanical.

## Roadmap it motivates (not built)

Per-label few-shot exemplars (Option C, after real-instructor contact);
per-label model routing (mechanical labels on Flash, inferential ones on a
stronger model or N-vote self-consistency — natural in the single-label
architecture, provenance-ready in Phase 2's per-label hashes);
disagreement-targeted audit sampling (the architecture diff is a free
uncertainty signal for #10).

## Honest limits

n=30, one annotator, no inter-rater ceiling, ground truth corrected
post-hoc by the same person who produced it (adjudication and audit are not
independent), correction applied by text-snippet matching rather than
message-by-message re-audit, and the audit tool/flow was built the same
evening (no instrument validation). Nothing here admits a label to the
simulation state space; Phase 0 (#3–#6) owns that. Student messages are
paraphrased as patterns, never quoted.
