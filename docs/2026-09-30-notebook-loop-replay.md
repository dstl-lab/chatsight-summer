# One saved notebook loop in the workbench

The workbench now presents one existing sequence directly as five stages:
**Captured start → Tutor reply → Student edit → Local execution → Next action**.
The stage controls sit above the notebook, with the shared chat alongside it.
The single-example view hides the unnecessary task picker; the ordinary policy
sampling view is unchanged.

The displayed case is the previously saved **guided-hint sample 1** from the
closed policy-sampling study and its execution follow-up. The student generated
an edit using `len(...unique())`; a local run returned **2,850**; the next saved
model decision was **no further action**, with no message or additional edit.
This turn made **zero model requests, zero code executions and zero new labels**.

The execution was researcher-triggered, not a model-selected Run action. The UI
names that distinction. The output first appears at Local execution, attached
to its exact source revision; the next stage labels it as the result supplied
before the reaction. Moving between stages does not run anything. Code changes
appear only at the edit stage, not again when the unchanged revision executes.
No-action comes from a saved model response, not missing messages or an exhausted
decision budget.

This is a replay of existing evidence, not a new fidelity result or a test of
evidence-card guidance. The card remains display-only for this notebook example.
The source history is sparse; historical dataset bytes/kernel are unverified;
the archived-data output is not a course grade or evidence of learning.

`--student-loop hint` reuses the existing verified comparison and continuation
loaders. It selects only that condition's predetermined reaction sample, rejects
incomplete sequences, and verifies source/runtime/raw-result/provider-response
attribution on each read. The view exposes no POST/send/execution endpoint.
Authored test data retains its explicit banner. Original artifacts are unchanged.

```sh
PYTHONPATH=. python -P apps/policy_sampling_preview.py \
  --branch data/notebook-source-branch-v1/branch \
  --comparison data/notebook-policy-sampling-v1 \
  --continuation data/notebook-policy-execution-v1 \
  --live-results --student-loop hint --port 8452
```

Validation: seven focused Python tests, three Node controller checks and browser
inspection of all five stages pass. The actual saved case reproduces revisions
0/0/1/1/1, output 2,850, and no-action. Checks cover output timing, unchanged inputs,
sample selection, rejection of changed receipts, read-only APIs, preserved
navigation, and authored-data disclosure. Independent review caught and corrected
an inherited edit diff on the execution stage. The existing Starlette/httpx
deprecation warning remains.

The local preview is <http://127.0.0.1:8452/>. This increment ends with the verified
replay; no additional student generation or kernel execution is queued.
