# One student continuation from recorded work

Minchan approved connecting a historical course checkpoint to the simulator after
reviewing the notebook replay UI. Complete one inspectable, saved continuation:
one source edit, chat message or model-selected stop. No manual labeling, new
training, database reads, tutor calls or automatic follow-on experiment.

Reuse the already-recovered initial course exchange and the work/instruction
selection retained by the earlier notebook-action preparation. Reconstruct that
task from its pinned initial capture and verify the old selection; do not select
from later outcomes or reopen the old experiment. The conversation is exposed
development evidence with sparse student history, not a held-out student sample.
Keep the original capture, old runs and the new branch separate.

The notebook executor accepts a declared single-table activity, not an arbitrary
course notebook. Do not invent table data, installed dependencies or an execution
result to satisfy its schema. Reuse `notebook_action.initial_task`, its existing
prompt/action schema and `apply_action` for a source-only decision. Record omitted
dependencies and keep execution unavailable. Preserve empty chat for quiet edits.

Add the smallest saved one-action wrapper: immutable initial inputs, exact prompt
and schema/source pins, one pending receipt before dispatch, one single-attempt
Gemini student call, and offline result reconstruction. A pending, failed or
completed receipt cannot resend. Reuse existing storage/provider helpers. Expose
initial and result frames through the browser notebook/chat shell as a read-only
generated branch, distinct from recorded event playback. No synthetic container
receipt or course grade is created.

Verify with authored data first, including source-only edits, separate generated
chat, chosen stop, missing feedback, altered inputs and interrupted-call refusal.
Pin the concrete private input and prompt before any provider call. Stop when one
continuation is saved and reloadable, or report an actual dispatch/configuration
blocker without generating a replacement. This is an integration milestone; it
does not score realism against the later historical notebook or establish learning.
All course content and generated outputs remain in ignored local data directories.

## Implemented

`src.agents.notebook_branch` creates, dispatches and reopens one source-only
decision using the existing action implementation and single-attempt provider.
The checkpoint pins action/schema, storage and provider dependencies. The browser's
exclusive `--notebook-branch` mode verifies the checkpoint and reconstructs any
completed action on every reload; it installs no mutation routes. Initial work,
generated revisions, generated messages, chosen no-reply, a pending request and
generation failure stay distinct. The notebook view shows selected instructions
and one cell; changes and original text are inspectable without implying execution.

```sh
python -m src.agents.notebook_branch create data/my-branch \
  --recovered /absolute/path/to/one-recovered-capture.json \
  --instruction-cells 14 --work-cell 15
python -m src.agents.browser_workspace --notebook-branch data/my-branch --port 8447
# After inspecting the exact checkpoint and authorizing its provider disclosure:
python -m src.agents.notebook_branch step data/my-branch \
  --checkpoint-sha256 <hash-printed-by-create> --send
python -m src.agents.notebook_branch show data/my-branch
```

Cell selections above are illustrative command arguments; select them from the
chosen earlier capture, never by inspecting its later outcome. The CLI prints
only request status, decision type and checkpoint hash. Course text, exact prompts,
provider diagnostics and saved actions remain in the ignored branch directory.

Verification: 804 Python tests pass with three optional skips and the existing
Starlette/httpx deprecation warning. The Node controller suite and syntax/diff
checks pass. Three targeted tests pass again after expanding dependency pins.
Independent review found no lifecycle/display blocker; its dependency-pin gap was
fixed before freezing the real input. Local HTTP checks verify the prepared
notebook/chat workspace. No real notebook code, tutor request or training ran.

The selected historical starting task reproduces from eight unchanged saved
source/preparation files. Its first two dialogue turns, one instruction cell and
one code cell form the 3,173-character prompt; later evidence and earlier generated
outputs are excluded. External table state is unavailable, so no runtime activity,
grade or feedback is fabricated. Private preparation and an exact disclosure file
are in `data/notebook-source-branch-v1/`.

Automatic approval review rejected dispatch before process launch because this
specific private course payload and the Google Gemini destination require explicit
approval. The rejection is retained locally. Minchan then explicitly approved
sending the pinned instruction cell, code cell and two dialogue turns to Google
Gemini 2.5 Pro for exactly one student decision. `approval-response.json` binds
that response to the unchanged checkpoint, prompt and preparation before dispatch.

## Completed continuation

The single-attempt request completed in 9.93 seconds with `revise-work`: the
student changed the code and sent no chat message. The saved result reports
`execution: not-run` and no observation. The browser at
<http://127.0.0.1:8447/> reloads two frames: captured starting work and generated
revision, with a source diff and the original two dialogue messages. Zero decisions
remain because the request budget is exhausted; this is not a chosen student stop.

`branch/decision.json` retains the result, and `completion-verification.json`
records artifact hashes and verification. All eight original source/preparation
files are unchanged. Independent verification confirms engine/input pins,
approval timing, exact offline reconstruction and the two-frame browser projection.
The live read-only endpoint also serves the completed result with sending disabled.

The one-continuation stopping rule is satisfied. No further provider request,
tutor reply, notebook execution, grade or label is needed. This demonstrates that
captured course work can feed a saved, inspectable simulated source edit; one
exposed example does not establish realistic student behavior or learning gains.
