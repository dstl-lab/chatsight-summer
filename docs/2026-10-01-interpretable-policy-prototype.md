# Offline behavior policy prototype

**TL;DR:** Implement the approved [minimal-LLM design](2026-10-01-interpretable-behavior-policy.md)
as one offline Python module, one focused test file and an authored JSON example.
No provider, database, model labeling, deployment or workbench change is part of
this implementation. The examples test mechanics; they are not student evidence.

**Status:** Implemented. The authored demo and its saved trace reproduce locally.
The first prototype is a standalone offline command, not the live generator.

## Implementation contract

`src/agents/behavior_policy.py:select(request)` accepts strict structured inputs
and returns an inspectable trace. Inputs contain a query, library examples and
an integer seed. The query and examples carry IDs, account IDs, source references
and context: last requested assistance (a set or unknown) and execution feedback
(pass, fail, runtime error, not checked, or unknown). These are explicitly supplied
observations, not facts inferred from raw text. A source reference is a declared
provenance link, not proof its contents were verified.

An example also declares its origin and next-message behavior: assistance kinds,
supplied material and same/different task relation. Empty sets mean absence;
null means unresolved. Duplicate labels, identifiers and unknown fields are
rejected. The request contains no query target. This first mechanics prototype
admits only authored examples with complete behavior labels from accounts other
than the query account. Recorded, generated and assistant-labeled inputs are
reported as excluded, never silently treated as trusted evidence.

Match all known query context fields exactly. Unknown fields are not matching
evidence. With fewer than two matching authored accounts, explicitly fall back to
the whole eligible authored library. If that also has fewer than two accounts,
return insufficient evidence without sampling. Two accounts is an authored-demo
support rule, not a scientific reliability threshold. There is no smoothing,
semantic similarity score, embedding, learned classifier or adaptive tuning.

Give each included account equal probability, then each of that account's examples
equal probability. Thus example weight is `1 / (accounts * examples_in_account)`.
Aggregate those weights over complete behavior combinations, retaining their
co-occurrence. Sort accounts/examples to make input ordering irrelevant and use
the supplied seed for the two draws. Save individual weights, counts, matching and
exclusion reasons, fallback, sampled account/example and chosen behavior.

Fixed authored templates demonstrate selected behaviors. Optional query fields
`work`, `diagnostic` and `next_task` supply literal content when needed. If a
template or required field is unavailable, preserve the choice and report an
unrendered result; do not resample, invoke a model or invent missing content.
Template coverage is reported separately from policy selection. No code executes.

`run(request, folder)` saves input JSON, a trace with input/source hashes and a
readable Markdown report in a new directory. `verify(folder)` recomputes the
trace and report without dispatch. Existing outputs must never be overwritten.
The CLI accepts an input JSON and output directory, or verifies a saved directory.
The public example lives at `docs/examples/behavior-policy-authored.json`.

## Execution and checks

Use the existing isolated worktree and Python environment. Leave unrelated edits
to CLAUDE.md and TASKLIST.md intact. Reuse installed Pydantic and stdlib; avoid
importing provider clients or changing frozen simulation/replay modules.

- [x] Write focused tests and observe the missing implementation fail. Pin
  hand-calculated account-balanced probabilities, joint labels, seeded replay,
  ordering invariance, fallback, unresolved/excluded cases, validation, missing
  renderer inputs and create-only output/tamper rejection.
- [x] Implement the pure selector, small template renderer and saved CLI in one
  module. Supply an explicitly authored example; no private evidence is ingested.
- [x] Run focused checks and the authored CLI/verification. Obtain an independent
  code review, address material findings and run relevant regression checks.
- [x] Document actual results and limitations, then commit only this change.

Stop when these mechanics checks pass. No extra generation study, calibration
claim, human-labeling queue or automatic production adoption follows. A later
experiment must separately establish the quality and coverage of its behavior
observations and evaluate selection independently from expression.

## Run and inspect

From the worktree root, using the project Python environment:

```sh
PYTHONPATH=. python -P -m src.agents.behavior_policy run \
  docs/examples/behavior-policy-authored.json data/my-policy-demo
PYTHONPATH=. python -P -m src.agents.behavior_policy verify data/my-policy-demo
```

Open `data/my-policy-demo/report.md`. Its summary lists the behavior probabilities
and selected authored message; the full trace contains every source, exclusion,
match and weight. `input.json` is the saved input and `trace.json` the machine-readable
receipt. Choose a new output directory for another run. Verification requires the
original module and Python version; it detects changed inputs, source pins,
decisions or report contents. This is reproducibility checking, not protection
against someone intentionally rewriting all artifacts.

The public example contains eight invented rows, including deliberately marked
excluded origins. Five qualify as authored examples outside the query account;
four match the known context, from two accounts. Account A contributes three
matching examples, each with weight 1/6; B contributes one with weight 1/2.
The resulting joint choices are **hint / no material / same task: 1/3** and
**checking / work / same task: 2/3**. Seed 4 selects A's second hint example and
renders `can i get another hint?`. These numbers were constructed to exercise
the weighting rule, not estimated from DSC 10.

The first focused test run failed on the absent implementation; all **14 focused
checks** then passed. The final run passed **28 checks** including the existing
behavior-scoring, chat-student and continuation regressions. An independent code
review found no material correctness issues. The authored CLI run and trace
verification passed with no model calls. No semantic accuracy or whole-repository
test result is inferred from these checks.

Matching uses only explicitly supplied context fields. This version does not
extract semantic state from dialogue or personalize from the query account's
earlier history. Templates cover six joint behaviors; other combinations preserve
the selected choice with an unsupported renderer status. Missing literal work,
diagnostic or next-task fields likewise produce no message, never a no-reply
decision. No current simulator default, notebook state or old evidence changed.
