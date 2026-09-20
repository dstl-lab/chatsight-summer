# Continue the existing conversation scenarios

The Marimo workspace can now select saved chat scenarios, generate a tutor reply
under an editable policy, continue one student decision, and reopen the result.
This is the next operational step approved by Minchan after the notebook workspace;
it does not reopen the paused labeling audit or introduce another fidelity study.

## Use

```sh
uv sync --extra workspace
.venv/bin/marimo run apps/student_workspace.py --host 127.0.0.1 --port 8424 --headless -- \
  --chat-sessions data/episode-pilot/chat-workspace-v1/sessions --send=true
```

Select a scenario, inspect its recorded prefix and pending simulated message, edit
the tutor policy or write a reply, and continue one decision. Reload reads the saved
result without a model request. Switching scenarios reopens their existing sessions;
it never recreates or rerolls them. Draft inputs reset when switching scenarios to
avoid applying another case's draft accidentally. Within a scenario they survive
view changes and reloads; they are not durable across a browser/kernel restart.

Omit `--send=true` for viewing only. `--session PATH` still opens an existing
notebook student; the two modes are mutually exclusive. The scenario directory is
chosen by the server operator, with only its immediate saved-session folders in
the selector. Student data stays on the local interface until a generation button
is clicked. Each policy click requests one tutor reply and one student decision
from Gemini, subject to the existing provider retry policy. Manual reply mode
requests only the student. Neither chat mode executes code nor calls Docker.

## Existing evidence and new interactions

The private preparation under `data/episode-pilot/chat-workspace-v1/` reuses all
29 original-generator first replies from the completed comparison. Each new
workspace session has its own identity, the exact recorded query and model, and
the original six-decision budget: one cached decision used, five remaining.
The original handoffs, initial sessions, comparison and review artifacts stay
unchanged. Preparation receipts distinguish original generation time from local
cache-import time. No provider is used to import or reopen a scenario.

Recorded turns, simulated student messages and tutor interventions are labeled in
the conversation. Notebook contents, edits, execution and grading remain unknown;
code pasted into chat is not a recovered notebook. These are conversation scenarios,
not reconstructed individual students or calibrated personas. Once simulation
diverges, no later recorded messages are appended.

`src/agents/chat_workspace.py` wraps the unchanged saved-chat runner. It supplies
only the visible dialogue and pending message to the policy tutor, with the latter
included once. Private query/learner identifiers are omitted from that prompt.
The exact policy, context, schema, model and generated tutor reply are saved under
`tutor-exchanges/STATE_HASH/`. A saved exchange blocks repeat tutor requests for
that state. Student delivery uses the original displayed binding and fixed budget.
Another writer can advance during tutor generation: the reply may finish and be
saved, but the runner rejects delivery to the changed state. An interrupted request
is retained for inspection, never automatically retried by the workspace.

The student generator, source-pinned replay engine and existing notebook helpers
are unchanged. The chat-specific tutor prompt is new. This increment makes the
existing scenarios usable for interaction; it establishes neither realistic
student behavior nor causal effects of tutoring policies.

## Verification

The full suite passes: 393 tests, with two optional container checks skipped and
one upstream Starlette/httpx deprecation warning. Marimo validation passes. New
authored lifecycle checks cover exact policy/context, origin preservation, manual
continuation, budget/terminal guards, interrupted tutor requests and a concurrent
student advance that rejects stale tutor delivery.

The browser check uses two separate invented scenarios and injected responses.
One policy exchange and one manual exchange advance only the selected case;
switching/reloading reopens the result without a request, scenario changes reset
drafts, and budget exhaustion removes generation controls. The test receipt is
ignored under `data/episode-pilot/chat-workspace-ui-v1/`. No live model or execution
calls were used for these checks.

All 29 real-data workspace sessions were prepared offline. The preparation
verifies 195 existing source pins, 87 startup files and distinct source/workspace
identities. Its `prepare.py verify` command protects startup evidence while
allowing subsequent workspace interactions. No new labels, provider calls or
database queries were needed for this increment.
