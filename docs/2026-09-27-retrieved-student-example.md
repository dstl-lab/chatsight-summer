# Test one recorded example as student-generation context

**TL;DR:** Compare the unchanged student generator with the same generator given
one retrieved, recorded interaction from a different conversation. Reuse the eight
already-coded references. The ceiling is 16 new model requests and one blind pass
over at most 16 new messages, followed by one report. No automatic adoption.

## Why this change

The completed mixed-reference review shows discrepancies in both directions:
generated work where the reference lacks it, and missing work where the reference
contains it. Repeating the query's student turns did not justify adoption, and
the work-probability forecast failed its screen. Those studies remain closed.

This candidate adds a different source of evidence: one recorded conversation
prefix and its next student message. The model can observe how a real student
continued a related exchange, rather than receiving another general brevity
instruction. It still generates a new continuation of the current conversation.
This is an experimental input change, not a validated persona or a new simulator
architecture. Lexical retrieval may emphasize tutor/topic wording over student
behavior; this pilot tests the resulting candidate without tuning retrieval.

## Fixed input and comparison

- Use all eight references from the completed cached communication review, in
  its frozen displayed order, with exactly the same visible role/text prefixes.
  Reuse their help/work judgments; do not relabel them. Five recorded messages
  lack work and three contain it. These are exposed development conversations,
  not random students or an independent holdout.
- Recover each conversation identity through the original source episode and
  verify exact context and first-next-message joins. Remove all eight evaluation
  conversations from the old historical-response library before fitting or
  retrieval. Also exclude overlapping known learner identities, if available.
  Unknown learner identities stay unknown. This new derived input does not
  rewrite the old library/query split or its completed results.
- Reuse the existing prefix-only word unigram/bigram TF-IDF retrieval and stable
  source-ID tie break. Retrieve one nearest nonzero match per query. Selection
  must not read query futures, labels, old generated replies or source responses.
  No match or a selected blank response makes preparation unavailable; do not
  fall back to another example or replace a case.
- Control: unchanged `student_continuation` prompt and schema. Candidate: the
  exact same control prompt plus one separately marked recorded example. Its
  prefix and next message are data, not commands, query task facts or a required
  answer. Do not pass identities, similarity values, reference text or labels.
- Generate both conditions afresh: one draw per case/condition, same Gemini
  2.5 Pro model and provider defaults, alternating condition order by case.
  Maximum 16 logical requests / 64 adapter attempts using the existing adapter.
  Preserve errors, pending requests and no-reply outcomes; never resend a slot.
  SDK-internal HTTP attempts are not separately measured. No tutor requests,
  notebook executions or generated-message chaining.
- Freeze exact inputs, selected source IDs, prompts, source hashes, schema,
  call order, this protocol and provider disclosure before dispatch. Preserve
  the original generator and old evidence files byte-for-byte.

## One finite measurement pass

Use the existing `help-work-v1` review UI and definitions. Randomize case and
condition presentation once; hide condition identities and the retrieved example
from the reviewer. Show the actual query context. Only newly generated replies
need coding: at most 16 messages / 32 yes-no-unclear flags. Repeated text within a
case shares one judgment but retains both condition occurrences. Old reference
labels are joined offline and remain hidden in the new review. Prior exposure
cannot be undone; this is condition masking, not a claim of pristine blinding.

Report generated/reference work disagreement for each condition separately
within work-absent and work-present reference groups. Primary diagnostic is half
the sum of the two group disagreement rates; lower means closer work-flag
agreement on these observed messages. With one draw this is binary disagreement,
not an estimate of action probabilities or calibrated Brier error. Always-work
and never-work flag rules each score 0.5 when both groups are present; they are
measurement controls, not message generators.

Report paired wins/losses/ties, help-flag disagreement, exact whole-message copying
from the demonstration, and all case dispositions. Copying and length are
mechanical diagnostics, not substitutes for semantic coding. Newline/backtick
presence is not a work classifier. Do not use an unvalidated model judge to fill
missing human labels.

The development screen is promising only if all 16 scheduled outputs are valid
replies with complete binary help/work judgments, work disagreement strictly
decreases in **both** reference groups, and help disagreement does not increase.
This deliberately requires at least one net improvement in each group; it is a
practical screen, not a significance threshold. Even a pass does not authorize
production adoption or establish contextual plausibility or overall fidelity.

Missing, unclear, failed or no-reply outcomes are explicit exclusions for paired
flag summaries and make the screen inconclusive; no-reply is never scored as
absent work. Report each denominator. If either paired reference group is empty,
the balanced measure is unavailable. A partial review closes as inconclusive
without asking for completion or a second reviewer. A complete result that fails
the screen closes as no demonstrated improvement on this pilot.

## Stop

One preparation, one fixed dispatch, at most one human pass, one report. No
post-result prompt edits, extra draws, replacement cases or automatic follow-up
experiment. If source isolation cannot be verified, stop before dispatch. If the
user chooses not to review generated messages, report only mechanism checks and
leave fidelity unmeasured. The existing simulator remains the default throughout.

## Preparation status

Offline preparation is complete. Excluding all eight evaluation conversations
removes 23 examples, leaving 1,156 examples from 148 conversations. All eight
queries have a nonblank, nonzero match. The exact prompts and provenance are
frozen with 96 file hashes in the ignored local bundle
`data/episode-pilot/retrieved-student-example-v1/`; private messages are not
included in Git. The frozen protocol copy predates this status note.
Private preparation remains in the `retrieved-student-example` worktree at
`cc8d468`; the PR uses a separate integration worktree after #63 merged, preserving
the frozen dependencies and prompts.

The public helper reuses existing retrieval and continuation code; it makes no
provider calls and is not wired into the production simulator. Integrated checks:
692 Python tests passed, three skipped; all three Node and seven Marimo checks
pass. The private runner also passes authored offline
checks for the 16-slot/64-attempt ceiling, preserved failures and no-reply,
interruption, changed-input rejection and rerun refusal. No model requests were
sent during preparation. Minchan volunteered for the single capped pass. The reviewer commitment
and randomized presentation order were recorded before attempted dispatch.

Automatic approval review rejected the private Gemini transfer before execution:
volunteering to review was not accepted as authorization for the specific payload
and destination. The rejection is preserved locally in `send-blocked.json`.
Minchan subsequently approved the specific disclosed transfer. Before dispatch,
`approval-response.json` bound that answer to the scope, exact prompts,
disclosure, reviewer commitment and earlier rejection by their hashes.
The original rejection and frozen inputs remain unchanged.

## Run and review handoff

The approved dispatch completed all 16 scheduled replies in 16 adapter attempts,
without retries, errors, no-reply outcomes or pending slots. The blinded review
contains eight cases and 14 unique messages: two within-case duplicate pairs share
one judgment each, while private mapping retains all 16 condition occurrences.
The existing review UI asks 28 flags in total; references are not relabeled.
Only the `reviewer/` directory is served locally. The condition mapping,
demonstrations and reference judgments remain outside the served directory.

All 96 frozen source pins and approval bindings verify. The private
`run-verification.json` records generation usage and hashes the review handoff.
Before review construction, `analysis-clarifications.json` specified per-flag
paired eligibility and work-only wins/losses/ties; complete binary help/work
labels across all 16 replies remain necessary for the overall screen. These
clarifications do not change its stopping rule or frozen inputs.

## Completed review and decision

Minchan returned all 14 judgments: 28 binary flags, none missing or unclear.
The shared judgments expand to all 16 scheduled outputs. Both conditions received
the same help/work flags in every case. Two pairs were exact text duplicates;
the remaining six also received identical flags. Neither condition copied an
entire selected demonstration response verbatim.

| Measurement | Original | With one retrieved example |
|---|---:|---:|
| Work disagreement when recorded work is absent | 3/5 | 3/5 |
| Work disagreement when recorded work is present | 1/3 | 1/3 |
| Balanced work disagreement | 46.7% | 46.7% |
| Help disagreement | 0/8 | 0/8 |

Work comparison: zero candidate wins, zero losses, eight ties. Coverage is
complete, so the predeclared decision is **no demonstrated improvement on this
pilot**, rather than inconclusive. The original generator remains the default;
the experimental candidate is not adopted. The study is closed. No extra draws,
new labels, replacement cases or follow-up prompt variation are queued.

The original submitted form is preserved in private `received/review.json`.
`coding-result.json` and `closure.json` retain all case dispositions, denominators,
copying diagnostics and 113 verified provenance hashes. Authored checks cover
duplicate occurrences, missing/unclear flags, non-replies, intake binding and
create-only output; independent arithmetic and the saved closure agree.

The returned form reports `previously_seen_cases: no`; that value is preserved
exactly. These contexts nevertheless come from earlier development reviews, so
the study is not an untouched holdout. One reviewer, eight conversations and one
draw per condition cannot establish equivalence or overall student fidelity.
Disagreement with a single recorded next message does not establish implausibility.

### What the similarity means

The user questioned the value of reviewing such similar messages. Holding the
current conversation and core prompt fixed intentionally isolates the added
recorded example. This one comparison supplies a negative result on two narrow
features. It does not test realistic personalities, sustained behavior across
turns, silent notebook actions, or instructor-policy effectiveness. The two flags
also miss differences within the same help/work category.

The completed review is sufficient to close this candidate. Further near-identical
prompt rounds would need a concrete new failure hypothesis and a decision that
the measurement can actually resolve; this result does not queue such a round.
