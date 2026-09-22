# Two tutor replies from one starting situation

## Browser comparison (September 22)

Open the existing pair together in the dedicated workspace:

```sh
.venv/bin/python -m src.agents.browser_workspace \
  --teaching-comparison data/teaching-pair/sessions --port 8434
```

The directory contains `a`, `b` and `comparison.json`. No replay argument or
send flag is needed. The shared task and initial code appear once, with each
supplied tutor reply, saved action sequence, latest code, local check and stop
reason alongside. Shared start / Reply A / Reply B selects one conversation in
the existing chat sidebar; source inspection follows that selection.

The loader pins the preparation receipt, checks child manifests and reply hashes,
verifies matching initial inputs and independent execution identities, and reads
current outcomes under existing locks. The original replaced tutor text cannot be
reconstructed from the preparation hash; actual shared inputs are compared instead.
Missing, changed, swapped, linked or unverified evidence is hidden. Preparation's
`model_calls: 0` is never presented as the later run's call count. Later tutor
interventions, if present, remain additional differences visible in chat.

Verified: 686 Python tests (three optional skips), three Node checks and seven
Marimo checks; independent review and desktop walkthrough. The existing completed
pair reopens with both edit → local check → no-reply outcomes, while all 13 source
files retain their contents and timestamps. No provider calls, executions, labels
or simulator changes. A related status fix updates pending-chat text after opening
a saved exercise without rebuilding the message nodes.

This interface change does not reopen the completed experiment below.

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
expected value, with six student decisions available each. Preparation made no
model or runtime calls. The readable `example.md` preserves that initial setup;
the subsequent completed run is recorded below.

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

## Completed bounded run

Minchan directed continuation. A pre-dispatch plan fixed A then B, six student
decisions and at most two follow-up tutor replies per condition, the same follow-up
policy and API reference, and no rerolls. The stopped local Docker runtime was
started and its existing immutable image verified before either model request.

| Initial reply | Generated student decisions | Requested checks | Generated tutor replies | End |
|---|---:|---:|---:|---|
| Hint | 3 | 1 | 0 | Chosen no-reply |
| Worked answer | 3 | 1 | 0 | Chosen no-reply |

Both generated the same source expression in one quiet edit, requested a check
that returned the expected float 0.5, and chose no-reply. Each retained three
student decisions. No chat was generated, so the common follow-up tutor policy
and optional library note were not exercised. There were six logical model
requests and two actual container checks. Physical provider attempts were not
observed; the unchanged adapter permits up to four attempts per logical request.

The pair demonstrates that the same setup can run under either supplied reply,
with independent state and recorded feedback. This easy authored task and one
draw per condition do not distinguish the approaches, establish their equivalence,
or demonstrate learning. Do not rerun until a difference appears. This increment
ends with the saved outcomes, without prompt tuning or another labeling pass.

`RUN_REPORT.md`, `run-summary.json`, and separate static replays are saved alongside
the prepared example. Both sessions reconstruct exactly without model or runtime
calls, and all 49 checked earlier run/review artifact hashes remain intact.
