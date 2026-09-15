# Use the existing generated replies to begin tutoring

Minchan asked to continue after the saved-chat workflow. PR #28 merged as
`9ac3e45` into PR #27's branch; main still awaits the required review. This
increment uses `codex/chat-continuation-handoff` in the existing isolated worktree.

The fixed comparison already contains one original-generator reply for each of
the 29 historical prefixes. Every reply's prompt, schema and model exactly match
the corresponding initialized chat scenario. Regenerating those replies would
add cost and start another unnecessary sample. Use the existing callback-based
`chat.step` to import those exact generated decisions into separate new sessions.
No production code, prompt change or general cache subsystem is needed.

Before each import, verify the frozen experiment/results and match the query,
exact prompt, schema and model to the selected original-control call. Preserve
the earlier 29 initialization-only sessions. Create new session identities and
record both the original generation time and the local import time. A separate
immutable handoff receipt links the source artifact hashes and call index to the
new session, saved step and current tutor-context export.

Each new session should reopen in `awaiting-tutor` with the original generated
message, one reused decision and five decisions remaining. The new operation's
timestamps mean local import, not fresh provider execution. Report zero new
provider requests and zero new samples. No recorded real next message, candidate
output, label or supplied tutor answer is imported into these initial contexts.

Write one readable tutor handoff per conversation, with the pending generated
message and its actual preceding context, plus an index. This is research output
for using the existing runner, not a new UI or a review packet. The teammate's
Marimo viewer remains separate. The next tutor reply is an intervention; later
generated messages must continue from it without appending historical futures.

Acceptance is exact replay and provenance for all 29 imports, unchanged prior
artifacts, and explicit separation of reused decisions from new API calls. Keep
all student text and handoffs in ignored private data. This is an interaction
handoff, not another benchmark, plausible-message rating round or fidelity claim.

## Completed handoff

All 29 original-control replies were imported into new, independently identified
sessions in ignored `data/episode-pilot/chat-continuation-handoff-v1/`. All reopen
as `awaiting-tutor`, with the exact original generated message, one reused
decision and five decisions remaining. There were **zero new provider requests,
zero new samples and zero new labels**. No simulator source changed.

`INDEX.md` links to one readable file per conversation in `tutor-handoffs/`.
Each puts the pending generated message before its actual recorded context.
Matching current snapshots are in `contexts/`, and runnable saved sessions are
in `sessions/`. The index is for selecting a conversation to tutor, not for
rating another message batch. Every case was retained in the original order.

For example, inspect the first imported conversation without a provider call:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.chat_student show data/episode-pilot/chat-continuation-handoff-v1/sessions/case-01
```

The next intervention is a supplied tutor reply to that generated message. A
subsequent `chat_student step` uses the corresponding context export and the
tutor reply, under the existing saved-chat command. That would be a new provider
request, whose private-data scope must be handled separately; none was made here.
No historical future is appended after the simulated conversation diverges.

`handoff.json` links each original call index, query ID and generation timestamp
to the new session/context/handoff and local import timestamp, with hashes for
the underlying source and saved artifacts. A `step-0001.json` receipt in these
folders represents the local import of a previously generated decision; its
timestamps are not the time of a fresh API request. The unchanged engine can
replay it and continue normally, while the handoff receipt supplies its origin.

Verification replays every session and compares each saved response and prompt
with the original receipt. Both the original 29 initialization-only sessions and
the completed 58-request comparison still pass their own checks unchanged. The
381-test source commit is unchanged; this increment verifies reuse and state,
not behavior or a new model result. Preserve the initial handoffs as evidence if
later continuing a conversation; they describe the imported starting state.
Independent audit verified all 29 imports, distinct identities across all 58 old
and new sessions, 203 rejected in-memory mismatches and 197 unchanged artifacts.
Verification also passed with provider construction explicitly forbidden.
