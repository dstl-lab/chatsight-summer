# Frozen independent test: awaiting one blind review

**TL;DR:** Twenty-four previously unused course accounts are selected and all
predictions are sealed. The one-question review is ready at
`http://127.0.0.1:8456/`. No independent score exists yet: human judgments are
still needed. Do not tune the model or replace cases while that review is pending.

## Completed

The [fixed protocol](2026-10-01-context-work-holdout.md), preparation code and
work-only reviewer UI were committed at `b1ad4df` before selection or content
retrieval. The model, feature and training labels are unchanged.

A renewed metadata-only exposure audit scanned 5,365 files across the original
and current worktree data directories and verified 5,377 source pins. After
whole-account exclusions it left 98 candidate accounts. Unknown identifiers were
restricted to established authored fixtures; no unresolved real identity or
readable-data gap remained. Unrecorded external exposure and identifiers found
only in unstructured text cannot be ruled out. Student eligibility was not
investigated.

Using the declared hash ranking, we selected 24 accounts and one conversation
each. A read-only query returned 97 structural checkpoints; one per account was
frozen before reading text. We then retrieved 192 earlier chat events, computed
all 24 predictions, and saved the sealed prediction artifact before launching
the separate read-only query for the 24 recorded targets. There were no account
or checkpoint replacements, labels inferred by an LLM, or provider calls.

The first prefix retrieval failed to connect after the tunnel dropped. It
produced no prefix artifact and never reached the database. The failed launch
record is retained alongside the recovery launch; the same query, parameters,
selection and model were used after restoring the tunnel. This was connection
recovery, not another sample or scored experiment. The database tunnels are closed.

## Review handoff

The portable file is `data/context-work-holdout-v1/review.html`. Give the reviewer
only this file; it works offline. The localhost server serves a byte-identical
copy from `data/context-work-holdout-v1/ui/index.html`. That served directory has
no predictions, linkage files or source receipts.

Each case shows its actual preceding conversation and one next student message.
The reviewer answers only **work/evidence present: yes / no / unclear**, with a
short note for unclear. The original human rubric is retained verbatim. Browser
drafts are local; finish and return the exported JSON. The page does not transmit
answers automatically. No messages have been sent to teammates.

One different reviewer is preferred. If the original reviewer completes it,
describe the result as a held-out-account, single-reviewer check. Neither option
establishes inter-rater reliability by itself. The reviewer-selection question
is pending; no reviewer identity or answers have been filled in by the assistant.

After the completed review is returned, produce the one predeclared report and
stop. Missing/unclear outcomes retain coverage accounting and full-set bounds.
No test labels enter training, no success threshold is chosen from the outcome,
and a negative or inconclusive result must be retained.

The private `data/context-work-holdout-reserved-accounts.json` records all 24
accounts for exclusion from concurrent development and future independent tests.
This reservation sits outside the current preparation directory so subsequent
exposure inventories can discover it. Older development reports are untouched.

## Verification

The focused suite passed **36 checks**, including whole-account selection,
parameter binding, prefix/target separation, work-only exports, draft preservation,
and existing policy/scoring regressions. The review landing page was verified in
the browser with empty reviewer fields and no recorded judgments. Private data
and selection/linkage artifacts remain ignored and outside Git.

An independent audit reproduced sampling, exclusions, parameters, training-only
forecasts and the blind page, checking **5,466 source-file bindings**. It confirmed
that sealing preceded target dispatch, that no target event entered a prefix,
and that prefix recovery preserved the exact frozen query. No target semantics
were assessed and no labels were assigned during that audit.
