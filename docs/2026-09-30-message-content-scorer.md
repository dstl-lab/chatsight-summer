# Evidence-backed message-content scorer: authored smoke test

The approved scope is a runnable scorer for the
[content/request definition](2026-09-30-message-content-definition.md), followed
by one smoke test on the twelve authored boundary examples already documented.
No student conversation, old review label or unseen target enters this test.

## Implementation decision

Reuse the existing strict student/tutor turn input and numbered-source-line
helpers. Accept only a supplied prefix and one nonblank current student message.
Reject additional metadata and missing/blank current messages before generation;
these are not no-reply decisions or negative labels.

Return content supplied and expressed request independently as yes/no/unclear.
The model selects `{turn_id, line}` evidence; the application copies the exact
source text. Each observation must cite the current message. A no judgment must
cite every nonblank line of that message. Prefix lines may resolve a referent
but cannot substitute for current-message evidence. Reject invented, blank,
out-of-range and duplicate citations rather than silently repairing them.
Exact quotation validates provenance, not the semantic truth of a judgment.

Use the repository's injected generation pattern. Keep the scorer independent
of provider setup and do not change any frozen experiment or shared transport.
The smoke runner reuses the existing single-attempt Gemini transport with the
verified `response_json_schema` configuration.

## Fixed authored smoke protocol

- The twelve examples and expected observations are copied from the authored
  definition before dispatch. They are specification checks, not human-labeled
  real-student ground truth. Expected answers remain outside the model prompt.
- Gemini 2.5 Flash, temperature 0, thinking budget 0, 2,048 output tokens,
  120-second timeout, one SDK attempt; sequential and at most twelve calls.
- Save exact prompts, schema/configuration, expected results and source hashes
  before dispatch. Retain raw responses and per-case evidence or failure status.
- Stop on the first transport, parsing or evidence-validation error. Preserve
  remaining cases as unattempted. Do not restart or resend this output directory.
- A valid but unexpected label is a semantic mismatch: record it and finish the
  remaining scheduled examples, without retries, repairs or prompt tuning.
- Report attempted/completed/error/unattempted counts, per-flag agreement with
  the authored expectations and full-case matches. All twelve valid matching
  observations are required for a clean authored smoke result. This criterion
  is not an admission threshold for real-data measurement.
- Stop with one report. No automatic real-data calibration, student generation,
  human labeling request, scorer adoption or change to the workbench follows.

The small contract tests cover malformed inputs, exact evidence reconstruction,
uncertainty preservation and one-attempt failure behavior. The live authored
smoke exercises provider integration that offline tests cannot establish.

## Completed result: smoke criterion not met

Exactly twelve requests completed, with zero transport/parse failures,
retries or unattempted cases. All returned line selectors passed the mechanical
evidence checks. **Ten of twelve cases matched both expected observations:**
content supplied matched 11/12 and expressed request matched 10/12. The model
returned no unclear judgments, including on the two examples designed to
exercise uncertainty. This is a failed authored smoke criterion, not a
real-student accuracy estimate.

| Authored boundary | Expected content / request | Returned content / request |
| --- | --- | --- |
| Bare code | yes / no | yes / no |
| Explanation request | no / yes | no / yes |
| Answer to tutor question | yes / no | yes / no |
| Confirmation question with context | yes / yes | yes / yes |
| `2?` without context | unclear / unclear | no / yes |
| Code plus checking request | yes / yes | yes / yes |
| Unframed exercise statement | no / unclear | no / no |
| Exercise expressly posed for a solution | no / yes | no / yes |
| Claim of a function plus a question | no / yes | no / yes |
| Claim that tests passed | no / no | no / no |
| Diagnostic output text | yes / no | yes / no |
| Acknowledgment and plan | no / no | no / no |

The two context-dependent numeric cases returned the expected values but cited
only the current message, omitting the tutor question. The prompt requests a
preceding citation when context resolves a judgment; the mechanical validator
cannot determine when that semantic condition holds. Thus exact, valid source
quotes do not establish that the selected evidence is complete or sufficient.
This is an additional evidence-quality limitation, not a reason to overwrite
the saved observations or report those cases as missing transport responses.

The batch is **closed** with its original prompt and observations. No prompt
tuning, repair calls, replacements, real-data calibration, human review request
or scorer adoption follows. The concrete remaining issue is uncertainty and
context-evidence selection, before testing an independent real-message sample.
Old help/work-v1 labels remain unchanged and cannot serve as the new rubric's
validation answers.

## Implementation and verification

`src/eval/message_content.py` exposes `Input`, `Selection`, `make_prompt`,
`materialize` and `score`. `score(data, generate)` uses the existing injected
`generate(prompt, response_model)` interface once; it contains no provider setup
or retry logic. The materialized result includes `rubric_id`, each value and
source line selectors with application-copied quotes. It is a development helper,
not an adopted simulation metric or a new workbench default.

The authored runner is `experiments/2026-09-30-message-content-smoke.py`.
For an explicitly authorized new run, with the configured key in the environment:

```sh
PYTHONPATH=. python -P experiments/2026-09-30-message-content-smoke.py OUTPUT --send
```

The completed output is the ignored local directory
`data/message-content-authored-smoke-v1`, containing `plan.json`, all twelve raw
responses, progress and `report.json`. Creating that output again fails before
any provider call. The wire request has only the current example and definitions;
the transport never receives authored expected answers or the other examples.

All 30 focused checks pass. The full Python suite reports **977 passed, 3 skipped**,
with one existing Starlette/httpx deprecation warning. Independent code review
found no actionable issues before sending. The prior closed private help/work
audit still reproduces with all source pins unchanged. No new private-data
transfer or student generation occurred.

Independent result verification reproduced all twelve raw responses through the
strict schema and materializer, all counts/matches and the five source-file
hashes. It confirmed the omitted context citations and loss of expected unclear
judgments described above. These limitations remain visible in the saved result.
