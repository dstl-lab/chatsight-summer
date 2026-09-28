# One student-role reminder

## Decision before execution

The saved-output diagnosis found replies that speak as the tutor. Test one
minimal prompt change: append `\n\nNow write only the student's next message.`
to the existing user message after its unchanged JSON transcript. No other
instruction, transcript turn, copying ban, model, adapter or sampler changes.
Keep the live backend and all closed studies unchanged.

Use the base local Qwen model on the 39 cached base-arm student requests
(13 recorded-prefix starts and 26 fixed later synthetic histories), plus the
separate one-call recorded smoke example. Preserve each prefix, seed and output
cap. Baseline replies remain cached; candidate replies never feed forward.
The final smoke case was inspected during development and is not a holdout.

Reuse the frozen local generation worker behind a small private wrapper. Freeze
all inputs, source hashes and exact tokenized prompts before running. At most
40 student generations, 120 seconds each, 1,200 seconds overall, 256 output
tokens, 4,096 total context tokens and 16 GiB reported MLX memory. Preserve
failures and unattempted slots; no retries, replacements or second variant.
No tutor calls, cloud transmission, training or new manual labeling.

Separately score the candidate on the same 28 exposed development targets already
encoded by the training check. Reuse their exact target tokens without decoding
reference text; preserve the previously excluded over-context case. This set
includes the smoke conversation's previously scored target, so the two checks
are not independent. Compare with the cached base scores only after verifying
the same model/runtime and scoring code. One scoring pass, 600 seconds maximum,
same context/memory limits; no training and no new target selection.

## Fixed decision and stopping rule

All integrity checks and all planned calls/scores must complete. Count tutor
containment with the existing literal case-insensitive helper, separately for
the three generation populations. Long means more than 40 stripped characters.
For this candidate to merit later opt-in integration, require all of:

- Fewer long tutor-containment matches, with reductions in at least two of the
  13 cohort conversations; the smoke example does not satisfy that count.
- No new tutor-containment matches among the 13 recorded-prefix first replies.
- The smoke candidate has no whole-response tutor containment and does not
  include the baseline's copied question as a case-insensitive substring.
  Inspect it in context as well; this literal check cannot detect paraphrases.
- No increase in conversation-weighted mean recorded-target negative log loss.

Report any new containment matches, student repetition, reply length, target
token counts and per-conversation loss changes. These are development screens,
not a measure of real-student fidelity; containment can also represent correct
code reuse, and shorter replies alone do not count as improvement. Inspect
changed matches in context before any integration recommendation. Passing
permits an opt-in implementation proposal only, not a default change.

Close after this one candidate and report, whether it passes or fails. Do not
start a reminder search, another training run or a labeling queue. Private
requests/results/scripts stay in ignored `data/student-role-reminder-v1/`;
the protocol and outcome are committed locally, with no publication.

Authorization: the user's standing model-run grant and current “Let's continue”
cover this local-only run. The closed private Gemini approval is not reused.
