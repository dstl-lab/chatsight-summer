# First-load screen redesign — design spec

Date: 2026-08-06
Status: approved in brainstorming (Bookend direction + side-rail data peek)

## Purpose

The idle screen (`screen-idle` in `src/labeling/static/index.html`) is the first
instructor-facing surface of the labeling loop, and today it is the barest part
of the app: one line of prose, a 3-row textarea, three raw number inputs, a
Start button, and a static tunnel footnote. This redesign gives it the same
identity PR#2 gave the done screen, frames the input as the instructor
authoring their own brief, and grounds that brief in a peek at real data.

Decisions made during brainstorming:

- **Audience: instructor-facing.** Design for someone who has never seen the
  tool, not just the researcher.
- **The base prompt stays invisible.** `ELICIT_PROMPT` in `src/labeling/elicit.py`
  is the generic, system-level framing (analogous to a user-level CLAUDE.md);
  the instructor writes only their specific, personal brief on top of it
  (analogous to a repo-level CLAUDE.md). No UI exposure of the base prompt, no
  changes to elicitation.
- **Visual direction: Bookend.** The dark plate component from the done screen
  also opens the run — the run starts and ends on the same surface.
- **Data peek: side rail.** Real stratified messages sit beside the writing
  surface the whole time the instructor composes, so the brief is written in
  contact with the material.
- **Run knobs collapse.** Max conversations / sample size / seed are research
  knobs, not instructor concepts; they move behind a collapsed disclosure with
  unchanged defaults.

## Screen layout (frontend)

All changes live in `src/labeling/static/index.html`, restyling `screen-idle`.

**Plate header.** Reuse the existing `.plate` component (done screen):

- Stamp line: `label-loop · new run`.
- Headline: "What do you want to see in your course's tutor chats?"
- Lede: short contract statement — your words become the label schema; a
  labeled sample comes back for review before anything is final.

**Two-column body.** Reuse the existing `.layout` flex pattern (stacks to one
column on narrow screens; peek rail moves below the writing surface).

- *Left, wider — writing surface.* The intent textarea grown to ~6 rows,
  placeholder in the "brief the labeler like you'd brief a TA — the more
  specific about what matters to you, the sharper the labels" voice. Below it,
  the primary button relabeled **"Draft labels from this →"** (same
  `/api/start` call as today).
- *Right — data peek rail.* Roughly 6 real student messages, stratified for
  diversity, each with a meta line giving the stratum in plain words (e.g.
  "short conversation · opening turn"). Rail header:
  `What students sounded like — 6 of N messages`, where N is the corpus
  message count from the peek fetch, plus a `resample` link-button (reuse the
  existing `linkButton` helper). Student text is rendered with `textContent`
  only, per the standing rule in the file.

**Run settings.** A native `<details>` element labeled "run settings" holding
the three existing number inputs (max conversations, sample size, seed),
collapsed by default, defaults unchanged (200 / 25 / 0).

## Data peek backend

New endpoint in `src/labeling/webapp.py`:

- `GET /api/peek?n=6&seed=<int>` — valid only in the `idle` phase (non-idle
  returns an error status; the frontend only calls it on the idle screen).
- Fetches a capped set of conversations (cap: 40) through the existing ingest
  path (read-only, through the tunnel), runs
  `src/labeling/sampler.py::stratified_sample` over them with the requested
  `n`, and returns: message text, human-readable stratum, and the message
  count over the fetched set (the N in the rail header).
- Resample calls the endpoint again with a fresh random seed.
- Peek data is display-only: never persisted, never part of any snapshot, and
  has no interaction with the run lifecycle. Starting a run performs its own
  full fetch exactly as today.

## Tunnel-down and edge behavior

- The peek slot doubles as a live tunnel check. States:
  - *Loading:* quiet "reading your course's chats…" line.
  - *Failure:* "Couldn't reach the chat logs — is `bin/tunnel` running?" with
    a retry link in the peek slot.
- The static tunnel footnote on the current idle screen is removed — the peek
  slot replaces it as a live status signal.
- The Start button stays enabled regardless of peek state; a failed start is
  still handled by the existing error screen.

## Not changing

Working, review, done, and error screens; run semantics and `/api/start`
payload; stratified sampling for the actual review loop; snapshot emission;
`elicit.py` and the drafting prompts.

## Testing

- Backend: webapp test for `/api/peek` — rejected outside `idle`, response
  shape (text / stratum / count), respects `n`, conversation fetch is capped.
- Frontend: manual verification by loading the app with the tunnel up (peek
  renders, resample works, run settings collapse/expand, start flow intact)
  and with the tunnel down (failure state + retry link).
