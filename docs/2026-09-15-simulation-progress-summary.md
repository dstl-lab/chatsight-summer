**We have a working research prototype for simulated students, plus evidence of a
specific behavior mismatch. We have not yet validated realistic student personas,
learning, or transfer to other courses.**

## Current direction: use the data already available

Minchan clarified that the next quarter is not imminent. Simulator development
must proceed from the existing corpus; new logging and collection are supporting
work, not a dependency. The earlier observation-contract priority below records
the path taken, not the current prerequisite for all further research.

The current data supports conditioning on recorded conversation prefixes and
captured work, comparing the next recorded message, and comparing net source
between compatible captures. It does not require an exhaustive set of student
labels before simulation can continue. Missing intermediate events limit which
claims we can test; they do not make the whole corpus unusable.

The immediate development target is the observed excess-work/narration mismatch.
Reuse existing continuation and action code and compare a separately identified
candidate with the unchanged generator and a simple baseline. Fix the comparison
and stopping rule before another generation run. A completed fixed comparison
must lead to an adoption/rejection/inconclusive decision, not another automatic
round of plausibility questions. Existing exposed cases can inform development;
they cannot become fresh validation cases. Additional historical conversations
remain a possible evaluation source, subject to overlap and coverage checks.

The historical notebook initialization and three-action example already exist;
repeating them is not a new milestone. Preserve the completed help/work benchmark,
notebook forecasts and human judgments. No new model run, labels, data collection
or simulator-quality claim follows from this priority correction. Full silent
action sequences, stopping probabilities, learning and causal tutor effects remain
unvalidated; those limitations do not block observable-message development now.

## Progress and earlier decisions

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
  isolated `codex/episode-pilot` worktree and PR #25. Private student data
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

The completed development evaluation is the **two-example next-capture work forecast**:
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
A subsequent authored API smoke check succeeded on its first adapter attempt, so
the specific format issue is now verified fixed live. After explicit permission
for the separate V2, both real-data forecasts completed on their first adapter
attempts. One predicted seven changed code cells where
one changed; the other predicted one where four changed. Together they overlapped
two of five observed changed positions, with six extra changes and three misses;
one changed source matched exactly. This is a completed development result, not
correctness or general student-fidelity evidence. The fixed batch is closed.

The subsequent [observation-window audit](2026-09-15-observation-window-readiness.md)
found three additional recorded tutor replies before one target capture, plus a
later linked student query in the other example. Neither pair establishes the
same question throughout. The net-state scores remain descriptive results; they
cannot diagnose a one-turn action policy or isolate a tutor effect. Changed-cell
counts also measure net differences, not student effort.

The next engineering priority is a common observation contract for real and
simulated sessions: task/version, cell identity, work revision, tutor boundary,
and revision-bound checks. Verify whether the logger already retains those
records before proposing changes. One replayable recorded example with the
bindings is the acceptance criterion before a next-action fidelity study.
This audit closes without new model calls, labels, or prompt tuning.

The architecture is an LLM choosing open-ended messages or code within a stateful
runner. It is not a fitted giant decision tree or transition matrix. The research
question is whether this mechanism predicts useful aspects of real behavior well
enough to support educator experimentation.
