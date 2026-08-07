# Corpus-grounded labeling — Phase 1 design (branch `corpus-grounded-labeling`)

Direction memo: `docs/2026-08-07-corpus-grounded-curated-labeling.md`. Phase 1
builds the exploration pass, the CourseProfile v2 artifact, and layered
prompt assembly. Out of scope: webapp review screen, materials-upload UX
(materials enter as an optional CLI path argument), affect/intent layer
tuning beyond drafting, re-exploration versioning UX.

## Decisions this spec encodes (Minchan, 2026-08-07)

- Concepts are **hybrid**: by default a list-valued `concepts` facet on the
  coverage call (zero extra API calls, analytics-grade); any concept can be
  **promoted** in the artifact to a full label (own single-label call, own
  criteria, Phase-0-admissible, pays one call per message).
- Course materials are optional (`--materials <path>...`); corpus-only when
  absent; presence recorded in artifact provenance.
- Accept gate for Phase 1 is git review: the exploration CLI writes a draft
  artifact; the instructor edits/approves it and commits it. The webapp
  skim-and-accept screen is Phase 2.

## 1. CourseProfile v2 artifact

New module `src/labeling/profile2.py`:

- `ConceptDef`: `name`, `description`, `aliases: list[str] = []`,
  `promoted: bool = False`, and (required when promoted)
  `positive_criteria` / `negative_criteria`.
- `CourseProfileV2`: embeds the six v1 `CourseProfile` fields verbatim
  (composition: `base: CourseProfile`), plus `concepts: list[ConceptDef]`,
  `affect_labels: list[LabelDef]`, `intent_labels: list[LabelDef]`, and
  provenance: `explored_on` (ISO date), `corpus_sample: {conversations,
  seed}`, `materials_provided: bool`, `repo_sha`, `accepted: bool = False`.
- `canonical()` / `profile_id` (sha256[:12] of canonical, like v1) /
  `render_context()` (v1 rendering + a "Course concepts:" block naming the
  taxonomy).
- Storage: **git-tracked** `profiles/<slug>.json` at repo root (unlike
  gitignored per-run schemas — a profile is course-level, reviewed, and
  rule-4-safe by construction). Draft artifacts are written as
  `profiles/<slug>-draft.json`; acceptance = instructor edits, sets
  `accepted: true`, renames to `profiles/<slug>.json`, commits.
- Rule-4 guard: `lint_profile(profile, conversations) -> list[str]`
  flags any profile string sharing a verbatim run of ≥8 consecutive words
  with any student turn in the explored sample; the CLI refuses to write a
  draft with lint findings. Distilled descriptions only.

## 2. Exploration pass

New module `src/labeling/explore.py` + CLI entry
(`python -m src.labeling.explore --course-slug dsc10 --sample 150 --seed 0
[--materials path ...]`):

- Fetches `--sample` conversations via the existing tunnel path; renders a
  bounded digest (per-conversation: notebook name, student-turn count, and
  length-stratified excerpts of student turns — excerpts go INTO the prompt,
  never into the artifact).
- Reads optional materials files as plain text, truncated per-file.
- One `EXPLORE_PROMPT` Gemini call (wire model = the artifact draft minus
  provenance) instructing: derive the six profile fields; enumerate a
  concept taxonomy of what the course demonstrably teaches (seed from
  materials when given, else from curricular artifacts in the chats; refine
  by what students discuss); draft affect and intent label layers whose
  criteria are judgeable on messages as they actually occur (median 23
  chars, often pasted or deictic — reuse the ELICIT judgeability
  constraint); never quote student text — distilled descriptions only.
- Fills provenance, runs `lint_profile`, writes
  `profiles/<slug>-draft.json`, prints a review summary and next-step
  instructions (edit → accepted:true → rename → commit).
- Exploration is never invoked at labeling time (rule 2); the CLI is the
  only caller.

## 3. Layered prompt assembly (classification path)

`src/labeling/draft.py`:

- `CoverageVerdict` gains `concepts: list[str] = []` (declared after
  `forms`); `COVERAGE_PROMPT` gains a concept-taxonomy block (names +
  descriptions of NON-promoted concepts) and an instruction to list every
  concept the student message engages. Hallucination-filtered against the
  taxonomy; lands on `MessageLabels.concepts: list[str] = []` (defaulted —
  old snapshots parse).
- Schema composition at run start (new helper `compose_schema(v2, instructor
  LabelSchema) -> LabelSchema`): promoted concepts become `LabelDef`s (kind
  `"conceptual"`), accepted affect/intent labels append as drafted (kind
  `"behavioral"`), instructor labels ride on top; name collisions are an
  error. The composed schema version-chains from the instructor schema so
  invariant 6 is untouched.
- `classifier_hash` gains the v2 canonical (when a v2 profile is in use) and
  the non-promoted taxonomy rendering — same \x1e-join discipline, golden
  test updated. A v1-only run hashes exactly as today (backward compatible;
  no re-vintage of existing behavior).
- CLI (`cli.py`) gains `--profile profiles/<slug>.json`; refuses a draft or
  `accepted: false` artifact. Webapp wiring deferred to Phase 2.

## 4. Testing (TDD, offline fakes)

1. Artifact round-trip: v2 model serializes/parses; `profile_id` stable;
   `accepted: false` rejected by the classify path.
2. Lint: a profile string containing an 8-word verbatim run from a fixture
   conversation is flagged; distilled text passes.
3. Exploration prompt: contains materials text when given, corpus digest
   always, judgeability constraint always; artifact provenance records
   `materials_provided` correctly; lint failure blocks the write.
4. Coverage call: concepts block lists non-promoted concepts only; verdict
   concepts filtered to taxonomy; land on `MessageLabels.concepts`.
5. Composition: promoted concept becomes a single-label call; collision with
   an instructor label name raises; composed schema chains parent version.
6. Hash: v2 profile changes hash; taxonomy edit changes hash; v1 path's
   golden unchanged.
7. No student text: exploration fixture asserts the written artifact
   contains no fixture-turn verbatim runs (reuses lint).

## Non-goals restated

No webapp changes, no embeddings, no affect/intent validation (they are
drafts until audited), no re-exploration flow, no materials storage (read at
explore time, only a boolean + digest recorded).
