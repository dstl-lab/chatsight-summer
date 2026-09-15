# Fixed help/work comparison: results and stopping decision

The benchmark is complete. Earlier dialogue did not improve the prespecified
two-flag score in these eight conversations. Both conditions frequently included
work or diagnostic evidence in their next messages, while all eight recorded next
messages were coded as requests for help without work/evidence.

This is a concrete communication mismatch in the existing chat continuation
generator. It does not validate or invalidate the separate notebook action policy,
and it does not establish a general effect of history. The production simulator
and prompts remain unchanged. The planned stopping point has been reached.

## What was measured

One reviewer coded 72 concealed-origin messages: eight recorded references and
four draws per condition for each case. Two independent flags mark observable
help requests and submitted work/evidence; both can be yes. These are measurements
of communication, not judgments of correctness, plausibility, skill or learning.

The two conditions used identical current student requests, tutor responses,
model, prompt and schema. **Earlier dialogue** retained the available earlier
student and tutor turns; **current exchange only** removed them. The reference
is the first subsequent recorded student message. No future messages entered
generation. The [frozen protocol](2026-09-15-help-work-benchmark.md) defines selection,
draws, coding, scoring and the stopping rule.

## Observed flags

| Message source | Messages | Help request: yes | Work/evidence: yes | Both: yes |
|---|---:|---:|---:|---:|
| Recorded next messages | 8 | 8/8 | 0/8 | 0/8 |
| Earlier dialogue | 32 | 32/32 | 26/32 | 26/32 |
| Current exchange only | 32 | 30/32 | 23/32 | 23/32 |

The generated messages largely retained a request for help, often alongside work.
The mismatch is therefore **additional work/evidence**, rather than the absence
of help requests. This is precisely what separate flags can reveal: a primary
category that gives work precedence over help would hide the co-occurrence.
Counts describe the supplied coding; no labels were revised or inferred.

## Prespecified score

Within each case and condition, `p = yes_count / 4`. For each flag, binary Brier
error is `(p - recorded_yes)^2`. Average the two flag errors, then average equally
across cases. Lower is better on this endpoint; the range is 0–1, not a percentage
accuracy. All eight cases meet the frozen complete-case rule.

| Mean Brier error | Earlier dialogue | Current exchange only |
|---|---:|---:|
| Help request | 0.000000 | 0.015625 |
| Work/evidence present | 0.718750 | 0.570313 |
| **Combined, primary endpoint** | **0.359375** | **0.292969** |

The paired difference, earlier dialogue minus current exchange only, is
**+0.06640625**. Earlier dialogue has higher error in this sample. It has a small
advantage on the help flag and a larger disadvantage on the work flag. These are
descriptive results from four draws per condition, not evidence of a statistically
established or practically calibrated difference.

| Case | Earlier dialogue | Current exchange only | Paired difference |
|---|---:|---:|---:|
| 1 | 0.500000 | 0.500000 | 0.000000 |
| 2 | 0.500000 | 0.156250 | +0.343750 |
| 3 | 0.500000 | 0.500000 | 0.000000 |
| 4 | 0.500000 | 0.500000 | 0.000000 |
| 5 | 0.281250 | 0.125000 | +0.156250 |
| 6 | 0.031250 | 0.281250 | −0.250000 |
| 7 | 0.281250 | 0.125000 | +0.156250 |
| 8 | 0.281250 | 0.156250 | +0.125000 |

Current exchange only has lower error in four cases, earlier dialogue in one,
and three tie. The direction is not uniform across cases. The private machine
report retains the unrounded scores and every individual flag judgment.

## Coverage and evidence

- All 64 scheduled requests produced valid replies. One adapter retry gave 65
  adapter attempts; physical HTTP attempts below the SDK are unmeasured. No final
  errors, no-reply outputs or replacement draws.
- All 72 messages / 144 flags were returned. Zero missing or unclear judgments,
  zero exclusions; all eight conversations contribute to the primary score.
  No notes were supplied or required. Prior case exposure is self-reported
  **unsure**. One reviewer does not establish inter-rater reliability.
- The returned 9,539-byte JSON was preserved byte-for-byte in ignored
  `data/episode-pilot/help-work-benchmark-v1/received/review.json`; the intake
  receipt binds its source, hash and exact packet identity. No normalization,
  adjudication, assistant suggestions or new model calls occurred at intake.
- The frozen scorer produced `coding-result.json` once. Its provenance hashes
  bind the packet, private mapping, received form and scorer source. Independent
  arithmetic matches every case, flag and aggregate. Earlier preparation, run,
  approval and blank review artifacts remain unchanged. `run-summary.json` and
  `RUN_REPORT.md` remain historical generation-only reports; they were not rewritten.

## What this supports and what remains unknown

The measurement process can detect a behavioral difference beyond whether a
message sounds plausible. Here it identifies frequent work/evidence presentation
where the recorded messages contain only help requests. The current quantity of
earlier dialogue does not resolve that mismatch on the chosen endpoint.

All eight references have the same two flags. This sample cannot evaluate matching
to recorded work submissions or distinguish help from non-help references. A
perfect help score here is not broad help-seeking fidelity. Selection was frozen
without target-text criteria; after seeing this outcome, no cases were substituted
to make the set more balanced. The homogeneous references are a coverage limit.

Four-draw frequencies are coarse and noisy, and eight conversations are not 64
independent students. Exports were previously audited, the prompt was developed
on this course, and student identities are unavailable for separation. This is
exploratory same-course evidence, not an untouched holdout or course-transfer
result. Origins were concealed, but prior exposure is uncertain and message
content can reveal origins. Zero unclear flags do not establish coding reliability.

Matching flags does not establish contextual appropriateness, learning or the
probability of replying. The logs do not establish the intervening notebook work,
runs or stops. This comparison used the older chat continuation interface;
the working notebook simulator's action choices were not evaluated here. Earlier
context also contains tutor/task information, so this is not an isolated test
of student personality, stylistic memory or acquired knowledge.

## Decision

Close the fixed benchmark with this report. Preserve every draw and human label;
retain existing production behavior. Do not automatically remove history, rewrite
prompts, request more labels, rerun cases or begin another batch.

For the simulated-student North Star, the advance is a working simulation
mechanism plus a completed measurement that exposes a specific fidelity gap.
Labels now function as evaluation measurements; they are not an exhaustive
student taxonomy or a prerequisite for enumerating every possible student action.
A future study would need reference behavior covering both help and work, and
linked notebook observations to evaluate the action policy. Its scope requires
a new research decision. No further review is required for this experiment.
