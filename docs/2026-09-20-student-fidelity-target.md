# Fidelity target: what the student chooses to send

**TL;DR:** Target the simulator's excess presentation of work/evidence in chat,
while preserving work-bearing messages when the context supports them. The
existing labels identify this discrepancy, but cannot establish that a fix works:
all eight references in the comparable study are help-only. A constant help-only
flag prediction scores perfectly. Keep the generator, make zero new requests,
and close this decision without another labeling queue.

## Selected target and evidence

The target is **matching whether the next student message presents work/evidence**,
alongside any request for help. Work means substantive candidate code, an answer,
calculation, reasoning or diagnostic output under the existing `help-work-v1`
rubric. It does not mean the student actually edited a notebook, executed code,
learned, or should have sent that particular message.

This addresses Minchan's repeated observation that simulated students explain or
submit work to the tutor more readily than the terse help requests in their
visible histories. That feedback motivates the target; the completed blind
help/work coding supplies the separate measurement below.

| Completed measurement | Recorded next messages | Existing generator with history | Same generator, current exchange only |
| --- | ---: | ---: | ---: |
| Messages | 8 | 32 | 32 |
| Help request present | 8 | 32 | 30 |
| Work/evidence present | 0 | 26 | 23 |
| Combined two-flag Brier error | — | 0.359375 | 0.29296875 |

All eight conversations, all four draws per condition and the original human
judgments remain included. The 26/32 work count is a descriptive frequency in
these saved messages, not an 81.25% student-error rate. A different continuation
can be plausible. One reviewer, homogeneous references, prior development
exposure and four-draw sampling limit interpretation.

The [completed length comparison](2026-09-15-student-communication-result.md)
also stays closed. Its candidate changed mean absolute length error by only
−1.25 characters and supplied no new semantic coding. Repeating visible student
turns, adding another generic brevity instruction, imposing a length cap, or
changing the history window is not justified by this result.

## Measurement check: a rule that ignores the conversation wins

This is a new, post-result diagnostic of the existing metric. It does not replace
the [frozen report](2026-09-15-help-work-results.md), create new outputs, or claim
that the following rules generate usable messages. They predict only two flags.

For each reference, the old score is the average of `(p_help-y_help)^2` and
`(p_work-y_work)^2`, then averaged equally across cases. Every reference has
`y_help=1, y_work=0`. Consequently:

| Constant flag prediction, ignoring all input | Existing combined Brier error |
| --- | ---: |
| Help, no work | **0** |
| Help and work | 0.5 |
| Neither | 0.5 |
| Work, no help | 1 |

The score detects the observed discrepancy but cannot distinguish an appropriate
reduction in work presentation from indiscriminately suppressing work. Optimizing
against it alone would reward the latter. This is why another prompt experiment
would currently have no defensible adoption decision.

## Measurement and stopping decision

| Item | Fixed decision for this step |
| --- | --- |
| Target | Work/evidence presentation in the next student chat message, with help requests retained as a separate flag |
| Baseline | Unchanged `student_continuation` generator with visible earlier context; its existing 32 draws |
| Cases | Exactly the eight conversations in the closed help/work benchmark; no replacements or new target-text selection |
| Available measure | Existing per-case two-flag Brier scores and work/help counts; descriptive diagnosis only |
| Desired improvement measure | Balanced work-flag Brier: half the mean error on recorded work-absent cases plus half the mean error on recorded work-present cases |
| Readiness rule | Both reference groups and comparable output judgments must exist before that balanced measure can be calculated; an empty group is unavailable, not zero |
| Current readiness | **Not ready:** zero work-present references; new candidate outputs have no human judgments |
| New call budget | **0** student, tutor or model-judge requests |
| Human work | **0** additional labels; do not resume the paused 86-message audit |
| Adoption rule now | No candidate adoption from this diagnostic; retain the existing generator |
| Stop | End at this verified report and target decision; no automatic prompt change, new draws, rerolls or replacement benchmark |

Balanced work error makes the missing coverage explicit: with both groups present,
an always-no-work predictor would score 0.5 on that measure, rather than zero.
Equal group weighting is a balanced error diagnostic; it does not measure natural
behavior prevalence or establish probability calibration. This is a proposed
measurement requirement, not a validated new benchmark. Help
retention and contextual appropriateness would still need assessment. Any later
adoption study needs its own fixed cases, comparable coding, call budget,
uncertainty treatment and practical decision threshold before dispatch.

The older independent eight-reference review contains two submitted-code and one
submitted-work label, so work-bearing examples exist in the current corpus.
However, its primary categories use a different coding procedure, including a
documented help-versus-code disagreement. They are useful examples for developing
measurement, not interchangeable binary flags or extra scored cases here. The
paused 29-case audit has no completed help/work labels to borrow. No new-quarter
data is required to investigate the measurement gap, and no missing labels are
silently filled by the assistant.

This closes task-list item 3 as a target and readiness decision. Item 4 is deferred
because its measurement gate failed. Simulator engineering can continue without
asking the instructor to rate another batch. The larger UI redesign remains
deferred at Minchan's request; packaging the existing tools for teammates is an
independent next engineering task.
The research pause does not disable the working simulator or its policy controls.

## Reproduction

The frozen report replayed identically through the original scorer after verifying
its packet, mapping, returned judgments and scorer hashes. Its SHA-256 is
`4dce95df35b7d71dace5ca30d7ee3c1abbfaea26b448613ee06d9e4535decde8`.
The new aggregate-only local diagnostic is
`data/episode-pilot/fidelity-target-decision-v1/report.json`. Original evidence,
labels, prompts and scores were not rewritten.

This small read-only check reproduces the new constant-prediction diagnostic:

```python
import hashlib
import json
from pathlib import Path
from statistics import mean

path = Path('data/episode-pilot/help-work-benchmark-v1/coding-result.json')
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '4dce95df35b7d71dace5ca30d7ee3c1abbfaea26b448613ee06d9e4535decde8'
rows = json.loads(raw)['cases']
assert len(rows) == 8 and all(not row['exclusion_reasons'] for row in rows)
flags = ('help_request', 'work_present')
predictions = {'help_only': (1, 0), 'both': (1, 1), 'neither': (0, 0), 'work_only': (0, 1)}
scores = {
    name: mean(mean((p - int(row['reference_judgment'][flag] == 'yes')) ** 2
                    for flag, p in zip(flags, prediction)) for row in rows)
    for name, prediction in predictions.items()
}
assert scores == {'help_only': 0, 'both': 0.5, 'neither': 0.5, 'work_only': 1}
print(scores)
```
