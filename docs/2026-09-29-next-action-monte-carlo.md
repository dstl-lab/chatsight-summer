# Monte Carlo sampling of one saved student decision

Question: was the saved no-further-action reaction typical of Gemini 2.5 Pro
at this exact input? This is a new sampling diagnostic, not an extension of the
completed trajectory or a student-fidelity evaluation.

Before sampling, fix 30 new requests. Every request receives the unchanged
4,024-character reaction prompt: the selected task, two original dialogue turns,
first simulated edit, and actual local execution result/runtime. The previous
no-reply and all new draws are excluded. No CSV rows, tutor calls, execution,
training, human labeling, model upgrade, or workbench mutation are involved.
Minchan requested this experiment: “Let's experiment and then report the results
back to me - use monte carlo simulation.” Standing project Gemini approval also
applies; the new preparation records this request and the exact input hash.

Use the existing action schema and generation configuration. Temperature,
top-p, top-k, seed and thinking settings remain omitted, matching the original
request; their resolved provider defaults were not recorded for that request.
Record current model metadata without treating it as proof of past defaults.
Three concurrent workers make separate stateless requests, with SDK retries
disabled and a 120-second timeout per request. Each pending receipt is saved
before dispatch. Failed, capped, interrupted and invalid attempts are retained
without replacement. The batch cannot be restarted or extended.

Count validated action decisions directly: edit notebook (possibly with a
message), message only, and no further observable action. Retain duplicate
outputs because their frequency is the quantity being measured. The prior
single reaction is excluded from the denominator. Report coverage out of 30,
action proportions conditional on valid responses, and marginal 95% Wilson
intervals. These intervals assume independent, stationary draws; separate API
requests cannot prove that assumption. They describe Monte Carlo sampling
uncertainty, not uncertainty about a real student's behavior. See the
[NIST method](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

All prompts and responses remain under ignored `data/notebook-action-monte-carlo-v1/`.
The public runner and aggregate report contain no private conversation text.
Stopping rule: 30 attempts, then report once, including failures. No tuning or
additional batch follows automatically.

## Preparation and launch status

Prepared input SHA-256:
`a38a5ab27d2cfa3994c70a07123464d9051cd5391ceaa3488358572c20d8ecaf`.
Prompt SHA-256:
`fd4c4a421395044ec9ab471f6c05c1b86002b852f65ee0ab161b14cbccf3c18f`.
New plan SHA-256:
`a40786f932f189c582664b9779e71643ed4b07ce8ace7efff3e25ccc7a976e0b`.

The runner preserves the original schema/configuration, records raw provider
responses privately, and derives counts from validated actions. Offline report
replay also reconciles each accepted action with its raw STOP response. Authored
checks cover transport, token-cap and schema failures, duplicate preservation,
fixed inputs, tampered results, interval boundaries, and refusal to resend.
The unchanged original preparation independently verifies before dispatch.
All 60 related notebook action/branch tests pass; the existing Starlette/httpx
deprecation warning remains. Independent review verifies the original task/prompt
reconstruction, all code/input/schema/SDK pins, failure accounting, and absence
of launch or draw receipts. No remaining runner blocker was identified.

Automatic approval review rejected launch before process creation: it requires
specific approval for sending the same private input to Google Gemini in 30 new
requests, and does not treat the prior one-request approval or the new general
Monte Carlo instruction as sufficient. No model request was made. The separate
`send-blocked.json` records the rejection and exact pins; an explicit question
identifying the payload, provider, and count is pending. Do not run indirectly,
substitute another provider, or invent simulation results.

From the worktree root, the offline authored check is:

```sh
PYTHONPATH=. python -P experiments/2026-09-29-next-action-monte-carlo/run.py self-test
```
