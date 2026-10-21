# Full post-deployment export and review batches

The previous upload flow was a development sample: at most 20 selected windows
and at most one per notebook scope. The new default imports an entire PR100
export into a private SQLite index and accounts for every tutor-request record.
Eligible bounded windows are prepared in batches of at most 20, preserving the
existing finding algorithm, source links, validator and review interface.

User-facing commands and the complete workflow are in
[`anomaly-review/PR100_QUICKSTART.md`](../anomaly-review/PR100_QUICKSTART.md).

The operator's `--all` export uses a read-only repeatable-read transaction and
streams every schema-v1 event in the requested received-time interval. The
default lower bound is the first verified production receipt on October 13,
2026, at 17:30:59.701280 UTC, rather than the October 8 UTC Git merge. This
distinction does not establish simultaneous rollout to all student clients.
The upper bound is fixed before extraction. A persistent private HMAC key keeps
account pseudonyms consistent across exports; exact payloads remain unchanged.

The gzip begins with a versioned export header. The importer enforces the
declared range, reads bounded lines and indexes events on disk. Identical client
events received more than once by the database are deduplicated, even when their
database row IDs/received timestamps differ; conflicting payloads fail visibly.
Source provenance points to the first retained row in the original export.

One window is considered per tutor-mode request, including multiple requests
within the same notebook. The default window remains five minutes before and
twenty after. Every request is represented in a downloadable coverage ledger:
eligible, other mode, missing identity/time, invalid binding, unmatched response,
mixed modes, too recent, or oversized. Eligibility is not a model result. The
windows overlap and must not be counted as independent student attempts. No
automatic question segmentation or semantic compression is introduced.

Preparation sends nothing to a provider. A user can analyze a single batch or
explicitly start all eligible batches. Durable receipts preserve failures and
interruptions. An additional private cache reuses only exactly identical evidence
and model/prompt/schema/analyzer configurations across overlapping uploads.
Changed evidence remains a separate version. A pending cached request is never
silently resent. Database extraction and provider access remain separate tools.

The browser opens one bounded review bundle at a time. Export-level progress and
coverage remain available, completed batches can be opened during processing,
and refresh/restart preserves saved jobs. Human labels stay in the existing
browser storage keyed to a review dataset; this change does not provide automatic
label migration between exports or a shared reviewer database.

## Validation

Synthetic tests cover all-request coverage within one notebook, multiple batches,
overlapping-export assessment reuse, duplicate delivery versus conflicting IDs,
interrupted uploads, production range selection, consistent pseudonyms and the
browser's explicit separation of preview from analysis. The real export/import
verification is recorded in the task's final report; no production content is
committed to this repository.

The October 17 verification exported 2,595,496 records (548,145,742 compressed
bytes) through 2026-10-18T06:13:47.991824Z (October 17 at 11:13 p.m. Pacific).
Import retained 2,595,435 distinct events after removing 61 identical repeated
receipts. All 10,295 tutor-request records were accounted for: 8,284 eligible
windows in 415 review batches, 363 oversized, 188 without a matched completed
response, 1,219 outside tutor mode, 213 in mixed-mode windows, 13 missing a scope,
and 15 awaiting enough follow-up time. There were also 753,705 source events
without complete notebook identity; the UI reports that coverage limitation.
The real export and its first batch opened in the browser without model calls.
