# Create and run policy pairs in the browser

The user approved continuing from the saved policy-pair viewer. Extend the same
Compare workflow with an explicitly configured local `--policy-workspace` for
numbered saved comparisons. Reuse eligible chat sources, `freeze_next`, and
`run_both`; do not add another simulator or batch coordinator.

The user chooses a saved starting conversation, enters Policy A / Policy B tutor
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

Initial implementation validation: 637 Python tests pass (three optional skips), all seven Marimo app
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
startup; adding numbered runs externally requires reopening it. Comparison setup
drafts recover across refresh in the same browser tab, as described below.
Multi-scenario batches and new fidelity experiments remain
deferred. This increment integrates the existing runner; it does not establish
simulator realism or a real-student policy effect.

## Navigation follow-up

After feedback that the integrations were too buried, a policy workspace now
opens directly on Tutor policies. An empty workspace shows setup immediately;
existing comparisons show their saved results. Explicit view URLs and older
conversation links retain the requested view. Conversations expose Compare tutor
policies and Saved results directly. Reply to student / Continue run opens the
tutor controls when available; Tutor instructions remains available for viewing
when continuation is unavailable. Only infrequent run
context stays under Run details; the empty menu is hidden during setup.

Setup labels the conversation and instruction steps. Saved policies expand before
running; the comparison list shows
Ready to run, One condition remaining, Results saved or Needs attention. A shortcut
from an ineligible conversation asks for another start rather than silently
substituting one. Existing drafts remain visible when returning from a conversation.
Save and Run remain separate, with one shared chat and no backend changes.

Navigation follow-up validation: 85 browser backend tests and all three Node checks pass, including direct entry, initial landing,
explicit/legacy URLs, unavailable starts, draft preservation, focus return and
navigation making no POST requests. Desktop setup and conversation controls were
inspected, and independent review found no remaining blockers. No provider calls,
new comparisons or labels were needed for this navigation change.

## HCI audit follow-up

Cases now show searchable literal question excerpts alongside stable titles and
source identity. The shared chat initially opens at **Question being tested ·
simulated**, then preserves the reader's position. Policy A / Policy B are neutral
draft labels; neither implies a recovered deployment policy. Saved outcomes state
**One simulated exchange per policy** beside the comparison.

**Use this setup** copies both policies and the exact eligible source into a new
draft. It is disabled when that source is unavailable or another unsaved draft
would be replaced. Setup fields recover after refresh through tab-scoped
`sessionStorage`, keyed by an opaque workspace identifier; chat messages are not
stored there. Save or Discard draft clears recovery. Storage failure is visible,
and drafts remain distinct from saved comparisons. Inline feedback explains why
Save is unavailable; successful saves and errors have explicit focus targets.

The primary Reply / Continue control replaces its duplicate Tutor instructions
button when usable. Source inspection remains visible with less emphasis. Input
borders are separate from the pale structural dividers and exceed 3:1 contrast
against their adjacent surfaces. These changes address the audit findings; they
are not a full WCAG certification or evidence of improved simulator fidelity.

Validation: 639 Python tests passed (three optional skips), all three Node checks
and seven Marimo checks passed. Independent integration review found no remaining
blockers. Authored desktop checks verified the tested question is visible on
entry, identical-policy feedback, save-to-heading focus, exact-source reuse, and
duplicate-save error focus without losing the draft. Automated checks cover
refresh recovery, storage isolation, stale-source rejection and scroll retention.
The browser's unsaved-change protection prevented an automated refresh; recovery
was verified in the controller harness rather than claimed from that browser run.
All 105 original files and their working copies, plus three authored source files,
remain unchanged. No new model calls or labels were required. The updated local
workspace is served at port 8431.
