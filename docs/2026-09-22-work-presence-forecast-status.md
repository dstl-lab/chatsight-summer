# Work-presence forecast: completed, development screen failed

**TL;DR:** All eight approved forecasts completed, with no missing results, errors
or adapter retries. Forecast error was **0.80625**, worse than the frequency
baseline (**0.612245**) and constant 50/50 (**0.5**). The declared development
screen failed. Close this test; do not connect the forecast to message generation
or tune it on these cases. No new labeling was needed; the simulator is unchanged.

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
`study.py`, `check.py`, `approval-block.json`, `payload-approval.json`,
`dispatch.json`, `events.jsonl`, `result.json` and `closure.json`. Exact prompts and all private
reference labels stay ignored. An independent audit verified all **69 pins**,
36 visible turns, eight source/label joins, rubric identity, and the exclusion
of future messages and metadata from prompts. All learner identities remain
unknown, and the eight conversation keys are distinct.

Preparation initially rejected a raw prompt equality assertion: historical
prompts used anonymous IDs and additional fixed unknown-state fields. Before
freezing, the assertion was corrected to compare every visible role and numbered
line, followed by a separate comparison with the exact reviewed prefixes. No
historical input or label changed.

The authored arithmetic check retains errors/missing forecasts as separate rows
and blocks advancement without full coverage. The runner reserves dispatch before
calls, refuses a second dispatch, and preserves flushed request/retry/result events.

Validation: **442 tests pass**, three optional container skips, one existing
Starlette/httpx warning. Both Marimo checks and the Node navigation check pass.
The original review's 50 preparation pins and returned judgments still verify.

## Completed result

The single Gemini 2.5 Pro run completed on September 22, 2026, from 02:23:57 to
02:25:18 UTC. It used eight logical requests, all valid, with zero adapter retry
events. SDK-internal transport retries were not measured. All eight references
remain comparable, so paired and all-reference baseline denominators coincide.

The frozen metric is multiclass-sum Brier, range 0–2; **lower is better**. This is
an error score, not an accuracy percentage.

| Forecast rule | All 8 cases | Work absent (5) | Work present (3) |
| --- | ---: | ---: | ---: |
| Gemini forecast | 0.806250 | 1.081000 | 0.348333 |
| Other seven conversations' work frequency | 0.612245 | 0.367347 | 1.020408 |
| Constant 50/50 | 0.500000 | 0.500000 | 0.500000 |
| Always no work | 0.750000 | 0.000000 | 2.000000 |

Equally weighting the two reference groups gives forecast error **0.714667**.
The forecast gave work a probability of 0.70–0.90 in four of the five cases
where the recorded next message contained none. Its work-present group score
was below 0.5, but its work-absent group and overall scores failed the declared
requirements. Full coverage alone therefore does not pass the screen.

This narrows the finding: asking the model to predict work presentation explicitly
did not clear even the fixed 50/50 baseline on these eight cases. It does not
establish that all alternative work-present replies were implausible, or that a
different architecture could never help. Model-stated probabilities are not
verified sampling frequencies. Do not compare this score directly with the
earlier two-draw generator score as evidence of improvement or regression.

## Approval, verification and closure

Automatic approval review initially rejected dispatch before process creation,
requiring exact private-payload authorization despite the standing grant.
Minchan then answered **“Yes”** to the explicit eight-prefix Gemini request.
`payload-approval.json` binds that answer to the unchanged scope, job payload and
earlier rejection. It precedes dispatch and every request. Preserve this
chronology; the earlier rejection is resolved, not removed. Scope SHA256:
`80573690b3e7e834fc132f233fe2ab8fae94fa7050e5f8628a9ccb8f6cfd7e16`.

Read-only replay matches the saved result exactly. Independent arithmetic checks
confirm every per-case and group score, all 69 frozen pins, approval chronology,
and eight one-time request/result pairs. `closure.json` records a failed screen
and no queued runs. The original review, source messages, labels, forecast code
and advance protocol remain unchanged.

**Decision:** retain the active simulator. Do not build a message-realization
component from this forecast, reroll, revise the prompt on these eight answers,
reopen a labeling queue or generalize to real-student learning/tutor effects.
These exposed development cases and one reviewer's coding supply a bounded
negative result, not population-level validation or a grounding-effect estimate.
