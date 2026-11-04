# Phase 3B Question Baselines and Review Ranking

## Purpose

Phase 3B prioritizes question-level tutoring sessions for instructor review. It does not diagnose tutor quality, establish causation, or classify a tutor response as a failure.

The implementation consumes Phase 3A metric reports. It does not modify ChatSight, contact a database, call an LLM, or infer missing values.

## Exact comparison scope

Sessions are compared only when all of these fields match:

- course ID;
- cohort ID;
- assignment ID;
- assignment version;
- question ID.

Learner and notebook IDs are not part of the baseline key. Different questions never share a threshold.

## Question-level baselines

`session_review.baselines.calculate_question_baselines` reports the following for each metric:

- known and missing counts;
- minimum, median, 25th, 75th, and 90th percentiles;
- maximum, interquartile range, and median absolute deviation;
- a robust upper reference threshold;
- episode IDs and explicit unknown reasons.

The threshold is `p75 + 1.5 * robust_scale`. The scale is the interquartile range when positive, otherwise scaled median absolute deviation, otherwise a documented constant-value fallback. This avoids division by zero when peers have identical values.

Question summaries that include all sessions are descriptive only. Every score uses a separate leave-one-out reference that excludes the evaluated episode. The output records `evaluated_episode_excluded: true` and lists the exact reference episode IDs.

The default requires at least eight other same-question sessions. The configuration has
a hard floor of four reference sessions, but lowering the default is an exploratory
choice that must be documented before evaluation. Smaller cohorts remain
`insufficient_data` and receive no score.

## Shared eligible population

Random selection, total-time ranking, and post-help ranking use the same episode IDs. A session enters this common population only when:

- Phase 3A marks total and post-help behavior usable;
- all five required Phase 3B metrics are known numeric values;
- its exact question scope is complete;
- at least the configured number of complete same-question references are available
  (eight by default).

The required metrics are total active time, post-help active time, failed checks after
help, tutor requests in the observed session, and repeated failed checks after help.
Post-help repeats are derived by intersecting Phase 3A's post-help failure references
with its logical-check groups. A session is excluded when those groups are missing or
do not cover every post-help failure. Unknown metrics and small cohorts are reported
in `eligible_population.excluded` instead of receiving artificial zero scores.

An unfinished outcome does not by itself exclude a session. Its ranking entry carries
a `data_limitations` warning that the score describes observed behavior rather than a
final outcome. Missing outcomes are not converted to failures.

## Ranking methods

### Random comparator

The random comparator uses a deterministic SHA-256 ordering from the dataset ID, configured seed, and episode ID. It has no behavioral score and exists only for reproducible research comparison.

### Total-time ranking

Method A uses total observed active time. A value at or below its leave-one-out upper reference threshold receives zero tail points. Values above it receive a monotonic score:

```text
100 * (1 - exp(-excess / robust_scale))
```

The score expresses distance above the question-specific reference threshold. It is not a probability.

### Post-help ranking

Method B applies the same tail calculation to four metrics, then computes a fixed weighted sum:

- post-help active time: 35%;
- failed checks after help: 30%;
- repeated failed checks after help: 20%;
- tutor requests in the observed session: 15%.

The tutor-request contribution is session-wide because Phase 3A does not currently
partition request events around the first completed response. It measures repeated
help-seeking intensity, not strictly post-help requests. This limitation must be tested
against the real event schema before interpreting the composite.

The weights are transparent preregistration candidates. They have not been validated on real instructor judgments and must not be described as learned or optimal.

## Explainability and provenance

Every contribution contains:

- the observed metric value and unit;
- its fixed weight and weighted points;
- the leave-one-out reference statistics;
- empirical peer percentile;
- a plain-language threshold explanation;
- canonical metric evidence references;
- source event IDs and source JSON pointers when a reconstruction report is supplied;
- unresolved evidence references when source resolution is unavailable.

Each ranked entry repeats the combined evidence references and includes a non-causal interpretation warning.

## Frontend boundary

`build_frontend_ranking_overlay(report, method)` produces
`anomaly-review.frontend-ranking-overlay.v1`. The future UI integration should join
this overlay to the existing session contract using `episode_id`. It should not replace
the existing timeline or event evidence.

Each overlay session provides:

- `rank`, `score_status`, and `score`;
- `priority_reasons` and individual `metric_contributions`;
- canonical `evidence_refs`;
- original `source_event_ids` and `source_pointers`;
- `data_limitations` for unfinished or unknown outcomes;
- a non-causal `interpretation` statement.

Excluded sessions remain in `excluded_sessions` with reasons. The dashboard must not
display an excluded session as a zero-scored normal session.

No frontend integration is performed in Phase 3B.

## Commands

From `anomaly-review`:

```bash
uv run pytest -q

uv run session-review fixtures/frontend_demo_sessions.json --output /tmp/sessions.json
uv run session-rank /tmp/sessions.json --output /tmp/ranking.json

uv run session-ranking-demo --output /tmp/synthetic-ranking.json
```

Outputs are create-only. The existing frontend fixture has one session per question, so it is correctly reported as insufficient for real baseline scoring. The separate Phase 3B demonstration contains enough invented same-question metric rows to exercise ranking behavior.

## Real-data validation still required

Phase 2C must establish:

- whether event density supports the active-time estimator;
- whether the active interval cap is appropriate;
- whether tutor completion means the response reached the student;
- whether grader ID plus grader version identifies one logical check;
- whether retries generate duplicate semantic events;
- whether request, response, execution, revision, and check identifiers are stable;
- whether timestamps preserve actual action order;
- whether question attribution is consistently explicit or verifiable;
- whether export coverage is complete enough to interpret absence;
- whether cohort sizes per exact question are sufficient;
- whether the fixed weights and threshold rule produce useful instructor review yield.

Research evaluation must also define instructor review labels, adjudication, sampling size, and metrics such as precision at a fixed review budget. Synthetic rankings are software checks, not research findings.
