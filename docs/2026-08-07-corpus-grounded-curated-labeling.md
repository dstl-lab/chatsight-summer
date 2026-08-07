# 2026-08-07 — Corpus-grounded curated labeling: layered facets from an automated exploration pass

Status: **direction adopted, not yet built.** Follows the 2026-08-06
label-quality pilot's finding that a one-sentence intent produces generic
labels and an 11% abstention rate. Design decisions below were made by
Minchan 2026-08-07; implementation belongs to a future branch.

## Problem

Today the entire label schema is compiled from one instructor sentence. That
sentence must carry every facet at once — domain concepts, affect, intent,
behavior — so the drafted labels come out as generic verbs
("asks-for-answer", "pastes-error") regardless of course. Meanwhile the
knowledge that would sharpen them already sits in the corpus: what the course
teaches, what students actually paste, how they reference work. The pilot's
32-message abstention pile is the measurable symptom.

## Direction

A pipeline that grounds the labeling prompt in the course data before the
instructor ever types:

1. **Ingest** course AI-tutor data (existing tunnel/fetch path). Course
   materials (syllabus, notebooks) are an **optional instructor upload**
   (decision 2026-08-07): when absent, the exploration pass works from the
   corpus alone, including curricular artifacts students paste into chats.
2. **Exploration pass**: an LLM reads a sample of the corpus plus any
   uploaded materials and emits a structured **CourseProfile v2**: today's
   six profile fields plus a course-concept taxonomy and drafted baseline
   facet layers.
3. **Curated prompt generation**: the profile compiles into labeling
   instructions covering three standing layers —
   - **curricular**: concept labels for what the course teaches (for an OOP
     course: loops, inheritance, visibility; for DSC 10: babypandas
     idioms, histograms, hypothesis testing),
   - **affect**: student sentiment/emotion labels,
   - **intent**: generic help-seeking intent labels —
   layered on the **mechanical** forms facet already shipped (2026-08-06).
4. **Instructor gate**: the generated layers are shown as a pre-checked
   review screen; one skim-and-accept before the first run (decision:
   skim+accept, not always-on and not fully hand-curated — keeps the
   top-down invariant at minimal friction).
5. **Instructor intent layer**: the instructor's own question compiles into
   decision-specific labels exactly as today, now layered on the baseline
   instead of carrying all coverage alone.
6. **Combined system prompt** = profile context + accepted layers;
   instructor labels ride on top. The coverage call's abstention channel
   then only needs to catch what every layer misses.

**Concept-taxonomy source (decision):** chats + materials — seeded from
uploaded materials when provided, otherwise from curricular artifacts
appearing in the corpus, and refined by what students actually discuss.
Concepts nobody chats about don't earn labels; concepts students avoid can
still surface in analytics as conspicuously-absent.

## Invariants, restated for this design

- **Provenance (rule 2):** the exploration pass runs once and emits a
  versioned, reviewed, hashed artifact. Labeling-time calls never invoke
  exploration; CourseProfile v2 joins the classifier hash exactly as v1's
  canonical()/render_context() do today. A re-explored profile is a new
  classifier. Whether materials were provided is part of the artifact's
  provenance.
- **Top-down principle:** generated layers are drafts; the accept gate is
  where they become instructor-compiled. Acceptance stays a drafting
  decision; reliability still comes only from blind audit (invariant 8), and
  per-label admission to the simulation state space still goes through the
  Phase 0 gate. Nothing here creates a bottom-up emergent-taxonomy path.
- **Rule 4:** the exploration artifact contains distilled descriptions
  (concept names, conventions), never verbatim student text, so it can live
  in git next to schemas. Uploaded course materials are instructor-owned
  content and stay out of git like student data unless the instructor says
  otherwise.

## Why layers, not more labels in one flat set

The pilot showed the flat set forces a trade: instructor specificity vs.
facet coverage. Layers give each facet its own budget and its own
reliability standard — mechanical forms are near-free, concept labels are
low-inference, affect labels are high-inference and rare (frustration fired
4/299) and may only ever be analytics-grade. Per-label admission thresholds
(open decision #1) already accommodate exactly this spread.

## Open questions for the implementation branch

- Exploration sample size and cost; upload UX for optional materials.
- Affect layer honesty: median 23-character messages rarely evidence
  emotion; the layer must inherit the pilot's lesson (criteria judgeable on
  terse messages, else abstain).
- Concept granularity: per-concept labels vs one concept-mention label with
  a concept *field* (list-valued, like forms).
- Where the review screen lives in the webapp flow, and how re-exploration
  (new quarter, new course) versions the profile chain.
