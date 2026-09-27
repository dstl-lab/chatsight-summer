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
interruption, changed-input rejection and rerun refusal. No model requests have
been sent. Reviewer availability for the single capped pass is pending; fidelity
remains unmeasured.
