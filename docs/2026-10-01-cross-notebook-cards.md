# Cross-notebook communication-history comparison

**TL;DR:** Test whether a small descriptive card from earlier conversations
improves next-message form prediction over the same current conversation alone.
One fixed ten-account comparison; no new labels, retries or iterative tuning.

## Protocol frozen before selection or content access

Use the 72-account / 741-conversation metadata subset verified in
[history availability](2026-10-01-history-availability.md). Each candidate has at
least ten earlier nonempty query events across at least two notebook identities
different from its starting notebook. This is a history-rich course-account
subset, not verified students or a representative random DSC 10 student sample.

Use seed `cross-notebook-cards-v1-20261001`, SHA-256 over
`seed:kind:value`, and lexical identifiers to break hash ties. Rank accounts and
take the first ten; independently rank each account's qualifying conversations
and take the first. Freeze these before retrieving event metadata. Within each
selected conversation, rank the original third-or-later-query checkpoints that
immediately follow a nonempty tutor response in event-ID order. Select one before
checking its complete prefix for nondecreasing timestamps through the target;
equal timestamps use event ID. Retain an invalid selection as a failure, without
reranking, replacement or repairing its order.

History sources must be complete, query-bearing conversations ending strictly
before the target conversation starts, with a single complete notebook identity
different from the target's first-chat identity. Exclude all ten selected target
conversations from every history pool. Retrieve event metadata first; verify
counts, account/notebook bindings and times against the saved receipts.

Select at most twenty earlier student queries per matched card. Reserve the
latest query from each of the two most recent distinct eligible notebooks, ranked
by `(created_at, event_id)`, then fill remaining slots with the most recent other
queries. Present selected events chronologically. Preserve repeated/blank-like
events, with no wording-based replacement. Freeze these event IDs before fetching
content. Historical tutor text is unnecessary. Fetch only selected history
queries and the complete current-conversation prefix; references stay unfetched
until generation has ended or the preparation is closed as unusable.

## Arms and donor assignment

All arms receive the identical full current-conversation prefix, including the
complete current student/tutor exchange. Reuse the existing continuation schema
and prompt renderer. The additional card contains only existing evidence-card
statistics and student-message count, with a short scope/uncertainty instruction.
It contains no verbatim examples, notebook names, account IDs or source hashes.

- **Generic:** current conversation only.
- **Matched:** add the selected account's earlier-history statistics.
- **Other account:** add a donor card as a diagnostic, with matched-versus-generic
  remaining primary.

Choose donors only among the other nine selected accounts, from their eligible
history sources also ending before the recipient's conversation starts. Exclude
the recipient's notebook as well as the donor's target notebook and all selected
target conversations. Require at least two earlier notebook identities and enough
queries to equal the recipient's matched-card sample count. Cap donor evidence
using the same reservation/recency rule. Prefer the largest Jaccard overlap of
available notebook-identity sets with the recipient's eligible history set;
break ties by `seed:donor:recipient_account:donor_account`. Reuse of a donor is
allowed and will be reported. Do not match on message wording or form statistics.
If none qualifies, retain an unavailable donor arm without replacing an account.

Reusing only metadata for matching cannot ensure equal task exposure. A donor's
card is constructed as of the recipient cutoff; do not blindly swap cards built
from later histories. Different notebook identities do not establish distinct
tasks or enduring personality. Cards are recent communication samples.

## Budget, measures and stopping

Prepare five draws per available arm: 100 primary requests and at most 50 donor
requests. Use Gemini 2.5 Pro, temperature 1, maximum output tokens 8,192, timeout
120 seconds, one worker, SDK/adapter attempts one; leave seed/top-p/top-k/thinking
settings omitted as in the prior comparison. Supply the continuation JSON schema
through the SDK's `response_json_schema` field in every arm. Cycle through all six arm-order
permutations across case/draw triplets, omitting unavailable donor slots. Freeze
model/SDK/schema, sources, code, prompts and schedule before dispatch. Standing
project authorization applies; an actual automatic-review rejection still needs
the requested exact-payload approval.

Reuse the five-draw fair multicategory form Brier score: twelve literal
length/newline/backtick categories plus valid no-reply. Primary is equal-account
matched minus generic, with per-account outcomes and ten-account missing-outcome
bounds. Other-account contrasts are secondary. Score two explicit empirical
baselines from the exact matched-history sample and current-prefix student turns.
These distribution baselines do not generate coherent replies.

Technical failures, pending and unattempted calls are missing, never no-reply.
Require all five valid decisions for an arm score; keep failures and unfinished
batches without restarting. A donor failure does not erase a primary pair.
Record model versions and actual counts. No significance/population or overall
realism claim follows from ten accounts, five draws and one recorded future each.
The reference is a recorded return to chat; silence probabilities and notebook
action sequences remain outside the observable endpoint.

Before dispatch, verify all ten selected prefixes and history samples are usable
and still meet the frozen evidence requirement, and report descriptive card/form
contrast without looking at targets. If any selected primary input is unusable,
or all ten matched cards are identical, close preparation as insufficient rather
than replace cases or change the cap. Donor absence is reported separately. One
completed or interrupted batch and one report close the study, even if negative
or inconclusive. No prompt tuning, automatic follow-up or default adoption.
