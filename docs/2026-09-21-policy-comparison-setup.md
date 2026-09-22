# Tutor-policy comparison setup

## Decision before implementation

Add a small Marimo setup page for one saved conversation scenario. The researcher
selects an eligible saved starting state, enters a confirmed current tutor policy
and a proposed tutor policy, and freezes a new two-condition comparison with one
new student decision per condition. Preparation is offline and sends no model
request.

This setup milestone uses the existing saved policy-pair runner. Its eligible
source contains a real recorded prefix followed by one saved simulated student
reply awaiting a tutor response. That limitation must remain visible. A later
cohort runner should branch directly from recorded student requests; this page
does not claim to solve that research upgrade.

## Controls and persistence

- List only direct child folders that pass the existing frozen-source checks.
- Require nonblank, different current and proposed policies.
- Prefill the current-policy field with a locally pinned summary of the packaged
  DSC 10 Socratic policy from `jupyterlab-ai-tutor` commit
  `d899879c3e7537b021d16bb901da341945606891`. Show its source and warn that a
  deployed instructor configuration can override the packaged default.
- Label condition A as current and condition B as proposed in the setup page.
- Fix the budget at one new student decision per condition.
- Refuse an existing destination and preserve the exact policies in the existing
  comparison receipt.
- On reopening, display the frozen plan instead of editable controls.

## Definition of done

An authored test proves source filtering, policy validation, immutable creation,
zero provider calls during offline freezing and offline reopening. With explicit
`--send=true`, the same page offers **Freeze and run comparison**: persist the plan,
then run A and B once and show both generated tutor/student outcomes. Existing
frozen plans expose a **Run both conditions** control. Each untouched condition
makes one tutor and one student request; completed, failed and interrupted work is
never automatically resent. Freezing or running one pair is not a policy result.
