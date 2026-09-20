# Marimo controls for one saved student

Minchan approved continuing from the saved replay to researcher intervention.
Manual labeling remains paused. Add a bounded Marimo interface over the existing
notebook student: inspect work and dialogue, supply a tutor reply when requested,
and continue one student decision. Reuse the runner, context projection and saved
receipts; do not change generator prompts or recreate the teammate's full viewer.

The server opens one session selected at launch. Viewing and refreshing only read
saved state. A submit callback is the only route to generation, available when the
server was launched with sending enabled. Each submission uses the displayed
session/state hashes and a one-decision cap. Stale submissions, pending operations,
terminal states and exhausted budgets retain the runner's refusal behavior.
Tutor guidance is accepted only for an actual pending student message. Runtime
checks happen only if the student requests one, through the existing container.

Test the complete intervention with authored injected model/check adapters:
inspect, submit guidance, save one action, reopen, reject an old submission. Browser
verification covers display and refresh without sending private data. Existing
completed demonstrations remain closed; initialize a separate authored session
for the usable workspace without making a model request.

This increment improves operation of the simulator. It does not establish student
fidelity, persona differences, a learning effect or historical notebook behavior.
Automatic tutor-policy generation, multi-session browsing and richer replay views
can use the existing mechanisms later; they are outside this small control surface.

## Run locally

Install the optional workspace dependency and open an existing notebook session:

```sh
uv sync --extra workspace
uv run --extra workspace marimo run apps/student_workspace.py \
  --host 127.0.0.1 --port 8424 --headless -- --session /absolute/path/to/session
```

This defaults to viewing only. Add `--send=true` after the session argument to
enable explicit student steps using the session's model and the existing Gemini
credential loader. The page identifies the destination and which context is sent.
One step is one student decision; the existing provider adapter may retry that
logical request up to four times. Quiet work needs no tutor message; a pending
message reveals the tutor-reply form. A stopped or exhausted session cannot resume.
Use the [existing task setup](2026-09-14-task-portability.md) to create a new session.

`apps/student_workspace.py` contains the Marimo UI;
`src/agents/student_workspace.py` binds its explicit submission to the existing
runner. No separate server, receipt format or generator is introduced. The UI's
source is Python; generated Marimo caches and session output are ignored by Git.

The local prepared example is `data/episode-pilot/student-workspace-v1/session`,
initialized from the earlier authored color-table task with six unused decisions.
It preserves the old closed sessions and makes no model request during setup.
It is a usable invented exercise, not a sampled historical student persona.

## Verification

The integration test first failed with the missing control helper, then passed:
guidance reaches the inspected state, exactly one decision is saved, reloading
replays it, and stale resubmission or terminal continuation is refused. The full
suite passes 389 tests; two optional container checks skip. Marimo's app check
passes. Existing simulator sources and frozen audit files remain unchanged.

A separate authored browser fixture embeds the actual app with injected model
and check adapters. Submission saved one quiet edit; a stale second tab was
refused and kept its submitted text. Reload showed the saved result, another
explicit quiet step chose no-reply, and terminal controls disappeared. No Gemini
or container request was made. The delivered fresh session remained untouched
through opening and refresh. Private evidence is under
`data/episode-pilot/student-workspace-v1/`; it is UI verification, not a behavioral
experiment or new human judgment.
