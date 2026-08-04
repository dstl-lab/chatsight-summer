# Labeling Web UI — design

**Date:** 2026-08-03 · **Status:** approved (Minchan, via background session)

## What

A simple localhost web UI for the Phase 1 interactive labeling loop, covering the full
`label-loop` CLI flow: intent entry → draft schema + stratified labeled sample → review →
accept/tweak → mass-label with progress → snapshot confirmation. FastAPI + one
self-contained static HTML page; no frontend toolchain. This is the first
instructor-facing surface (CLAUDE.md Phase 1), deliberately minimal — not the Phase 4
frontend.

## Why

The accept/tweak loop is the instructor's arbitration step. Reading 25 labeled messages
with rationales in a terminal is hard; a page grouped by stratum with the schema alongside
is the honest minimum UI. The CLI remains and stays canonical for scripted runs.

## Architecture

- `src/labeling/webapp.py` — FastAPI app + in-process session state machine.
- `src/labeling/static/index.html` — single page, vanilla JS, polls state.
- Entry point `label-loop-web` (uvicorn on `127.0.0.1` only).
- Reuses the CLI's building blocks unchanged: `draft_schema`, `revise_schema`,
  `stratified_sample`, `draft_labels`, `save_schema`, `emit_snapshot`,
  `fetch_conversations`/`count_conversations`. `run_loop` and `cli.py` untouched.
- New deps: `fastapi`, `uvicorn`; dev: `httpx` (TestClient).

## State machine

Single session (one instructor; a `start` while a job is running returns 409).

```
idle → fetching → drafting → review → mass_labeling → done
              ↘ error (from any working state; message surfaced, quit resets)
review --tweak--> drafting → review   (new schema version each tweak)
review --accept--> mass_labeling → done (schema saved, snapshot emitted)
quit → idle (nothing written)
```

LLM/DB work runs on a background thread; `GET /api/state` reports phase + data.

## API

- `POST /api/start` `{intent, max_conversations=200, sample_size=25, seed=0}`
- `GET /api/state` → `{phase, error, schema, sample (with labels+rationales+stratum),
  provenance {fetched, total, excluded}, snapshot_path, schema_version}`
- `POST /api/tweak` `{feedback}` — only valid in `review`
- `POST /api/accept` — only valid in `review`
- `POST /api/quit` — resets to idle; invalid-phase actions return 409

## Page

Intent form (with max-conversations / sample-size / seed) → review screen: schema panel
(name, kind, description, version id), sample grouped by stratum with applied labels and
rationales, the ACCEPT_NOTE displayed prominently, tweak textarea + accept + quit →
mass-label spinner → snapshot path + "add a row to snapshots.md" reminder.

## Invariants respected

- ACCEPT_NOTE shown on the review screen (invariant 8: acceptance ≠ measurement).
- Excluded-conversation provenance displayed, same numbers as the CLI prints.
- Every tweak is a new schema version (existing `revise_schema` behavior).
- Binds 127.0.0.1 only; student text is rendered in the local browser, never written
  outside `data/`; nothing student-derived enters git.

## Testing

Hermetic, matching existing test style: fake `generate` + fabricated conversations, no DB
or Gemini. TestClient exercises: full happy path (start→review→accept→done with snapshot
on tmp data dir), tweak produces new schema version, invalid-phase actions 409, error
path surfaces message, quit resets. Background thread made synchronous/injectable in
tests.

## Out of scope (YAGNI)

Multi-user sessions, auth, persistence of UI state across restarts, editing labels
directly in the UI (feedback is free-text, matching the intent-compilation design),
anything Phase 4 (policy views, click-through trajectories).
