# Experiments

One directory per experiment: `YYYY-MM-DD-short-name/` containing

- `config.json` — the pins: snapshot ID, schema version ID, classifier prompt/config hash,
  model IDs. An experiment without complete pins is invalid (CLAUDE.md rule 2: no orphan
  numbers).
- results artifacts (metrics JSON/CSV; never verbatim student text — that stays in `data/`)
- the analysis notebook, outputs stripped before commit
