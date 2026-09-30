# Student-only earlier context: one simulator development comparison

**TL;DR:** Test whether the simulator better preserves student message form when
earlier context contains only the student's own messages. Keep the entire current
student–tutor exchange in both conditions. Use the existing ten development cases,
five fresh draws per condition, and automatic literal measurements. No new labels
or semantic evaluator are involved. The existing simulator default stays unchanged.

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
No new provider requests have been sent yet.

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
that rejection. There is no execution directory and zero provider requests were
sent. The user has been asked to approve this one prepared 100-request batch;
no alternate dispatch, retries or additional preparation are queued. After a
specific approval, preserve it against the frozen plan and disclosure before
consuming this batch once.
