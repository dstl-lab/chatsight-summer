# Synthetic Phase 3B Comparison

These values are invented software fixtures. They are not student data and are not research evidence.

The synthetic input contains 15 sessions. Eleven same-question Q1 sessions have complete metrics and four sessions are explicitly excluded: one ambiguous Q1 session and three Q2 sessions with too few same-question peers.

The Q1 fixtures include ordinary progress, quick successful recovery, long independent
work, repeated post-help failures, multiple tutor responses, unfinished work, and an
ambiguous session. They exercise software behavior only.

## Top results

| Rank | Total-time method | Score | Post-help method | Score |
|---:|---|---:|---|---:|
| 1 | `q1-long-independent` | 99.996747 | `q1-post-help-struggle` | 79.744858 |
| 2 | `q1-post-help-struggle` | 99.908812 | `q1-multiple-help` | 21.136906 |
| 3 | `q1-multiple-help` | 28.346869 | `q1-long-independent` | 0.000000 |

The total-time method prioritizes a session with long observed work but quick post-help recovery. The post-help method instead prioritizes the fixture with prolonged post-help time, four failed checks, three repeated failures, and three tutor requests.

For `q1-post-help-struggle`, the generated reasons are:

- post-help active time 110 seconds, above a 34-second leave-one-out threshold;
- four failed checks after help, above a 2.5-event threshold;
- three repeated failures, above a 1.5-event threshold;
- three tutor requests, above a 2.5-event threshold.

The fractional thresholds are statistical reference values, not possible event counts. Scores are bounded tail-distance measures, not probabilities.

The deterministic random comparator uses the same eleven eligible episode IDs but ignores behavioral metrics.
