# Next-actions workspace preview — 2026-09-29

The desktop preview adds a collapsible **Next actions** panel above the existing
notebook, alongside Captured / Generated / Reaction. It reads the completed
[Monte Carlo batch](2026-09-29-next-action-monte-carlo.md): 29 no-action draws,
one message, and zero edits. Counts, sample shares, and sampling intervals come
from the verified report. These are model frequencies at one input, not calibrated
student probabilities.

Selecting an action opens a saved sample as Reaction, brings its code into view,
and highlights a sampled message in the chat when present. Previous/next browse
samples within that action; **Original reaction** restores the existing receipt.
Captured and Generated remain available. A no-action sample adds no message or
code change. Any execution result is the observation supplied before the sample,
not a new execution of sampled code.

**New batch** previews a run-count input with default 30 and range 1–100. Its Run
button is disabled and explains that generation is not connected. Changing the
input does not relabel the saved 30-draw batch. There is no POST route, provider
request, tutor continuation, or notebook execution in this preview.

## Run locally

From the worktree with the private saved artifacts (these are not committed):

```sh
PYTHONPATH=. ../episode-pilot/.venv/bin/python -P apps/next_actions_preview.py \
  --branch data/notebook-source-branch-v1/branch \
  --execution data/notebook-course-execution-v2/results.json \
  --execution-sha256 6ca0ecd985a1cccdbda6b2b2ec7315f78abb9906e7fa31b50977388294b04e9c \
  --reaction data/notebook-course-execution-v2/reaction.json \
  --reaction-sha256 f66d7f0d7e3f092c2a6f3b7457843086b2e9b1eda7a0ba10cc9835c9ead6316a \
  --batch data/notebook-action-monte-carlo-v1 \
  --report-sha256 de2e3428ed12765476acbe7d5ab9b4e3a120a269f24fcdb998a5f608b4410317
```

Open `http://127.0.0.1:8449/`. Only this launcher adds the preview assets; the
normal workspace is unchanged. Saved samples must match the pinned report,
pre-reaction input, raw provider responses, and frozen report implementation.

## Checked

- 65 focused Python tests pass, including seven authored preview tests covering
  projection, failed draws, read-only behavior, unchanged evidence, and tampering.
- JavaScript syntax check passes.
- Browser checked at 1280×720: saved message/no-action selection, sample navigation,
  original restoration, Captured switching, run counts 30/50/invalid 0, and panel
  hide/reopen. Expanded details stay contained; selected code and chat remain
  visible together. No browser console warnings or errors were observed.

Next step is review of this layout. Connecting new sampling requires a bounded
background job, visible progress/cancellation, and saved batches bound to the
starting state; none of that is implied by this visual preview.
