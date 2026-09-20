# Learner-Agent Simulation for Screening AI Tutor Policies (temporary name)

A research prototype for **simulating student interactions with tutors**, informed by
DSC 10 tutoring logs. The intended audience is educators and researchers exploring
student support. Screening tutor policies is a research goal; realistic cohorts,
calibrated behavior probabilities and learning effects have not been established.

The repository includes an instructor-facing **top-down labeling tool**, help-episode
review and a saved notebook student. The current student uses visible dialogue, work
and feedback to propose edits, request checks, communicate or stop. Labels support
description and evaluation; they are not the current generator's state space.
See the [research reassessment](docs/2026-09-14-research-reassessment.md) for the evidence,
data limitations and proposed finite evaluation.
The [existing-data corpus summary](docs/2026-09-19-corpus-summary.md) describes the
252 saved conversations, the development subset's message patterns, and the limits
of sampling students from the current exports.
The [recorded behavior audit](docs/2026-09-19-recorded-behavior-audit.md) is **paused**;
its 86-message coding pass is not required to continue. Our
[standing workflow](docs/2026-09-19-minimize-manual-labeling.md) minimizes manual
labeling, reuses existing evidence, and prioritizes the saved simulator. Human
review returns only when needed for a specific consequential decision.

Raw data: DSC 10 tutor chat logs in an external Postgres (`dsc10_tutor_logs`), read-only
via `kubectl port-forward`. The database is shared with ChatSight, a distant-cousin project
doing bottom-up labeling — the two systems share raw logs and nothing else; their labels
are never compared or mixed.

**Read `CLAUDE.md` first** — it carries the rules (classifier parity, snapshot immutability,
blind measurement, no student data in git) that every claim in this project depends on.

The [Marimo workspace](docs/2026-09-19-saved-student-workspace.md) opens one saved
notebook student, shows work/diffs and dialogue, and lets a researcher supply tutor
guidance or [use a tutor policy](docs/2026-09-20-workspace-tutor-policy.md) and continue
one decision. Viewing is offline; sending requires an
explicit launch option and button click. The existing saved-student commands
remain available. See also the [UI direction](docs/2026-09-15-marimo-and-observation-contract.md).
The intended interface is a notebook-focused VS Code/Cursor-style editor on the
left with student–tutor chat on the right; the current layout is a prototype.
The same app also [opens saved chat scenarios](docs/2026-09-20-chat-scenario-workspace.md)
with a scenario selector and policy controls. The local preparation reuses the 29
cached first replies in separate sessions; recorded and simulated messages stay
distinct, and missing notebook activity is shown as unknown. No new labeling is required.

## Running a saved student

For historical **chat-only prefixes**, use the
[saved-chat workflow](docs/2026-09-15-saved-chat-student.md). It starts a conversation
scenario, generates one student reply at a time, and accepts your tutor response
after reopening. It uses the unchanged continuation prompt and requires no notebook
runtime. Saved state, fixed budgets and explicit no-reply are preserved; code in
chat does not execute or establish student work. `create` and `show` are offline;
generation requires `step --send` with a current context export.

The [saved-student workflow](docs/2026-09-14-continuing-student.md) initializes a task
and resumes bounded student actions across process reloads. The current executor
supports one selected cell, a supplied string column and a scalar result, with
requested checks in an isolated local Docker image. A separate
[task evaluation](docs/2026-09-14-task-portability.md) supplies the expected scalar
without adding it to either agent's prompt. Counting and category proportion use
the same action engine. This is limited task portability, not a general notebook
kernel or evidence that student behavior transfers across courses.

Use [tutor context](docs/2026-09-14-tutor-context.md) to inspect work and supply your
own reply, or [the notebook tutor](docs/2026-09-14-notebook-tutor.md) to generate one
reply under a supplied teaching policy and continue the same student. Both paths
bind the reply to the inspected state. Saved student replay makes no external calls.
The [bounded lesson command](docs/2026-09-14-notebook-lesson.md) alternates student
actions and generated tutor replies automatically until a terminal state or budget
limit, preserving the same work, checks and receipts.
The [teaching-pair setup](docs/2026-09-15-teaching-pair.md) prepares two initial
tutor alternatives with identical student work, earlier dialogue and budgets,
ready for the existing saved-student commands.
After a completed encounter, [next-task initialization](docs/2026-09-15-multi-task-history.md)
carries verified history across tasks, up to 64 KB. Both agents receive the ordered
records, with prior feedback separate from the current task. This is not evidence of learning.
The [portable coding review UI](docs/2026-09-14-next-task-history.md#portable-review-ui)
lets two independent reviewers code the fixed eight recorded messages one at a time
and return their answers without installing the project.
The [offline scoring command and saved replay](docs/2026-09-14-offline-scoring-and-replay.md)
provide a hand-checked toy comparison against training frequencies and a read-only
view of the existing linked encounters. These tools do not establish student fidelity.

## Running the labeling loop

Two entry points (installed via `uv sync` from `pyproject.toml`):

- `label-loop` — interactive CLI for the elicit → sample → draft → review/tweak →
  mass-label loop
- `label-loop-web` — the same loop as an instructor-facing web page (FastAPI), with live
  progress during drafting and mass-labeling

Both write immutable labeled-corpus snapshots to `data/snapshots/<id>/` with a full
provenance manifest.

## Where things live

- Phase plan and invariants: `CLAUDE.md`
- Memos: `docs/` (start with `2026-08-05-simulation-first-framing.md` and
  `2026-08-01-topdown-labeling-same-repo.md`)
- Snapshot provenance ledger: `snapshots.md`
- Code: `src/` (ingest → labeling → eval → trajectories → agents → replay, plus scoring)
- Experiments (pinned configs + results): `experiments/`

Data (`data/`) is gitignored and contains IRB-covered student conversations. Never commit it.
