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

Raw data: DSC 10 tutor chat logs in an external Postgres (`dsc10_tutor_logs`), read-only
via `kubectl port-forward`. The database is shared with ChatSight, a distant-cousin project
doing bottom-up labeling — the two systems share raw logs and nothing else; their labels
are never compared or mixed.

**Read `CLAUDE.md` first** — it carries the rules (classifier parity, snapshot immutability,
blind measurement, no student data in git) that every claim in this project depends on.

## Running a saved student

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
After a completed encounter, [next-task initialization](docs/2026-09-14-next-task-history.md)
carries its observed history into a fresh task. The record is shared with both
agents; it is not a private memory model or evidence of learning.

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
