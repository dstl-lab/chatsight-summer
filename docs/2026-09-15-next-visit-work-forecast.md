# A bounded forecast of work at the next tutoring visit

Minchan asked to continue from the notebook-pair availability check. A later
capture cannot score the current simulator's next action or chosen stop: the logs
lack the action count and elapsed-time mapping. Selecting only cells known to
change would also let future work determine the editable scope.

Use an explicit **next-visit state forecast**, conditional on a subsequent recorded
visit to the same notebook. The target is the next eligible linked capture in the
filtered logs; intervening unlinked or ambiguous visits may be unobserved. This is a small predictive baseline for net notebook
work, not a replay of the current action policy. Keep the working action/runtime
engine unchanged. The existing engine remains useful for generated interactions;
this different observation boundary needs a plainly different forecast prompt.

## Fixed development check

Use only pairs 2 and 3 from `notebook-snapshot-pairs-v1`, the two already-exposed
pairs with equal cell-type layout and exact non-code source. Pair 1 remains
excluded for unresolved alignment; no replacements or new sampling. Both examples
are development evidence. Their selection based on future layout compatibility
prevents a prospective deployment/holdout claim.

Recover each first capture's initial student/tutor exchange using the existing
read-only probe and `recover_initial`. Query only those two earlier conversations
and same-learner query metadata within five minutes preceding their captures.
Keep learner identities server-side. Missing/ambiguous attribution excludes a case
without replacement. Preserve query receipts and earlier evidence.

The forecast receives all source cells from the first notebook capture, plus only
its matched first student/tutor exchange. Include all initial code positions, not
positions selected from later changes. Exclude notebook/account/conversation names,
event IDs, timestamps, outputs, execution counts, later dialogue, the second
capture and the measured time gap. Source text and the two messages remain private
student/course material; removing metadata does not make the excerpts anonymous.

Return complete replacement source for zero or more distinct initial code indices.
Unlisted cells retain their initial source. Empty replacement text clears a cell;
an empty edit list means unchanged net source. Do not modify/add/delete/reorder
cells or claim actions, execution, feedback, mastery or hidden emotions. No student
chat is generated in this work-only forecast. This fixed-layout restriction is
explicit and cannot evaluate arbitrary notebook restructuring.

Use Gemini 2.5 Pro with the existing adapter/default settings, one logical request
per recoverable pair, at most two logical requests and eight adapter attempts.
Record pending dispatch before sending. The existing adapter retries network,
JSON and schema failures within its four-attempt limit; these are adapter attempts,
not replacement logical requests. Preserve final failures and forecasts with
invalid cell scope without replacement; do not reroll for a more interesting change. Standing user approval
applies; preserve any automatic-review rejection and request the exact required
input only if it cannot be resolved under that authorization.

## Measurement and checks

Compare predicted and observed net source changes across **all** initial code
positions. Report changed/unchanged counts and edit-detection TP, FP and FN, plus
exact text matches at observed changed positions. An unchanged-source baseline
uses the identical scope. Whitespace differences count; text equality is not
semantic equivalence or correctness. Avoid overall cell accuracy: mostly unchanged
cells would dominate. With one forecast per example, do not report calibrated
probabilities or population fidelity. No additional human labels are needed for
these mechanical source comparisons.

Add only a pure forecast/schema/comparison helper using the installed Pydantic
and existing generation adapter. Reuse the ingestion recovery; no new runtime,
policy tree, UI or framework. One authored test covers future exclusion, unchanged
baseline, quiet net edits, invalid/duplicate/non-code indices, input preservation
and layout mismatch. The private preparation must prove that modifying any future
capture cannot change prompt or editable scope. Independently audit preparation
and recompute results from saved source/response artifacts.

## Stop

Finish after the fixed requests, exact offline reproduction and a report of actual
results, exclusions and limitations. No automatic tuning, more examples, human
plausibility pass or adoption into the action simulator. Commit code and aggregate
findings in the existing isolated worktree and draft PR #25; keep data private and
the PR unmerged. If dispatch requires new explicit approval, prepare and verify the
exact payload first, then stop at that required input.

Pre-dispatch clarification: endpoint wording and adapter-invalid retry behavior
were made explicit after protocol audit. The original recovery-only protocol
copy is retained; the final execution protocol will be pinned separately.

## Prepared and verified; dispatch blocked

Both fixed examples recovered successfully without replacement. Each has one
matching initial query; the saved conversation metadata contains one and four
tutor responses respectively, with one uniquely matched first response per case.
The recovered capture hash binds the assembled six fields (ID, time, conversation,
student message, embedded response and notebook JSON), not the full database row;
original source receipts are separately pinned. `check_recovery.py` reproduces
these inputs exactly without database access.

| Prepared example | Initial code positions | Observed changed positions | Unchanged baseline: TP / FP / FN |
|---|---:|---:|---:|
| Pair 2 | 58 | 1 | 0 / 0 / 1 |
| Pair 3 | 54 | 4 | 0 / 0 / 4 |

The two exact prompts contain 35,900 and 25,765 characters. Their only data fields
are initial cell index/type/source and first-exchange role/text. Future captures,
outputs, execution counts, elapsed gap and identifying metadata are excluded.
Names or other identifying material within source text may remain; these are
still private student/course excerpts, not anonymous inputs. The later captures
are stored separately in `targets.json`. All initial positions remain in scope.

`src/eval/notebook_forecast.py` supplies `Forecast`, `make_prompt`,
`apply_forecast` and `compare`. It validates typed, distinct in-range code edits,
preserves all unlisted source and input objects, and rejects incompatible target
layouts/scaffolds. It makes no provider calls or notebook executions. The single
authored regression was observed failing before implementation; the final run
of forecast/action/context/continuation tests passes **17 tests**. The private
runner's authored control verifies invalid-scope retention and refusal to resend
an existing run. Exact projection and future-mutation checks pass.

Independent preparation review matched the initial sources, recovered exchange
hashes, targets, complete code scope, source pins, exact disclosure and dispatch
bounds. The earlier notebook-pair completion's 20 file hashes and completed
help/work coding's nine pins remain unchanged.

The attempt to start the fixed run was **rejected by automatic approval review
before process creation**. Its stated reason was that the standing project
approval did not specifically authorize these private notebook sources and
student–tutor exchanges to Gemini. `send-blocked.json` preserves the rejection
and exact payload hashes. No run receipt exists: zero logical model requests,
zero adapter attempts and no generated forecasts. No workaround was attempted.
The remaining input is specific authorization for the unchanged two disclosed
payloads. Preserve the rejection even if that authorization arrives. A future
approval receipt must bind these same files and precede dispatch.

This is ready preparation and a working offline comparison, **not a completed
model study**. The baseline values above are observed-source measurements; they
must not be presented as simulator performance. Production action/runtime behavior,
prior experiments and human judgments remain unchanged. PR #25 stays draft and
unmerged. After exact authorization, run these two requests once and report their
outcomes; do not select replacements or expand the study.

Reproduce the preparation from the isolated worktree:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m pytest -q tests/test_notebook_forecast.py tests/test_notebook_action.py tests/test_notebook_context.py tests/test_student_continuation.py
PYTHONPATH=. ../main/.venv/bin/python data/episode-pilot/next-visit-work-v1/check_recovery.py
PYTHONPATH=. ../main/.venv/bin/python data/episode-pilot/next-visit-work-v1/run.py --check
```

All private inputs, source/query receipts, original and clarified protocol copies,
runner, exact disclosure and rejection are in
`data/episode-pilot/next-visit-work-v1/`. The execution protocol and preparation
artifacts remain pinned separately from this status report.
