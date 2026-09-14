# Continue one notebook student across tutor exchanges

Minchan redirected work from presentation preparation back to making simulated
students. Build one usable continuing student with the existing notebook action
and runtime components. The unfinished history ablation stays paused; no new
labeling or plausibility-review batch is part of this change.

The bounded change is a local command-line session. Initialize it with an
explicit task, work, dialogue and declared runtime. Take a limited number of
student actions, show the resulting work/message, and save the session. When
the student sends a message, accept a separately supplied tutor reply and
continue with the same work, observation and complete generated history. Store
that tutor reply as supplied intervention, never a recorded historical future.
Keep existing prompts, schemas and completed experiment artifacts unchanged.

An action-budget pause leaves the student active and resumable. A chosen no-reply
ends the encounter; it cannot be reinterpreted as a budget pause. Environment
failures, provider errors and interrupted requests stop safely and cannot
silently resend. Chat and tutor claims cannot change notebook work or produce
execution feedback. Only the existing isolated runtime executes requested checks.

Reuse the existing JSON state and injected provider/check functions. Persist an
initial manifest and sequential operation receipts under ignored data/. Record
pending before external work, keep exact prompts/responses/checks, and replay
the saved choices through the existing state transitions when reopening. Hold
one local session lock during an operation and reject changed source/schema,
incomplete receipts or replay mismatches. This is a small local session, not a
database service, new interface, memory framework or course-general runtime.

Verify the full edit → chat → supplied tutor → resumed edit/check lifecycle with
controlled provider outputs, including process reload, capped continuation,
stale feedback and terminal/error paths. A bounded authored live smoke run can
check integration without asking the instructor to judge another batch. Keep
its generated behavior distinct from scripted test choices.

This milestone is complete when a single session can survive reopening and a
tutor exchange without losing or inventing state, with a runnable command and
saved demonstration. It establishes continuity of the mechanism. It does not
validate student personas, learning, behavior probabilities or cross-task memory.

## Run the student

From the worktree, initialize a new folder with a task JSON and a runtime activity
JSON. The existing runtime supports the declared single-cell distinct-count
activity; these files do not turn it into an arbitrary notebook kernel. The task
contains `initialization`, `task`, `work` (cell index, source, revision), and visible
`dialogue` ending with a tutor reply. The activity declares the local immutable
image, library/version, table/column/result names and supplied string values.

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_student create data/my-student --task task.json --activity activity.json --max-decisions 12
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_student step data/my-student --send --max-actions 3
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_student show data/my-student
```

`show` rebuilds the state entirely from saved choices and observations, without
provider or Docker dispatch. When status is `awaiting-tutor`, write the intended
tutor reply to a UTF-8 text file, then continue:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_student step data/my-student --send --tutor-file tutor.txt
```

When the student is still active, another `step --send` continues quiet work.
No tutor reply is inserted during a quiet action-budget pause. Every step uses
at most six model decisions and shares the session's initial total budget.
The provider's existing adapter permits up to four attempts per logical decision;
operation receipts store logical requests and terminal responses/errors, not an
independent count of every internal retry attempt. An exhausted budget does not
become a student stop. A pending interrupted operation requires inspection, not
an automatic retry. The local POSIX lock prevents concurrent steps for one student.

The manifest preserves input capture/omission metadata outside the model packet.
Saved source/schema pins deliberately reject code changes during resumption;
the later tutor-context extension explicitly supports the original b2a417b wrapper
with unchanged underlying prompts, schemas and runtime. It preserves old manifests
and receipts, recording the current engine for new operations. Other implementation
changes still require the pinned environment or a new session. There is no general
migration. See [the tutor-context workflow](2026-09-14-tutor-context.md) for readable
inspection and replies bound to the exported session/state.

## Completed implementation and integration check

`src/agents/notebook_student.py` now supplies create/show/step commands with saved
tutor interventions and bounded continuation. Eight new regression cases and
the related existing suites pass: 27 tests total. They cover two exchanges,
edit-plus-chat, checked work carried across a tutor turn, pending interrupts,
provider failure, mismatched receipts, concurrent access, cumulative budget,
CLI dispatch gating and infrastructure exit status. The older authored runtime
trajectory still replays offline with all 25 preparation pins unchanged.

The separate two-decision authored integration run is retained in
`data/episode-pilot/continuing-student-v1/`. The first actual Gemini decision
silently revised the source to use `unique().size`. A fresh process reconstructed
that state exactly; the second decision requested a check. Docker was stopped,
so execution did not begin and the session saved an environment error with no
correctness result. It did not invent student silence or silently retry the run.

Starting the existing Docker application restored the original immutable image.
One separately recorded runtime diagnostic evaluated the saved revision and
returned 3 with passing feedback. It made zero model calls and did not update
or reopen the original terminal student session. Both the failure and successful
availability diagnostic remain intact. No replacement student choices or human
plausibility review were requested. This verifies persistence/provider integration
and the restored checker, while the tutor-resumption path is verified by the
controlled lifecycle/CLI tests. It remains one authored task, not learner fidelity.
