# Browser workspace concept

September 22, 2026. Desktop is the target; mobile support is not required.

Open `student-workspace.html` directly, or serve this directory on localhost.
It is one self-contained HTML file with authored examples, no external assets,
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
outside this mockup. Connecting existing snapshot/advance/respond operations
requires a separate implementation; the mockup does not replace their saved-state
checks or execution boundaries.

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
