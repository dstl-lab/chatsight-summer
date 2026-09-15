# Two hands-on repo explorations

Both tasks can happen on separate branches while the main simulator and logger
work continues. Their results are useful additions, not prerequisites.

## 1. Try new exercises with the existing simulated student

Use the current student runner to try a couple of small exercises beyond the
examples we've already used. Stay within its table/one-cell/scalar-result setup;
counting a particular category or calculating a proportion could be starting points.
Explore what kinds of tasks it handles, where the student's behavior gets strange,
and what is awkward about setting up an exercise.

Bring back runnable examples and a short walkthrough of anything interesting.
You can use invented tasks and data, so this doesn't depend on access to the
private student dataset. Keep experiments in new session folders.

Start with `src/agents/notebook_student.py`, `tests/test_notebook_student.py`,
`tests/test_task_evaluation.py`, and the
[task setup guide](2026-09-14-task-portability.md).

## 2. Make a small Marimo viewer for a simulated student's session

Use the repo's saved-session loader and replay code to explore how a simulation
could be easier to follow in Marimo. What would help you understand what happened:
stepping through actions, seeing code diffs, following tutor messages, or comparing
work before and after a check? Pick the view that seems most useful and try it.

Build around an invented session using the existing test patterns, or a saved
session available locally. Keep this first viewer read-only and reuse the loader,
so exploring the display doesn't require changing the runner or making model calls.
A small working prototype and your observations would be useful.

Start with `src/eval/notebook_replay.py`, `src/agents/tutor_context.py`,
`tests/test_notebook_replay.py`, and the
[replay guide](2026-09-14-offline-scoring-and-replay.md#saved-simulation-replay).
