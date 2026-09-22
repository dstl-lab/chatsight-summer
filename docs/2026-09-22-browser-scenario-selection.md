# Switch saved conversations without restarting

Add a collection launch option over the existing single-session browser. Reuse
Marimo's direct-child scenario discovery, freeze that allowlist at startup, and
show neutral numbered scenarios in the sidebar. Fetch catalog metadata first,
then verify and load only the selected conversation. No imports, new generation
batch, labeling, inferred notebook work or generator changes.

Every collection read and explicit continuation names its selected catalog ID;
the existing session/state binding still protects submissions. Selection is per
browser page, never server-global. Paths stay server-side, symlinks cannot redirect
selection, and completion/error messages belong to their own scenario. Keep the
existing single-process writer lock and default sending off.

Switching clears old content and resets tutor drafts. Keep the selected ID in the
page URL for refresh. Disable switching during loading/generation/polling so a
late response cannot overwrite another selection. A corrupt case clears its view
but leaves the catalog available. Single-session notebook/chat launches still work.

Verify with authored independent sessions, wrong-scenario bindings, failed reads,
symlinks and pending operations; then inspect the existing collection read-only
and confirm its files are unchanged. This is a navigation increment, not a new
student-fidelity experiment. Work remains in the existing isolated checkout under
the user's standing continue authorization.

## Result

Implemented as `--chat-sessions` on the existing server, with a metadata-only
catalog and explicit scenario selectors on reads/submissions. Missing, extra,
duplicate and unknown selectors are refused. A changed/symlinked path or invalid
receipt cannot display stale content or dispatch a request. Each scenario retains
its own operation messages; independent tabs cannot change each other's selection.

All 508 Python tests pass (three optional container skips), both Marimo checks
and all three Node checks pass. Independent review caught a detached-button focus
issue; the regression now verifies restoration without stealing focus from a
different control. Final frontend/backend review found no remaining blocker.

All 29 historical scenarios verify through their selected HTTP views. Actual
browser checks covered scenarios 1, 2, 3 and 29, filtering/clearing, playback,
draft reset, disabled sending, keyboard focus and selection after refresh.
All 105 saved files remain unchanged; local audit records are in ignored
`data/browser-scenario-selection-verification/`. No model requests, execution,
new labels or student-fidelity results. Port 8428 serves the read-only collection;
port 8427 still opens the completed notebook run, also read-only.
