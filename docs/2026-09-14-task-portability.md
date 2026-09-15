# Separate task evaluation from student actions

## TL;DR — setting up a new task

Give the existing student a small table exercise, such as counting categories or
calculating a proportion. The current runtime supports **one editable code cell,
one string column, and one scalar answer**.

1. Prepare three files: **task JSON** with instructions, initial code and dialogue
   ending in a tutor reply; **activity JSON** with the table data and declared
   runtime; **evaluation JSON** with the expected answer, e.g. `{"expected": 0.5}`.
   The expected answer stays out of the student/tutor prompts.
2. Create a **new session folder** using `notebook_student create` with `--task`,
   `--activity` and `--evaluation-file`. The full command is
   [below](#use-a-different-scalar-task).
3. Use `step --send` to generate actions and `show` to inspect the saved state.
   When it reaches `awaiting-tutor`, supply a reply with `--tutor-file` on the
   next step. See the [runner guide](2026-09-14-continuing-student.md#run-the-student).

Live steps need the Python dependencies and a Gemini API key; requested checks
need local Docker and the declared image. `show` works offline. Expected values
must match both value **and type**: `1`, `1.0` and `true` are different answers.

Minchan asked how the current implementation becomes generalizable. Saving a
student and supplying a version-matched tutor reference makes an interaction
reusable, but does not establish transfer of student behavior. The immediate
software limitation is concrete: the container returns a scalar, yet its parent
always grades that scalar as a distinct count. Adding a lesson runner would leave
that task-specific assumption intact.

Keep the existing action engine, prompt, worker and declared image. Allow a
researcher to supply a separate scalar evaluation object, `{"expected": ...}`.
Grade the returned scalar by exact type and value in the parent process. Bind
feedback to the evaluation object's hash as well as source, revision, activity
and runtime. Do not include the expected result in the worker request, student
prompt or tutor context. The task statement and table remain visible; the
student can of course derive an answer from those inputs. This separation avoids
handing the answer directly to either agent, not all possible grader gaming.

Without an explicit evaluation, preserve the old distinct-count semantics and
input shape. Permit the exact two previously shipped saved-session engines to
replay unchanged. New operations record a new receipt version and their actual
source hashes. Old checker observations are accepted only with their original
distinct-count semantics and otherwise matching bindings. Unknown source changes
remain unsupported. This is a declared revision of the runtime/session boundary;
older experiments stay frozen at their recorded commits and are not regraded.

Completion is a bounded software check: use the same student action engine for
distinct counting and the proportion of rows containing a given category, with
authored wrong and correct solutions in the same immutable table runtime. Verify
evaluation isolation, feedback invalidation on edits or evaluator changes, saved
replay and the authentic earlier session receipts. No new Gemini batch or human
plausibility review is required for this architectural check.

## Honest limit

This remains one selected cell, one string column, one scalar output and a fresh
Python namespace per check. Exact scalar equality is a local exercise assertion,
not a general correctness proof. Arbitrary notebooks, other languages, external
course graders and numeric tolerance are outside this increment. Add support
when a concrete next task requires it, rather than building a plugin framework.

Task portability, behavior fidelity and educational usefulness are separate
claims. Two authored exercises establish only the first within this narrow
runtime. They cannot validate student personas, learning gains or transfer to a
different course. The paused labeling/review loop and history ablation stay
paused; this work supplies a more reusable mechanism for a later finite,
held-out behavioral evaluation.

## Use a different scalar task

Keep the task statement, initial work and dialogue in the existing task JSON;
the activity JSON supplies the declared image, table, column and values. Add a
separate evaluation file containing `{"expected": 0.5}` for a proportion task:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_student create data/proportion-student --task data/proportion-task.json --activity data/table-activity.json --evaluation-file data/proportion-evaluation.json
```

Then use the existing `step`, `show` and tutor commands. The evaluator belongs to
the saved session; it cannot be replaced through a later CLI step. Accepted
expected results are strings, integers, finite floats and Booleans. Types match
exactly: integer `1`, float `1.0` and Boolean `true` are distinct. Null, containers
and extra fields are rejected. Without the option, legacy distinct counting
remains the default. These local files contain researcher-authored task inputs;
this command does not automatically recover a course assignment or its grader.

For the authored values `blue, amber, blue, green`, the same engine checked:

| Task | Separate expected result | Authored expression that passed |
| --- | --- | --- |
| Count distinct shades | `3` | `len(swatches.get('shade').unique())` |
| Proportion of blue rows | `0.5` | `(swatches.get('shade') == 'blue').sum() / len(swatches.get('shade'))` |

Only task inputs and submitted source differ; no exercise-ID branch, new student
prompt, worker image or label category selects the behavior. The expected result
is saved in private session/check receipts for replay. Privacy here means exclusion
from model and worker inputs, not encryption or filesystem access control.

## Completed verification

The related offline suite reports **44 passed, 2 skipped**. Both skipped tests
require an explicitly selected image; the new two-task integration was then run
separately against the existing immutable image and **passed**. Coverage includes
typed evaluation, answer isolation in both prompts and worker requests, evaluator
and revision binding, saved tutor continuation, feedback clearing, CLI validation
and exact V1/V2 receipt compatibility. Independent code review found no actionable
issue. The worker and student prompt are unchanged.

Five authored session checks ran through the action engine with `origin=scripted`:
counting returned `4` (fail), then `3` (pass); category proportion returned `4`
(fail), `0.0` (fail), then `0.5` (pass). Each intervening edit cleared feedback.
The first intended proportion solution used Python's `sum` over a Babypandas
Series. Two separately recorded diagnostics showed that Python iteration yielded
no values, while the Series retained the correct Boolean comparison and its own
`.sum()` returned `2`. Correcting the authored expression fixed the proportion;
the evaluator and expected answer did not change. All failed actions and the
initial control script's assertion failure are preserved alongside the correction.
This is a library-usage limitation exposed by actual execution, not generated
student behavior or a model improvement. In addition, the integration regression
executed two container checks. No Gemini requests were made.

The original V1 student and V2 tutor-linked student still replay exactly, with
unchanged files and all eight previous live-trace artifact hashes verified.
Legacy source pins were checked against commits b2a417b and a4f6e48. Plans, control
inputs, action states, diagnostic observations and results are retained in ignored
`data/episode-pilot/task-portability-v1/`. Earlier generated traces retain their
original statuses and budgets. This increment is complete; student realism and
cross-course transfer remain separate, unvalidated research questions.
