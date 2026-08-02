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
| _(none yet — labeling subsystem not built; k8s tunnel access is open decision #6)_ | | | | | | | |
