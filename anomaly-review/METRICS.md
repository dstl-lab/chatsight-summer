# Phase 3A Behavioral Metrics

## General rules

All calculations operate on reconstructed question episodes. Metrics have `known` or `unknown` status, a value, and source-event references. Missing evidence is never converted to zero or failure. These metrics describe observed behavior and do not assert that tutor help caused later behavior.

The default active interval cap is 300 seconds and is configurable through `MetricsConfig` or `--active-interval-seconds`.

## Time metrics

### Observed elapsed span

Seconds from the first observed event to the last observed event in the question episode. This includes inactivity and must not be interpreted as productive work.

### Total observed active time

The sum of intervals between adjacent active observations when all of the following hold:

- both observations represent student activity;
- their order is certain;
- they are in the same work bout;
- the interval does not exceed the active interval cap;
- no tutor response, terminal activity signal, or status event appears between them.

Student messages, code edits, executions, checks, focus, heartbeat, and resume events can support active intervals. Blur and pause events cannot. With fewer than two qualifying observations, active time is unknown rather than zero. This is a conservative event-based estimate, not continuous attention measurement.

### Before and after first help

Active time is partitioned around the first unambiguous completed tutor response. A streaming or failed response is not a help boundary. If the first boundary or an activity event's position is ambiguous, both partitioned time metrics are unknown.

### Response-to-action elapsed time

For each completed tutor response, this records elapsed seconds to the first concrete student action before the next completed response. Concrete actions are messages, edits, executions, and checks. This is elapsed latency, not active time. No observed action produces an unknown value.

### Active time between completed responses

For every consecutive pair of completed tutor responses, this applies the same active-time estimator only to activity strictly between those responses. Fewer than two completed responses produces an unknown value.

## Activity metrics

- **Tutor requests:** observed student-message events carrying a request ID.
- **Completed tutor responses:** unambiguous response events explicitly marked completed.
- **Failed checks before and after help:** observed failed check events partitioned around first completed help.
- **Repeated failures:** failures after the first failure for the same `grader_id` and `grader_version`. If either identifier is missing from a failed check, this metric is unknown.
- **Code edits and executions:** observed event counts before and after first completed help.

Counts are event counts. Real-data validation must determine whether source instrumentation emits duplicate semantic actions with distinct event IDs.

### Per-response windows

Every completed response also has its own window containing active time and counts of failed checks, edits, executions, and student messages before that response and after it until the next completed response. Later-response activity is retained as references instead of being assigned to an earlier response. This prevents a multi-help session from being reduced to only its first interaction.

## Recovery metrics

### Eventually passed question check

`true` when at least one question-scope passing check is observed. A subcheck pass does not satisfy this metric. Absence of a question pass is unknown, not false.

### Failed checks between help and recovery

The number of failed checks strictly after first completed help and before the first unambiguous later question-scope pass. Without both boundaries, the metric is unknown.

### Continued and resumed work

Continued work is true when a concrete student action is observed after first completed help. Resumed work is true when such an action occurs in a later work bout. A false value requires a known terminal question outcome; otherwise absence remains unknown.

### Question outcome

Outcome is copied from explicit reconstructed status evidence. Check results do not supply final completion. Intermediate subcheck passes are exposed separately as references.

## Evidence and evaluation populations

Every metric contains `evidence_refs`. Each reference resolves to a normalized event, whose `sources` identify the original JSON record without placing raw student content in metric definitions.

Each episode records eligibility for:

- random selection;
- total active-time analysis;
- post-help behavior analysis;
- a common comparison population requiring both total and post-help metrics.

Phase 3B should define one eligible comparison population first, then apply random selection, total-time ranking, and post-help ranking to that same population. Eligibility is not an anomaly score.

## Real-data limitations to validate

- Whether event frequency is sufficient for the active-time estimator.
- Whether a 300-second cap is appropriate for notebook work.
- Whether heartbeat or focus events reliably indicate activity.
- Whether tutor completion status means the response reached the student.
- Whether request and response IDs are stable across retries.
- Whether grader ID plus version identifies one logical check.
- Whether question-scope checks and explicit completion events are consistently emitted.
- Whether delayed or batched timestamps preserve actual action order.
- Whether export coverage is complete enough to interpret absence.
