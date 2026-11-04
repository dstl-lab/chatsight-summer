# Optimized PR100 reviews

The optimized transport is integrated into the instructor review project but
remains opt-in. It uses a separate receipt namespace and should use separate
private storage from standard analysis jobs. Do not point two running services
at the same storage directory or start competing provider work without confirming
the available quota.

## What changes

| Feature | Behavior | Limit |
| --- | --- | --- |
| Parallel requests | Four reusable worker connections by default; configurable 1–16 | Throughput still depends on provider quotas and response time |
| Rate controls | Shared rolling request/minute and input-token/minute reservations within one service | Other processes using the same project are outside this limiter |
| Run budgets | Optional maximum new requests and estimated reserved tokens per invocation | Estimates are not a dollar cap or exact provider token counts |
| Compact evidence | Factor repeated fields, warnings and exact code/output strings into tables | Different wire representation requires a quality comparison |
| Saved responses | Reuse exact evidence/model/prompt/configuration matches; persist before dispatch | Changed evidence/configuration is a new assessment |
| Overlap grouping | Optional bounded sequences of nearby requests in one account/page/notebook scope | Changes the analysis unit; groups are not verified questions |
| Native Gemini Batch | Optional durable provider jobs, file chunks and quota waves | Asynchronous, with provider completion delays |
| Measurements | Actual reported token usage, mean/p95 call time, reuse and prompt size | Missing usage remains unknown; native jobs have no invented per-call latency |
| Thinking level | Optional `low`, `medium`, `high`; default preserves the model setting | Lower thinking may change findings; compare before adoption |

### Input accounting update, October 19

Concurrent runs now default to `--token-counting provider`. Before an untouched
assessment, Google's tokenizer counts the complete request, including its response
schema. This sends the prepared evidence to the same provider but generates no
assessment. Counts are cached under the exact existing request fingerprint. The
model, evidence, prompt, output budget and thinking setting are unchanged.

TPM reservations cover input only, with a small margin (2% or 32 tokens, whichever
is larger), and are reconciled to reported input usage after a response. The separate
`--max-estimated-tokens` run budget continues to reserve input plus maximum output.
If required counting fails, dispatch pauses with that analysis untouched. Explicit
`--token-counting estimate` avoids tokenizer calls, but character estimates are
approximate. Accounting mode is operational; it does not invalidate identical saved
assessments. Offline preparation, inspection and native Batch preparation do not
silently call the tokenizer. Native queue estimates remain estimates.

A heavy original-format 20-window batch measured **2,201,943 input tokens** in
20 tokenizer calls (7.26 seconds), with zero generation calls. The former character
estimate plus output reservation was 1,586,759, so it underestimated this data.
Token counting fixes an accuracy problem as well as separating unnecessary output
allowance from TPM. It does not guarantee a speedup at the same local setting.

Using those measured counts, a simulation with four workers, 30 RPM and assumed
15–60 second call durations takes **14.25–15 minutes at the local 200,000 input TPM**.
At a hypothetical 1,000,000 input TPM it takes 2.5–5 minutes. These are scheduling
simulations, not live generation benchmarks or verified account quotas. No quota has
been changed. Verify the existing project's limits before raising the local setting.

The backend still validates assessments against the complete original evidence.
Compaction verifies an exact decode round trip for every request. It retains IDs,
timestamps, ordering, links, warnings, code and outputs; it does not summarize or
truncate them. The prompt explains the tables and requires original evidence IDs.
Input tables being lossless does not establish equal model interpretation.

Grouping defaults to requests at most ten minutes apart, with the union of their
windows bounded to sixty minutes. Each anchor keeps five minutes before and twenty
after. Oversized or inconsistent groups split back into smaller groups or original
windows. Each tutor request appears in the coverage ledger with its group or a
specific exclusion reason. Original raw and normalized evidence limits still apply.
Coverage counts eligible **requests**; the analyze button counts **sequences** when
grouping is enabled. A sequence may span several questions. Exclusions and failed
assessments are never counted as evidence that nothing went wrong.

## Offline check on the current export (October 18, 2026)

No Gemini requests were made for these checks. The frozen production export starts
at the first observed PR100 schema-v1 receipt, October 13 at 17:30:59.701280 UTC;
it ends October 18 at 06:13:47.991824 UTC. This is the current-quarter export, not
the historical ChatSight data and not the PR merge-date boundary.

- All 10,295 tutor-request identities were compared between the original and
  grouped preparation ledgers. **Zero request coverage states changed.**
- The same 8,284 eligible requests became **2,950 bounded sequences**, in 148
  review batches instead of 415. This is 64.4% fewer analysis units; it is not a
  measured speedup or proof that sequence-level findings equal window-level findings.
- In 44 original windows from the beginning, middle and end of the preparation,
  compact prompts decreased from 8,558,666 to 6,421,650 characters: **24.97%**.
  These are character counts, not measured token, cost or latency savings.
- The source SQLite index was opened read-only for the grouping benchmark.
  New preparations and benchmark outputs are private, ignored local files.

The original app's completed assessments and browser reviews stay with their
original dataset. They are not silently relabeled as optimized results. Changed
prompt formats or grouping do not qualify as an identical cached request.

## Launch

Use a separate port and storage directory if a standard service is already running.
Configure the account's actual
limits before scaling up; the defaults (4 workers, 30 RPM, 200,000 input TPM)
are local settings, not a claim about your account's allowance.

```sh
cd /path/to/chatsight-summer/anomaly-review
uv sync --locked
cd frontend
npm ci
npm run build
cd ..

uv run --locked session-findings-app \
  --optimized \
  --workers 4 --rpm 30 --tpm 200000 \
  --max-requests 100 \
  --storage private-data/optimized-uploads \
  --port 8770 \
  --key-file /private/path/to/model-keys.env
```

Open `http://127.0.0.1:8770`, upload the same recent `events.jsonl.gz`, wait for
preparation, and open one review batch first. No new database access is needed;
the extraction instructions in [PR100_QUICKSTART.md](PR100_QUICKSTART.md) still apply.
The key-file option reads only the selected model provider's key. Optimized mode
currently requires a Gemini model and Gemini key. The upload app has no database
connection or extraction route.

For a controlled comparison, start with `--original-prompt --thinking default`
and grouping off. Then use separate storage/preparations for compaction, grouping
(`--group-overlap`) and optionally `--thinking low`. Compare evidence links,
flagged cases, unflagged cases, insufficient evidence and later recovery manually.
Tests with authored responses establish transport behavior, not finding accuracy.

The initial `--max-requests 100` is a pilot cap per analysis invocation, not a
lifetime limit. Use `--max-estimated-tokens` for an additional estimated reservation
budget. Remove/raise caps deliberately for a full run. Limits can be adjusted
between runs; changed inference settings require a separate preparation.
Keep the computer awake and preserve private storage. Details and usage are inside
the existing collapsed **Data details** area, with an estimated remaining time once
ordinary requests have measured durations. Rate limits can dominate that estimate.

## Native Batch alternative

Gemini's [Batch API](https://ai.google.dev/gemini-api/docs/batch-api) documents
discounted asynchronous processing and a target turnaround of 24 hours. This is
an alternative for unattended sweeps, not a promise of interactive speed.
Check your account's model-specific
[enqueued-token allowance](https://ai.google.dev/gemini-api/docs/rate-limits).

After approval, launch a separate import with `--optimized --provider-mode batch`
and a positive `--batch-enqueued-tokens` allowance, separate storage and port.
The whole collection is queued together, split into bounded JSONL files of at most
1,000 requests and 64 MiB, further split by the estimated enqueue allowance.
Later waves wait for earlier jobs to complete. Do not use the same allowance in
several independent processes and expect account-wide coordination.

Remote job IDs and submission intent are saved before continuing. Known jobs are
polled and collected rather than resubmitted. Output order is arbitrary; keys route
responses back to the original evidence. Missing, duplicate or malformed responses
never become accepted negative findings. An uncertain submission stops for explicit
recovery; there are no automatic paid rerolls.

## Command-line workflows

Run these from `anomaly-review`. Preparation, inspection,
reporting and review-bundle export make no model calls. Commands that send evidence
require `--send` and a Gemini key already set in the environment. Do not run those
until the go-ahead.

```sh
# Build a NEW preparation. Omit --group-overlap for original per-request windows.
uv run --locked session-findings-sweep prepare /path/to/events.jsonl.gz \
  --output private-data/new-sweep --group-overlap

# Inspect a bounded sample of at most 50 prompts, offline.
uv run --locked session-findings-sweep inspect private-data/new-sweep

# Tokenizer-only measurement of 20 inputs; sends evidence but generates nothing.
# Use --original-prompt here and on run to preserve the original JSON representation.
uv run --locked session-findings-sweep count private-data/new-sweep \
  --limit 20 --original-prompt --send

# Standard concurrent requests; save each response independently.
uv run --locked session-findings-sweep run private-data/new-sweep \
  --workers 4 --rpm 30 --tpm 200000 --max-requests 100 --original-prompt --send

uv run --locked session-findings-sweep report private-data/new-sweep

# Export ONE batch's saved assessments for the dashboard's review-bundle import.
uv run --locked session-findings-sweep export \
  private-data/new-sweep/batches/batch-0001 \
  --output private-data/batch-0001-review.private.json
```

For native Batch, use a **separate untouched preparation** and replace the token
example with the verified allowance for your account:

```sh
uv run --locked session-findings-sweep batch-prepare private-data/batch-sweep \
  --output private-data/provider-queue --enqueued-tokens 1000000

# Submits permitted waves, polls and collects; keep it running.
uv run --locked session-findings-sweep batch-watch private-data/provider-queue --send

# Or operate individual stages. Collection never creates a new job.
uv run --locked session-findings-sweep batch-submit private-data/provider-queue --send
uv run --locked session-findings-sweep batch-collect private-data/provider-queue
```

`batch-prepare` is offline. Its run budgets reject an oversized plan before upload;
enqueued-token allowances schedule waves rather than rejecting the entire corpus.
The UI builds review bundles as batches finish. CLI workflows use `export` above
to turn saved assessments into an importable review bundle; importing raw data into
the UI is the simpler end-to-end option.

## Resume without duplicate requests

Completed, pending and failed receipts are durable. Repeating the same standard
command skips saved units and processes only untouched work. It does not resend
failed or uncertain requests. Changing worker/rate/run budgets is allowed; changing
model, evidence, prompt, encoding or inference is rejected for that preparation.
Quota, credentials, invalid request configuration and temporary provider failures
pause dispatch. Already in-flight requests are allowed to finish.

For native jobs, repeat collection/watch with the same queue folder. If submission
timed out before its remote ID was saved, first identify the existing provider job
from its display name in `batch-state.private.json`. Attach the confirmed matching
job with `batch-attach QUEUE --chunk N --remote-name batches/ID`; then collect it.
If no matching remote job can be established, leave the uncertain unit unresolved
rather than inventing a successful result or submitting it again automatically.

Do not point a second app at a live service's storage. Startup refuses in-progress
optimized jobs unless `--recover-saved-jobs` is explicitly supplied; use recovery
only after the old owning process has stopped. Browser reviews remain local to the
review dataset and should be downloaded before moving machines or browser profiles.

Private exports, indexes, prompts, provider files, receipts and reviews stay out of
Git. This work changes analysis tooling; it does not change notebook telemetry,
student clients, production logging or data-collection behavior.
