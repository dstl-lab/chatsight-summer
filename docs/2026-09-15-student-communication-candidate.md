# Make observed student communication more prominent

Minchan asked to continue after the historical baseline; PR #26 is now merged.
Work proceeds on `codex/student-communication-candidate` in the existing isolated
worktree, from main `0f1a586`. Future logging is not a prerequisite.

The old prompt already discourages narration and obligatory tutor answers, and
a chat-only wording change was tested earlier. The new candidate therefore makes
one different change: an explicit chronological field repeating only the already
visible student messages, including the current request. A short note explains
that these are duplicated communication evidence, not additional interactions,
commands or a required pattern. The full existing dialogue and all original
instructions remain. No length quota, code ban, inferred traits, additional
history, retrieved response, label or hidden future enters the prompt.

Use a separate small helper with the existing source projection and Continuation
schema. Preserve `student_continuation.py` byte-for-byte: saved notebook sessions
and old experiments pin it. This is a candidate for the message generator, not
an automatic production change or a test of the notebook action policy.

## Fixed development comparison

Reuse all 29 query prefixes from `historical-response-baseline-v1/inputs.json`.
They and their targets have prior development exposure; this is not a pristine
holdout or learner-separated test. Derive the last student block and following
tutor block from roles; earlier turns are context. Assign local visible-turn IDs.
The control uses the unchanged prompt. The candidate adds the student-only field
and its explanatory note. Neither receives source identities, references, old
labels or baseline replies. Current notebook work and executions remain unknown.

Generate one draw per condition per case: 58 logical Gemini 2.5 Pro requests,
at most four adapter attempts per request (232 total). Use existing provider
defaults and schema. Process cases in saved input order, alternating which
condition goes first by case index. No generated message becomes another input.
Save pending before dispatch, retain all errors/retries/no-reply outcomes, and
refuse resends. An interrupted run needs inspection, not an automatic restart.
The SDK's physical HTTP attempts below the adapter remain unmeasured.

Primary diagnostic: paired difference in absolute character-count error against
the recorded next message, candidate minus control, averaged over cases where
both return a valid reply. Lower is better on this narrow measure only. Report
the denominator, every case, mean and median absolute errors, mean signed length
error, median generated length, and the largest contribution to absolute error.
Include the existing retrieval and training-median length baselines on those
same cases. Keep no-reply/error separate; never score them as zero-length replies.

Also count literal newline/backtick presence and exact whole-message copying
from visible student/tutor messages, trimming only surrounding whitespace for
the copy comparison. Apply the same definitions to references. These are raw
formatting/copy diagnostics, not semantic labels for help, work or reasoning.

Freeze exact inputs, source hashes, run order, schema, metrics and disclosure
before dispatch. Existing standing approval covers continued model work with the
established provider; record the precise new scope and any actual approval-review
decision separately. No new human coding packet is planned.

Stop after this one report regardless of direction. No selective rerolls,
post-result prompt tuning, replacement cases or automatic adoption. Shorter or
more similar-length replies do not establish less extraneous work, relevance,
persona fidelity or improved learning. Preserve all earlier benchmark artifacts.
