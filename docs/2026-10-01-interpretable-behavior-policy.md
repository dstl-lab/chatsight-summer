# Interpretable student behavior policy

**TL;DR:** Minchan approved the behavior-policy direction and requested that LLMs
have as small a role as possible for transparency and interpretability. Make
behavior selection inspectable Python logic over recorded evidence. An LLM may
eventually express a selected behavior, but it must not secretly determine the
state, behavior probabilities or evaluation verdict. Begin with an offline
prototype that needs no model calls.

## Adopted constraint

This records the design decision, not a deployed policy or a new experiment.
The existing generator, source-pinned sessions and closed studies remain intact.
No new labels, provider calls, database queries or human review queue are created.

The first target is communication **conditional on another student message**.
Chat records do not establish the probability of a quiet edit, execution or
stopping. A later notebook policy needs evidence for those operations separately.
No fixed persona, latent emotion, ability or learning state is introduced.

## Responsibility boundaries

| Responsibility | Implementation direction | What must be visible |
| --- | --- | --- |
| Read the current state | Parse recorded dialogue, supplied task identifiers, notebook revisions and revision-bound feedback in Python | Source references, missing fields, and distinction between recorded and generated events |
| Describe semantic behavior | Use explicitly supplied, provenance-bearing observations; unknown remains unknown | Definition, source evidence, annotation method and disagreement; raw text alone does not give trustworthy semantic labels |
| Find comparison situations | Explicit filters or a documented simple matching rule over permitted earlier context | Fields compared, matching rule, included/excluded examples and support counts; no hidden LLM summary or embedding model |
| Choose behavior | A local empirical distribution and seeded sampler over joint behavior bundles | Counts, account weighting, any smoothing/fallback, normalized probabilities, selected bundle and seed |
| Express the choice | Authored templates in the first mechanics prototype; optional LLM wording/code generation only in a later comparison | Which renderer was used, supplied choice, actual output and any observed mismatch |
| Apply an action | Existing state validators and notebook runtime | Source revision, actual execution result, errors and explicit action origin |
| Evaluate | Deterministic mechanics checks and arithmetic over qualified observations | Coverage, disagreements and errors; semantic fidelity does not become a rule-based fact or an LLM judge's verdict |

Transparent rules and sampling make a decision reproducible; they do not make
the selected features, annotations or estimated distribution valid. In particular,
the [assistant-coded pilot](2026-10-01-behavior-pilot-results.md) remains exploratory.
Its labels cannot silently become trusted policy-training data or ground truth.
Removing model calls at runtime does not remove model influence from labels made
earlier. Preserve that provenance in any later use.

## Smallest first prototype

Use authored structured examples to check the mechanics without new annotation
or private-data dispatch. Choose a whole combination of assistance requested,
material supplied and task relation, preserving co-occurrence rather than drawing
each dimension independently. The example library and any counts in this check
are authored inputs, not estimates of DSC 10 behavior.

Expose the matching examples, counts, probability calculation and sampled result
as a saved trace. A sparse or unsupported query must return a declared fallback
or insufficient evidence; it must not ask a model to invent probabilities. Missing
labels cannot be treated as absence, and coverage/exclusions must remain visible.
Generated contributions may update the simulated conversation but never count as
new recorded evidence for the empirical policy.

Use a few explicitly authored utterances to display selected behaviors. They
demonstrate routing only; neither templates nor verbatim historical replies are
automatically appropriate to a new task. Do not claim wording realism from this
prototype. A later LLM renderer must be optional and assessed separately: choosing
"request a hint" does not prove its generated sentence requests a hint. Keep
mismatches instead of silently retrying until a compliant output appears.

Reuse the generator callback and receipt pattern in
`src/agents/student_evidence.py` and `src/agents/chat_student.py` when integration
is warranted. Avoid changing the frozen continuation prompt or old replay
contracts merely to demonstrate the policy. No new service, model training,
framework, UI or dependency is needed for the first prototype.

## Evidence needed before a fidelity claim

The mechanics check ends when sampling, trace reconstruction, missing evidence
and action boundaries pass their fixed checks. It cannot establish realism.
A later comparison needs qualified behavioral observations, account-separated
development/evaluation data, a frequency baseline and a fixed stopping rule.
Matching must use preceding context, never a query's recorded next message.

Evaluate policy selection separately from expression. An LLM-generated
explanation of a decision is not an explanation of the actual sampler; show the
saved inputs and arithmetic instead. Semantic uncertainty remains a limitation
until it is resolved for the specific comparison. Human review is reserved for a
named consequential ambiguity, not another open-ended labeling cycle.
