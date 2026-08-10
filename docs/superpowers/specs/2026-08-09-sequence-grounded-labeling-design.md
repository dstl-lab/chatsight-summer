# Sequence-grounded labeling — design

Date: 2026-08-09. Branch: `behavioral-sequences`. Builds on
`src/ingest/sequences.py` (pilot) and the findings in
`docs/2026-08-09-sequence-pilot-first-numbers.md`. Approved by Minchan
("Let's do this", all five in one branch).

## Goal

Use what actually lies in `events` — autograder runs, at-ask notebook
snapshots, the tutor/chatgpt toggle, question-number references — to make
labels context-aware and to move mechanically-decidable labels out of the
LLM entirely.

## The five pieces

### 1. Sequence context injected into every classifier call

- New per-message `SequenceContext`: pre-chat pattern (`ask-first` /
  `fail-then-ask` / `pass-then-ask`), minutes since last autograder run,
  its grader_id and success, and whether the at-ask snapshot contains a
  traceback. Computed at sampling time (ingest layer owns the DB join,
  rule 3) and carried on `SampledMessage` like latency is today.
- Rendered into `_SHARED_CONTEXT` alongside latency:
  `"Autograder state when the student asked: last run 4m before this
  message: FAILED (q3_2). Notebook shows an unresolved traceback."`
  Absent data renders as `"No autograder activity in the 45 min before
  this message."`
- `classifier_hash` covers the new rendering (provenance, rule 2).
  Golden-hash tests re-vintage once, with comment.
- The ablation probe gains a `strip_sequence` axis so the effect is
  measurable (context-awareness instrument).

### 2. Mechanical facets — logged facts, not LLM verdicts

Recorded on `MessageLabels` as facts (never sent to Gemini, never
audited, precision 1.0 by construction):

- `mode`: `tutor` | `chatgpt` (from tutor_query payload).
- `defected`: true on the first chatgpt-mode message following a
  tutor-mode message by the same student in the same conversation.
- `attempted`: pre-chat pattern != ask-first.
- `error_verified`: traceback present in at-ask snapshot or last
  autograder run failed — the mechanical check behind pastes-error.

LLM labels keep judging what they judge; overlap is measured, not
assumed: `error_verified` vs the LLM's pastes-error becomes a standing
consistency check in the validation table (disagreement rows are audit
candidates, not auto-corrections — invariant 1: humans stay the judge).

### 3. Mode-aware criteria and reporting

- `mode` joins the shared context block ("The student is in plain-ChatGPT
  mode — no tutor persona").
- `distinctness_report` and the validation table split per-label counts
  by mode so tutor-mode and chatgpt-mode reliability are never averaged
  silently.

### 4. Question linkage from reference conventions

- Deterministic extractor (regex family for "3.2", "q3_2", "question 3",
  from `reference_conventions`) over the message text → `question_ref`.
  No LLM call.
- Where a `question_ref` exists, the sequence join narrows from
  notebook-level to grader-level (`grader_id` startswith normalized ref):
  `pass-then-ask` then means *this question's* tests were passing.
  Fallback stays notebook-level, and the context line says which
  granularity it used.
- Measured, not assumed: report extraction coverage (% of messages with
  a ref) per notebook.

### 5. Sequence-stratified review sampling

- `stratified_sample` gains sequence strata: ask-first→no-run-after,
  fail-then-ask, mode-switch conversations are deliberately represented
  (invariant 9), alongside the existing tercile/position strata.
  Composition ratios configurable; strata recorded per message
  (server-side only in audits, invariant 8).

### Validation win (rides along)

`validation.py` gains an outcome-anchor check: for labels with a
directional expectation (answer-extraction ⇒ concentrates in
fail→quick-pass), report the concentration ratio. A label violating its
anchor is flagged for audit, never auto-relabeled.

## Data flow and boundaries

- All DB joins live in `src/ingest/` (sequences.py grows; sampler calls
  it). `user_email` never leaves the join; snapshots contribute only
  derived booleans (traceback present) — raw notebook JSON never enters
  a snapshot artifact or prompt (rule 4).
- Snapshot manifests record the sequence-context parameters (windows,
  granularity) as part of provenance.
- Everything downstream (eval, trajectories) keeps consuming snapshots
  only.

## Testing

Unit tests per piece with fake DB rows (no tunnel in tests): context
rendering incl. absent-data lines; mechanical facet derivation incl.
defection edge cases (chatgpt-first conversations never "defect");
question-ref extractor against DSC 10 reference shapes; grader-narrowing
join; sampler strata composition; hash re-vintage golden; ablation
strip_sequence flips. One live smoke run at the end (small corpus,
sequence context visibly in prompts via a debug dump, distinctness +
mode-split report printed).

## Out of scope (YAGNI)

Webapp UI for sequence facets, re-labeling old snapshots, external-tool
defection inference, notebook-diff copy-detection scoring (needs its own
design), question-ref via LLM fallback.
