# Student-only earlier context: one simulator development comparison

**TL;DR:** Implemented student-only earlier context and completed the approved
100-request comparison. Literal form error is **0.420 current exchange versus
0.390 student history**: three cases improve, three worsen and four tie. One case
accounts for more than the net improvement. This is weak, mixed development
evidence, not sufficient reason to change the default. No new human labels or
semantic evaluator were used. The comparison is closed without another batch.

The intervention keeps the entire current student–tutor exchange in both
conditions, using the existing ten development cases and five fresh draws per
condition. The isolated prompt helper is available for further development; it
is not enabled in the production workbench or adopted as the simulator default.

## Completed result

| Measurement | Current exchange | Student-only earlier context |
| --- | ---: | ---: |
| Mean literal form error; lower is better | 0.420 | 0.390 |
| Replies / no reply / errors | 50 / 0 / 0 | 50 / 0 / 0 |
| Short replies, 0–40 characters | 17/50 (34%) | 20/50 (40%) |
| Mean characters | 71.18 | 65.98 |
| Character MAE against recorded next message | 41.64 | 37.52 |
| Replies containing newline | 5/50 (10%) | 10/50 (20%) |
| Replies containing backtick | 3/50 (6%) | 0/50 (0%) |

The recorded messages are short in 8/10 cases, average 41.5 characters, contain
one newline-bearing message and no backticks. The unchanged visible-student
form-frequency baseline scores **0.1550**. Both generative conditions remain far
from that baseline on this narrow form score. The frequency baseline supplies a
distribution, not a coherent next message, so it is not itself a student simulator.

All ten pairs are complete. Student-history minus current score is **−0.030**.
The implementation's floating-point report retains approximately −0.03; exact
score arithmetic has the same result. There is no statistical significance or
population-improvement claim.

| Case | Current form score | Student-history score | Change | Current character MAE | Student-history MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 0.10 | 0.20 | +0.10 | 18.4 | 21.4 |
| 02 | 0.00 | 0.00 | 0.00 | 5.0 | 10.6 |
| 03 | 0.00 | 0.30 | +0.30 | 28.0 | 80.0 |
| 04 | 0.60 | 0.00 | −0.60 | 52.4 | 5.0 |
| 05 | 0.80 | 0.60 | −0.20 | 79.2 | 39.0 |
| 06 | 0.00 | 0.00 | 0.00 | 23.2 | 24.0 |
| 07 | 0.70 | 1.00 | +0.30 | 72.6 | 56.6 |
| 08 | 1.00 | 0.80 | −0.20 | 72.6 | 76.6 |
| 09 | 0.00 | 0.00 | 0.00 | 16.4 | 15.4 |
| 10 | 1.00 | 1.00 | 0.00 | 48.6 | 46.6 |

Post-result influence check: case 04 contributes −0.060 to the all-ten mean,
while the net is −0.030. Omitting that case would leave +0.0333 across the other
nine. This is a diagnostic of concentration, not permission to exclude it, a new
primary endpoint or a confidence interval. Case 10's prompts are identical;
form scores tie, while character errors differ because its draws differ.

This is a distribution score: case 08 improves despite neither arm sampling a
short reply matching its recorded length category. Category dispersion can lower
the score without a target-category hit. A score of zero likewise does not mean
that generated text or meaning matches the recorded message.

The earlier full-history study also had a −0.030 contrast, but it was a separate
batch with different draws. This coincidence does not establish equivalence
between full history and student-only history. Do not pool the batches or use
the older history outputs as a concurrent control.

**Decision:** retain the experimental helper, preserve the unchanged default,
and close this candidate's fixed comparison. Removing earlier tutor messages
alone has not supplied strong evidence of a broadly better simulator. Form
improvement does not settle whether replies pursue the student's aims. No further
labeling, prompt tuning or generation is queued by this result.

The [saved history diagnosis](2026-09-30-history-benchmark-diagnosis.md) found that
full history supplied 67,796 earlier tutor characters versus 2,854 student
characters. Generated replies often completed the tutor's teaching sequence.
This motivates removing earlier tutor turns; it does not establish that tutor
volume caused those responses. The change can also remove useful task context.

## Fixed intervention

| Condition | Input |
| --- | --- |
| Current exchange | All consecutive current student request messages followed by all current tutor reply messages |
| Student history | The identical current exchange plus earlier student messages in chronological order |

Reuse the original splitter and continuation instructions/schema. Preserve the
existing line representation, source line numbers and wording. Assign stable
request/response IDs independently of history; renumber retained context after
filtering so omitted tutor turns do not leave source-index gaps. Do not add a
brevity instruction, length cap, forced help request, persona or target example.

Retain all ten original provisional course accounts and their exact query
prefixes. They are already exposed development cases, not a fresh holdout or
verified enrolled-student sample. Case 10 has no earlier student messages, so its
two prompts are identical. Keep it as an explicit no-intervention case; any
observed difference there reflects sampling or provider variation. The helper
also accepts a prefix containing only the current exchange.

The control prompt must match the earlier benchmark's current-exchange prompt
byte-for-byte. Both arms receive **fresh draws** in this new batch; the old 100
outputs are not reused as a concurrent control. No old artifact or source-pinned
engine is modified. Recorded next messages remain outside generation requests.

## Budget and transport

- Ten accounts × two conditions × five draws: **at most 100 requests**.
- Gemini 2.5 Pro; temperature 1.0; at most 8,192 output tokens; same schema and
  settings as the closed history benchmark. Top-p, top-k, seed and thinking
  settings remain omitted. Record returned model versions.
- Alternate condition order by case and draw, as in the original schedule.
  One worker, one SDK attempt, one adapter attempt, 120-second timeout per call.
- Freeze exact prompts, query/source/code hashes, condition mapping, reference
  hash and schedule before sending. Full disclosure stays in ignored local data.
- Save raw responses and terminal receipts; errors retain only exception type.
  A started batch cannot resume or resend, including after interruption.
  No retry, replacement draw, case exclusion or automatic follow-up batch.

## Automatic measurement and stopping rule

Reuse the original half-scaled, finite-ensemble-corrected categorical form Brier
score. Categories combine raw Unicode length bins (0–40, 41–300, over 300), newline
presence and backtick presence. No-reply remains a separate thirteenth category;
it is never a blank text reply. Errors are missing outcomes, not student behavior.

Primary: equal-account mean of **student-history minus current-exchange** score.
Negative values indicate lower observed literal form error for student history.
Report every case, improvements/worsenings/ties and both condition means over the
same complete case pairs. If a draw fails, keep that case in the scheduled
population, show complete-pair results and the existing missing-outcome bounds;
do not supply an all-ten point estimate. Bounds are not confidence intervals.

Secondary: character MAE, newline/backtick rates with reply denominators, all
reply/no-reply/error counts, and the unchanged visible-student form-frequency
baseline. Five draws remain noisy; the finite-ensemble correction assumes
independent stationary draws, and alternating order does not create paired seeds.

One batch and one report close this comparison, regardless of its direction.
Do not tune on the outputs, ask for another labeling pass, adopt a new default,
or claim a semantic improvement from a lower form score. A successful mechanical
run is implementation evidence; lower form error is only development evidence
for this narrow observable. These data condition on a recorded return to chat
and cannot validate actual silence, learning or hidden notebook behavior.

## Implementation and verification

`src/eval/student_history.py` supplies the isolated prompt mode.
`experiments/2026-09-30-student-history.py` owns the new plan and execution receipt,
reusing frozen parsing, transport, receipt verification and literal scoring.
It does not reuse the old runner's hardcoded user authorization. There are no new
dependencies or UI changes.

Authored checks cover multi-message current blocks, exact control preservation,
ordered student history, unchanged source input, exclusion of identity/future
fields, both empty-student-history cases, the 100-slot budget, error/no-reply
handling, raw-response replay, changed references and refusal to overwrite or
rerun. The original benchmark remains independently replayable.

## Status

Implementation and preparation are complete. The ignored private packet is
`data/student-only-history-v1/`: twenty prompts, 3,048–8,554 characters each,
100 scheduled requests, and one identical-prompt case. Plan SHA-256:
`1fd95accddb63286ba2655178ad4cfeb629478aed0f60011f342ee6212659b1d`.
Prompts SHA-256:
`db108d0c5988a0df54265da434f7087f48765ef722b7ee0d00adde0ddf9294be`.
These preparation hashes remain unchanged after the completed run.

Verification passed: 1,021 Python tests, three skipped, with the existing
Starlette/httpx deprecation warning. The command used `--import-mode=importlib`
because the two frozen experiment directories both contain `test_run.py`; the
initial combined invocation otherwise stops at a test-module name collision.
Independent authored checks confirmed scoring arithmetic, target isolation,
balanced order, raw-output tamper rejection and legacy receipt compatibility.
The original 100 saved decisions still replay unchanged.

Independent review of the real packet verified all fourteen code/source pins,
each complete current block and retained student context, the original model
settings, balanced order and absence of model-visible IDs or target fields.
The reference file was not opened for this review.

Automatic approval review rejected the attempted private Gemini dispatch before
process creation: it requires specific authorization for this exact payload and
destination despite the standing project grant. `send-blocked.json` preserves
that rejection. No execution directory existed and zero provider requests were
sent by the rejected attempt. The user subsequently replied **"Approve this
100-request batch"**. `approval.json` binds that response to the exact plan,
prompts, disclosure, earlier rejection and preflight, before launch and all
100 requests. No workaround or alternate batch was used.

The approved batch completed all 100 requests in approximately 20.5 minutes,
with 100 replies, no errors, no no-reply outcomes and no retries. Every response
reported `gemini-2.5-pro`. All raw outputs, receipts, source pins and aggregate
results passed independent replay; exact Fraction arithmetic reproduced every
case score and the aggregate contrast. The saved `report.json` is reproducible
offline, and `closure.json` records the stopping decision. No additional provider
call, manual review or automatic follow-up is queued.
