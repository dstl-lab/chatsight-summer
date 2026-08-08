# Context-timing labels — design (branch `context-timing-labels`)

Approved 2026-08-07. Two constructs: a mechanical per-message timing facet
(computed from DB timestamps, never LLM-judged) and a judged discourse-move
facet on the coverage call. Both are injected context for every label call.

## 1. Ingest (`src/ingest/rawlog.py`)

- `_TURNS_SQL` selects `created_at`; `assemble_turns` rows become
  `(event_type, question, response, created_at)`; `Turn.at: datetime | None
  = None` (defaulted — old snapshots parse).

## 2. Timing facet (`src/labeling/sampler.py`)

- `LATENCY_BUCKETS`: `conversation-opening` (no preceding tutor turn),
  `rapid` (<2 min), `working` (2–30 min), `delayed` (30 min–6 h),
  `returned` (>6 h), `unknown` (timestamps missing). Thresholds are module
  constants (`RAPID_S = 120`, `WORKING_S = 1800`, `DELAYED_S = 21600`).
- `SampledMessage.latency_seconds: float | None = None`,
  `.latency_bucket: str = "unknown"` — computed in `_context`/sampling from
  the nearest preceding tutor turn's `at` to the target turn's `at`.

## 3. Prompt injection + move facet (`src/labeling/draft.py`)

- `_SHARED_CONTEXT` gains a line before STUDENT MESSAGE:
  `Time since the tutor's last message: {latency}` where `{latency}`
  renders e.g. `4 minutes (working)`, `(conversation opening)`,
  `(unknown)`. Template change ⇒ new classifier vintage (both templates).
- `MOVE_TAXONOMY = ("responds-to-tutor", "initiates-new-topic",
  "continues-own-thread")`; `CoverageVerdict.move: str = ""` (single-valued
  discourse position), prompt instruction after concepts; filtered against
  taxonomy (else "").
- `MessageLabels` gains `move: str = ""`, `latency_seconds: float | None =
  None`, `latency_bucket: str = ""` (mechanical copy-through from the
  SampledMessage at assembly).
- `classifier_hash`: templates already pinned; add
  `"latency=" + bucket spec string` and `"move=" + ",".join(MOVE_TAXONOMY)`
  to the canonical. Golden literal refreshed (intentional re-vintage: the
  injected line changes every rendered prompt).

## 4. Tests

1. rawlog: `assemble_turns` carries `at`; missing timestamps → None.
2. sampler: bucket boundaries (0s/119s/121s/29min/31min/7h), opening turn,
   missing timestamps → unknown; follows-own-message measured from the
   tutor turn before it.
3. draft: latency line present in BOTH templates' rendered prompts; move
   lands filtered/defaulted; hash covers taxonomy + thresholds; golden
   refreshed.
4. Old-snapshot compat: `MessageLabels`/`Turn` parse without new fields.

## Non-goals

No webapp UI; no latency-conditioned labels (promotion path exists via
criteria later); no backfill of timestamps into old snapshots.
