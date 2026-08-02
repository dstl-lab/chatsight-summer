# Snapshot ledger

Human-readable register of every labeled-corpus snapshot this repo knows about.
Snapshots live in `data/snapshots/<snapshot_id>/` (gitignored — see CLAUDE.md rule 4) and
are immutable: if labels change upstream in ChatSight, that is a *new* snapshot with a new
row here. Experiments pin exactly one snapshot ID; this file is the only place a snapshot's
provenance is recorded in git, so keep it complete.

Each snapshot directory must contain a `manifest.json` with at minimum:
`snapshot_id`, `export_date`, `chatsight_sha`, `schema_version`, `row_counts`
(conversations / turns / label applications). `src/ingest/` validates this on load.

| snapshot_id | export date | course | chatsight SHA | schema version | conversations | notes |
|---|---|---|---|---|---|---|
| _(none yet — blocked on the ChatSight-side export mechanism, open decision #6)_ | | | | | | |
