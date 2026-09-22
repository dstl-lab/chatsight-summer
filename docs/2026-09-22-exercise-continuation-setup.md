# Continue into a supplied exercise

**TL;DR:** Let the existing exercise setup consume a completed notebook session
through `--previous`. It creates the next task and its policy together using the
existing verified-history handoff. No new student generation is part of setup.

Custom exercise files now work for fresh students, but using one as a later task
still requires splitting its task/activity/evaluator into separate files. Add an
optional `previous` argument to notebook_example and mutually exclusive CLI
`--previous` / `--chat-source` options. A continuation inherits its original
conversation example from the existing lineage instead of introducing another.

Reuse notebook_next_task.create, its terminal-state requirement, model inheritance,
history verification, provenance and context limit. Use the new exercise's task,
work, activity, evaluator and tutor policy, with six fresh decisions and no current
feedback/actions. Keep the former encounter closed. The researcher supplies the
next task; the setup does not infer a student's choice to continue or learning.

Publish the session and policy through the current staging path. Reject an output
inside any ancestor session, hold read locks on the source chain through publication,
and verify the staged child's lineage before publishing. Existing destinations,
unfinished/invalid sources and conflicting source options must leave saved work
unchanged. Do not duplicate history assembly or change a saved engine/prompt.

Verify the actual CLI and authored two/three-task chains offline: original example
once, ordered observed history, fresh task state, inherited model, new policy,
evaluator exclusion, source preservation, refusal of unfinished/conflicting/nested
inputs, and interrupted publication. Existing workspace and replay consume the
normal saved session. No live run, new labels, UI or automatic task scheduler.

## Completed verification

`--previous` now uses the existing handoff and stages its session with the new
exercise policy. Initial ancestor locks remain held through publication; the
staged lineage must match the original manifests, states and receipts. The
[quickstart](teammate-quickstart.md#continue-into-another-exercise) covers setup,
viewing with the new policy and read-only replay.

Three authored regressions verify the CLI, three-task history/example retention,
inherited model, fresh state, private evaluator exclusion, conflicting/unfinished
sources, ancestor nesting, interruption, locks and a replayable source-receipt
mutation. All **457 tests pass**, with three optional container skips and one
existing dependency warning; Marimo checks and Node navigation pass. Independent
review found no actionable issue.

The actual CLI also prepared the public fruit-count exercise from the closed,
authored notebook example at `data/custom-notebook-continuation-example/`. Its
initial replay shows prior feedback separately and six unused decisions. The
predecessor and the completed communication run's 59 frozen inputs remain
unchanged. No new model or runtime call, human label or live run was needed.
