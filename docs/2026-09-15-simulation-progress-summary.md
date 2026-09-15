**We have a working research prototype for simulated students, plus evidence of a
specific behavior mismatch. We have not yet validated realistic student personas,
learning, or transfer to other courses.**

The North Star remains a tool for educators and researchers to experiment with
how to support students. The coaching game and Animal Crossing-inspired visual
direction are deferred while we establish the simulation's behavior.

The main achievements across this chat are:

- **Labeling became more useful and less central to construction.** Broad,
  overlapping categories evolved into help episodes and ordered tutor components
  such as checking work, explanation, guidance and questions. Labels now serve
  as measurements of behavior; we do not need to enumerate every possible student
  situation before building an agent. Reliable sentiment/ability inference remains
  unresolved.
- **The simulator can act beyond chat.** Students can quietly revise code, request
  an actual bounded check, receive source-linked feedback, communicate with a
  tutor and choose to stop. Saved sessions resume, retain observed history across
  tasks and replay their decisions. Researcher-authored examples demonstrated
  these connections across three tasks. This proves functioning software, not
  learning or human-like choices.
- **Evaluation became more concrete.** We built review UIs, preserved human
  feedback and completed a fixed comparison: eight recorded next messages plus
  64 generated messages, coded with separate help and work/evidence flags. The
  endless plausibility-review loop is paused.
- **We found usable notebook observations.** The bounded inventory found 5,921
  candidate capture pairs across 222 learner identities. Three fixed pairs were
  inspected; two permit cautious positional comparisons, showing one and four
  changed code cells. The third has unresolved alignment.
- **The work is reproducible.** Code, tests and research decisions live in the
  isolated `codex/episode-pilot` worktree and draft PR #25. Private student data
  stays outside Git; saved inputs and results are hash-checked.

The strongest measured finding is that the older chat generator often submitted
extra work/evidence where the eight recorded messages only requested help:
26/32 generated messages with earlier history and 23/32 without it. Additional
history did not improve the prespecified score in this sample. This is a specific
communication mismatch, not proof that history generally hurts or that the newer
notebook-action simulator is invalid. All eight references had the same flags,
which limits what the comparison can establish.

The main difficulties are **measurement and observation coverage**. We cannot
reconstruct every silent edit, execution or stop between notebook captures.
Captures lack stable cell IDs; outputs are not bound to executed source versions.
The runtime currently supports narrow single-cell/table tasks, not arbitrary
course notebooks. Small exposed samples, one completed review at each relevant
stage and limited course coverage do not establish annotation reliability,
population fidelity, persistent learner traits or improved learning outcomes.

The immediate evaluation target is the **two-example next-capture work forecast**:
give the model the initial notebook and first tutor exchange, predict net source
at a later eligible recorded capture, and compare missed/unnecessary changes with
an unchanged-work baseline. All 112 initial code positions are eligible; future
work stays out of prompts. This explicitly evaluates a later state, not the very
next action. One request per example, then report and stop; no new labeling pass.
The helper passes 17 related tests and independent preparation review.

Your specific Gemini approval is recorded, and this recap was delivered before
dispatch. The two requests then exhausted eight adapter attempts with a schema
compatibility error; neither returned a forecast. I had missed an existing Gemini
schema convention in the new helper. That omission is now corrected offline, with
17 tests passing. The failed run remains preserved and has no behavioral score.
The next technical step is an authored API smoke check before a separately bounded
real-data run; the corrected format has not yet been verified live.

Beyond that development check, the priority is one finite fidelity study with a
fixed dataset, baseline, metric and stopping rule. Broader claims need evidence
across students/tasks and eventually courses. Exact action-sequence claims need
better observations at chat/run boundaries. More agreeable examples alone will
not close those gaps.

The architecture is an LLM choosing open-ended messages or code within a stateful
runner. It is not a fitted giant decision tree or transition matrix. The research
question is whether this mechanism predicts useful aspects of real behavior well
enough to support educator experimentation.
