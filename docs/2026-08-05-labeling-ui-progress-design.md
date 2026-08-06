# 2026-08-05 — Labeling web UI: live progress and work safety

## Problem

The labeling web UI (`label-loop-web`) turns into a black hole the moment a long
operation starts. The working screen is one spinner plus one line of text; the
"live progress counter" (commit `3f3ec7b`) appends `12 / 250 messages (4%)` and
nothing else. Concretely:

- **Fetching** (one query per conversation over the tunnel, 200+ round-trips)
  shows a static spinner with no count.
- **Schema drafting** is an uninstrumented LLM call that runs *before* the
  counter exists, so every draft/tweak cycle starts with a bare spinner.
- **Gemini retries** back off silently (up to ~14s per message in `with_retries`);
  the counter freezes with no signal distinguishing a retry from a hang.
- **Snapshot writing** happens while the bar is pinned at 100%.
- **Errors destroy work.** Any failure flips to an error screen whose only exit
  wipes all state. A `FileExistsError` on a colliding snapshot directory throws
  away a completed full-corpus labeling run — a run's worth of LLM spend lost to
  a stack trace.

Scope decision (with Minchan, 2026-08-05): richer feedback **plus** the safety
fixes above. Explicitly out of scope: cancel buttons, in-flight button
disabling, dead-server detection, smarter polling.

## Design

Architecture is unchanged: single static `index.html`, vanilla JS, polling
`GET /api/state` every 1.5s. No framework, no build step, no SSE.

### 1. Structured status (server)

`LoopSession` replaces the bare `progress` dict with a `status` object exposed
in `/api/state`:

```json
{
  "steps": [
    {"key": "schema", "name": "Schema v3 saved", "detail": "6 labels · help-seeking behavior", "state": "done"},
    {"key": "sample", "name": "Sampled 4,812 messages", "detail": "from 203 conversations", "state": "done"},
    {"key": "label",  "name": "Labeling messages", "state": "active",
     "progress": {"done": 1781, "total": 4812}, "started_at": 1786000000.0},
    {"key": "snapshot", "name": "Snapshot written", "state": "pending"}
  ],
  "retry": {"attempt": 2, "max": 4, "wait_s": 4.0},
  "recent": [
    {"text": "<student message>", "labels": ["instrumental ask", "frustrated"]}
  ]
}
```

Steps per phase:

- **fetching**: Counted conversations → Fetched conversations *i / N* (add an
  `on_progress` callback to the fetch loop in `src/ingest/rawlog.py`, mirroring
  the one `draft_labels` already takes).
- **drafting**: Schema drafted (or revised, on tweak) → Sample labeled *i / N*.
- **mass_labeling**: Schema saved → Sampled corpus → Labeling messages *i / N*
  → Snapshot written.

`recent` holds the last 3 `(message text, labels)` pairs, updated as each
message finishes. In-memory only; nothing new is written to disk.

### 2. Retry visibility

`with_retries` in `src/labeling/llm.py` gains an optional
`on_retry(attempt, delay)` callback. The session records it into
`status.retry`; cleared on the next successful call. The UI renders it as an
amber banner: *"Gemini rate-limited — retry 2 of 4, waiting 4s."*

### 3. Rate + ETA (client only)

The frontend keeps a rolling window of recent `(time, done)` samples and
derives *"~3.1 msg/s · about 16 min left · elapsed 9:42"*. No server timing
logic beyond `started_at`.

### 4. Work safety

- **Snapshot collision:** `emit_snapshot` picks a unique directory (suffix
  `-2`, `-3`, …) instead of failing on `mkdir(exist_ok=False)`.
- **Incremental accumulation:** mass-labeling appends each result to the
  session as it completes, so a mid-run failure keeps completed labels.
- **Resumable errors:** the error screen shows what survived (fetched
  conversations, accepted schema, N completed labels) and offers **Retry from
  where it stopped** (re-runs the failed step reusing in-memory state; labeling
  resumes after the last completed message), **Back to review** (when a
  reviewed sample exists), and **Start over** (the current wipe-everything
  reset).

### 5. Working-screen layout (mocked with Minchan, 2026-08-05)

Two-column, 60rem page column (rest of the app stays 52rem):

- **Left — vertical gate rail (16rem):** the phase's steps as gates on a
  vertical bar. Passed gates show ✓ plus a one-line receipt (label count,
  message count, snapshot path); the active gate is lit with a pulsing dot;
  pending gates are dim. The rail fill advances proportionally with the active
  step's progress.
- **Right — action panel:** current step name, progress bar,
  rate/ETA/elapsed row, the retry banner, and a **Recently labeled** ticker —
  last 3 labeled messages (newest on top, older entries fading) with their
  label chips.
- Below ~44rem viewport width the rail stacks above the action panel.
- Page header: phase title plus a provenance line (schema version, intent,
  conversation counts).

Student text in the ticker follows the existing rule: `textContent` only,
never `innerHTML`.

## Honest limits

- The ticker shows drafted labels mid-run; it is a liveness surface, not a
  review surface — invariant 8 (blind measurement) is untouched because
  nothing seen here feeds reliability numbers.
- ETA is a rolling-window extrapolation; it will wander under rate-limit
  bursts. That is acceptable — its job is "minutes, not hours," not precision.
- Resume-after-error trusts in-memory state; a server crash still loses the
  run. Persisting partial labels to disk is out of scope (and would need the
  same Rule-4 care as snapshots).

## Testing

- Unit tests for `LoopSession` with a fake LLM and fake fetcher: step
  transitions, retry surfacing, incremental accumulation, resume-after-error,
  snapshot-collision renaming.
- Manual end-to-end run through the tunnel for the visual layer.
