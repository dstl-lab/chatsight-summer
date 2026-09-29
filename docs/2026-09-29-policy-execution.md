# Saved policy edits: execution and one reaction

This follow-up preserves the completed 60-sample comparison and adds actual
execution feedback. It does not rerun either tutor or replace any saved sample.

## Fixed scope

- Execute the three distinct saved source strings once each in the existing
  immutable archival-data container. Duplicate samples share that source check;
  they do not count as independent executions.
- Select sample 1 from each tutor condition before execution results are known.
- Supply each selected sample's own dialogue, edit and actual result to one
  Gemini 2.5 Pro student request. Maximum: two requests, no retries or subsequent
  execution of any proposed repair.
- Show execution beneath Generated and the separate follow-up under Reaction in
  the current browser workspace. Other samples have execution evidence only.
- Prepare the missing notebook setup and BabyPandas API reference for future
  tutor calls through the existing reference-file mechanism. This context does
  not retroactively change the original tutor replies or student samples.

The environment uses archived course data and declared package versions, not a
recovered historical kernel. Output and errors are local observations, not course
grades. A successful execution does not establish learning, and a model reaction
does not establish real-student fidelity or a general tutor-policy effect.

## Results

All three local executions completed in the existing immutable image. The full
archived table and declared package versions verified inside the worker.

| Saved edit | Matching samples | Distinct executions | Observed result |
| --- | ---: | ---: | --- |
| Direct answer, `.nunique()` | 30 | 1 | `AttributeError`: method unavailable |
| Guided hint, `len(...)` | 26 | 1 | 2,850 |
| Guided hint, array `.size` | 4 | 1 | 2,850 |

This establishes a concrete library-compatibility failure in the saved direct
reply and copied edits. It does not establish that hints are generally better:
each condition contains only one generated tutor reply. The duplicate samples
share one source check, rather than 60 independent executions.

Both new reactions completed after explicit user approval of the two prepared
Google Gemini requests. The initial automatic approval rejection remains recorded;
it occurred before any provider call. The subsequent authorization binds the
unchanged prepared inputs and precedes the launch receipt.

| Condition, sample 1 | Feedback supplied | One simulated reaction |
| --- | --- | --- |
| Direct answer | Actual missing-method error | Replaced the call with `len(...unique())`, without chat |
| Guided hint | Actual value 2,850 | No further action; no message or code change |

The direct reaction is revision 2 and **has not been executed**. Its view shows the
revision-1 error separately as the feedback it received. The hint reaction retains
revision 1 and is an explicit model choice, not an inference from missing logs.
Neither response establishes real-student fidelity, learning, understanding or a
general policy advantage. In particular, the repair may reflect the model's own
coding ability rather than this student's knowledge.

Exactly two requests completed, with distinct provider response IDs and 4,068
reported tokens, in about 21 seconds. Both report `gemini-2.5-pro`. Raw responses
reproduce the accepted actions; original comparison artifacts and all three
execution checks remain unchanged. No retries, tutor requests, further execution
or new human labels occurred. This bounded follow-up is closed.

Private artifacts: `data/notebook-policy-execution-v1/` contains the plan, checks,
prepared inputs, initial blocked-send record, authorization, launch, both raw
reaction receipts, and completion verification. The comparison digest is
`0db2d8a4bc46ff7c233e03d934c9053a4e5ef5949f1e38840da9f62a6c6066f2`.
All original study/probe files and receipts still verify unchanged. Private code,
messages, raw outputs and data remain ignored.

The existing workbench at <http://127.0.0.1:8450/> shows checks below each matching
Generated edit. Captured remains the shared pre-tutor state. Sample navigation
keeps the floating comparison open; later reaction edits cannot inherit a previous
execution result. The optional attachment is verified on startup and every read;
the viewer has no provider-send or code-execution endpoint.
Select sample 1 from either condition, then **Reaction / After execution** to see
its saved follow-up. Other samples have execution checks but no generated reaction.

Validation: 21 focused Python tests and three Node controller checks pass.
Browser inspection verifies the direct error, both hint values, continuous sample
navigation, the unexecuted repair and the hint's explicit no-action note.
Independent review verifies approval ordering, raw response replay, two distinct
provider receipts and unchanged prior artifacts. The existing Starlette/httpx
warning remains.

```sh
PYTHONPATH=. python -P apps/policy_sampling_preview.py \
  --branch data/notebook-source-branch-v1/branch \
  --comparison data/notebook-policy-sampling-v1 \
  --continuation data/notebook-policy-execution-v1 --live-results --port 8450
```

## Course context for future tutor calls

`src.agents.notebook_course_context` builds the existing `LibraryReference` format
offline. It binds a recovered capture to the saved branch, selects explicit setup
code before the editable cell, and combines those excerpts with the shipped API
reference. Optional line ranges are inclusive and one-based; selection never
executes code or automatically extracts imports. A separate manifest pins the
capture, API reference, declared runtime and branch checkpoint. Existing outputs
are never replaced.

The prepared private reference is
`data/notebook-course-context-v1/course-reference.json`. It includes captured
cell 1 lines 2–4 and cell 5, excluding grader setup, unrelated helpers, later work,
notebook outputs and previous tutor replies. Its environment is the verified
local probe: Python 3.13.15, BabyPandas 1.0.0, NumPy 2.3.3 and pandas 2.3.3.
These are declared local versions; the historical kernel and historical dataset
bytes are not established. The full captured input and original source pins stay
private beside the reference.

Build a new reference from explicit inputs with:

```sh
PYTHONPATH=. python -m src.agents.notebook_course_context \
  --output data/new-course-reference.json \
  --source-branch data/notebook-source-branch-v1/branch \
  --recovered-file data/notebook-course-context-v1/recovered.json \
  --reference-file runtime/notebook/babypandas-1.0.0-reference.json \
  --runtime-file data/notebook-course-context-v1/runtime.json \
  --setup-cells 1 5 --line-ranges '{"1":[2,4]}'
```

Future ordinary `notebook_tutor`, `notebook_lesson`, and notebook browser-workspace
launches accept this through their existing
`--reference-file data/notebook-course-context-v1/course-reference.json` option.
The reference is delivered only to the tutor, under the chosen teaching policy;
students receive the resulting tutor reply. The frozen policy-sampling runner
has no reference input and remains unchanged. This preparation makes no new tutor
request and does not establish that a future tutor will follow the reference.

The authored regression verifies CLI construction, capture binding, invalid
cell/range/version rejection, create-only behavior, exact delivery through the
existing tutor adapter, and exclusion from the student prompt. The related tutor
and context checks pass with injected callbacks and no provider calls.
