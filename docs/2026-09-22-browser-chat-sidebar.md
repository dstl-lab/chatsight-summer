# Keep the conversation beside the work

The user requested chat in a sidebar instead of a separate tab. Add a persistent,
independently scrolling right conversation panel and retire Inspect in the live
workspace. Replay keeps notebook work (or explicit missing-notebook/activity
information) in the center. Compare keeps recorded/simulated next replies in the
center and shows only that reviewed case's shared prefix in the conversation
panel. Never append alternatives into a single fabricated conversation.

Reuse the current source/details inspector in the center so chat stays visible
while reviewing evidence or editing tutor controls. A Chat toggle makes room for
comparisons when needed. On narrower desktop panes, comparison cards stack within
their available center width. Preserve drafts, origin labels, exact source access,
state-bound generation, read-only comparison and error/loading isolation.

Use the existing controller/shell and restricted tutor formatting. No new layout
framework, engine changes, labels or generation. Verify chat follows case/state,
Compare does not leak the selected replay conversation, failed reads clear both
panes, controls cannot send from Compare, and the browser shows the layout before
committing in the isolated worktree.

## Result

The connected workspace now keeps chat in a right sidebar with its own scroll.
Replay shows the selected saved state; Compare shows only the selected review
case's earlier/current exchange, with alternatives kept in the center. Tutor
context uses the existing restricted Markdown display; exact source remains
available. The live Inspect tab is retired. Details and tutor controls open in
the center while chat stays visible; Hide/Show chat preserves selection, drafts
and details without making requests. Comparison cards stack when center space
is narrow. The original static prototype and simulation engine are unchanged.

All 534 Python tests pass (three optional container skips), both Marimo checks
and all three Node checks pass. Regression coverage verifies context isolation,
source offsets, drafts, toggling, and clearing stale chat on loading/failure.
Independent review found no blocker within the requested desktop scope.
Browser checks at 827px verified notebook/chat separation, comparison context,
source and review details, tutor controls, hide/show and focus recovery without
page overflow. Mobile layout remains outside the user's requested scope.

The 20 comparison, 105 chat and five notebook files match the previous audit;
the new local audit is in ignored `data/browser-chat-sidebar-verification/`.
Ports 8428 and 8427 remain read-only. No new generation, execution, labels,
scores or student-fidelity evidence were produced.
