# Top-Down Labeling + Learner-Agent Simulation (temporary name)

Research codebase in two subsystems: (1) an instructor-facing **top-down labeling tool** —
the instructor describes the trends they want to see (conceptual, behavioral, …), the tool
drafts labels on a stratified sample for review and tweak-by-prompt, then mass-labels; and
(2) a **learner-agent simulation** — LLM agents grounded in the labeled behavior of real
students with an AI tutor, used to screen tutor-policy changes against a synthetic cohort
before any real student is exposed.

Raw data: DSC 10 tutor logs in an external Postgres, read-only via `kubectl port-forward`
(same access pattern as the sibling project
[ChatSight](https://github.com/minchan/chatsight), which does bottom-up labeling).

**Read `CLAUDE.md` first** — it carries the rules (classifier parity, snapshot immutability,
blind measurement, no student data in git) that every claim in this project depends on.

- Phase plan and invariants: `CLAUDE.md`
- Memos: `docs/` (start with `2026-08-01-topdown-labeling-same-repo.md`)
- Snapshot provenance: `snapshots.md`
- Code: `src/` (ingest → labeling → eval → trajectories → agents → replay, plus scoring)
- Experiments (pinned configs + results): `experiments/`

Data (`data/`) is gitignored and contains IRB-covered student conversations. Never commit it.
