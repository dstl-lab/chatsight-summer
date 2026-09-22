# Policy lab corrections

The user approved fixing the PR #47 review findings before browser integration.
Scope: verify held-out receipts with the existing loader; keep observation reads
read-only; distinguish logical requests from unmeasured retry attempts; derive
cohort status from saved receipts; surface errors without a saved failure; and
correct ready-state/shared-context attribution in the Marimo tools.

Reuse existing pair, session, and locking conventions. Preserve frozen studies
and saved results; no provider calls, private-data runs, or new labeling.
Regression checks use authored local sessions and mocked callbacks. Browser
integration is a separate change, starting with read-only saved policy pairs.

Completed: held-out finalization/loading replays the saved request and recomputes
the displayed review/provenance; the exact PR #47 helper hash remains readable
without rewriting old artifacts. Fresh observation inspection creates no lock;
saved/busy sessions retain read-only locking. Budget copy distinguishes logical
requests from unmeasured attempts. Structured pair lifecycle validates cached
starts, pending requests, tutor-policy links and results; errors without a saved
failure surface. Cohorts preserve a valid peer when the other startup is damaged
and enforce distinct conversations, one model and safe source locations.

Marimo now distinguishes the shared cached question from a new follow-up, uses
surviving context when A fails, and avoids calling authored source turns recorded
evidence. The default policy is described as a summary rather than an exact copy.

Validation: 529 Python tests passed, three optional tests skipped; seven Marimo
apps and the review-navigation Node check passed. New regression cases reproduced
the review findings before their fixes. Independent backend/evaluation/UI review
is complete. No engine or prompt change, live request, private-data run, or label.
