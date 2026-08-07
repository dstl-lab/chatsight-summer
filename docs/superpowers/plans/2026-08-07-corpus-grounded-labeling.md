# Corpus-Grounded Labeling Phase 1 Implementation Plan

> **For agentic workers:** executed inline this session (lead-only git policy:
> the session implements and tests; the lead commits at each checkpoint).
> Spec: `docs/superpowers/specs/2026-08-07-corpus-grounded-labeling-phase1-design.md`.

**Goal:** Exploration pass → versioned CourseProfile v2 artifact → layered
prompt assembly (concepts facet + promoted/accepted label composition).

**Tech stack:** Python 3.12, pydantic, existing `Generate` injection; tests
offline via fakes; `uv run python -m pytest`.

## Global constraints

- No verbatim student text in any artifact: `lint_profile` (≥8-word shared
  run) gates every artifact write.
- Exploration never runs at labeling time; `accepted: false` profiles are
  refused by the classify path.
- All new `MessageLabels`/wire fields default (old snapshots parse).
- v1-only runs keep today's `classifier_hash` (golden untouched); v2 runs
  extend the canonical string.
- Tasks 3–4 require the branch rebased onto main (form facet present).

## Task 1: CourseProfile v2 artifact (`src/labeling/profile2.py`)

Files: create `src/labeling/profile2.py`, `tests/test_profile2.py`.
Produces: `ConceptDef(name, description, aliases=[], promoted=False,
positive_criteria="", negative_criteria="")` (criteria required iff
promoted — model_validator); `CourseProfileV2(base: CourseProfile,
concepts, affect_labels, intent_labels, explored_on, corpus_sample:
{conversations:int, seed:int}, materials_provided: bool, repo_sha: str,
accepted: bool=False)` with `canonical()`, `profile_id`,
`render_context()` (v1 rendering + "Course concepts:" name list);
`lint_profile(v2, conversations) -> list[str]` flagging any artifact string
sharing ≥8 consecutive words with any student turn; `load_profile(path)` /
`save_profile(v2, path)`.
Tests: round-trip + stable profile_id; promoted-without-criteria rejected;
lint catches an 8-word run from a fixture turn, passes distilled text;
render_context carries v1 fields + concept names.
Checkpoint commit: `feat: CourseProfile v2 artifact with concept taxonomy and rule-4 lint`

## Task 2: Exploration pass (`src/labeling/explore.py`)

Files: create `src/labeling/explore.py`, `tests/test_explore.py`.
Produces: `EXPLORE_PROMPT`; `ExplorationDraft` wire model (v2 minus
provenance: the six v1 fields flattened + concepts + affect_labels +
intent_labels, list-typed only — no dicts); `build_digest(conversations,
per_conv_excerpts)` length-stratified digest (excerpts prompt-only);
`explore(conversations, materials_texts, generate, *, sample_meta,
repo_sha) -> CourseProfileV2` (fills provenance, materials_provided);
`main()` argparse CLI: `--course-slug --sample --seed --materials...`,
fetch via existing tunnel path, lint-gate, write
`profiles/<slug>-draft.json`, print review/accept instructions. Prompt
carries: derive profile fields; concept taxonomy seeded from materials else
curricular artifacts in chats, refined by what students discuss; affect +
intent layers with terse-message judgeability constraint (reuse ELICIT
wording); distilled descriptions only, never quote student text.
Tests: prompt contains materials text when given / digest always /
judgeability constraint always; provenance fields set; lint failure blocks
the write (tmp_path); wire model has no dict fields.
Checkpoint commit: `feat: corpus exploration pass emitting CourseProfile v2 drafts`

## Task 3: concepts facet on the coverage call (`src/labeling/draft.py`)

REQUIRES REBASE. Files: modify `src/labeling/draft.py`,
`tests/test_draft.py`.
Produces: `CoverageVerdict.concepts: list[str] = []` (after `forms`);
`COVERAGE_PROMPT` gains `{concept_block}` (name: description lines for
NON-promoted concepts; empty→"(none)") + instruction to list engaged
concepts; verdict concepts filtered to taxonomy;
`MessageLabels.concepts: list[str] = []`; `draft_labels(...,
profile2: CourseProfileV2 | None = None)` threads the block;
`classifier_hash(schema, model, profile, profile2=None)` appends
`profile2.canonical()` + rendered concept block iff profile2 — v1 golden
literal unchanged, new v2 hash test.
Tests: concepts land filtered/defaulted; non-promoted only in block;
v1 golden byte-identical; v2 hash moves when taxonomy edits.
Checkpoint commit: `feat: course-concept facet on the coverage call`

## Task 4: composition + CLI gate (`src/labeling/profile2.py`, `src/labeling/cli.py`)

REQUIRES REBASE. Files: modify both + `tests/test_profile2.py`,
`tests/test_cli.py`.
Produces: `compose_schema(v2, instructor_schema) -> LabelSchema` — promoted
concepts → LabelDef(kind="conceptual"), affect/intent labels appended
(kind="behavioral"), collision → ValueError, result chains
`parent_version=instructor_schema.version_id`,
`feedback_applied="composed with profile <profile_id>"`; `cli.py`
`--profile path` → load, refuse `accepted: false` (exit with message),
pass profile2 into both `draft_labels` calls and compose before labeling.
Tests: composition kinds/chaining/collision; CLI refuses unaccepted;
accepted profile threads through (fake generate sees concept block).
Checkpoint commit: `feat: layered schema composition and --profile gate`
