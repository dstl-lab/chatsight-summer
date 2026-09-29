# Next-actions workspace preview — 2026-09-29

The desktop preview adds **Next actions** to the top-right toolbar. Its floating
panel opens over the chat side without resizing or covering the notebook, using
no additional sidebar tab. It reads the completed
[Monte Carlo batch](2026-09-29-next-action-monte-carlo.md): 29 no-action draws,
one message, and zero edits. Counts, sample shares, and sampling intervals come
from the verified report. These are model frequencies at one input, not calibrated
student probabilities.

Selecting an action closes the panel, opens a saved sample as Reaction, brings
its code into view, and highlights a sampled message in the chat when present.
The toolbar button reopens the panel; Escape and outside clicks dismiss it.
Keyboard focus returns to the toolbar button after choosing an outcome.
Previous/next browse
samples within that action; **Original reaction** restores the existing receipt.
Captured and Generated remain available. A no-action sample adds no message or
code change. Any execution result is the observation supplied before the sample,
not a new execution of sampled code.

**New batch** defaults to 30 runs, with range 1–100. When launched with
`--sampling-dir` and a configured Gemini key, clicking Run starts independent
student decisions from the fixed, verified after-execution input. Choosing another
displayed sample does not change that starting point. The form names the model,
context sent to Google Gemini, and number of requests before submission.

The panel and toolbar show progress. Cancel stops future requests after the one
in flight finishes; that request has a 120-second provider timeout. Valid outcomes
remain inspectable in partial batches. Failed draws are reported separately and
excluded from action-frequency denominators. Requests are not retried or replaced.
The batch picker preserves prior results, including the original saved 30 draws.
Notebook code and further tutor replies are not executed or generated.

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
  --report-sha256 de2e3428ed12765476acbe7d5ab9b4e3a120a269f24fcdb998a5f608b4410317 \
  --sampling-dir data/notebook-action-batches
```

Open `http://127.0.0.1:8449/`. The launcher reads `GEMINI_API_KEY` from the environment,
the worktree `.env`, or the repository's `main/.env`, following the existing
workspace convention. It does not start sampling on launch. Omit `--sampling-dir`
for the original read-only mode with no POST routes. The normal workspace remains
unchanged. Saved samples must match their input and raw provider responses.

One local process owns the output directory and runs one request at a time.
Each UUID identifies one submission; duplicate submissions with that UUID return
the saved job. Atomic local receipts retain the frozen prompt/settings and every
raw response, including failed output. On restart, unfinished jobs become
interrupted; they never resume or resend. Private prompts and samples stay in the
ignored data directory. HTTP submissions require the local origin/host checks and
a workspace token; request bodies cannot select input files or arbitrary prompts.

## Checked

- Functional follow-up: 890 Python tests pass, three optional skips; the existing
  Starlette/httpx deprecation warning remains. The 23 runtime and eight API tests
  cover bounds, input binding, idempotency, cancellation, restart interruption,
  failed-output preservation and tampering. Both Node controller checks pass.
- Browser stub: completed three requests, inspected an earlier batch's message,
  cancelled another batch with its in-flight sample preserved, and reopened saved
  batch history. Starting a batch collapses setup into progress. No paid model
  calls were made by these checks. The configured real workspace exposes Run but
  remains idle until explicit submission.
- 65 focused Python tests pass, including seven authored preview tests covering
  projection, failed draws, read-only behavior, unchanged evidence, and tampering.
- JavaScript syntax check passes.
- Browser checked at 1280×720: saved message/no-action selection, sample navigation,
  original restoration, Captured switching, run counts 30/50/invalid 0, and panel
  hide/reopen. Expanded details stay contained; selected code and chat remain
  visible together. No browser console warnings or errors were observed.
- After the floating-panel revision, checked native keyboard opening, Escape,
  outside dismissal, setup, sample selection and focus restoration. Notebook
  position and height remain identical with the panel open and closed.

The functional path is checked with an authored provider stub; implementation and
browser verification do not submit a paid batch. Cross-policy sampling remains a
future task: this version holds the starting point and model fixed.
