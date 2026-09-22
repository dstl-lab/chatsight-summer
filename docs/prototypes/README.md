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
Generation controls using existing advance/respond operations remain the next
integration step; this mockup does not replace their saved-state checks or
execution boundaries.

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
repository-directory mount, browser-selected filesystem path, write endpoint,
provider request, notebook execution, or new dependency is added. Malformed,
incomplete, busy, or incompatible saved sessions fail visibly; the page clears
previous content rather than presenting stale results as current. Use the saved
run's original environment if its engine is incompatible.

Playback frames are receipt endpoints, not necessarily individual decisions: one
saved step can contain several decisions. Diffs compare neighboring saved states.
Pending messages are shown once; edits clear old feedback. Missing origins stay
unspecified. Local checks, decision-budget pauses, and chosen no-reply remain
separate. Runtime/evaluator internals and raw error diagnostics are omitted; the
researcher-supplied initialization is available as saved context. This supports
notebook sessions only, not the separate chat-only scenario format.

The opened example has authored starting content plus previously saved generated
actions and local feedback: quiet edit → check (`0.5`, pass) → no-reply. Opening it
creates no new research result and does not establish simulator fidelity.

Validation: 470 Python tests pass (three optional container tests skipped), both
Marimo checks and all three Node checks pass. Browser verification covers saved
playback, current-revision feedback, code diffs, stop status, context and returning
focus. Independent review caught and fixed structured task-cell rendering and
unspecified-origin attribution. No private session files are committed.
