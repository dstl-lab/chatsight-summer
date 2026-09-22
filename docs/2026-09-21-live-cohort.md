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

The initial instruction was “Continue,” alongside the standing project approval
for Gemini work. Automatic approval review rejected that send before process
creation, requiring approval for this specific private payload and destination.
`authorization.json` and `send-blocked.json` preserve that sequence; the earlier
38-prompt selection approval was not reused. Minchan then answered “Yes, approved”
to the disclosed cohort payload and its 12-request / 48-attempt ceiling.
`payload-approval.json` binds that reply to the unchanged scope, disclosure and
prior rejection before dispatch. The run sent historical private dialogue, cached
simulated replies, fixed policies and newly generated replies to Gemini. Exact
initial payloads and subsequent-prompt templates remain in ignored
`chat-cohort-live-v1/disclosure.md`. No private text or credentials enter Git.

## Status

**Complete and stopped.** The approved invocation ran from 13:34:30 to 13:37:13
UTC on September 21, 2026. All six conditions saved a tutor reply and a simulated
student reply. Every child exhausted its one-new-decision budget; this is a
simulation pause, not student silence. No replacement draws or labels followed.

| Operational outcome | Count |
| --- | ---: |
| Complete tutor replies | 6 |
| Complete simulated student replies | 6 |
| Generated no-replies | 0 |
| Tutor/student failures | 0 |
| Interrupted or unstarted conditions | 0 |
| Logical requests recorded | 12 |
| Adapter-attempt upper bound | 48 |

Actual retries and SDK HTTP attempts were not recorded. The initial blocked send
made zero requests. `dispatch.json`, `result.json`, `audit.json` and `OVERVIEW.md`
preserve the completed run, exact verification and readable exchanges. All 106
frozen files match, including original source and child startup files. Each tutor
prompt matches its frozen payload; each student prompt reconstructs exactly from
the frozen state and the generated tutor reply. Read-only replay reproduces the
saved result without changing group files. Independent terminal audit confirmed
the approval and call chronology, all six results, the exact 18 new group files,
and the overview against raw receipts. All 25 focused workflow tests passed;
the public engines, prompts and schemas are unchanged.

The outputs also show a limit of the demonstration: different policy instructions
did not consistently produce distinct tutor interventions. Both policies asked
for missing task text in case 1 and another step in case 2. Generated task text,
table values and an error claim are synthetic dialogue, not recovered notebook
state. None was established by execution or assignment verification. Do not read
differences between these single student draws as an effect of tutor policy.

The operational acceptance criterion is met: six bounded interactions can run,
remain linked to their supplied policy and reopen for inspection. Student fidelity
remains unvalidated. Keep this run closed and the generator unchanged; no further
manual review or generation is queued by this demonstration.

PR #44 merged the coordinator into the results branch, not main. This protocol
joins the combined PR #43, whose independent GitHub review remains required.
