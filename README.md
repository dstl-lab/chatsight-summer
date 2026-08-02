# Learner-Agent Simulation

Research codebase for simulating learners: LLM agents grounded in real students' logged
behavior with an AI tutor (via [ChatSight](https://github.com/minchan/chatsight)-labeled
corpora), used to screen tutor-policy changes against a synthetic cohort before any real
student is exposed.

**Read `CLAUDE.md` first** — it carries the cross-repo rules (classifier parity, snapshot
immutability, no student data in git) that every claim in this project depends on.

- Phase plan and invariants: `CLAUDE.md`
- Memos: `docs/`
- Snapshot provenance: `snapshots.md`
- Code: `src/` (ingest → eval → trajectories → agents → replay, plus the scoring wrapper)
- Experiments (pinned configs + results): `experiments/`

Data (`data/`) is gitignored and contains IRB-covered student conversations. Never commit it.
