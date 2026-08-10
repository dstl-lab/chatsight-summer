# Learner-Agent Simulation for Screening AI Tutor Policies (temporary name)

A **screening instrument for AI tutor design**: simulated student cohorts, grounded in a
full quarter of real DSC 10 tutoring logs, that let an instructor test candidate tutor
policies ("never give direct answers," "answer-then-probe") before any real student is
exposed. The aim is to narrow twenty candidate policies to the three worth a real quarter —
never to claim a policy "improves learning."

The machinery underneath is an instructor-facing **top-down labeling tool**: the instructor
describes the trends they want to see, the tool drafts labels on a stratified sample for
review and tweak-by-prompt, then mass-labels the corpus into an immutable snapshot. Those
labels are the state space the simulation moves through; agents are grounded in real
students' labeled trajectories, and policy effects are shifts in the distribution of
trajectories. (Framing memo: `docs/2026-08-05-simulation-first-framing.md`.)

Raw data: DSC 10 tutor chat logs in an external Postgres (`dsc10_tutor_logs`), read-only
via `kubectl port-forward`. The database is shared with ChatSight, a distant-cousin project
doing bottom-up labeling — the two systems share raw logs and nothing else; their labels
are never compared or mixed.

**Read `CLAUDE.md` first** — it carries the rules (classifier parity, snapshot immutability,
blind measurement, no student data in git) that every claim in this project depends on.

## Running the labeling loop

Two entry points (installed via `uv sync` from `pyproject.toml`):

- `label-loop` — interactive CLI for the elicit → sample → draft → review/tweak →
  mass-label loop
- `label-loop-web` — the same loop as an instructor-facing web page (FastAPI), with live
  progress during drafting and mass-labeling

Both write immutable labeled-corpus snapshots to `data/snapshots/<id>/` with a full
provenance manifest.

## Extracting trajectories

Convert a labeled snapshot into per-conversation label trajectories with:

```bash
uv run extract-trajectories data/snapshots/<snapshot_id>
```

By default this writes:

```text
data/trajectories/<snapshot_id>/trajectories.json
```

The trajectory artifact contains IDs, active labels, timing fields, and snapshot
provenance. It intentionally omits student text and model rationales.

## Where things live

- Phase plan and invariants: `CLAUDE.md`
- Memos: `docs/` (start with `2026-08-05-simulation-first-framing.md` and
  `2026-08-01-topdown-labeling-same-repo.md`)
- Snapshot provenance ledger: `snapshots.md`
- Code: `src/` (ingest → labeling → eval → trajectories → agents → replay, plus scoring)
- Experiments (pinned configs + results): `experiments/`

Data (`data/`) is gitignored and contains IRB-covered student conversations. Never commit it.
