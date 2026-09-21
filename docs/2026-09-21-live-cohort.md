# One live round through the three-scenario workflow

**TL;DR:** Use the prepared historical group for one operational demonstration:
three conversation scenarios, two fixed tutor policies, one new student decision
per condition. At most 12 Gemini requests and 48 adapter attempts. Preserve every
outcome and stop; no labels, rerolls, judge calls or generator changes.

## Fixed scope

Reuse `chat-cohort-v1/historical-group`, prepared from frozen handoff cases 1–3.
Each policy starts from the same cached simulated student reply within a case.
The source conversations, first replies, policies, child manifests, budgets and
execution order are already saved. They were selected before this run; outcomes
will not change eligibility. Original frozen handoff files remain untouched.

| Policy | Instruction |
| --- | --- |
| A | Give one concise next-step hint. Ask at most one focused question; do not provide a complete solution. Ask for essential missing task details instead of inventing them. |
| B | Give a concise direct solution when the available context supports it. Ask for essential missing task details instead of inventing them. |

Run the existing coordinator in order 1A, 1B, 2B, 2A, 3A, 3B. Both tutor and student
use the saved Gemini 2.5 Pro model and existing provider defaults. Each ready
condition permits one tutor reply followed by one student decision: no more than
six new student decisions or twelve logical requests. The four-attempt adapter
sets an upper bound of 48 attempts; actual retries and SDK HTTP attempts are not
individually recorded by these existing workspace paths.

Freeze the exact six initial tutor prompts, current child states and both schemas
before dispatch. Student prompts are produced by the existing function from the
frozen state plus that condition's generated tutor reply; those final strings
cannot exist before generation. Preserve their templates and implementation hashes
now, and verify the exact delivered prompts from the saved receipts afterward.
No private reference answer, recorded future or evaluation label is added.

## Acceptance and stopping rule

The operational question is whether the coordinator can continue the six bounded
conditions and reopen an inspectable result for each. Report successful replies,
generated no-replies, tutor/student failures, interrupted operations and unstarted
conditions separately. Report the logical requests represented by receipts, the
fixed request limit and remaining decisions. Verify frozen source/startup files,
policy delivery and tutor-to-student linkage. Viewing makes no model calls.

Stop after this invocation and one saved overview. An error is retained, not
replaced by another sample. Do not score plausibility, code correctness, learning,
sentiment or policy quality, request another manual review batch, or optimize a
prompt based on this small demonstration. Preserve the closed recognition study.

## Limits and authorization

These are three conversation scenarios, not identified or representative students.
The starting reply is already simulated; case 2 has only two recorded dialogue
turns. Both agent roles use the same unvalidated model. A generated no-reply is a
model decision, not evidence of student abandonment. Chat text cannot establish
hidden notebook edits, code execution or autograder outcomes. The existing student
prompt omits origin markers; generated tutor interventions are stored as `scripted`
in dialogue but linked to their actual provider receipts. Do not infer human
authorship from that stored marker. There is no causal or fidelity estimate here.

The current user instruction is “Continue,” alongside the standing project
approval for Gemini work. The private authorization record must state that basis
without treating the earlier 38-prompt selection approval as approval of this new
payload. This run would send historical private dialogue, cached simulated replies,
the fixed tutor policies and newly generated replies to Gemini. Exact initial
payloads and subsequent-prompt templates are in the ignored
`chat-cohort-live-v1/disclosure.md`. No private text or credentials enter Git.

## Status

Preparation is complete: six untouched conditions, 106 frozen files, exact tutor
prompts and student-prompt templates. Offline verification reproduces the saved
initial state, and the 25 cohort/pair/workspace tests pass. Independent review
reconstructed all six prompt pairs and found no material defects. The private
runner uses the existing coordinator, checks frozen files and initial state, and
creates an exclusive dispatch receipt before any calls. A second invocation
cannot replace the first.

Automatic approval review rejected the send before process creation: private
student dialogue and generated content need specific approval for this payload
and the Gemini destination, beyond the standing grant or earlier selection
approval. `send-blocked.json` preserves that reason and binds the frozen scope
and disclosure. No dispatch receipt exists; zero new requests or adapter attempts
occurred. Offline verification after rejection confirms all six conditions remain
untouched. The next step is exact-payload approval, then this one invocation;
no alternative transfer, extra preparation batch or manual labeling is needed.

PR #44 merged the coordinator into the results branch, not main. This protocol
joins the combined PR #43, whose independent GitHub review remains required.
