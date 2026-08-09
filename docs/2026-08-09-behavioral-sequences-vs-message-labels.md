# Behavioral sequences vs. message labels — ingested position memo

Date ingested: 2026-08-09. Provenance: received from Minchan (author not
named in the handoff — a collaborator's write-up; "Simulated student
archetypes (Minchan's idea!)" is the internal attribution marker). Status:
**position memo under discussion, not an adopted decision.** It argues for
a direction change that touches CLAUDE.md's core framing, so per working
style it is recorded here before any code responds to it, with its
tensions made explicit below.

---

## The memo (as received)

**TL;DR:** Message labels miss too much context and do not give professors
clear actions, so we should instead connect tutor chats to students'
notebook activity and outcomes to reveal useful behavior patterns.

### Understanding How Students Use the AI Tutor

We explored whether message labels could help professors understand how
students use the AI tutor, drawing on research and several months of our
own testing.

**Our original goal was to label each student message so a professor could
see how students were using the AI tutor.**

### Why message labels are not effective

**Message labels are not effective because complex messages lack one
agreed meaning and the resulting categories rarely guide professor action;
they work better as intermediate signals than as final insights.**

First, a message often does not contain enough context to label it
correctly. In our work with ChatSight, simple messages such as
`"give me the answer"` were easy to classify, but complex messages were
difficult to map to either an agreed label or the specific interpretation
a professor wanted. We tried capturing as much context as possible,
including intent, surrounding messages, the problem, and the assignment,
but this was still not enough because meaning also depended on what the
student had already done and what the professor wanted to learn. This
matches *Procedural Questions Predominate Student-LLM Chatbot
Conversations*, which found that four schemas could not cover 6,113
student messages, and *Unpacking Vibe Coding*, which achieved reliable
labels only through repeated researcher review and codebook refinement.

Second, the labels are not very useful to a professor even when they are
accurate. Our testing mostly produced category counts or identified a
difficult question, but the difficulty was usually already clear from
reading the question, while the most valuable and complex student requests
were the hardest to summarize with a shared label. The useful result in
Brender et al. (AIED 2024) was not the taxonomy itself, but the later
finding that different patterns of use were connected to performance and
learning. Instructor studies support this distinction: professors asked
for common mistakes and changes in behavior over time rather than label
counts (*Meta-Reflective Dashboard for Instructor Insight*), and broader
dashboard research finds that descriptive information often fails to
produce a clear teaching action (*Co-designing a Learning Analytics
Cockpit with Teachers*).

### What could work

**Connect each tutor conversation to what the student did before and
after it, then use repeated patterns to show professors where and how
students are struggling.**

For each assignment question, connect the sequence **attempt → error →
tutor conversation → code change → test result**. This distinguishes
students who ask before trying, ask after real effort, copy an answer,
revise an answer, or continue independently. Repeated patterns could point
to a specific action, such as rewriting an unclear question, adding
scaffolding for a common error, or changing a tutor response that
encourages copying. The professor could then compare future course
offerings to see whether that action changed student behavior.

What the sequence could reveal:

- If many students ask before attempting the question, the instructions
  may be unclear or the task may be too easy to hand off to the tutor.
- If students repeatedly fail before asking, they may need better
  scaffolding or a review of a prerequisite concept.
- If students paste the tutor's response and immediately pass, the tutor
  may be completing the work rather than supporting learning.
- If students revise their own code and then succeed, the tutor is more
  likely supporting productive problem-solving.

Where the sequence data comes from:

- **Attempt:** Jupyter can record when a student edits or runs the active
  code cell before asking the tutor.
- **Error:** Jupyter cell outputs can capture whether an execution failed
  and the resulting error or traceback.
- **Tutor conversation:** the tutor already logs each student message,
  tutor response, timestamp, conversation ID, and assignment context.
- **Code change:** Jupyter can record later cell edits or snapshots,
  allowing comparison of the student's code before and after the response.
- **Test result:** existing autograder events already record the question
  ID, pass/fail result, output, and timestamp.

### Simulated student archetypes

The existing labels would be a weak foundation for simulated students
because complex messages are often assigned uncertain or professor-
specific categories. If we build archetypes from those labels, the
simulations will inherit the same ambiguity, and labeling every message
creates an expensive step that may not improve the grouping.

**The behavioral sequence could provide a stronger foundation because
student groups can emerge from observable patterns across attempts,
errors, tutor use, code changes, and results.** Labels can be added
afterward only to help describe the discovered groups. These grounded
archetypes could show instructors how students with different behavior
patterns move through a complete session with the tutor.

---

## Tensions with current project positions (recorded, not adjudicated)

The memo's two empirical complaints are partly what this repo's last two
weeks of instruments were built to measure, so the discussion should
happen against those numbers rather than in the abstract:

1. **"Complex messages lack one agreed meaning."** Partly confirmed here:
   the first two-annotator ceiling was 70% on 10 joint pairs, and the old
   Confusion label was re-convicted 0/8 by a second blind human. Partly
   answered here: per-label reliability varies widely (Seeking Validation
   κ=0.75, pastes-error precision 1.00), which is exactly why invariant 3
   admits labels *per label*, not as a schema. The memo's claim is true of
   some labels and measurably false of others; the admission threshold is
   the instrument that separates them.
2. **"Context is never enough."** The context-ablation probe and the
   move/latency facets were built for this. What the memo calls missing —
   what the student *did* before asking — is real and is not in the chat
   context; no prompt engineering recovers notebook state we do not log.
   On this point the memo identifies a genuine ceiling of the current
   data source, not a fixable prompt defect.
3. **"Labels rarely guide professor action."** Consistent with the
   project's own claim discipline (invariant 5: the contribution is a
   screening instrument, not a teaching prescription). The memo pushes
   further: even as description, counts underwhelm. This is a fair attack
   on Phase 2's standalone value and should be tested in the instructor
   study rather than assumed either way.
4. **Archetypes from label trajectories (CLAUDE.md Phase 2–3) vs.
   archetypes from behavioral sequences.** The memo proposes inverting
   the pipeline: cluster on observable sequences, use labels only to
   describe clusters. Note the two are not mutually exclusive — the
   memo's own framing ("labels work better as intermediate signals than
   as final insights") is compatible with labels as *state-space
   dimensions* inside a sequence, which is closer to what CLAUDE.md
   already says an agent is (a thing that moves through label-space).
   The genuinely new element is the notebook/autograder event stream,
   which this repo currently has no access to.

## What adopting any of this would require (facts, not advocacy)

- **New data sources**: Jupyter cell-edit/run/error telemetry and
  autograder events joined to tutor logs. None of this exists in
  `dsc10_tutor_logs` as ingested here; it is new instrumentation and a
  new ingest surface (and for past quarters, may simply not exist).
- **IRB**: notebook keystroke/edit telemetry is a materially different
  data category from chat logs; the existing protocol position (open
  decision #4) would need review before any collection.
- **Ownership**: same unresolved question as open decision #5 (who owns
  the tutor/notebook surface) — the memo's sequence requires cooperation
  from whoever runs the Jupyter environment and autograder.
- **Timeline**: December 2026 evidence targets (Phase 0 + a Phase 2
  descriptive result) are currently within reach on chat data alone. A
  sequence pipeline restarts the ingest clock on a data source we do not
  yet have.

## Status

Open decision for Minchan and Sam (adds to the CLAUDE.md open-decisions
list): whether behavioral sequences become (a) the new grounding layer
with labels demoted to descriptors, (b) an additional signal joined to
the existing label state space, or (c) future work noted in the papers'
limitations. No code in this repo responds to this memo yet.
