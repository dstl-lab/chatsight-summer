# A runnable notebook example with explicit task data

**TL;DR:** Package the existing notebook simulator as one public, authored example.
It supplies task text, table values and initial work. Execution feedback comes from
the existing local checker. This makes the grounded path usable without private
experiment files; it does not repair or validate the chat-only generator.

The closed three-scenario chat run exposed invented missing task details and
notebook observations. Its conversations have no aligned captured notebook state.
The separate notebook engine already supports supplied work, silent revisions,
requested execution and tutor interaction. Repeating another private live probe
would not address the missing public setup.

Add a small create-only command for the existing four-row blue-proportion task.
Require an explicit immutable local-runtime image ID. Save a fresh session and
editable tutor policy together; refuse existing destinations. Creation neither
calls a model nor executes code. Keep the task, table, initial cell and answer
explicitly authored. The evaluator's expected answer stays out of tutor/student
prompts and worker inputs. Use existing session, lesson, workspace and replay
commands; no new prompt, schema, checker, scheduler or UI.

Completion requires a reproducible setup from tracked files, validation before
publishing, and preservation on a repeated create. Check the declared task/data
in both agent inputs and answer isolation. An authored wrong-check → quiet edit
→ cleared feedback → correct-check trajectory must run through the existing
container and reopen exactly. Keep that integration check optional when Docker
is unavailable; never substitute host execution or a fabricated pass.

One session permits six student decisions; the documented lesson permits two
tutor replies. Live use is optional and is not part of this packaging step.
No Gemini calls, new labels, realism scores or changes to frozen studies are
queued. The runtime still covers one editable cell, one string column and one
scalar answer. Generated chat remains unvalidated even with explicit task data.

## Completed verification

`src.agents.notebook_example` now creates the fresh session and policy together.
The [teammate guide](teammate-quickstart.md#2b-start-with-an-explicit-notebook-task)
covers runtime setup, viewing, optional bounded live use and saved HTML replay.
Creation and replay of the prepared local example made no model or execution calls.

The full suite passes **432 tests**, with three optional container skips and one
upstream deprecation warning. Both Marimo apps and the existing Node navigation
check pass. The new optional integration check was then run separately against
the existing immutable local runtime and passed: two real container executions
returned wrong `2`, then correct `0.5`, with a quiet edit and cleared feedback in
between. Saved state and HTML replay reopen without changing session files.

These test actions were explicitly authored and supplied by test callbacks, not
model generations. The legacy runner labels injected actions `model`; that field
alone is not evidence that a provider was called. The integration check forbids
provider construction. No live run, behavior label or realism assessment occurred.
Independent code/docs review found no substantive issue; the optional-test count
in the teammate guide was corrected. Existing engine/prompt files and frozen
research evidence remain unchanged.
