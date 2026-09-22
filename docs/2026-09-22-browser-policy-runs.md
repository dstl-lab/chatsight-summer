# Create and run policy pairs in the browser

The user approved continuing from the saved policy-pair viewer. Extend the same
Compare workflow with an explicitly configured local `--policy-workspace` for
numbered saved comparisons. Reuse eligible chat sources, `freeze_next`, and
`run_both`; do not add another simulator or batch coordinator.

The user chooses a saved starting conversation, enters current/proposed tutor
instructions, and saves a frozen comparison offline. Its common prefix and cached
simulated question appear once in the chat sidebar. An explicit run action is
available only with `--send`; it generates at most one tutor reply and one student
decision per untouched arm. Completed, failed and interrupted arms are not rerun.
Drafts, progress, saved results and uncertainty about pending requests remain
visible. Reads/reloads never generate.

Preserve the fixed `--policy-comparison` and communication-review `--comparison`
launch modes. Requests use server-issued source/run identifiers and state/hash
bindings, never browser-selected paths. Verify configured paths, read-only locks,
source eligibility and pinned saved manifests before mutation. The serving
process serializes submissions using the existing operation lock. Save and run
are distinct actions; repeated save rejects the exact source/policy pair.

Tests use authored sessions and callbacks: successful freeze/run, untouched-arm
resume, double submission, stale source/run binding, tampering, read-only mode,
interrupted requests and no calls on reload. No new private-data experiment,
manual label, engine/prompt change, or fidelity claim is part of this increment.

Implemented on the existing policy-labs integration branch / PR #57. Compare now
offers New comparison, an eligible-source selector, two instruction fields, an
offline save, and an explicit Run both / Run remaining action. It preserves drafts
after rejected or lost responses and recovers through reads only; metadata from an
older operation cannot falsely confirm a new save. Existing fixed viewers remain
read-only. Saved attempts are not resent; an untouched peer can still run.

Validation: 637 Python tests pass (three optional skips), all seven Marimo app
checks and all three Node checks pass. Independent review found no remaining
blockers, including a two-server concurrency check with no duplicate requests.
The desktop browser walkthrough used authored callbacks: save made zero calls,
run made exactly two tutor and two student calls, one arm replied and the other
chose no follow-up. Reload made no additional calls; all three source files stayed
unchanged. No live provider was used for validation.

The local workspace at port 8431 uses separate working copies of all 29 saved
conversations, with 27 eligible starts. Sending is enabled only through explicit
buttons; no new course-data requests were made during setup. All 105 original
source files remain unchanged. Runtime inputs, outputs and local checks stay in
ignored `data/`; no private data is included in the PR. Launch from this worktree:

```sh
python -m src.agents.browser_workspace data/browser-policy-workspace/sources \
  --chat-sessions --policy-workspace data/browser-policy-workspace/runs \
  --send --port 8431
```

The workspace supports one serving process. Its source/run catalog is pinned at
startup; adding numbered runs externally requires reopening it. Drafts last only
for the current page. Multi-scenario batches and new fidelity experiments remain
deferred. This increment integrates the existing runner; it does not establish
simulator realism or a real-student policy effect.
