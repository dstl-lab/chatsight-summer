# Two tutor replies from one starting situation

Educators need to try different support from a comparable starting point. The
new `src/agents/notebook_teaching_pair.py` prepares two saved notebook sessions
from one initial task, replacing its final tutor reply with two supplied texts.
It reuses the existing student engine; no labels select or constrain the student.

Task, earlier dialogue, selected-cell work, activity, private evaluator, model,
timeout and decision budget are identical. The initial student prompts differ
only in the final tutor text. Each session has a unique branch identity so check
feedback cannot cross between conditions. A/B identifiers and comparison hashes
stay in private provenance. The new tutor turns are explicitly supplied.

This is an alternative initialization, not a fork of a progressed learner. The
input must be an initial task ending with a student request and tutor response;
the original last tutor response is replaced. Saved-state fields are rejected.
Both sessions start with empty action history and no check feedback. Existing
observations are neither copied nor rebound to claim a fresh execution.

## Prepare

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_teaching_pair data/teaching-pair --task task.json --activity activity.json --evaluation-file evaluation.json --first-tutor-file hint.txt --second-tutor-file worked-answer.txt --max-decisions 6
```

`--evaluation-file` is optional, with the same meaning as saved-student creation.
The model defaults to Gemini 2.5 Pro and can be selected with `--model`.
Identical replies are allowed as a control. Preparation makes no model or runtime
call and has no send flag.

The output directory must be new. It contains `sessions/a`, `sessions/b` and a
`sessions/comparison.json` preparation receipt with source/input hashes, child
manifest hashes, supplied-reply hashes and the total student decision allowance.
Both children and the receipt are staged before publication together. Interrupted
preparation cannot expose only one runnable child; an interrupted publication may
leave an empty reserved parent, which must be inspected rather than overwritten.

Use the existing saved-student or lesson command on either child. The preparation
receipt remains a record of setup; current status and outcomes belong to each
child's operation/lesson receipts. If comparing only the initial reply, keep the
subsequent tutor policy and tutor caps identical and declare them before running.
Preparation does not impose a shared provider-call budget on later commands.

## Checked example and limits

The authored example in ignored `data/episode-pilot/teaching-pair-v1/` uses the
existing four-row blue-proportion task and declared Babypandas activity. A receives
a hint, B a complete expression. Both retain the same starting code and private
expected value, with six student decisions available each. No student actions,
model calls or code executions were run for this prepared pair. The readable
`example.md` shows the two replies and shared starting work.

The integration regression first failed because setup was missing, then passed.
The related suite passes 31 tests. Coverage includes equal prompt context,
independent feedback bindings and continuation, private metadata isolation,
input preservation, invalid inputs, no-clobber output, interrupted preparation
and CLI initialization without a provider. Independent code review found no
concrete issue. Existing simulator modules and saved traces remain unchanged.

This supplies a reproducible place to vary teaching support. Two outcomes, if run,
would not establish a causal tutor effect, learning or student fidelity. Sampling
budgets, behavioral measurement and replication remain separate research work.
The one-review labels stay provisional; no additional labeling pass is required
to use this engineering capability.
