# Separate operator extraction from dashboard uploads

The operator can read the production logging database; a dashboard user does not
need that access. A standalone command exports recent PR100 records to a private
file. The local dashboard accepts that file, prepares bounded notebook windows,
previews their evidence without model calls, and analyzes only after an explicit
Gemini action. It never imports the database client or exposes extraction routes.

```text
operator's private DB connection
  -> session-findings-extract -> events.jsonl.gz + manifest.json
  -> authorized private handoff of the file
  -> Upload PR100 export -> validate/prepare -> preview
  -> Analyze with Gemini -> saved receipts -> review bundle/dashboard
```

The extractor uses the operator's PG* environment, a read-only repeatable-read
transaction, parameterized queries, recent date boundaries and schema_version=1.
It defaults to the last 24 hours and 30 tutor-bearing page/notebook scopes, with
requests at least 30 minutes before the export boundary. Account columns are
pseudonymized; private text/code and exact request snapshot strings are retained.
The PostgreSQL dependency is an optional operator-only installation extra.

The dashboard requires only its local storage and, for analysis, a Gemini key in
the service environment. No key is sent to JavaScript. The built frontend and API
can run from one loopback-only service; the development server also proxies /api.
This is a local prototype, not a remotely deployed multi-user service. A future
shared deployment would need its own login/access policy for uploaded datasets.

Uploads accept JSONL or gzip JSONL up to 50 MB, with bounded decompression, line
length and event count. Historical/mixed-schema and saved-result documents are
rejected as raw input. Uploaded files and jobs stay in ignored private storage;
no uploaded content enters frontend imports or build assets. The file name is
display metadata only, never a filesystem path.

Preparation defaults to 25-minute windows (5 before, 20 after a tutor request),
dialogue coverage, and 10 selected windows. Users can choose 1–20 windows and
10- or 25-minute context. Eligibility, selected count, source span and event count
are shown; insufficient availability fails visibly rather than silently reducing
the requested batch. Oversized windows remain exclusions, not truncated prompts.

Preparation and analysis run in a background worker. The UI shows response-save
progress and loads the completed bundle automatically. Jobs and receipts persist;
reopening and downloading results make no model calls. Concurrent start requests
are refused, and completed/failed/interrupted receipts are not rerolled. Continuing
an interrupted job sends only previously untouched sessions. Uploading or previewing
never authorizes a model call on its own.

The local HTTP service restricts host/origin and requires a custom header for
mutations, does not enable cross-origin access, confines static files to the built
frontend, limits input sizes and uses private files. Provider diagnostics are
reduced to safe state/error messages. Tests cover the raw-upload lifecycle,
duplicate-send and restart handling, old/corrupt/oversized input, origin/path
boundaries, read-only extraction and UI actions that separate preview from analysis.


## Verification

The new path passes 135 Python tests, 18 frontend tests and the frontend production
build. A fresh operator export contains 5,772 PR100-only events from 20 recent
page/notebook scopes (about 1.7 MB compressed). In the local service, previewing
that file prepared a selected session from 18 eligible scopes and created no
model receipt. The raw upload control was also exercised in the browser with the
seven-event fictional fixture.

One real session was then analyzed through the dashboard button with the approved
Gemini configuration. The result completed, passed the evidence validator and
appeared automatically. After a page refresh, reopening the saved upload restored
the completed result without another request. Private exports, uploaded sources,
job state, receipts and model output remain in ignored local storage. The running
upload service was launched without PostgreSQL environment variables.
