# Extract fresh production data, upload it, and review findings

For optional bounded parallelism, compact prompts, grouping, or native Gemini
Batch, use [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md).

Run the commands below from the repository's `anomaly-review` directory. The
dashboard runs on your computer. Database access belongs to the
person extracting data; someone receiving the export does not need that access.

## Which data does this include?

`--all` starts at **October 13, 2026, 10:30:59.701280 a.m. Pacific**
(`2026-10-13T17:30:59.701280Z`), the first verified production receipt of the
new schema-v1 telemetry. **This is not the PR merge timestamp.** PR #100 merged
October 7 Pacific; using that date would include the period before the new
observations appeared in production.

The export includes every schema-v1 event received from that boundary up to a
fixed cutoff captured when the command starts. It does not select a few students,
limit the number of notebook scopes, or exclude accounts by guessing from their
names. Older-schema records remain excluded even if they arrived later. The
boundary establishes observed availability; it does not prove that every student
client upgraded at the same instant or that every action was successfully logged.

## 1. Extract a fresh file (operator only)

Prerequisites: `uv`, working `kubectl` access to the production logging pod in the
correct context/namespace, and the PostgreSQL password. Neither an export nor
opening the dashboard changes the production database.

From the approved operator's checkout:

```sh
cd /path/to/chatsight-summer/anomaly-review

uv run --locked --extra extract session-findings-extract \
  --all \
  --port-forward \
  --env-file /private/path/to/database.env \
  --output "private-data/pr100-$(date -u +%Y%m%dT%H%M%SZ)"
```

The command opens a temporary local tunnel, reads a consistent snapshot, closes
the tunnel, and prints the output path and record count when finished. It can
take several minutes. Wait for successful completion and `manifest.json` before
uploading; a still-growing gzip is not a completed export.

The output directory contains:

- **`events.jsonl.gz` — upload this file directly, without unzipping.**
- `manifest.json` — keep it with the export; it records the cutoff, counts and hash.

The persistent pseudonym key lives at `private-data/.pr100-pseudonym.key` by
default. Keep that file private and retain it for later exports so account labels
stay consistent. If moving the export destination, pass the same key explicitly
with `--pseudonym-key /private/path/.pr100-pseudonym.key`.

For a different machine, substitute the checkout and credential-file paths.
The explicit env file reads only standard `PGHOST`, `PGPORT`, `PGDATABASE`,
`PGUSER`, `PGPASSWORD` or their `PG_HOST`, `PG_PORT`, `PG_DATABASE`, `PG_USER`,
`PG_PASSWORD` aliases. It does not load Gemini keys. If you already have a private
connection and PG variables configured, omit `--port-forward` and `--env-file`.

Optional `--since` and `--until` take timezone-aware ISO timestamps. The lower
bound cannot precede the production boundary. For this week's review, leave
them out to capture everything available since that boundary. Repeating the
command later into a new directory is the simplest refresh workflow.

## 2. Start the app

First-time setup, from `anomaly-review`:

```sh
uv sync --locked
cd frontend
npm ci
npm run build
cd ..
```

Start the service and leave this terminal running:

```sh
uv run --locked session-findings-app \
  --port 8766 \
  --storage private-data/full-uploads \
  --key-file /private/path/to/model-keys.env
```

Open **http://127.0.0.1:8766**. On another person's machine, use a separate
private file containing the selected provider key, or set that variable in the
service environment and omit `--key-file`. The dashboard has no database
connection or extraction route. Previewing works without a model key; analyzing
requires one. Standard mode supports Gemini and OpenAI model names. Optimized mode
is Gemini-only.

If the app is already running on that port, use the existing app. After updating
the code, stop the old service with Ctrl+C, rebuild the frontend, and restart.

## 3. Upload and prepare

1. Click **Upload new**. Defaults analyze all eligible tutor windows.
2. Keep the default 25-minute context; **Import settings** contains optional changes.
3. Click **Upload PR100 export** and choose `events.jsonl.gz`.
4. Wait for reading/preparation to finish. The app reads records into a local
   disk index, then prepares review batches of at most 20 windows.
5. Check **Export coverage**. It accounts for all tutor-request records, including
   those missing a matched response, too recent for follow-up, too large, or
   otherwise unsuitable. These exclusions are **not** negative findings.

This path accepts a file up to 2 GiB compressed, 12 GiB expanded, and ten million
records, with an 8 MiB per-line limit. If a limit is reached, extract a smaller
date range; no partial import is offered as complete. Imports and preparation
make no model calls. Identical repeated database receipts count once. Conflicting
payloads under the same event ID stop the import.

Each eligible request gets a window of five minutes before and twenty minutes
after it. Multiple requests in the same notebook are all considered. Windows
can overlap; their number is not the number of independent attempts or students.
Later recovery outside the window remains unobserved by that assessment. Very
recent requests wait for a later export with sufficient follow-up time.

## 4. Analyze and review

For your first manual review, **open Batch 1**, inspect its preview, and click
**Analyze 20 windows** (the last batch may contain fewer). The app
sends prepared dialogue, code captures, outputs and activity evidence to Gemini.
It saves responses and opens the resulting dashboard when the batch finishes.

Review flagged cases **and** cases with no supported finding or insufficient
evidence. Inspect evidence links and later recovery, record your judgment in
**Instructor assessment**, and use **Download reviews** to back up your labels.
Human judgments remain in this browser and are specific to that review dataset;
they are not automatically transferred to a newly exported dataset.

Use **All batches** to choose another batch. Or click **Analyze all …
windows with Gemini** from the export view to process every eligible batch
sequentially. That button can authorize thousands of model calls; the displayed
window count is the workload, not the raw event count. This is an offline job,
not an instant result. Keep the service running and the computer awake.

Completed batches are available while later batches run. Refreshing the browser
does not cancel the job. The **Saved exports** selector reopens the export; each batch has a
**Download review bundle** link under **Data details & coverage** for offline viewing. A whole export is deliberately
not loaded into one enormous browser timeline.

## 5. Refresh later, or resume after interruption

Repeat step 1 into a new output directory, then upload that new gzip. There is no
live database synchronization. Re-uploading the same completed export with the
same context setting reopens its saved import. Across exports, identical prepared
evidence/model/prompt configurations reuse saved assessments. Changed evidence,
context, or model configuration gets a separate assessment. Preserve the private
storage directory and pseudonym key to retain this behavior.

After restarting the service, **Continue untouched sessions with Gemini** skips
saved requests. Failed or interrupted requests are kept visible and are not
silently resent, because a request might have reached the provider before the
connection was lost. If preparation itself was interrupted, re-upload the file;
no model calls were made during preparation. Failed preparations never enable
analysis of a partial dataset.

Private exports, disk indexes, batches, receipts and cache stay in ignored
`private-data/`. Keep the original gzip and manifest. Do not put them in Git or
frontend assets. The account column is pseudonymized; notebook text/code may
still identify people, so the file remains private course data.
