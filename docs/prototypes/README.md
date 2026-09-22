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

Try switching cases and Inspect / Simulate / Compare, selecting a timeline step
or a message, and opening Tutor instructions. Edits are temporary browser-memory
drafts. Advancing a demo only reveals authored steps. Reload resets everything.

Design: a compact explorer, persistent work area, contextual inspector, and
timeline. Slate navigation, light gray working surfaces, teal selection, system
sans-serif for controls and monospace for source. The comparison is the focal
surface; no metrics imply that one simulator is better.

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
save/restore, and selection focus. Independent review found no remaining desktop
blocker. These are prototype interaction checks, not a human usability study.
