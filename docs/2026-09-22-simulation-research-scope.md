# Simulation errors and educator decisions

**TL;DR:** The working simulator is now on main through PR #43. Pause additional
infrastructure work and examine whether a specific simulation error affects how
educators assess a tutor. This is a proposed research direction, not an
established contribution or authorization to launch a study.

## Question

Can unrealistic simulated students mislead teachers about which tutoring
approaches work, and how can we help teachers spot that?

The student simulator remains central. The proposed HCI contribution concerns
the consequences of its errors when people use it, beyond whether its replies
look plausible. Labels remain narrow measurement tools, not an exhaustive
behavior taxonomy or prerequisite for running the simulator.

## Existing overlap

We cannot claim novelty from simulation, history, code execution, personalization
or fidelity measurement alone:

- [Generative Agents](https://arxiv.org/abs/2304.03442) develops believable agents
  with memory, reflection and planning.
- [CoderAgent](https://www.ijcai.org/proceedings/2025/0034.pdf) simulates programming
  submissions and edits using memory and execution feedback.
- [Substance or Illusion?](https://arxiv.org/abs/2601.04025) evaluates student
  dialogue fidelity and compares prompting with trained simulators.
- [StudentSim](https://arxiv.org/abs/2609.01591) trains individualized simulators
  and evaluates response fidelity and responsiveness to guidance.
- [Teachers' Insights](https://aclanthology.org/2025.bea-1.8/) already identifies
  unnatural attentiveness and language complexity in simulated students.
- [CoBRA](https://arxiv.org/abs/2509.13588) operationalizes and controls cognitive
  bias through experimental tasks.

These overlaps motivate the narrower question; this is not an exhaustive review
or proof that the proposed contribution is unique. Asking for an answer is an
observed interaction choice, not sufficient evidence of a cognitive bias.

## What the current evidence supports

The [cached communication review](2026-09-22-cached-communication-results.md)
identifies a candidate discrepancy: when students present work in chat. It covers
eight recorded messages and sixteen generated occurrences from one condition.
Its existing labels cannot be transferred to newly generated messages. Differences
from one recorded continuation do not establish that every alternative is wrong.

The [forecast screen](2026-09-22-work-presence-forecast-status.md) failed and stays
closed. No replacement prompt or model is adopted. Notebook executions and
policy comparisons establish operational capability; historical missing notebook
actions, individual learner identities and real policy effects remain unknown.

## Next decision and stopping rule

Prepare one offline feasibility assessment using existing frozen evidence. It
must identify one concrete educator decision and determine whether available
material can expose a documented simulation discrepancy without changing the
tutor policy, inventing notebook activity or selecting only persuasive examples.
Record exclusions and unavailable comparisons. Do not treat a recorded reply as
the outcome of a different, unobserved tutor intervention.

If a defensible comparison exists, propose a small moderated decision task:
observe educators' policy assessments and evidence use, then ask how they reached
them. Policy choices and confidence are observable outcomes; a changed choice
alone is neither improvement nor harm. Any interface benefit requires a defined
comparison, independently checkable evidence judgments and treatment of order
and additional-information effects before recruitment.

If the materials cannot support that task, report the missing evidence and stop.
Do not generate another batch to manufacture the desired contrast. Participant
availability, study size and review requirements remain unresolved. There is no
recruitment, new model call, interface implementation or manual coding in this
increment. Its endpoint is a proceed/defer decision, not a rolling review queue.

**Assessment completed:** the [feasibility report](2026-09-22-educator-decision-feasibility.md)
supports a small formative walkthrough and defers policy-effectiveness and
interface-benefit claims. Existing evidence verifies; participant availability
is the remaining input. No walkthrough or new generation has occurred.
