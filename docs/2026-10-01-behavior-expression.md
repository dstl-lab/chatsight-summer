# Keep behavior selection separate from expression

**TL;DR:** Reuse a saved local policy choice with either its authored template or
an optional wording-only model. Python inserts the selected work/error material
literally. A model response never changes the sampled behavior, its weights or
the saved seed. This develops the expression component; it does not estimate new
behavior probabilities or establish realism.

The user requested continuing the minimal-LLM behavior-policy direction after
the Gemini 3.8 Flash compatibility check. The current workbench demonstration
only supports one authored communication step. Multi-step action selection would
require supported transition/stopping evidence and trustworthy updated context;
the rejected prior-code predictor and the 20% comparator remain excluded.

## Bounded implementation

Add one renderer over the existing `behavior_policy` saved input/trace. Its default
is the existing template, with no model call. The optional callback receives the
chosen behavior, explicitly supplied context and optional student wording examples.
The policy library/probabilities and the query's literal work, diagnostic and
next-task fields are withheld. Supplied wording examples are visible as supplied;
Python inserts the selected literal fields afterwards.
The model is asked for a single request phrase, not an action or reasoning.

Save a self-contained copy of the verified policy, the actual wording request,
model, candidate, assembled output and structural outcome in a new directory.
Missing material or unsupported templates block before dispatch; failed or
interrupted requests remain saved and never trigger retries or another draw.
Reopening verifies the policy binding, request and literal assembly without calls.

Structural checks cannot prove that a phrase expresses the selected meaning or
contains no invented claim. Model wording therefore stays explicitly unverified
semantically. Preserve failures; do not appoint an LLM judge or start another
manual-labeling queue. Template mode remains the default, and the source-pinned
workbench demonstration remains intact. Browser integration is deferred until the
reusable expression boundary is checked.

Completion: fixed-selection checks across both renderers, exact selected material,
prompt isolation, missing-input prevention, retained single-attempt failure,
create-only saves and read-only replay. Use invented inputs for a single Gemini
3.8 Flash compatibility request, with no private student data or rerolls.

## Result

Implemented in `src/agents/behavior_expression.py`. Template is the default;
`--model` plus `--send` enables one wording request. Completed, failed and
interrupted output directories all refuse another dispatch. Saved candidates
remain distinct from the policy's original template and selected behavior.

The initial live check failed with a provider `ClientError`. One additional
diagnostic request with the same invented prompt established a 400
`INVALID_ARGUMENT`: the installed SDK sent `additional_properties` inside the
legacy `response_schema`. Offline HTTP interception reproduced the invalid
field names. The renderer now sends a simple text schema while keeping strict
extra-field, nonblank, line and 500-character checks in Python. Existing provider
and policy source files were not modified.

One separate compatibility request with the corrected schema succeeded. Thus
there were **three API attempts total: two errors and one completed candidate**,
all with invented inputs and no automatic retries. The prompt and selected
behavior were unchanged; no semantic variants were rerolled. The original
failure, diagnostic and original source snapshot remain saved alongside the
corrected result in ignored `data/behavior-expression-v1/`.

Both renderers used the same saved choice: checking, diagnostic material, same
task. Python inserted `IndexError: list index out of range` literally in both.
The template request was `can you check this error?`; Gemini 3.8 Flash supplied
`can you check what is causing this runtime error?`. These are mechanics examples,
not evidence that the model's wording is more realistic or semantically reliable.

All **53 focused policy, expression, saved-chat and provider checks pass**, including
the actual outgoing API shape, interrupted receipts and unsupported inputs.
The corrected expression and original failed receipt verify without generation;
the existing authored workbench demo still verifies unchanged. An independent
review found no material issue. The browser does not yet consume this optional
renderer; the existing local demo stays local.

## Run

Use a saved policy created by `src.agents.behavior_policy run`. Every expression
gets a new directory; the verified policy is copied inside it for later replay.

```sh
PYTHONPATH=. python -P -m src.agents.behavior_expression render \
  data/my-policy-demo data/my-template-expression
PYTHONPATH=. python -P -m src.agents.behavior_expression render \
  data/my-policy-demo data/my-wording-expression --model gemini-3.8-flash --send
PYTHONPATH=. python -P -m src.agents.behavior_expression verify data/my-wording-expression
```

Optional `--style-examples examples.json` accepts an explicit JSON list of earlier
student wording examples. It does not infer a persona or retrieve private data.
Semantic correctness remains `unverified` for model wording; a structural pass is
not a behavioral-fidelity score. No new labels or holdout reuse were needed.
