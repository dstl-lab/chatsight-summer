# Does wording change the amount of proposed student work?

Minchan accepted the first two initial-action proposals and qualified the third:
finishing both functions after one tutor response seemed doubtful. The existing
action schema already permits unfinished cells. This probe tests whether making
that permission explicit changes proposed work; it does not measure time, effort,
student ability or realistic progress rates.

Use the same three exposed initial tasks from initial-action-review-v1, including
the exact assignment, code, read-only context and first exchange. Run six fresh
Gemini 2.5 Pro requests: one original and one clarified prompt per case, with the
schema and default generation settings unchanged. No prior generated answers or
human verdicts enter the inputs. Keep every success, failure and retry notice.

The clarified prompt adds only this paragraph before the unchanged state JSON:

> Return the whole cell as it would stand after the next proposed revision,
> before any new tutor reply or execution feedback. Include unchanged code;
> unfinished parts may remain. Either partial or complete progress may fit.
> This action has no assumed duration or keystroke count.

Fixed request order is original/clarified for case 1, clarified/original for case 2,
then original/clarified for case 3. These are fresh requests, not branches from
earlier draws. The old accepted proposals remain unchanged. Cases 1 and 2 check
whether explicit partial-work permission disrupts answer copying or a small hinted
fix. Do not require mistakes, partial work, a line cap or forced tutor replies.

Reuse the frozen action parser/application and provider adapter. Keep the new
runner, source/input hashes, authorization, full disclosure and receipts private.
Persist pending calls before dispatch, retain terminal errors, and refuse resends
or partial-batch resumes. Replay makes no provider calls; nothing executes student
code or supplies a grader outcome. Verify the prior preparation as well as new
inputs. Standalone invented checks cover the prompt delta, receipt boundaries and
review preservation; completed modules and experiments remain frozen.

Present one Markdown file per case with both candidates and the same initial
context. Omit condition names from the displayed candidates, retain the mapping
in receipts, and show identical actions once while preserving both draws. Keep
all human fields blank. A compact index links the three files; no review UI is
needed. One draw per condition and three reused cases can reveal output differences
but cannot estimate response distributions, establish a causal wording effect or
prove better student fidelity. Human review is required before interpreting any
changed proposal as more plausible.

## Preparation

The same selected task records are reused byte-for-byte; baseline prompts match
the prior prepared prompts exactly. State JSON is identical across conditions.
The six requests contain 4,784, 5,063, 4,786, 4,507, 6,153 and 6,432 characters.
The new authorization records the standing grant, the earlier exact-excerpt
approval and Minchan's approval of this comparison without claiming a separate
review of the newly prepared exact prompts.

All 31 preparation pins verify, including the preceding experiment's 20 pinned
inputs and sources. Both private checks pass under normal Python: six fake calls
retain errors/retries and replay exactly, while the reviewer preserves verbatim
context/actions, masks condition labels and refuses altered or incomplete output.
No production source changed, and no real model call is needed for these checks.

An independent audit confirmed all 31 pins, the exact 279-character insertion,
identical state JSON and the complete six-prompt disclosure. Authorization and
per-case A/B mapping are accurate; no actionable issue was found.

The send attempt was rejected by automatic approval review before process launch.
It requires explicit approval of the exact changed prompts going to Gemini,
despite the standing grant, prior exact-excerpt approval and approval of the
comparison. The private `send-blocked.json` preserves that rejection and binds the
unchanged experiment/disclosure. That attempt made zero model calls and created
no results file.

Minchan subsequently approved sending the six exact disclosed prompts to Gemini.
The separate private `approval-response.json` links that answer to the unchanged
experiment, disclosure, inputs, authorization and rejection. It was recorded before
dispatch; the completed preparation and original rejection remain unchanged.

## Results

All six requests completed without retry notifications. Every proposal revised
the selected cell without a tutor message. The two conditions produced identical
actions in cases 1 and 2. Both case-3 draws filled the first unfinished function
and left the second unfinished; their new local variable names differ. The
original wording therefore also produced partial work in this fresh batch.
This comparison supplies no evidence that the clarification improved realism,
and no prompt change is adopted from it. No code was executed or graded.

Offline replay verifies the six requests, responses and applied states against
all 31 preparation pins. The three case pages and index render identically on
repeat; 12 completion-file hashes bind the inputs and outputs. Human judgments
remain blank, and the original approval/rejection records remain intact. No
production module changed; the existing private runner and reviewer checks
cover this batch without a new full-suite test run.
An independent audit confirmed the five approval-linked hashes, approval before
all six calls, the 31 preparation pins, 12 completion hashes and verbatim pairing.

Case 1 exactly repeats the previously accepted action with identical context.
Case 2 differs from the earlier proposal only by retaining a final display
expression; its two new candidates are identical to each other. Preserve that
distinction without transferring earlier verdicts into new review fields. To
reduce repeated review, bring case 3 forward first and retain the other two case
files for reference. Plausibility remains a human question, not a conclusion from
the amount of code changed.

## Human review and decision

Minchan judged both case-3 candidates plausible and noted that their only
difference is variable naming. The separate private `human-review-response.json`
records both judgments, the exact reply and six artifact hashes. No preference
between conditions was given. Cases 1/2 receive no new judgments, and the original
blank review pages and earlier qualified judgment of complete case-3 work remain
unchanged.

Close this wording diagnostic and retain the original generator. The reviewed
examples support copying a supplied answer, making a small hinted correction and
making a partial edit as possible actions; they do not establish how often any
should occur. Both prompt conditions produced accepted partial work, so this
feedback provides no reason to adopt the clarification or force smaller edits.

The next useful check is continuity from an accepted partial state: carry the
generated work forward and inspect the next proposed action with no invented
intervening tutor reply, execution or outcome. Reuse the existing action schema;
do not add a memory system or new grader merely for this check. This will test
whether subsequent choices stay grounded in the current notebook state, while
the amount and plausibility of further progress remain separate judgments. No
additional model calls were made to record or verify this feedback.
