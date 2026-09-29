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

Automatic approval review initially rejected launch before process creation: it required
specific approval for sending the same private input to Google Gemini in 30 new
requests, and did not treat the prior one-request approval or the new general
Monte Carlo instruction as sufficient. No model request was made by that attempt.
The separate `send-blocked.json` preserves the rejection and exact pins.

Minchan subsequently answered **“Approved”** to the explicit question naming the
private course task, two recorded turns, simulated code edit, execution feedback,
Gemini 2.5 Pro destination, and 30-request limit. `authorization.json` binds that
approval to the unchanged plan and prior rejection before dispatch; its SHA-256 is
`efa82023afa7fadf1b381d341f559f4f7b4c06d07a1658a996b16c52922f8c78`.
The approved batch runs once, with no substitutions, retries, or additional draws.

From the worktree root, the offline authored check is:

```sh
PYTHONPATH=. python -P experiments/2026-09-29-next-action-monte-carlo/run.py self-test
```

## Completed results

All 30 fresh requests completed with a valid STOP response. None failed,
reached a token cap, retried, or required a replacement. Each request returned
a distinct provider response ID and the same model version, `gemini-2.5-pro`.
The batch ran from 09:36:05 to 09:37:55 UTC on 2026-09-29 (109.59 seconds).

| Next action | Draws | Sample share | Marginal 95% Wilson interval |
| --- | ---: | ---: | ---: |
| No further observable action | 29/30 | 96.7% | 83.3–99.4% |
| Message only | 1/30 | 3.3% | 0.6–16.7% |
| Edit notebook, with or without a message | 0/30 | 0.0% | 0.0–11.4% |

These are complete-action frequencies, not token probabilities. All intervals
are marginal, not a simultaneous confidence region. There are **30 draws from
one context**, not 30 students or contexts; provider independence/stationarity
is an assumption, not established by distinct request identities.

The earlier saved no-action result was representative of the model's behavior
in this batch. It was not the only possible continuation: the single message
explained the code correction back to the tutor. That reflective wording is
relevant to the previously identified tendency to over-explain, but this
observation is not a newly labeled plausibility judgment. The 29 identical
no-action outputs remain in the denominator; deduplicating would destroy the
frequency estimate. Two distinct action objects were observed overall.

This experiment does **not** establish that the real student would stop with
96.7% probability, that they understood the fix, or that the answer passed the
course grader. One researcher-selected encounter with a researcher-triggered
execution result cannot establish cohort fidelity. Omitted sampling parameters
retain request parity with the original run; their effective provider values
are not known. No comparison with trained Qwen or a newer Gemini model was made.

Recorded API usage: 31,110 prompt tokens, 770 candidate tokens, and 29,147
thinking tokens (61,027 total). No token-level probabilities were requested or
inferred. No generated action was applied, and no tutor message or code execution
was triggered. The live workbench and its original single reaction remain intact.

The private raw report SHA-256 is
`de2e3428ed12765476acbe7d5ab9b4e3a120a269f24fcdb998a5f608b4410317`.
The [aggregate results](../experiments/2026-09-29-next-action-monte-carlo/results.json)
retain the plan/input/model/configuration references without conversation text.
Offline analysis reproduces the report from all 30 raw responses, and the
original preparation, source branch, execution result and saved reaction still
verify unchanged. Approval precedes every request.
Independent review also recounts all raw actions, verifies the 30 distinct
provider IDs, every receipt hash, marginal intervals, usage and timestamp
arithmetic, and 36 original/source/code/input pins. The separate private
`verification.json` records closure checks. No issues were found.

The stopping rule is met; this batch is closed. The useful UI representation is
“29 of 30 sampled continuations” with the interval and exact input/model details.
It should not say “96.7% chance the student is finished.” More draws at this same
checkpoint are not queued; they would refine model-frequency precision without
establishing real-student realism.
