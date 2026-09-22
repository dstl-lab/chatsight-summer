# Work-presence forecast: implemented, private run awaiting approval

**TL;DR:** The separate forecast helper is implemented and tested. Eight fixed
requests reuse already coded references, so no new labeling is needed. Automatic
approval review rejected dispatch before process creation; zero requests were
sent. The existing simulator is unchanged.

The [advance protocol](2026-09-22-work-presence-forecast.md) is frozen with the
run's inputs and code. Its checklist records intended work at preparation time;
this document supplies the subsequent status without rewriting that protocol.
The helper returns a strictly validated probability that the first next recorded
student message contains work, conditional on another message being recorded.
It uses the existing future-excluding dialogue projection, removes identifiers,
and uses the same work definition as the completed review.

## Verified preparation

Private artifacts are in `data/episode-pilot/work-presence-forecast-v1/`:
`scope.json`, `jobs.json`, `references.json`, `joins.json`, `baseline.json`,
`study.py`, `check.py` and `approval-block.json`. Exact prompts and all private
reference labels stay ignored. An independent audit verified all **69 pins**,
36 visible turns, eight source/label joins, rubric identity, and the exclusion
of future messages and metadata from prompts. All learner identities remain
unknown, and the eight conversation keys are distinct.

Preparation initially rejected a raw prompt equality assertion: historical
prompts used anonymous IDs and additional fixed unknown-state fields. Before
freezing, the assertion was corrected to compare every visible role and numbered
line, followed by a separate comparison with the exact reviewed prefixes. No
historical input or label changed.

On the declared 0–2 multiclass Brier scale, the all-reference baselines are
**0.612245** for leave-one-conversation-out frequency, **0.5** for constant 50/50,
and **0.75** for always no work. These are baselines only; no model score exists.
The authored arithmetic check retains errors/missing forecasts as separate rows
and blocks advancement without full coverage. The runner reserves dispatch before
calls, refuses a second dispatch, and preserves flushed request/retry/result events.

Validation: **442 tests pass**, three optional container skips, one existing
Starlette/httpx warning. Both Marimo checks and the Node navigation check pass.
The original review's 50 preparation pins and returned judgments still verify.

## Remaining input and stopping rule

The standing model-run grant remains recorded. Nevertheless, automatic approval
review requires a specific user approval for sending these eight private dialogue
prefixes to **Google Gemini**, at most eight logical requests / 32 adapter attempts.
It rejected process creation; neither a dispatch receipt nor an event ledger
exists. Preserve the rejection and frozen scope; do not bypass or retry it without
the required approval. Scope SHA256:
`80573690b3e7e834fc132f233fe2ab8fae94fa7050e5f8628a9ccb8f6cfd7e16`.

Once specifically authorized, run that scope once, retain all failures, score with
the frozen rule, and close. No rerolls, new human coding, default generator change
or student-realism claim follows automatically. This is a development forecast
screen; it neither measures reply probability nor establishes a grounding effect.
