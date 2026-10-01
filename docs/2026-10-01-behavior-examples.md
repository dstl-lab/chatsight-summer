# Concrete behaviors in the recorded course conversations

**TL;DR:** The records support more useful distinctions than message length:
requesting a solution versus a hint, asking for checking without pasting work,
reporting an error, correcting the tutor, and moving between questions. These
can coexist and change within one account's conversation. They are candidate
observable behaviors, not validated personality types or a new labeling campaign.

## Read-only database check

On October 1, a bounded read-only query retrieved 134 events: 67 tutor-query events
and 67 tutor-response events from the ten already-exposed course accounts in the
completed cross-notebook comparison. Retrieval included only the frozen current
prefixes and their now-exposed next replies. All rows exactly match the previously
saved source records. No fresh comparison account was opened, no student code was
executed, and no model requests or human labeling were needed. The tunnel is closed.

This is a retrospective qualitative reading of selected history-rich course
accounts, not a random student sample or an estimate of behavior frequencies.
Account/student eligibility is unverified. Repeated text can reflect repeated
messages or duplicated logging; no repetition rate is estimated. Private event
IDs, source hashes and example bindings are in ignored
`data/behavior-examples-v1/{events,findings}.json`. Public examples below are
paraphrases, not verbatim student records.

## Examples and what the simulator must represent

| Observable behavior | Example from the retrieved records | Simulation implication |
|---|---|---|
| Direct help requests followed by question movement | Case 1 makes short requests about successive question numbers, then asks for a fix on another question. | A next message can request help elsewhere instead of supplying the answer invited by the latest tutor reply. A changed question number does not establish completion of the previous task. |
| Deliberately requesting limited assistance | Cases 5 and 9 explicitly request hints; case 9 later asks for another small hint. | Preserve the requested amount of help. Do not treat every request as asking for a complete solution. |
| Asking for checking without pasting code | Cases 4, 7 and 10 ask what is wrong or whether work is correct without including substantive work in those messages. | Chat can refer to work held elsewhere. Missing pasted work does not mean no attempt or unchanged notebook state. |
| Reporting failures and supplying diagnostic artifacts | Case 6 pastes failing-test output, a runtime warning and a name error during its conversation. | A follow-up may communicate a problem artifact instead of explaining reasoning. Pasted output is a student report, not an independently linked execution. |
| Redirecting the task after difficulty | Case 6 explicitly asks to move on after reporting test failures and supplies the scaffold for another question. | Task movement need not follow success. The record supports redirection, not an inferred emotional state or permanent abandonment. |
| Constraining or questioning tutor guidance | Case 2 says a suggested approach has not been covered; case 10 questions the tutor's interpretation of the requested result. | Students can reject a suggestion or correct the task framing. This does not establish their knowledge level or whether their correction is right. |
| Reporting partial resolution | Case 3 distinguishes one operation that worked from a related operation that did not. | Mixed progress is possible; avoid treating a turn as either total success or total failure. |

Case 9 is particularly useful for the persona question: the same conversation
includes conceptual explanation requests, work checking, a request to explain a
programming construct, and repeated requests for small hints. This demonstrates
within-conversation variation. It does not establish transition probabilities or
prove stable preferences across tasks.

## Relevant previous write-ups

- [Student behavior diagnostic](2026-09-11-student-behavior-diagnostic.md): in one
  code-rich conversation, advice is incorporated partially and then more fully in
  a later recorded code contribution. An accumulator inconsistency disappears in the next
  recorded attempt. All twenty code-start follow-ups in that audit came from one
  conversation; code overlap cannot distinguish copying from independent work.
- [Student reporting audit](2026-09-11-student-reporting-audit.md): an assistant
  reading of 64 recorded follow-ups from twelve exposed development conversations
  found no clear success-only announcement, three definite problem-bearing
  contributions from two conversations, and nine ambiguous problem reports. The
  sole passing-test report also contained a failed subtest. These are not human
  ground truth or evidence that students never report success.
- [Notebook context recovery](2026-09-11-notebook-context-recovery.md): one
  repeated checking request followed four relevant failed checks between tutor
  reply and follow-up. Another complaint followed a relevant failed check by
  4.98 seconds. Actual code changes remained unknown, but the chat repetition
  alone did not describe everything that happened.
- [Notebook snapshot pairs](2026-09-15-notebook-snapshot-pairs.md): two compatible
  capture pairs showed one and four changed code positions. A third had a net
  increase of three code cells with unresolved alignment. These establish some
  net work differences, not the intermediate edit/run sequence or execution order.
- [Evaluator source disagreement](2026-09-30-evaluator-source-disagreement.md):
  in one saved eight-case comparison, human judgments marked all eight recorded
  next messages as containing no substantive work but 23/32 current-exchange and 26/32 history-generated
  replies work-present. This is direct prior evidence of a communication-choice
  mismatch in those saved outputs, not a population realism score. Human and
  automatic help judgments diverged substantially over implicit checking.

The [September 29 refresh](2026-09-29-notebook-data-refresh.md) found richer
execution/source-change logging, but those detailed records came from one account
with strong instrumentation-test indicators. They support testing replay mechanics,
not estimating natural student behavior. Earlier sparse notebook coverage and this
newer instrumentation finding should not be conflated.

## What this suggests for labels

Use separate dimensions when the evidence supports them: requested assistance
(hint, explanation, solution, checking), material supplied (work, error/test
artifact, neither), and task relation (same, different, unclear). They can overlap;
a pasted error plus a help request should retain both. Observable notebook changes
and executions form a separate evidence channel, rather than being inferred from
message wording or silence.

Explicit requests and source-linked artifacts provide the clearest examples.
Implicit intent remains harder: a bare code submission may also seek checking,
which is precisely where the previous evaluator disagreed with human judgments.
These examples therefore motivate a behavioral target but do not validate an
automatic labeler. The current task ends with this evidence summary; no new
classifier, persona taxonomy, generation batch or reviewer queue is introduced.
