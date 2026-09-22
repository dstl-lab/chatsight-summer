# One tutor-policy comparison across three conversation scenarios

**TL;DR:** Reuse the existing simulator to prepare three independent policy pairs,
run at most one new student decision in each of their six conditions, and reopen
all outcomes. Preparation and viewing are offline. This adds a small-group workflow;
it does not change student generation or run another fidelity experiment.

## What this adds

The existing policy-comparison app and runner handle one conversation at a time.
`src.agents.chat_cohort` coordinates exactly three of those existing comparisons.
Each uses the same two frozen tutor policies, the source model, and one new student
decision per policy. Source conversations must be distinct and use the same model.
These are conversation scenarios, not three verified individuals or personalities.

The group preserves the cached first student reply from each source. All subsequent
tutor and student outputs are saved through the unchanged comparison and session
code. Sources remain untouched, each condition receives a fresh identity, and a
failed or interrupted condition remains inspectable alongside the other outcomes.
The cohort has no new generator, behavior labels, notebook reconstruction or game UI.

Comparisons containing symbolic links require inspection instead of being replayed
or advanced; they cannot redirect writes into original sessions or another folder.
Use ordinary copied files for portable private bundles.

## Prepare, continue, reopen

Use three frozen source sessions, each containing exactly one completed cached
student reply and no tutor interventions. The teammate quickstart describes the
[private-session setup](teammate-quickstart.md#3-open-private-working-sessions-when-provided).
Write the two policies into UTF-8 files and choose a new destination:

```sh
.venv/bin/python -m src.agents.chat_cohort create data/my-cohort \
  --source /path/to/source-1 --source /path/to/source-2 --source /path/to/source-3 \
  --policy-a /path/to/policy-a.txt --policy-b /path/to/policy-b.txt
```

Preparation publishes the group only after all three comparisons are ready. It
refuses an existing destination or a destination inside a source. The manifest
fixes the group and comparison identities; changing a saved policy or comparison
does not silently redefine the run. It makes zero model calls.

Inspect the saved group before enabling generation:

```sh
.venv/bin/python -m src.agents.chat_cohort show data/my-cohort
```

For an explicitly authorized live group, configure `GEMINI_API_KEY` as in the
quickstart. This command continues only ready, untouched conditions:

```sh
.venv/bin/python -m src.agents.chat_cohort run data/my-cohort --send
```

The order is 1A, 1B, 2B, 2A, 3A, 3B. A fully ready group permits at most six new
student decisions and twelve logical model requests: one tutor reply followed by
one student decision per condition. The existing four-attempt provider adapter
allows at most 48 adapter attempts across that group; SDK HTTP retries are not
independently instrumented. Calls are sequential. The order is fixed for operation,
not presented as randomization or a statistically balanced policy-effect study.

Ordinary failures remain saved while the coordinator continues untouched peers.
An interruption stops the command. A later explicit `run --send` can finish only
conditions still ready; it cannot resend the interrupted exchange or extend any
condition's one-decision budget. Running again after all conditions stop or use
their budget makes zero calls. Existing receipts supply this protection; there is
no second scheduling ledger. Viewing and reloading always make zero calls.

Reopen a pair using the existing Marimo interface:

```sh
.venv/bin/marimo run apps/chat_policy_comparison.py \
  --host 127.0.0.1 --port 8425 --headless -- \
  --comparison data/my-cohort/comparisons/case-01
```

Change `case-01` to `case-02` or `case-03` to inspect another pair. The cohort summary
shows every case, including one that cannot be loaded. Keep notebook activity as
unknown for historical chat scenarios. A budget stop, a generated no-reply, and
a provider failure are different operational outcomes; none establishes learning
or real-student abandonment.

## Acceptance and stopping point

Verify one authored three-case group with injected tutor/student responses,
including a failed condition. Check identical policies and budgets, independent
sessions, source preservation, visible failures, and zero dispatch on create,
show, completed rerun or an attempted resend of an interrupted condition.
Reject duplicate conversations, mixed source models, changed manifests and unsafe
destinations. Keep all existing source-pinned engines and the live workspace intact.

Prepare a separate private group from the first three existing frozen handoff
scenarios as an engineering starting point. Do not select scenarios by appealing
model outcomes, generate new historical replies, or call this a representative
cohort. Stop after the workflow and saved fixtures are verified. No live policy
comparison, new semantic labels, replacement continuation-selection cases or
simulator-fidelity claim is included in this implementation.

## Verification result

The full suite passes **430 tests**, with two optional container skips and one
upstream deprecation warning. Both existing Marimo apps validate, and the Node
navigation check passes. Eight authored cohort checks cover saved outcomes,
student and tutor failures, interruption and untouched-peer continuation, plan
changes, unrecorded-error propagation, duplicate sources, corrupt
pairs, and symlink containment. Independent review confirmed the containment fix.
No existing student engine, prompt, model schema, dependency or app changed.

The private `data/episode-pilot/chat-cohort-v1` folder contains:

- `historical-group`: the first three frozen handoff scenarios, with six ready,
  untouched conditions. Source file hashes still match the preparation record.
- `authored-group`: six scripted outcomes through the actual coordinator: three
  replies, two no-replies and one saved student-provider failure. Twelve injected
  callbacks ran; no provider was constructed. Reopening or running the completed
  group again changes no files and makes no additional calls.
- `OVERVIEW.md`: a readable view of all six authored outcomes and the prepared
  historical group, with the distinction between them stated explicitly.

CLI preparation and viewing were also verified, including refusal to run without
explicit sending enabled. The recent API failure was isolated to the evaluation's
new `Choice` schema: existing tutor, chat-student and notebook-action schemas
already omit that unsupported field while retaining strict local validation.
Offline SDK checks confirmed those interactive paths need no repair. The live
workspace, closed studies and paused labeling queue remain unchanged.
