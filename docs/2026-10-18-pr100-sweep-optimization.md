# PR100 sweep optimization — October 18, 2026

The immediate task is manual review of recent current-quarter PR100 observations.
At more than ten seconds per sequential model call, 8,284 overlapping windows are
an impractical interactive workload. Preserve the raw export and existing results;
reduce redundant analysis and transport overhead without claiming better findings.
Austin explicitly requires the running process to remain undisturbed until his
go-ahead. Implementation therefore lives in a separate worktree and branch,
`codex/session-findings-optimized`, based on `5fbd1de`.

## Decisions

- Keep extraction outside the dashboard. Accept the same recent schema-v1 gzip;
  database access and application use retain separate permissions.
- Add an opt-in executor with bounded concurrency, connection reuse, shared local
  rate reservations, optional per-run budgets, durable receipts and exact caching.
  Default to the existing model thinking setting. No automatic ambiguous retries.
- Compact exact repeated strings and shared record fields rather than summarizing
  notebook content. Verify a full decode round trip and validate returned references
  against original evidence. A lossless encoding can still affect model behavior.
- Make bounded overlap grouping optional. Preserve every tutor-request identity in
  the coverage ledger; split oversized groups rather than truncating evidence.
  Groups reflect account/page/notebook scope and time, not verified question identity.
- Offer the genuine Gemini Batch API for asynchronous sweeps. Freeze keyed input
  files, persist submission intent and remote job identities, schedule quota waves,
  and route out-of-order results. Missing or failed responses remain explicit.
- Keep runtime information under the existing collapsed details panel. Show sequence
  counts separately from eligible request coverage. Native jobs have no fabricated
  per-call duration or ETA.

## Evidence and limits

Offline grouping of the frozen recent export retained all 10,295 request identities
and exactly the same per-request coverage states. The 8,284 eligible windows became
2,950 bounded sequences (148 batches rather than 415). A separate 44-window check
reduced prompt characters from 8,558,666 to 6,421,650 (24.97%). These measurements
establish preparation/encoding behavior only: no new Gemini calls, speed measurement,
quality evaluation, human labeling or provider cost measurement took place.

Validation: 161 Python tests, including fake-provider concurrency, budgets, replay,
quota waves, result routing, coverage and HTTP regressions; 21 frontend tests; locked
dependencies checked offline; TypeScript and production frontend build pass. Fake
assessments establish transport correctness, not detection quality. The original
checkout remains clean at `5fbd1de`; its three running jobs completed naturally,
with twenty responses saved each. No service restart or activation occurred.

Next, after Austin authorizes activation, run a small real-data comparison under a
known quota and request cap. Compare compaction, grouping and reduced thinking
separately, including false negatives and later recovery; do not infer quality
equivalence from retained coverage alone. Native batch is an optional unattended
path, not a guaranteed faster interactive path. Detailed commands and recovery:
[OPTIMIZATION_GUIDE.md](../anomaly-review/OPTIMIZATION_GUIDE.md).
