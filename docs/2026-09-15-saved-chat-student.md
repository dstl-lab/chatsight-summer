# Continue a student from an observed conversation

The fixed communication comparison is closed and the original generator stays.
Minchan asked to continue core simulator work using the current data. The useful
gap is persistence for dialogue-only situations: the existing continuation and
branch helpers have no saved interactive command, while every current student
command requires a declared notebook runtime. Most available historical prefixes
can support a chat continuation without establishing that runtime or current work.

Add a small `src/agents/chat_student.py` workflow on `codex/saved-chat-student`,
stacked on PR #27 in the existing isolated worktree while that PR awaits review.
Reuse the strict historical `Query` input, unchanged `student_continuation`
prompt/schema/branch helper, and existing local atomic-save/lock helpers. A seed
contains only an observed prefix; unexpected future/label fields are rejected.
Assign local turn IDs, retaining source identifiers only in the local manifest.

`create` initializes a new folder without a model call. `show` reconstructs saved
state and exports its binding. `step` takes that binding and makes one student
decision; a later step requires the researcher's supplied tutor reply. Recorded
prefix, generated student messages and supplied tutor turns remain distinct.
The supplied reply must address the state that was inspected. Reopening neither
regenerates old messages nor substitutes a recorded future after divergence.

Each session has a fixed decision budget. Generated no-reply and provider failure
are terminal; exhausted budget is a runner limit. Save pending before external
work; an interrupted receipt blocks resending. Verify source/schema pins and
exact prompt/result replay under the existing local session lock. CLI generation
requires `--send`; create/show do not load credentials or invoke a provider.

This is a chat scenario, not a persistent identity or a notebook simulation. Code
in a message executes nothing, and the runner records no edits, grades, feelings,
learning or inferred traits. It provides no new fidelity result or prompt change.
The existing notebook workflow remains available when its explicit inputs exist.
No generic session framework, new dependencies or interface is needed here.

Acceptance: reopen across two supplied tutor exchanges, retain the exact observed
and generated prefix, reject stale bindings, distinguish no-reply from budget,
preserve failures/interruption and refuse overwrite, and reproduce saved prompts
without model calls. Use authored provider outputs for this engineering check.
Then initialize the same 29 historical prefixes locally and verify their first
prompts match the frozen original-control prompts exactly. Do not generate another
batch or reopen the completed comparison. Raw inputs and session artifacts stay
outside Git; later private-data sends require their exact scope handled separately.

## Use

Save this invented starting situation as `data/query.json`, or supply one existing
historical Query record with the same strict structure. `response`, future turns
outside the prefix, labels and notebook fields are not accepted. Source IDs are
local provenance, not persona traits, and are omitted from the model prompt.

```json
{
  "id": "invented-addition",
  "conversation_id": "invented-chat",
  "prefix": [
    {"role": "student", "text": "values = [2, 5]\nhow do i add these"},
    {"role": "tutor", "text": "Try sum(values)."}
  ]
}
```

Initialize and inspect without credentials, Docker or a model call:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.chat_student create data/my-chat --query data/query.json --max-decisions 6
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.chat_student show data/my-chat > data/chat-context-1.json
```

To request the first student message, explicitly enable the provider call:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.chat_student step data/my-chat --context-file data/chat-context-1.json --send
```

When the result is `awaiting-tutor`, read `state.message`, save your tutor response
as UTF-8 in `data/tutor.txt`, and export the updated context before continuing:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.chat_student show data/my-chat > data/chat-context-2.json
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.chat_student step data/my-chat --context-file data/chat-context-2.json --tutor-file data/tutor.txt --send
```

Each step uses the model saved in the manifest (Gemini 2.5 Pro by default), loaded
only after validation. The existing provider adapter allows up to four attempts
per logical decision; individual adapter retries are not logged by this wrapper.
The CLI reports `decisions` and `remaining`. The budget cannot be changed by a
step. Even identical seeds receive different session bindings, so their context
exports cannot be interchanged. The whole dialogue is retained; there is no
memory compression, retrieval, trained persona or general session migration.

`origin: source` identifies the supplied starting prefix, `generated` identifies
student continuations, and the reused branch helper's `scripted` identifies your
supplied tutor reply. None of the supplied/generated text is a recorded future.
Do not delete pending receipts to retry an uncertain provider call. Preserve
terminal errors and use `show` to replay completed operations without calls.

## Completed checks and historical preparation

The lifecycle regression first failed because the saved-chat module was missing,
then passed across two tutor exchanges and reloads. A same-seed cross-session
regression exposed missing unique session identity; the manifest UUID fixed it
without changing any prompt. Guard tests verify provider failure, interruption,
stale/edited context, no-clobber output, strict input fields, fixed budget and
credential loading only after validation. All **381 tests pass**, with two
optional container checks skipped and one existing upstream deprecation warning.

All **29 existing historical prefixes** are initialized as new, independent chat
scenarios under ignored `data/episode-pilot/saved-chat-student-v1/`. Each first
prompt exactly matches its original-control prompt from the closed comparison.
Each remains `ready`, with zero decisions and six available. This preparation
made **zero model calls** and did not reuse generated outputs as new observations.
The separate manifests, context exports, preparation receipt and verification
script retain hashes; the earlier comparison and its source pins remain intact.
Independent audit verified all 29 source projections and unique bindings,
rejected 58 future/label-field injections, and preserved all 75 preparation pins
plus the 59 earlier comparison pins.

These are scenarios initialized from 29 conversations, not 29 validated student
personas. Only the offline lifecycle was advanced with authored provider outputs;
the real-data scenarios were not advanced or scored. The result is a reusable
interaction workflow for the existing corpus, not another fidelity experiment.
