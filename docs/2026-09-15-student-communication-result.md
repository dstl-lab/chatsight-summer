# Student communication candidate: completed development comparison

**Decision: retain the current generator.** Repeating already-visible student
messages in an explicit chronological field changed some outputs, but this one
fixed comparison gives insufficient evidence to adopt the candidate. The helper
remains available for research; it is not wired into the default simulator.
The fixed run is closed, with no rerolls, prompt tuning or new labeling round.

## Completed run

The original prompt produced 29 replies. The candidate produced 28 replies and
one no-reply. All 58 logical requests completed with valid responses using
Gemini 2.5 Pro; 61 adapter attempts were used, including three retries for the
candidate on case 8. There were no terminal errors. Physical HTTP retries below
the adapter are not measured. Exact-scope user approval preceded dispatch.

The primary comparison includes **28 cases where both conditions replied**.
Case 4 is excluded from paired length/format/copy scores: the candidate returned
no-reply while the recorded next message had three characters. Its disposition
is retained separately, not scored as a zero-length success. All 29 cases were
selected because a nonblank later student message exists; this sample cannot
estimate realistic non-response rates.

| Paired character-count diagnostic | Original | Candidate |
|---|---:|---:|
| Mean absolute length error | 127.357 | 126.107 |
| Median absolute length error | 76 | 52 |
| Mean signed length error | +21.786 | +15.036 |
| Median generated length | 86.5 | 52.5 |
| Largest absolute length error | 582 | 586 |
| Largest error / total absolute error | 16.32% | 16.60% |

The frozen primary result, candidate minus original mean absolute error, is
**−1.25 characters**. Median error is lower, but that does not replace the primary
result or establish reliable superiority from one draw per condition. Large
opposing changes matter: in case 21, reference/original/candidate lengths were
36/14/329, adding 271 characters to the candidate's absolute error relative to
the original. Every case remains in the declared comparison.

On the same 28 cases, the existing retrieval baseline's length error is 393.357;
the constant training-median length of 35 characters has error 75.679, lower than
both generators. The constant predicts a length, not a usable student message.
These subset scores differ from the earlier 29-case baseline report by design;
the earlier report and predictions remain unchanged.

| Literal property, among the 28 paired cases | Recorded | Original | Candidate |
|---|---:|---:|---:|
| Contains a newline | 6 | 11 | 10 |
| Contains a backtick | 0 | 3 | 1 |
| Exact whole-message copy of a visible student turn | 0 | 0 | 0 |
| Exact whole-message copy of a visible tutor turn | 0 | 0 | 0 |

Copy comparisons trim only outer whitespace. These are literal properties,
not labels for help-seeking, submitted work, reasoning or relevance. A lower
median length does not show that the earlier excess-work/narration mismatch was
resolved. The candidate also required 291,553 prepared prompt characters versus
262,419 for the original, without adding observations.

## Limits and stopping decision

The 29 conversation prefixes have prior development exposure and do not establish
independent learners or transfer to other courses. Ten contain only one visible
student turn; across the set, the median is three and maximum six. One draw per
condition cannot establish sampling stability. The results do not measure silent
notebook actions, appropriate stopping, learning or causal effects of tutoring.
No semantic quality or population-fidelity claim follows from this diagnostic.

Do not adopt this candidate or automatically start another prompt experiment.
Keep the existing generator and reusable stateful simulator while preserving
this completed result. Any later intervention needs a concrete behavioral target
and an outcome that can distinguish improvement; optimizing message length alone
is not that target. Future-quarter collection is not a prerequisite for using
the current prototype and historical corpus.

## Reproduction and review

The frozen protocol is `2026-09-15-student-communication-candidate.md`. The
separate 19-line helper reuses the original source projection, instructions and
Continuation schema. Source validation and future exclusion are covered by two
new tests; the unchanged source commit passed 376 tests with two optional
container tests skipped. An authored harness exercised the actual private runner
with retry exhaustion, no-reply, paired arithmetic and refusal to resend.

Private artifacts under `data/episode-pilot/student-communication-candidate-v1/`
retain exact inputs, separately withheld references, source pins, approval and
dispatch receipts, all results, every case's scores and an independent audit.
The initial rejected dispatch remains recorded separately from the subsequent
explicit approval and completed run. Raw student text stays outside Git.

Replay validation checks all 58 ordered slots, timestamps, retry bounds, schema
and the 59 original artifact pins. `run.py replay` is read-only; `score` and
`send` refuse existing outputs and must not be rerun to replace this result.
No prior benchmark, source generator or runtime behavior was changed.
