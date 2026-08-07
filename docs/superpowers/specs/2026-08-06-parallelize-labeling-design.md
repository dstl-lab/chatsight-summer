# Parallelize labeling — Phase 1 design (branch `parallelize-labeling`, issue #1)

Direction memo: `docs/2026-08-06-parallel-labeling-live-schema-growth.md`. This spec
covers Phase 1 only: the parallel executor and live abstention surfacing. Phase 2
(label proposal / approval / backfill / composite provenance) is a follow-up branch.

## Scope

In: `src/labeling/draft.py`, `src/labeling/cli.py`, `src/labeling/webapp.py` (+ its
static UI), `src/config.py`, tests.
Out: any prompt change, any schema/snapshot format change, Phase 2 features.
`classifier_hash` inputs are untouched — concurrency is not provenance.

## 1. Parallel executor (`draft.py`)

`draft_labels(messages, schema, profile, generate, on_progress=None, on_result=None,
workers: int = 8)`:

- `ThreadPoolExecutor(max_workers=workers)`; one task per message. Each task builds
  the prompt and calls `generate` exactly as today (`with_retries` already wraps it,
  per-call state is local, so retry behavior is unchanged and thread-safe).
- Results are written into a pre-sized list by input index; the returned list order
  equals input order regardless of completion order.
- A single internal lock guards the completed-count; `on_progress(done, total)` is
  called with a strictly increasing `done` ending at `total`. `on_result(m, result)`
  fires per completion, any order (webapp already locks and keys by
  `(chatlog_id, message_index)`).
- Error semantics: first task exception (i.e. after `with_retries` exhausts its 4
  attempts) stops submission of remaining tasks, in-flight tasks finish and deliver
  their `on_result`, then the original exception is re-raised. Net: run aborts,
  finished work survives, webapp resumes from its done-set — same contract as the
  sequential version.
- `workers=1` must behave observably identically to today's sequential loop
  (escape hatch + test baseline).

The google-genai sync client is a stateless HTTP wrapper; concurrent
`generate_content` calls from multiple threads are safe.

## 2. Configuration

- `src/config.py`: `labeling_workers: int = 8`, env-overridable
  (`LABELING_WORKERS`), following the existing settings pattern.
- CLI: `--workers` flag on the labeling entry points, defaulting from settings.
- Webapp wiring passes the settings value through to both the review-sample and
  mass-label `draft_labels` calls.

## 3. Live abstention surfacing

- **Webapp, during `mass_labeling`:** state exposes a running abstention count and
  the abstained messages accumulated so far (derived from `on_result` payloads —
  `r.no_label_fits`); the mass-labeling screen shows "N abstentions so far" with the
  abstained messages viewable, updating live like the existing recent-results feed.
- **Webapp, `done` phase:** the summary carries a coverage report: abstention count,
  rate, and the abstained messages (summary.py's existing abstained-messages
  machinery reused/extended for the full corpus rather than the review sample).
- **CLI mass-label path:** prints the same coverage summary after the run
  ("N of M messages (X%) showed acts no label captures").
- No snapshot format change: `no_label_fits` is already persisted per message.

## 4. Testing (TDD, offline fake `generate`)

1. **Concurrency is real:** fake `generate` blocks on a `threading.Barrier(k)`
   (k ≤ workers); the run completes only if k calls are truly in flight.
2. **Order:** scrambled completion (per-message artificial delays) → returned list
   is in input order.
3. **Progress:** `done` values strictly increase and end at `total`.
4. **Failure:** one poisoned message → run raises; `on_result` deliveries for
   completed messages survived; no further submissions after the failure.
5. **Sequential parity:** `workers=1` produces byte-identical results and callback
   sequence to the pre-change behavior.
6. **Abstention feed:** webapp state reflects live abstention count during
   mass_labeling and the coverage report at done; CLI summary line asserted.
7. Thread-tolerance of existing fake-generate fixtures (call-order assumptions
   removed where they exist).

## Non-goals / guardrails restated

- Schema frozen per run; no label creation anywhere in Phase 1.
- No change to prompt, wire models, snapshot manifest, or `classifier_hash`.
- Default `workers=8` assumes paid tier; free-tier users set `LABELING_WORKERS=2`.
