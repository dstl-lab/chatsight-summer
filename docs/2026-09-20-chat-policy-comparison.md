# Compare two tutor policies from one saved starting point

**TL;DR:** Prepare two independent chat sessions from one frozen, cached first
student reply. Fix both tutor policies and the remaining decision budget before
continuing. Inspect both saved outcomes together; preparation and viewing are offline.

## Scope and stopping rule

This implements task-list item 2 using the existing saved-chat runner, tutor
adapter and receipt reader. It does not change the student generator or infer
notebook activity. The existing workspace and its ongoing conversations remain
available. Interface redesign stays deferred.

The initial acceptance check uses invented conversation text and injected
responses: one cached first reply plus exactly one new student decision per
condition. One condition may stop without replying or fail; retain that result
alongside the other condition. No live comparison, additional labels or fidelity
claim is part of this implementation. A later research run must name its cases,
policies, measure and stopping rule before sending requests.

## Implementation

- `src/agents/chat_policy_pair.py`: create the pair atomically from a source with
  exactly one completed cached reply and no tutor interventions. Replay the source,
  require exact import prompt/schema, and create fresh session identities. Save
  policies, source provenance, budget and child startup hashes. Never overwrite or
  fork a progressed session. Default to one new decision per condition.
- Reopen each condition independently with the existing replay checks and saved
  history reader. Verify startup pins and fixed-policy delivery; expose each
  condition's errors without concealing the other result. An explicit bound
  continuation reuses `chat_workspace.respond`; pending operations never resend.
- `apps/chat_policy_comparison.py`: a small comparison view with both fixed policies,
  saved results and one explicit continuation button per condition. Retain its
  public layout binding for standalone Marimo. No editable policy drafts, automatic
  generation or generation during reload.
- Authored regression checks cover identical starting states, independent identities
  and budgets, source preservation, terminal/error outcomes, altered inputs and
  interrupted operations. Verify the standalone controls in a separate authored
  browser fixture, then run the existing suite and Marimo validation.

## Use

Create two UTF-8 text files containing the policies. Choose a frozen saved-chat
folder containing `session.json` and exactly `step-0001.json`, with a completed
student reply and no tutor-exchange attempts. Use an original frozen handoff,
not a workspace conversation that has already advanced. Then prepare offline:

```sh
.venv/bin/python -m src.agents.chat_policy_pair create data/my-policy-pair \
  --source /path/to/frozen-chat-session \
  --policy-a /path/to/policy-a.txt --policy-b /path/to/policy-b.txt \
  --max-new-decisions 1
```

This creates `comparison.json` and `sessions/a` and `sessions/b`. Each child has
one reused decision plus the same fixed number of new decisions. It preserves
the source model while assigning fresh identities and the new bounded budgets.
Import and generation are distinct; create performs zero provider requests.
Existing destinations are refused. A changed source or interrupted staging does
not publish a partly prepared comparison.

```sh
.venv/bin/marimo run apps/chat_policy_comparison.py \
  --host 127.0.0.1 --port 8425 --headless -- \
  --comparison data/my-policy-pair --send=true
```

Both policies and conversations appear together. Each Continue button applies
only its condition's saved policy, generating at most one tutor reply and one
student decision through the existing adapters. A progress indicator appears
while the call is running. No automatic run, reroll, retry of an interrupted
operation or extension of the budget is added. Omit `--send=true` for viewing only.
Reopen offline from the command line with:

```sh
.venv/bin/python -m src.agents.chat_policy_pair show data/my-policy-pair
```

Use the comparison controls for these branches. Direct manual interventions or
different-policy exchanges through the generic workspace invalidate the comparison
and are displayed as requiring inspection. Their saved records are retained.

## Verification result

The full suite passes 417 tests, with two optional container checks skipped and
one upstream Starlette/httpx deprecation warning. Both Marimo apps validate.
The 15 pair checks cover startup equality and identity separation, exact policy
delivery, source and budget guards, interrupted preparation, tutor/student
failures, no-resend behavior and changed comparison records.

The standalone authored browser check showed progress while A continued, then
left B's budget untouched. A finished at its fixed budget; B subsequently chose
no reply. Both reopen together, with four total saved student steps (two imported,
two new authored decisions) and two tutor exchanges. Reload changes no files and
generates nothing. The CLI create/show paths were checked offline as well.
Private fixtures are under `data/episode-pilot/chat-policy-pair-ui-v1/`.

The existing workspace preparation still verifies all 195 frozen source hashes
and 87 startup files, allowing the user's later workspace interactions. No
student-engine files, live scenarios, historical evidence or generator prompts
were changed by this implementation. No live comparison or labeling pass ran.

## Limits

Equal starting context and budgets make the two runs inspectable. Stochastic
outputs from a single pair do not estimate policy effects, student probabilities,
learning or fidelity. The reused first reply is a cached simulation, not an observed
student future. New local import timestamps are not original generation times.
Tutor and student generation remain sequential and subject to existing provider
retries. A decision budget limits simulation steps, not network retry attempts.
