# Fixed tutor-reply sampling comparison

Status: completed. All 62 approved requests returned valid responses. The
workspace at <http://127.0.0.1:8450/> now displays verified live results.

## Completed live smoke check

The existing sampling workspace at port 8449 sent three fresh Gemini 2.5 Pro
requests from its fixed after-execution input. All three completed and saved:
two `no-reply`, one `reply`, zero edits, zero failures. The reply replays in the
existing chat beside the unchanged notebook. There are three distinct provider
response IDs, 5,981 total tokens, and about 32 seconds between start and finish.
This checks the provider/save/replay path; three draws do not estimate student
behavior. The earlier 30-draw batch remains separate and unchanged.

Private receipt: `data/notebook-action-batches/64bfba97-ce87-4bea-8a8c-c8fe742a4a1b.json`.

## Fixed comparison

Start from captured revision zero, selected instructions, and the initial student
question. Remove the original tutor reply. Neither the previously generated edit
nor its execution result is supplied to either condition.

- **Direct answer:** generate one concise tutor reply with the complete corrected
  cell and a brief explanation.
- **Guided hint:** generate one actionable conceptual hint and focused question,
  without the complete corrected cell or final answer.
- Generate 30 independent student next actions per fixed tutor reply, using the
  existing action schema and sampler. At most two student requests run concurrently.
- Retain every attempted draw, including failures. No reroll, retry, resume,
  execution, grading, or manual labeling is part of this comparison.

The maximum is two tutor requests plus 60 student requests to Google Gemini
(`gemini-2.5-pro`). Private input, prompts, replies, and raw receipts stay in
ignored `data/notebook-policy-sampling-v1`. The prepared plan digest is
`fd98fe2fe3b0e568e922beb443edb40eac32da3ad895e30c1d22d00bd7d0ea62`.
Automatic approval review initially blocked the launch pending explicit
payload/destination/count approval. The user then approved exactly those inputs,
Google Gemini, and the 62-request maximum. The approval is recorded privately in
`authorization.json`; `started.json` binds the launch to the unchanged plan.

## Inspection

`apps/policy_sampling_preview.py` reuses the existing notebook/chat workspace and
its renderers. The floating **Compare next actions** panel shows both conditions'
counts, valid denominators, failures, and marginal Wilson intervals. Choosing a
cell opens that condition's saved action in **Generated**; **Captured** always
shows the shared pre-tutor input. **View tutor reply** restores the condition's
unchanged notebook and generated tutor message. The preview exposes no send API.
Previous/Next keeps the panel open while updating the notebook and chat in both
sampling views. Keyboard focus stays on navigation, moving to the enabled arrow
at either end. Regression checks cover both directions; live browser checks
browsed through all 30 comparison samples without reopening the panel.

The initial authored demo contains a toy addition task and deterministic stub
responses. It remains separate under `data/notebook-policy-sampling-demo-v1`;
its counts are UI test data, not experiment results.
Opening the app requires an explicit `--authored-demo` or `--live-results`
choice; it never silently defaults test artifacts to live results.

Validation for this follow-up: 86 focused Python tests and the policy sampling, next-action sampling,
and existing workspace Node controller checks pass. Browser checks cover real
three-sample saving/replay, live comparison selection, policy switching, captured
baseline preservation, and tutor-reply restoration. Glyphs preserve accessible
control names. The existing Starlette/httpx deprecation warning remains.

## Completed comparison

| Observed action | Direct answer | Guided hint |
| --- | ---: | ---: |
| Edit notebook | 30 / 30 | 30 / 30 |
| Chat without an edit | 0 / 30 | 0 / 30 |
| No further action | 0 / 30 | 0 / 30 |
| Failed student requests | 0 | 0 |

No edit included a chat message. Both edit shares have a marginal 95% Wilson
interval of 88.6–100%; the other action intervals are approximately 0–11.4%.
Zero observations do not make an action impossible.

The high-level distributions are identical, but the source differs. All 30 direct
samples copied the complete tutor-provided code, giving one distinct action.
The hint condition produced two source forms: 26 used `len(...)`, four used an
array's `.size`. These are descriptive code patterns, not correctness grades.
The source-only samples were neither executed nor compared against an actual
student's later actions. Thus this probe shows sensitivity in the proposed edit,
not an established improvement in realism or teaching effectiveness.

The run took 326 seconds, with 62 distinct provider response IDs and 87,540
reported total tokens. The two tutor requests are included; the earlier three
smoke requests are excluded. All 60 scheduled student draws remain in their
original order. No failed draws, replacement requests, extra samples, code
execution, or new labels were needed. The fixed run is closed.

Public aggregate: [results.json](../experiments/2026-09-29-notebook-policy-sampling/results.json).
The aggregate contains counts and metadata only; raw inputs and responses remain
private. The frozen runner reproduces action counts and intervals; descriptive
fields count nonempty edit messages, distinct serialized actions/sources, and
literal `.nunique(`/`len(` occurrences in the saved replacements.

```sh
PYTHONPATH=. python -P experiments/2026-09-29-notebook-policy-sampling/run.py \
  show data/notebook-policy-sampling-v1
PYTHONPATH=. python -P apps/policy_sampling_preview.py \
  --branch data/notebook-source-branch-v1/branch \
  --comparison data/notebook-policy-sampling-v1 --live-results --port 8450
```

## Interpretation and stopping rule

Stop after the scheduled 30 attempts per condition; do not add draws based on the
observed outcome. Report failed and unattempted draws separately from valid
actions. Frequencies describe this model conditional on two specific generated
tutor replies. They do not isolate a general policy effect, measure real-student
fidelity, or establish learning or instructor effectiveness. The recovered source
may be instrumentation testing, and the student history is sparse.

If action frequencies are similar, report that result; do not begin another
labeling loop. Inspect the proposed code as well as the high-level action label.

## Tutor reply check

The direct reply supplies complete replacement code, while the hint explains the
return type and asks how to determine its size. Thus the intended assistance
contrast is present. However, the direct reply uses a method absent from the
documented BabyPandas 1.0 Series API, while the captured setup imports BabyPandas.
This is a library-compatibility concern, not an observed runtime result: none of
the new code was executed. The frozen prompt omitted the setup cells and library
reference. Keep the response unchanged in this experiment; do not reroll it to
obtain a cleaner comparison. Source: [BabyPandas 1.0 implementation](https://babypandas.readthedocs.io/en/latest/_modules/bpd.html).

The next implementation priority is supplying the tutor with the course's
declared library/API context, then checking compatibility before treating
policy comparisons as instructional evidence. More action labels would not
resolve the limitation exposed here.

## Glyphs

Shared notebook/chat navigation, source and diff controls, results/details,
student/tutor identities, and comparison outcomes now use consistent 14–16px
outline glyphs. Visible text labels remain; SVGs are hidden from accessibility
names and do not receive focus. No dependency, image request, or CSP relaxation
was introduced. The notebook/chat rendering and action selection are unchanged.
