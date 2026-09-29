# Recorded notebook evidence in the VS Code-style workspace

Minchan clarified that the target is the existing VS Code/Cursor-style browser
workspace, not the standalone Marimo app. Reuse its notebook center, persistent
chat sidebar, event playback and source inspector. Add one exclusive read-only
`--recorded-replay` mode with a required `--recorded-sha256`; reuse the pinned
projection loader and prefix-frame helper already tested for Marimo. This is a
display integration, not a new importer, simulator experiment or UI framework.

Recorded frames retain their own origin and shape: no fabricated synthetic
receipts, revisions, generation budget or runtime checks. Open at the first
verified source difference. Full notebook captures, submitted execution source,
source-change metadata and recorded results remain distinct. Display only chat
and results available through the selected client event. Keep probable test
activity, prediction cutoff and source gaps visible; hide tutor/generation and
next-exercise controls for recorded mode. Expose no mutating route in that mode.

Read and verify the configured projection on each workspace reload; reject file
changes with a redacted error. Do not accept arbitrary paths or session overrides
from HTTP query parameters. Retain localhost host/origin protections. No database
access, model calls, notebook-code execution, or private source mutation occurs.
Use the existing browser shell and its backend, not an iframe or static HTML
rehosting. Authored HTTP and Node controller tests verify the integration. Launch
the browser workspace locally, document results and commit on the current
isolated branch.

## Usage and verification

```sh
python -m src.agents.browser_workspace \
  --recorded-replay /absolute/path/to/replay.json \
  --recorded-sha256 <expected-projection-sha256> --port 8446
```

Open `http://127.0.0.1:8446/`. The existing notebook pane, chat sidebar and
Previous/Next controls display the selected observation. Source and Recording
details expose original content, the prediction cutoff and evidence limitations.
Reload preserves the selected event. The hash verifies projection bytes and the
loader checks their structure; it does not independently revalidate database joins.
The complete replay is available for inspection, while each displayed frame uses
only its prefix. This is an inspection UI, not an evaluation input boundary.

Verification: 801 Python tests pass, three optional tests skip; the complete Node
controller suite and syntax/diff checks pass. The only Python warning is the
existing Starlette/httpx deprecation. Independent review found no actionable issue.
The private projection opens at event 15 (first retained source difference), with
the event-11 notebook capture, event-11/12 chat and pending execution result.
Event 16 reveals that execution's recorded result. All 15 pinned input files remain
unchanged. No new database reads, provider calls, code execution or labels.
Local HTTP checks verify the native workspace and API; no browser visual inspection
was performed. This integration does not turn probable test activity into evidence
of realistic student behavior. Changes remain committed locally; private artifacts
remain ignored and are not published.
