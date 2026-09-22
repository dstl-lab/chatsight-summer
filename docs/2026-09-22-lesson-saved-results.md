# Notebook lesson policies in Saved results

The lesson runner writes tutor exchanges under `lesson/tutor-*`, while Saved
results only discovers `tutor-exchanges/*`. Thus a completed lesson can show a
supplied reply without its saved policy, and failed tutor requests can disappear
from the view. Reuse the existing receipt validation and delivery matching for
both locations. No generator, prompt, receipt format or notebook execution changes.

Show the lesson's configured policy separately. Its session binding must match;
configuration alone does not establish delivery. Only a matching tutor context,
reply and completed student continuation can attribute a policy to a student step.
The lesson's starting state may follow earlier steps, and its completed tutor-turn
count excludes interrupted attempts; neither is a shortcut for delivery validation.
Unreadable records must remain warnings without hiding other readable evidence.

Verify with authored callbacks through the actual lesson runner: delivered and
unused policies, failed/interrupted calls, damaged bindings and unchanged repeated
viewing. Reopen the existing public notebook walkthrough without generation. Its
policy was configured but no new tutor reply was produced. Keep chat rendering
unchanged, including the frozen cohort's saved views.

Historical source pins and artifacts remain immutable. This display-only repair
changes the renderer's hash, not the saved student engine; the earlier checkout
remains available at `a5bd63e`. Replaying an old all-source audit requires its
recorded revision. This fixes inspection, not simulation fidelity. No new labels,
model requests, rerolls or UI redesign are planned for this change.

Verified: seven new regression cases failed before the repair and pass afterward.
The full suite passes 439 tests, with three optional container checks skipped and
one upstream warning; both Marimo apps and the Node navigation check pass.
Independent review found no issues. The existing public walkthrough reopens with
its configured policy, quiet edit, passing local check and no-reply, with no
confirmed tutor delivery. All six historical cohort views still match their saved
result exactly. Repeated inspection changed no saved session or evidence files.
Of the public walkthrough's 77 source/setup pins, only `workspace_history.py`
differs in this checkout, as intended; its original pinned revision is preserved.
