# Existing evidence supports a formative educator task

**TL;DR:** Proceed to a small walkthrough of an educator decision task using
saved evidence. Defer claims about tutor-policy effectiveness or interface benefit.
The offline feasibility assessment is complete; no new student messages, labels,
notebook executions or participants were added.

## Concrete decision

**Would you keep this tutor reply, revise it, or inspect more evidence before
deciding? What in the material supports your choice?**

This narrows the [research question](2026-09-22-simulation-research-scope.md) to an
observable decision about the actual displayed reply. There is no objectively
correct keep/revise choice supplied by our logs. Inspecting more evidence and
making no change are legitimate outcomes.

## Evidence assessment

| Saved material | What is available | Appropriate use |
| --- | --- | --- |
| Completed mixed-eight review | Same historical tutor response and prefix; one recorded next message and two generated replies per case; existing help/work flags | Formative assessment of how contrasting outcomes inform an educator's decision |
| Earlier eight-case history comparison | Two input conditions, but all recorded next messages are help-only | Background evidence; keep its completed experiment closed |
| Three-scenario policy demonstration | Six generated tutor/student exchanges, beginning from cached simulated replies | Demonstrate the tool; no linked real-student outcomes for those generated interventions |
| Authored notebook runs | Actual local checks and preserved task history | Demonstrate execution; no historical student action ground truth |

The mixed-eight cases use one generator condition sampled twice. Five cases have
at least one disagreement with the recorded work flag; three have none. Preserve
all eight, both draws, and the identical pair. Do not select only conspicuous
mismatches or treat a draw as another learner. These existing single-reviewer
flags describe communicated work, not original effort, correctness or learning.

All eight contexts are readable enough for an evidence-use task, with limitations.
Two have no earlier turns; several rely on tutor descriptions of unavailable
notebook state. Case 1's reference is only the first of eleven recorded follow-up
messages. Neither silence nor the entire follow-up contribution is measured.
One recorded outcome does not make a different generated reply implausible.

## Proposed walkthrough, ready for participant availability

Use the first case in the existing packet order (source case 1) for at most two
internal walkthroughs, roughly 15 minutes each. This administrative selection is
for testing the task, not estimating an effect. No additional cases are selected
in response to participants' reactions.

1. Show the exact common prefix and historical tutor reply, the missing-context
   notice, and both saved simulated replies, clearly identified as simulated.
   Ask the concrete decision above and how confident the participant feels.
2. Add the first recorded reply, clearly identified as one observed outcome,
   with the eleven-message follow-up limitation visible. Repeat the decision and
   ask what, if anything, changed their reasoning.
3. Ask what the material cannot establish and whether the decision task was
   understandable. Retain unchanged decisions, disagreements and uncertainty.

No plausibility labels, recoding of student messages or model judgments are
requested. Existing private messages stay local; this memo contains none. A
facilitated walkthrough can use the saved material without building another UI.
Only appropriately authorized viewers should see the underlying course records.

Stop after the two walkthroughs. Their purpose is to check whether the task is
understandable and produces interpretable reasoning. Team involvement and prior
case exposure must be recorded; internal feedback is not an independent study.
If the task is unworkable, report that and stop rather than creating more examples.

This before/after sequence deliberately adds information. Any changed judgment
would be descriptive and confounded with order and additional evidence. A later
interface study would need matched information, appropriate allocation/order,
independently checkable evidence-use measures and a declared analysis before
recruitment. A preference or confidence change alone establishes neither better
teaching nor harm. The broad causal research question remains unanswered.

## Verification and handoff

The existing report replays exactly. Verified: 50 preparation pins, nine closure
pins and 37 inventory pins; separately, 38 frozen cohort data pins and 40 cohort
result-file pins (these lists overlap). Both cohort conditions start from the same
cached simulated reply, and all six tutor-to-student handoffs match their receipts.
Historical code pins were not rewritten to match current code. Independent
read-only review confirms the eight source joins and the context limitations.

Private `data/episode-pilot/educator-decision-feasibility-v1/check.py` reproduces
`assessment.json` and refuses a changed result. It verifies existing judgments;
it creates none. The remaining input is who can try the task: instructors/TAs,
research-team members, or no available participants. No invitations were sent and
no walkthrough has occurred. No new generation, manual student labeling or
infrastructure work is queued by this report.
