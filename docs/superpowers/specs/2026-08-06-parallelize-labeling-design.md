# Parallelize labeling — Phase 1 design (branch `parallelize-labeling`, issue #1)

Direction memo: `docs/2026-08-06-parallel-labeling-live-schema-growth.md`. This spec
covers Phase 1 only: the single-label call architecture, the parallel executor, and
live abstention surfacing. Phase 2 (label proposal / approval / backfill, likely
embedding-clustered proposals) is a follow-up branch.

## Scope

In: `src/labeling/draft.py`, `src/labeling/cli.py`, `src/labeling/webapp.py` (+ its
static UI), `src/config.py`, tests.
Out: snapshot manifest format changes beyond the new hash value, Phase 2 features,
embeddings.
`MessageLabels` (the per-message record: labels, rationales, no_label_fits) is
unchanged, so snapshot rows and downstream consumers are untouched.

## 1. Single-label prompts (`draft.py`)

Replaces `CLASSIFY_PROMPT`. Both new prompts carry over the redesign memo's
CourseProfile preamble, ~6-turn context window, and judgment rules verbatim in
spirit (act-not-surface, pasted-material rule, short-message inheritance,
unjudgeable→false).

- **`SINGLE_LABEL_PROMPT`**: course context + context window + student message +
  tutor reply after + ONE label (name, description, positive/negative criteria) →
  wire model `{applies: bool, rationale: str}`.
- **`COVERAGE_PROMPT`**: same context + ALL labels (name + description only) →
  wire model `{no_label_fits: bool, note: str}` — `note` is one sentence describing
  the uncaptured act when abstaining, empty otherwise. It describes, never names
  (redesign memo rule). Runs for EVERY message, not only all-false ones: partially
  captured messages (one act labeled, another not) are exactly the ones conditional
  firing would miss.

`MessageLabels` gains `coverage_note: str = ""` (defaulted, so old snapshots still
parse). Hallucination guard: single-label calls can no longer hallucinate label
names; a malformed/missing verdict for a label defaults to
(False, "(no verdict returned)") as today.

## 2. Provenance (`classifier_hash`)

New canonical string over: both templates, schema version (pins every label's
definition), model, profile canonical + rendered, window parameters, and the
window-rendering probes — same \x1e-join discipline. One run-level hash (schema is
frozen in Phase 1); per-label hashes arrive with Phase 2. Any snapshot produced by
this code is a new vintage; not comparable to block-era snapshots (invariant 6).

## 3. Parallel executor (`draft.py`)

`draft_labels(messages, schema, profile, generate, on_progress=None, on_result=None,
workers: int = 8)`:

- Unit of work: one call — (message, label) verdict or (message) coverage —
  (N_labels + 1) × M tasks on a `ThreadPoolExecutor(max_workers=workers)`. Each
  task calls `generate` exactly as today (`with_retries` wraps it; per-call state is
  local, so retries are unchanged and thread-safe; the google-genai sync client is a
  stateless HTTP wrapper, safe across threads).
- A message's `MessageLabels` assembles when all its calls land; `on_result(m, r)`
  fires per completed MESSAGE, any order (webapp already locks and keys by
  `(chatlog_id, message_index)`). `on_progress(done, total)` counts completed
  messages, strictly increasing to total, lock-guarded.
- Returned list is in input message order regardless of completion order.
- Error semantics: first task exception (after `with_retries` exhausts its 4
  attempts) stops submission of remaining tasks; in-flight tasks finish; messages
  whose calls all completed still deliver `on_result`; then the original exception
  re-raises. Net: run aborts, finished messages survive, webapp resumes from its
  done-set. Partially-called messages are discarded (their calls re-run on resume).
- `workers=1` executes strictly sequentially (escape hatch + test baseline).

## 4. Configuration

- `src/config.py`: `labeling_workers: int = 8`, env-overridable
  (`LABELING_WORKERS`), following the existing settings pattern.
- CLI: `--workers` flag defaulting from settings; webapp passes the settings value
  to both the review-sample and mass-label `draft_labels` calls.

## 5. Live abstention surfacing

- **Webapp, during `mass_labeling`:** state exposes a running abstention count and
  the abstained messages so far with their coverage notes (derived from `on_result`
  payloads), shown live like the existing recent-results feed.
- **Webapp, `done`:** summary carries a coverage report — abstention count, rate,
  abstained messages + notes (summary.py's abstained-messages machinery extended to
  the full corpus, not just the review sample).
- **CLI mass-label path:** prints the same coverage summary after the run.

## 6. Testing (TDD, offline fake `generate`)

1. **Fan-out shape:** M messages × N labels → exactly (N+1)×M generate calls, each
   single-label prompt containing exactly one label's criteria; coverage prompt
   containing all label names.
2. **Concurrency is real:** fake `generate` blocks on a `threading.Barrier(k)`
   (k ≤ workers); the run completes only if k calls are truly in flight.
3. **Order:** scrambled completion (artificial per-call delays) → returned list in
   input order; assembled labels/rationales/coverage_note per message correct.
4. **Progress:** `done` strictly increases, counts messages, ends at total.
5. **Failure:** one poisoned call → run raises; `on_result` for fully-completed
   messages survived; no submissions after failure; partially-called messages
   absent from results.
6. **Sequential parity:** `workers=1` runs strictly sequentially with identical
   assembled output.
7. **Hash:** classifier_hash changes vs. old code; is stable across runs; changes
   when either template, window, model, profile, or schema version changes.
8. **Abstention feed:** webapp state shows live abstention count + notes during
   mass_labeling and the coverage report at done; CLI summary line asserted.

## Non-goals / guardrails restated

- Label set frozen per run; no label creation anywhere in Phase 1.
- Coverage call always runs; embeddings nowhere in Phase 1; embedding-based
  call-skipping is rejected outright (memo).
- Default `workers=8` assumes paid tier; free-tier users set `LABELING_WORKERS=2`.
