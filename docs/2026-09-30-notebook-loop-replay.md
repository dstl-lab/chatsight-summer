# Saved notebook loops in the workbench

The workbench presents each existing sequence directly as five stages:
**Captured start → Tutor reply → Student edit → Local execution → Next action**.
The connected event timeline sits above the notebook, with the shared chat alongside it.
The single-case view hides the unnecessary task picker; the ordinary policy
sampling view is unchanged.

The preview now includes the previously saved **sample 1 from each policy** in
the closed study and its execution follow-up. A native **Tutor policy** selector
above the timeline preserves the selected stage while updating notebook, output,
and chat together. Guided hint produced `len(...unique())`, a local result of
**2,850**, and a saved **no further action** decision. Direct answer produced
`.nunique()`, a local **AttributeError**, and a saved repair that **has not been
executed**. This UI change made **zero model requests, zero notebook executions
and zero new labels**. Each path has one predetermined follow-up; neither is a
policy-level success estimate or a finding about real-student fidelity.

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

`--student-loop both` reuses the existing verified comparison and continuation
loaders. It selects each condition's predetermined reaction sample, rejects
incomplete sequences, and verifies source/runtime/raw-result/provider-response
attribution on each read. The view exposes no POST/send/execution endpoint.
Authored test data retains its explicit banner. Original artifacts are unchanged.
The `direct` and `hint` options still expose just one path without a selector.
The selector rejects switching during reload and is hidden when evidence is
unavailable; switching closes any old inspector selection. Policy instructions and limits are
available under Saved results. Mouse and native keyboard selection retain focus.

```sh
PYTHONPATH=. python -P apps/policy_sampling_preview.py \
  --branch data/notebook-source-branch-v1/branch \
  --comparison data/notebook-policy-sampling-v1 \
  --continuation data/notebook-policy-execution-v1 \
  --live-results --student-loop both --port 8452
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

Policy-switch validation: seven focused Python checks and three Node controller
checks pass. The browser preserves Local run / Next action when switching,
displays the correct error or value, keeps the repair unexecuted, and maintains
native keyboard focus. Changed receipts still redact both paths. All five glyphs
remain centered in their nodes.

## Next simulation boundary

The existing `notebook_student` engine already supports student-selected
`request-check` actions. This archival charts task cannot use its runtime
unchanged: the runtime takes at most 2,048 one-column values, while the archive
has 70,183 rows and 2,850 distinct URIs. The archive worker also uses a different,
ungraded output protocol. Raising the value limit would put the whole table into
the model prompt. Future student-selected execution on this exact case therefore
needs an explicit file-backed runtime adapter; truncating the table or substituting
placeholder values would change the task. That adapter is not implemented here.

## Timeline refinement

The five events now share a continuous neutral rail, with glyphs, short labels,
and visible actor attribution. The researcher-triggered run uses a square node;
model events use circles. Only the selected event is highlighted, without
suggesting that earlier events passed a test. The redundant Previous/Next row is
hidden. Each event retains the existing native button, click handler, pressed
state and focus restoration, so keyboard users can tab between events and select
them with Enter or Space. The authored example still identifies its source as
authored. No replay data, prompts or generation behavior changed.

The refinement passes four Python checks, three Node controller checks, and
browser verification of layout, Tab/Shift+Tab navigation, Enter/Space selection,
preserved focus and the matching output/reaction. Independent review also checked
actor attribution and the neutral timeline state.
