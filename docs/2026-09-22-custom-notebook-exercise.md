# Supply a notebook exercise with an existing conversation example

**TL;DR:** Extend the existing setup command with an optional exercise JSON file.
Researchers can combine their own supported task with an original saved chat
prefix without private Python glue. The existing blue-proportion example remains
the default. This is setup portability, not a new fidelity experiment.

The generic notebook student already accepts task, activity and evaluator inputs.
Only notebook_example currently attaches and verifies a conversation source, and
it hardcodes its task. Add `--exercise-file` to that command and an `exercise`
argument to its create function. One object contains the existing `task`,
`activity`, `evaluation` and `policy` structures. Require all four explicitly;
the immutable runtime image remains a separate required argument. Reject unknown
bundle fields, malformed task/policy, an embedded image and invalid existing
activity/evaluator values before publishing anything. Keep supplied objects
unchanged when adding conversation context; preserve optional task provenance.

Reuse existing source-prefix verification, staging, destination refusal, session
creation and private-evaluator projection. Keep the model, six-decision budget,
runtime, generation prompts, lesson/workspace/next-task contracts and historical
results unchanged. Do not add a catalog, upload service, new runtime or UI.

Verify the CLI with a distinct, entirely authored exercise and authored chat
source: exact task/work/data/evaluator/policy, unchanged source, original prefix
only, evaluator excluded from both agent prompts, saved replay, invalid-input
rejection and refusal to overwrite. Provider and execution callbacks must remain
unused during setup and replay. Use scripted decisions only to exercise the
existing tutor/student handoff in tests. Run the repository's required checks.

The runtime still handles one selected cell, one string column and a scalar
result. Supplied task data is authored or explicitly provided; historical chats
do not imply a recovered notebook or a validated student persona. No new live
model run, labels, prompt tuning or generator adoption is queued.

## Completed verification

The optional exercise input now works through both the Python setup and CLI,
including the unchanged conversation-source bridge. The public
[fruit-count bundle](../examples/fruit-count.json) and
[teammate guide](teammate-quickstart.md#supply-your-own-supported-exercise) provide
a reproducible starting point. Supplied inputs are copied before adding context;
the default exercise, engine and generation prompts remain unchanged.

Two new regressions failed before implementation and now pass. They cover custom
facts reaching both agents, evaluator/provenance exclusion, original-prefix-only
context, next-task retention, caller/source preservation, CLI loading, malformed
input rejection and refusal to overwrite. All **446 tests pass**, with three
optional container skips and one existing dependency warning. Both Marimo checks
and the Node navigation check pass; independent review found no code blocker.

The documented public CLI was also run locally, producing a fresh fruit-count
session and initial replay in ignored `data/custom-notebook-exercise-example/`.
Its explicit evaluator is 2 (not the distinct-category default of 3), current
feedback is empty and all six decisions remain unused. Creation and replay made
no model or execution calls. The completed continuity run's 59 frozen files still
verify. This increment stops at reusable setup, without another live run.
