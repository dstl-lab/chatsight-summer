# Browser workspace

September 22, 2026. Desktop is the target; mobile support is not required.

For the design preview, open `student-workspace.html` directly, or serve this
directory on localhost. The preview is one self-contained HTML file with authored examples, no external assets,
no model requests, and no connection to private course data or the Python backend.

```sh
python3 -m http.server 8426 --bind 127.0.0.1 --directory docs/prototypes
```

Then open `http://127.0.0.1:8426/student-workspace.html` in a desktop browser.

The accepted direction is a dedicated browser workspace over the existing Python
simulation operations. The research target is fidelity of baseline versus
interaction-grounded simulated students; tutor-instruction testing is the eventual
application. This prototype explores that workflow, not a new evaluation result.

Try switching cases and Inspect / Simulate / Compare, selecting a playback step
and View step details, inspecting a message, and opening Tutor instructions. Edits are temporary browser-memory
drafts. Advancing a demo only reveals authored steps. Reload resets everything.

Design: one Cases sidebar and one Inspect / Simulate / Compare navigation row.
The inspector starts closed and opens from the content being inspected; playback
controls appear only in Simulate. Plain comparison columns, a single global demo
notice, light gray surfaces and a muted green selection color keep the examples
central. Nothing is preselected as the better simulator. System sans-serif is used
for controls and monospace for source.

The declutter pass used the cognitive-load and Impeccable distill skill guidance,
with visual and interaction checks through the browser MCP. Impeccable’s static
detector ran in regex fallback mode because optional parser modules were absent;
it did not evaluate computed contrast and is not an accessibility audit.

The notebook preview illustrates a future editable surface. Runtime, notebook
editing, arbitrary run branching, data import, and baseline/grounded dispatch are
outside this mockup. The connected saved viewer below reuses the same visual shell.
The connected workspace also supports the existing advance/respond operations
through explicit submissions; the design preview itself remains disconnected.

Run the lightweight state/render smoke check with:

```sh
node tests/workspace_prototype.cjs
```

The check uses a minimal DOM stub; it does not validate browser layout or replace
interactive browser checks.

Verified in a 1440×900 browser: all three modes, case selection/filtering, notebook
playback through the authored final output, evidence inspection, temporary draft
save/restore, closing details and returning focus, and step inspection from Starter
code. The default comparison has no inspector or playback strip. Independent review found no remaining desktop
blocker. These are prototype interaction checks, not a human usability study.


## Connected saved workspace

The accepted layout now reads verified notebook sessions through the existing
Python backend. From the repository root:

```sh
.venv/bin/python -m src.agents.browser_workspace data/notebook-example/session --port 8427
```

Open `http://127.0.0.1:8427/`. Select a task and an initial/saved state, inspect code
changes or a check result, and open Run context for the supplied initialization.
Reload saved run rereads disk without continuing the simulation. The original
prototype on port 8426 remains an authored design preview.

The server accepts one notebook session folder at launch and includes its verified
predecessors. It uses the existing `notebook_next_task.lineage` validation and
read-only locks, with one JSON endpoint and explicit page/script routes. No
repository-directory mount, browser-selected filesystem path,
automatic provider request or notebook execution, or new dependency is added.
Explicit generation is available only with the opt-in controls below. Malformed,
incomplete, busy, or incompatible saved sessions fail visibly; the page clears
previous content rather than presenting stale results as current. Use the saved
run's original environment if its engine is incompatible.

Playback frames are receipt endpoints, not necessarily individual decisions: one
saved step can contain several decisions. Diffs compare neighboring saved states.
Pending messages are shown once; edits clear old feedback. Missing origins stay
unspecified. Local checks, decision-budget pauses, and chosen no-reply remain
separate. Runtime/evaluator internals and raw error diagnostics are omitted; the
researcher-supplied initialization is available as saved context. Notebook sessions
retain their work and check evidence. Chat sessions use the explicit mode below
and show unavailable notebook activity instead.

The opened example has authored starting content plus previously saved generated
actions and local feedback: quiet edit → check (`0.5`, pass) → no-reply. Opening it
creates no new research result and does not establish simulator fidelity.

Validation: 470 Python tests pass (three optional container tests skipped), both
Marimo checks and all three Node checks pass. Browser verification covers saved
playback, current-revision feedback, code diffs, stop status, context and returning
focus. Independent review caught and fixed structured task-cell rendering and
unspecified-origin attribution. No private session files are committed.


## Tutor and student controls

Sending is disabled by default. To enable controls for an **active** notebook
session, add `--send`. Optional `--policy-file` (UTF-8) and `--reference-file`
(library reference JSON) load once at startup, matching the Marimo workspace.
For example, after creating the authored example with the
[existing setup command](../teammate-quickstart.md#2b-start-with-an-explicit-notebook-task):

```sh
.venv/bin/python -m src.agents.browser_workspace data/browser-workspace-example/session \
  --policy-file data/browser-workspace-example/policy.txt --send --port 8427
```

Open **Tutor controls**. Continue one decision while the student is working; when
it asks for help, choose either a generated tutor reply from your instructions or
a manual reply. Either reply is followed by one student decision. Each explicit
submission uses the displayed latest-state binding and the existing saved runner.
Historical playback and completed/budget-exhausted encounters cannot submit.
Tutor instructions and manual drafts remain in page memory across Reload saved
run; a browser refresh resets them to the server configuration. Edited instructions
are sent exactly as entered and retained in the existing tutor receipt. The
configured reference goes only to generated tutor replies.

A running request disables duplicate submission and displays progress. Refreshing
the page polls saved status with GET requests; it never repeats the POST. Finishing
returns to the result view. A lost connection does not cancel backend work; reload
to inspect it. Failed or incomplete operations are preserved. An existing bound
tutor exchange blocks every continuation mode for that state after restart, so a
manual reply cannot silently bypass an interrupted generated reply.

The server supports one process per session. Do not edit the same session from a
second server or CLI while it is running. In-memory progress coordinates browser
tabs; existing on-disk receipts enforce replay and prevent automatic resends.
Raw provider diagnostics remain in local receipts rather than browser responses.
No automatic experiment loop, queue, or retry was added.

Controls verification: **491 Python tests pass**, with three optional container
skips; Marimo and Node checks pass. The browser completed an authored offline
continue → policy reply → manual reply flow with exactly three saved student
decisions and one authored tutor response. Refresh during the first request
recovered its result without duplication; edited policy/manual text matched their
saved receipts. No Gemini calls or notebook execution occurred in this test.
The separate [live browser walkthrough](../2026-09-22-live-browser-workspace.md)
then used real Gemini and local execution on the public authored example:
quiet edit → requested passing check (`0.5`) → no-reply. Three student requests,
one container check, no generated tutor turn or errors. Refresh and exact offline
replay preserve the result; continuation is disabled. This example is now closed.
The policy-generation and manual-reply browser paths remain covered by the
authored test above; this live run did not exercise them or validate student realism.

## Saved conversation scenarios

Use `--chat` to open one existing saved chat session in the same browser layout.
For example, after creating the [authored teammate demo](../teammate-quickstart.md):

```sh
.venv/bin/python -m src.agents.browser_workspace \
  data/teammate-demo/comparison/sessions/a --chat --port 8428
```

Historical workspace sessions also open directly, for example
`data/episode-pilot/chat-workspace-v1/sessions/case-01`. Open
`http://127.0.0.1:8428/`; playback shows the supplied prefix and each saved student
decision. Notebook cells, changes and execution feedback are unavailable. Code
inside a message remains text, and a saved `source` origin alone does not prove
whether the prefix was recorded or authored. Raw origins remain inspectable.

Sending is off by default. `--send` enables the same explicit policy/manual reply
and one-decision controls for an authorized active scenario; `--policy-file` loads
its draft. Chat cannot run notebook checks, and `--reference-file` is refused.
Opening a completed study does not authorize rerunning it. Cached imports and
scripted callback responses must not be treated as fresh model calls.

The viewer requires the runner's existing `.lock` and verifies receipts under a
shared read-only lock. A freshly created chat that has never been opened needs
the existing `chat_student show` command once to initialize that lock; viewing
does not create one or repair invalid records. Use the collection mode below to
switch sessions; matched comparisons remain separate work.

Verification: 497 Python tests, Marimo checks and all three Node checks pass.
All 29 historical workspace scenarios reopen with 105 files unchanged. Browser
playback, source inspection, pending-message display and disabled sending were
checked on an existing six-state conversation. No new provider calls, runtime
checks, labels or student-fidelity result. See the
[scope and result](../2026-09-22-browser-chat-scenarios.md).

## Browse a saved collection

```sh
.venv/bin/python -m src.agents.browser_workspace \
  data/episode-pilot/chat-workspace-v1/sessions --chat-sessions --port 8428
```

`--chat-sessions` selects a collection instead of a single `--chat` session. The
server lists only direct, non-symlink children containing session manifests and
freezes that list at startup. Restart to include newly added folders. The sidebar
shows numbered scenarios without loading every conversation or exposing filenames.
Filter and select a scenario to verify its saved conversation and playback.
The page URL retains selection on refresh; tabs select independently.

Switching resets tutor/manual drafts and clears the previous content. Loading or
generating disables switching; a failed case clears its view but leaves the list
available. Reloading the same case preserves its draft. Reads and optional bound
submissions name an allowed scenario; filenames and arbitrary paths are never
accepted from the browser. The existing global writer lock allows one operation
at a time. The normal `--send` opt-in applies; the research collection is opened
without it, and closed studies remain closed.

Verification: 508 Python tests, Marimo and all Node checks pass. All 29 scenarios
reopen with 105 files unchanged; actual browser switching, filtering, draft reset,
focus and refresh were checked. No new model requests or labels. See
[scope and result](../2026-09-22-browser-scenario-selection.md).
