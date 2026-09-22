# Load the prepared tutor policy into the workspace

**TL;DR:** Add an explicit `--policy-file` launch argument to the existing Marimo
workspace. It initializes the editable policy draft with the supplied file instead
of requiring a researcher to copy it manually. No layout or sending behavior changes.

The exercise setup writes its policy to `policy.txt`, but the documented workspace
launch initializes the policy control from generic text. The lesson CLI already
accepts a policy file. The missing handoff is in the workspace's initial draft;
the existing submit path correctly records and sends the draft's actual value.

Read an explicitly supplied UTF-8 file once during initialization. Refuse an
invalid path, unreadable/invalid-encoding file or blank policy without falling back.
No argument retains the current defaults for notebook and chat modes. Keep the
policy editable, retain edits through reload, and keep the existing reset when
selecting another scenario. A file is the starting draft, not a live file watcher
or evidence that the tutor has received it. Generation still needs sending enabled
and a pending student message. Saving a custom exercise does not authorize a call.

Use the existing Marimo control-test harness to verify file-to-draft-to-saved
request behavior with authored callbacks, edits surviving refresh, no calls on
load/reload, invalid inputs stopping initialization, and unchanged defaults.
Update workspace launch examples to explicitly pass the prepared policy file.
Keep saved sessions, policies already delivered, engines and prompts unchanged.
No live run, labels or extra review queue is part of this repair.

## Completed verification

The workspace accepts `--policy-file` for notebook and chat sessions, and the
public exercise launch examples pass their saved policy explicitly. The initial
draft is read in the launch cell; refresh does not reevaluate it. Scenario changes
reset the draft to the initially loaded text, and restarting rereads the file.

The regression first reproduced the generic text replacing the supplied policy.
It now runs the real Marimo input/view cells and explicit submit callback with
authored model responses, verifying that the edited draft survives reload and
reaches the saved tutor request exactly. File edits do not overwrite the current
draft; defaults and invalid-file rejection are also checked. Opening/reloading
makes no provider or runtime call. Independent review found no actionable issue.

All **454 tests pass**, with three optional container skips and one existing
dependency warning. Both Marimo checks and Node navigation pass. No session,
generator, prompt or existing delivered policy was changed, and no live run or
additional human labeling was needed.
