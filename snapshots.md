# Snapshot ledger

Human-readable register of every labeled-corpus snapshot this repo knows about.
Snapshots are emitted by the labeling subsystem (`src/labeling/`) into
`data/snapshots/<snapshot_id>/` (gitignored — see CLAUDE.md rule 4) and are immutable: if
labels or the schema change, that is a *new* snapshot with a new row here. Experiments pin
exactly one snapshot ID; this file is the only place a snapshot's provenance is recorded in
git, so keep it complete.

Each snapshot directory must contain a `manifest.json` with at minimum:
`snapshot_id`, `export_date`, `repo_sha`, `schema_version`, `classifier_hash`,
`row_counts` (conversations / turns / label applications). `src/ingest/` validates this
on load.

| snapshot_id | export date | course | repo SHA | schema version | classifier hash | conversations | notes |
|---|---|---|---|---|---|---|---|
| 20260803-275ba59cc0fb-73419b | 2026-08-03 | DSC 10 | 3f3ec7b | 275ba59cc0fb | 73419b573364 | 151 (9,289 excluded by --max-conversations cap) | First real snapshot, emitted via label-loop-web; 2,745 turns, 1,381 label applications |
| 20260806-003cb322c943-2aa40b | 2026-08-06 | DSC 10 | 065f899 | 003cb322c943 | 2aa40bd1d96e | 19 (9,423 excluded by --max-conversations cap) | Smoke test of single-label parallel labeler (branch parallelize-labeling); 586 turns, 299 label rows; NOT for research use. Quality pilot ran against it (docs/2026-08-06-label-quality-pilot.md) |
| 20260807-c1c39e153ff2-168d80 | 2026-08-07 | DSC 10 | e0d3fec | c1c39e153ff2 | 168d80bb8385 | 8 (--max-conversations 10; 2 empty) | Smoke test of corpus-grounded layered labeling (profile2 233fdbe8c236, composed 13 labels, concept facet); 89 label rows, 3 abstentions; NOT for research use (docs/2026-08-07-corpus-grounded-curated-labeling.md). Snapshot directory LOST 2026-08-07 (deleted with its gitignored worktree data/); row retained as provenance record only |
| 20260807-d67ba530d3ee-dda99f | 2026-08-07 | DSC 10 | 7a7dff2+wip | d67ba530d3ee | dda99f346f14 | 6 (--max-conversations 8; 2 empty) | Smoke test of context-timing vintage (latency facet + discourse move; profile2 233fdbe8c236); 78 rows, move coverage 78/78, 4 abstentions; NOT for research use (docs/superpowers/specs/2026-08-07-context-timing-labels-design.md) |
| 20260810-937c9f6ba4b5-4ae154 | 2026-08-10 | DSC 10 | see manifest | 937c9f6ba4b5 | 4ae154 (see manifest for full hash) | 49 of 8,028 in window (60 drawn uniformly, seed 0, 2026-03-04..07-31; 11 empty) | First sequence-grounded research-candidate snapshot: composed 12 labels (profile a5241abd5c25), 170 label rows; pre-chat pattern 55% pass-then-ask / 25% fail-then-ask / 20% ask-first; question-level granularity 44%; error_verified 39%; outcome anchors hold (Debugging 42% vs 25% baseline). Copy rescued to main/data/. docs/2026-08-10-march-july-sequence-run.md |
