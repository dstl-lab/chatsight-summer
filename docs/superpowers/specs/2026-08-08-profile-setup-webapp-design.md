# Phase 2: instructor-facing course-profile setup in the label-loop webapp

Date: 2026-08-08. Implements Phase 2 of the corpus-grounded curated-labeling
memo (`docs/2026-08-07-corpus-grounded-curated-labeling.md`): the webapp
gains the explore → skim-and-accept flow, replacing the edit-JSON-by-hand
accept gate, and the label-loop finally runs the CourseProfile v2 path the
CLI already has.

## Decisions (made with Minchan, 2026-08-08)

- Entry point: the **idle screen** of the existing label-loop webapp — one
  server, one flow. Not a separate page or server.
- Accept screen power: **skim + toggle + delete.** Instructor can delete
  entries and toggle a concept's `promoted` flag; no free-text editing
  (wording changes belong to the tweak loop; the memo decided against
  hand-curated rubrics).
- Accept persistence: **the screen is the gate.** Accept writes
  `profiles/<slug>.json` with `accepted:true` (lint-gated) and the session
  uses it immediately; git commit happens with the next repo commit.
- Materials: **browser file picker, text only** (.txt/.md, multiple files),
  held in memory for the exploration call only.

## Flow

The idle screen gains a course-profile panel with three states:

1. **No accepted profile** → "Set up this course": course-slug field,
   optional materials picker, Explore button. Runs `explore()` on a corpus
   sample through the tunnel with step progress (like start/accept today).
   The draft is held in the session and also written to
   `profiles/<slug>-draft.json` (lint-gated), as the CLI does.
2. **Draft ready** → review screen: concepts / affect / intent layers in
   their layer colors, each entry showing name, description, criteria, with
   a delete control per entry and a promote toggle per concept. One
   **Accept profile** button. **Re-explore** discards the draft and runs a
   fresh exploration.
3. **Accepted profile** → one-line banner ("Course: DSC 10 · profile
   `a5241ab…` · 11 concepts · 2 promoted") with a Re-explore affordance.
   The normal intent box is active below it; every run uses `profile2`
   (composed schema, concepts section in the coverage prompt) exactly like
   the CLI v2 path.

## Accept semantics

Accept applies deletes/toggles via `model_copy(update=...)` — deterministic
surgery, no LLM call — then sets `accepted=True`, runs `lint_profile`, and
writes `profiles/<slug>.json`. Any surgery producing a name collision in
`compose_schema` or a lint finding rejects the accept with the reason shown;
the draft stays reviewable.

## Server/session changes

- `LoopSession` gains phases `exploring` and `profile_review`, both
  reachable only from `idle`; a `profile2_draft: CourseProfileV2 | None`
  field; and a `profile2` field threaded into `draft_labels`,
  `classifier_hash`, and `emit_snapshot` (manifest records `profile2_id`).
- Endpoints:
  - `POST /api/explore` — JSON body: `slug`, optional `materials` list of
    `{name, text}` read client-side via FileReader (avoids the
    python-multipart dependency). Materials text goes into the exploration
    prompt and is then dropped; never written to disk, never echoed in any
    response.
  - `GET /api/state` — extended with a `profile` block: phase-appropriate
    draft layers (name/description/criteria/kind/promoted) or the accepted
    summary (slug, profile_id, counts).
  - `POST /api/profile/accept` — body: list of deleted entry names per
    layer + list of promoted concept names.
  - `POST /api/profile/reexplore` — from `profile_review` or from idle
    with an accepted profile; runs a fresh exploration.
- Startup: `--course <slug>` flag (default `dsc10`); if
  `profiles/<slug>.json` exists and is accepted, load it as `profile2`.

## Rule-4 handling

Materials live in session memory only for the duration of the exploration
call. Drafts and accepted profiles pass `lint_profile` before every write
(no ≥8-word verbatim student runs). Server stays 127.0.0.1-only.

## Testing

Session-level tests with fake `generate`/`fetch` (existing webapp test
pattern):

- explore → profile_review → accept happy path; accepted file on disk,
  session labels with the composed schema.
- delete + promote surgery is deterministic and collision-checked.
- accept refuses when lint fires or composition collides; phase stays
  `profile_review`.
- phase guards: no `start` during `exploring`/`profile_review`; no
  `explore` outside `idle`.
- state payload never contains materials text.
- startup with an accepted profile: snapshot manifest carries
  `profile2_id`; classifier hash includes `profile2.canonical()`.

Finish with one live end-to-end Chrome pass against the real DB.

## Out of scope (YAGNI)

Inline wording edits, PDF/notebook parsing for materials, multi-course
switching in one session, re-exploration diffing.
