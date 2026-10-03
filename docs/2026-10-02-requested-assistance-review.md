# Requested-assistance human review: preparation only

Prepare the six already validated development records for one bounded human
review. Do not supply judgments, refit probabilities, inspect fresh accounts or
open any closed holdout. Keep conversation text, event mappings and response
files private under ignored data. Do not upload this packet to Library: automated
redaction cannot establish that student text is safely deidentified.

Two physically separate offline HTML files provide prefix-only and next-message
outcome views. The first asks about the most recent student turn in the prefix,
using only context at/before that turn; later tutor replies and the target outcome
are absent. The second shows the next student message with its full preceding
conversation, only after the reviewer loads a completed first-stage response.
This is order protection against accidental exposure, not cryptographic blinding.
Existing assistant/human judgments remain exclusively in separate provenance.

A new rubric distinguishes simultaneous requested-assistance kinds from uncertain
alternatives, and no expressed request from unknown. Preserve evidence line
selectors and reviewer/exposure attestations. Blank responses stay genuinely blank.
Stop after preparation, source/display verification and tests; no human judgments
are performed by the assistant.

## Prepared artifact

Private folder:
`data/requested-assistance-human-review-v1/`

- `01-prefix.html`: six previous-student-request judgments, no outcomes or later tutor replies.
- `02-outcome.html`: six next-message judgments with preceding conversation; requires a completed prefix response to unlock.
- `01-prefix-blank.json` and `02-outcome-blank.json`: all 12 judgments blank, with null status/labels and empty evidence.
- `README.txt`: local access and response-return instructions.
- `private-mapping.json`: anonymous case/turn IDs to original source IDs and displayed-line hashes; do not consult during first-pass review.
- `manifest.json`: source, exporter, template/script and output hashes, stable stage packet IDs, six cases and zero supplied judgments.

Open `01-prefix.html` on the connected Mac, for example through Finder's Go to
Folder and this absolute folder path:

`/Users/minchan/github/chatsight-summer/notebook-data-refresh/data/requested-assistance-human-review-v1`

Finish and download stage 1 before opening stage 2. Stage 2 accepts only the right
completed prefix packet, with all six unique cases, valid evidence and reviewer
attestations. It binds the exact prefix response bytes by SHA-256 without showing
the prefix judgments. Both completed JSON response files should be returned through
the private local workflow. No responses have been generated or submitted here.

## Review task and response contract

Rubric ID: `requested-assistance-human-v1`. It is a new, explicit review rubric,
not a replacement for prior labels. No conversion into the policy is implemented.

The reviewer chooses Definite request (one or more of hint, explanation, solution,
checking, unspecified), No expressed request (empty set), or Unclear (null labels
and an explanation). Multiple actual requests can have multiple labels; competing
interpretations of one request belong under Unclear. Unspecified is a definite
help request whose kind is not supported, not a synonym for uncertainty.

Evidence is a span at whole-line granularity: anonymous turn ID plus original
line number. Every judgment cites the highlighted student message, with preceding
lines when needed. No request cites every nonblank highlighted-message line.
No free-text quotation is required. The line-to-source/display mapping is pinned
privately. Reviewer alias, prior exposure, personal-human-judgment attestation,
no-old-label/model-consultation attestation and prefix-before-outcome order are
recorded. Prior exposure must be disclosed, not assumed absent.

Six clearly marked synthetic worked examples explain the rubric but supply no
judgments for the six real cases. Example: “Just a hint, please” illustrates hint;
“Explain range, and check my loop” illustrates two simultaneous requests; “2?”
without resolving context illustrates uncertainty. Existing coarse human and fine
assistant labels never enter the reviewer payloads.

## Privacy and scope

Account/conversation metadata, original case IDs, source paths, timestamps and
existing coders/labels are withheld from review pages. Displayed turns use R01–R06
and T01… aliases. Known identifiers, emails and URLs are subject to an explicit
redaction pass; this particular display required zero replacements. That does not
prove the text has no names or indirect identifiers. This is not certified
deidentification, and no Library/cloud upload was made. Raw source packets,
private mappings and student text remain under ignored data. All source text is
rendered literally with safe JSON embedding and textContent; no live links or
remote resources are loaded. CSP blocks network connections and form submission.

Physical stage separation and the prefix-file gate prevent accidental outcome
exposure. A reviewer can deliberately inspect the second HTML source or bypass
client code; the packet cannot prove blinding or human identity. The records are
already-exposed development cases, not an independent blinded evaluation. Viewing
these forms neither validates a label nor fits a policy.

## Verification

Four new authored exporter tests first failed on the missing implementation and
then passed. Forty focused Python tests pass across the exporter, evidence adapter
and distribution module. Sixteen authored Node scenarios cover multi-label
responses, unknown/none distinctions, full-line absence evidence, bad line refs,
missing declarations, wrong stage/packet, duplicate cases and incomplete drafts.
The draft test caught an overly strict completion rule; drafts now preserve partial
work. Completed-stage requirements remain strict. JavaScript syntax checking passes.

Private artifact checks verified: six cases in each page, same anonymous case IDs,
12 genuinely blank template decisions, exact source/display bindings, no target
in prefix views, no displayed account/conversation identifiers, and matching
manifest hashes. The prior validated packet/report and all upstream fingerprints
were checked before export. Original policy, distribution and evidence modules,
evidence tests, CLAUDE.md and TASKLIST.md remain unchanged.

Automated browser preview was unavailable: Chrome automation was not connected,
and the in-app browser rejected file:// pages under its URL protocol policy.
No browser-security workaround was attempted. Visual rendering and actual browser
download behavior are therefore not claimed as verified; the reviewer can open
the local HTML files manually. The plain blank JSON files are also available.
No new package, server, external transfer, model/database call, human judgment,
policy change, commit or push was made. Stop for human review of this packet.

Full Python suite: **1,131 passed, three optional container checks skipped**, one
existing dependency warning, in 50.90 seconds. All 16 authored client validation
scenarios and JavaScript syntax checks passed. No real response fields were filled.
