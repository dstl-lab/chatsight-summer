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
