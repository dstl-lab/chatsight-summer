# One-case tutor-policy fork walkthrough

## Decision before dispatch

The held-out continuation walkthrough established that one saved student decision
can be generated from a real conversation prefix while the recorded next message
remains outside the request. The next engineering milestone demonstrates the
counterfactual intervention workflow: start two independent simulation branches
from that same saved simulated reply, apply different tutor policies, and save one
tutor reply plus one subsequent student decision in each branch.

This is an exposed mechanism walkthrough, not a tutor-policy experiment. It does
not estimate a real-student response, learning, correctness, or a causal policy
effect. The recorded continuation remains separate and is not appended after the
simulation diverges.

## Fixed policies and budget

Condition A uses this verification-first policy:

> When a student asks you to check notebook work that is not visible, clearly say
> that you cannot inspect it, ask them to paste the relevant work, and do not judge
> correctness. Keep the reply concise.

Condition B uses this guidance-first policy:

> When a student asks you to check notebook work that is not visible, clearly say
> that you cannot inspect it, give a concise self-check checklist based only on the
> visible conversation, then ask them to paste the relevant work. Do not judge
> correctness.

Create two fresh session identities from the same completed held-out-continuation
session. Each condition permits exactly one new student decision. Run condition A
then condition B, with one Gemini tutor request and one Gemini student request per
condition, four provider requests total. Keep completed, failed, interrupted and
no-reply outcomes. Do not reroll or extend either budget.

## Acceptance and stopping rule

The milestone is complete when both branches can be reopened together, their
starting state matches, their fixed policies and receipts verify, and browser
reload changes no saved bytes. Display recorded history, simulated messages and
tutor interventions with their origins. Stop after the two fixed branches. Do not
score this pair, choose a winning policy, or describe it as evidence that either
policy would change actual student behavior.
