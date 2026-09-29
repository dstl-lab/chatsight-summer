# Fixed tutor-reply sampling comparison

Status: implemented and tested; live comparison prepared but not sent.
The local comparison preview uses explicitly marked authored test data.

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
Automatic approval review blocked the launch because it requires explicit
payload/destination/count approval. No `started.json` or comparison provider
receipt was created for that live plan.

## Inspection

`apps/policy_sampling_preview.py` reuses the existing notebook/chat workspace and
its renderers. The floating **Compare next actions** panel shows both conditions'
counts, valid denominators, failures, and marginal Wilson intervals. Choosing a
cell opens that condition's saved action in **Generated**; **Captured** always
shows the shared pre-tutor input. **View tutor reply** restores the condition's
unchanged notebook and generated tutor message. The preview exposes no send API.

The authored demo on port 8450 contains a toy addition task and deterministic
stub responses. Its counts are UI test data, not experiment results.
Opening the app requires an explicit `--authored-demo` or `--live-results`
choice; it never silently defaults test artifacts to live results.

Validation: 35 focused Python tests and the policy sampling, next-action sampling,
and existing workspace Node controller checks pass. Browser checks cover real
three-sample saving/replay and authored comparison selection, policy switching,
captured baseline preservation, and tutor-reply restoration.

## Interpretation and stopping rule

Stop after the scheduled 30 attempts per condition; do not add draws based on the
observed outcome. Report failed and unattempted draws separately from valid
actions. Frequencies describe this model conditional on two specific generated
tutor replies. They do not isolate a general policy effect, measure real-student
fidelity, or establish learning or instructor effectiveness. The recovered source
may be instrumentation testing, and the student history is sparse.

After approval, run the frozen plan once, inspect whether the generated tutor
replies actually follow the intended contrast, and replace the authored preview
with verified saved results. If action frequencies are similar, report that
result; do not begin another labeling loop.
