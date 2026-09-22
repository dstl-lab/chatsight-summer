# Assign the next notebook exercise from the browser

**TL;DR:** After a simulated notebook encounter ends, a researcher can assign one
configured next exercise without restarting the workspace. Preparation saves a
new session offline; model generation remains a separate explicit action. This
connects existing multi-task simulation machinery and does not change or validate
the student generator.

## Scope

Reuse `notebook_example.create(previous=..., exercise=...)` and the existing
verified notebook lineage. The predecessor must end with a generated no-reply
action. A failure, exhausted budget or unfinished tutor request is not a completed
encounter. Assigning a task is a researcher intervention, not evidence that the
student chose to continue or learned from the prior task.

Configure one exercise JSON file and one separate output directory at server
startup. The browser shows the supplied task before the researcher saves it.
It accepts no file paths or arbitrary exercise code from requests. The existing
exercise schema and single-cell/table runtime remain unchanged.

The successor inherits the verified earlier simulation history, original
conversation example, model and immutable runtime image. Its work and check
feedback start fresh; its configured tutor policy becomes the new draft. Earlier
tasks remain available through the existing replay. Source sessions remain intact.

## Request and recovery boundary

The save binds to the displayed source state and configured exercise hash.
Changed inputs, incomplete predecessors, symlinks, overlapping destinations and
duplicate saves cannot produce a new successor. Viewing and reloading write
nothing. If the response is lost, reload discovers a verified existing successor
and offers to open it; it never repeats the save or a model request.

The browser keeps the successor selection in its URL, separately for each tab.
Only the configured source and successor are addressable. The next task's ordinary
Continue control uses the existing sending configuration and saved-operation
rules. No new provider calls, notebook executions or human labels are part of this
increment's verification.

## Completion boundary

Complete one authored two-task browser walkthrough: preview and save the next
exercise, inspect fresh work and preserved history, reload the successor, and
exercise ordinary continuation with scripted callbacks. Verify stale/duplicate
requests and lost-response recovery, unchanged source files, and existing browser
flows. Stop there; do not generate another private notebook demonstration or
reopen a closed fidelity study.

## Launch

Use the branch `codex/browser-next-exercise` until its PR is integrated. For an
existing completed notebook session, configure the next supported exercise and
an unused sibling output directory:

```sh
.venv/bin/python -m src.agents.browser_workspace \
  data/my-completed-exercise/session \
  --next-exercise-file examples/fruit-count.json \
  --next-exercise-output data/my-next-exercise \
  --port 8433
```

Open `http://127.0.0.1:8433/`, choose **Next exercise**, inspect the task and select
**Save next exercise**. The workspace opens the successor with both tasks in its
sidebar. Refresh retains it through `?exercise=next`. **Open next exercise** on
the original view recovers the same saved task after a lost response or restart.

This command allows offline setup only. `--send` separately enables the ordinary
tutor/student controls when the provider and pinned local runtime are configured.
Only one successor is configured per launch; this is not an exercise catalog or
an automatic multi-task curriculum. Preparing a different successor uses a new
explicit launch configuration and unused output directory.

## Verified result

667 Python tests pass (three optional skips), including twelve new next-exercise
cases. All three Node checks and seven Marimo checks pass. An independent review
verified source binding, fixed selectors, receipt/policy validation, pending
requests and recovery. If publication is interrupted before the creation receipt
is saved, that existing output remains blocked for inspection; it is never
silently recreated.

The authored desktop walkthrough saved Task 2 from Task 1, verified fresh work
and empty feedback, inspected the supplied policy, and exercised the ordinary
student and tutor reply controls using scripted callbacks. All five source files
remained unchanged. No provider request, container execution, private benchmark
change or additional human label occurred. The demonstration is operational
evidence, not an improvement in simulated-student fidelity.

The walkthrough also caught a shared chat-status bug: after a successful request,
the pending-message note still said a request was running. Chat now refreshes
after the submitting state clears; a regression check covers that completed state.
