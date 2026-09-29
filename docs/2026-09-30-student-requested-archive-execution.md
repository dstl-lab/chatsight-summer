# Student-requested execution on the full archive

The next simulator step lets a generated student choose when to run the selected
cell on the complete archived CSV. Earlier replay executions were researcher
interventions. This changes the mechanism, not our evidence for student realism.

`src.agents.archived_notebook` starts at captured revision zero with one previously
saved tutor reply. It reuses the existing action schema, edit application, receipt
storage, immutable archive worker and isolated container executor. Frozen student
engines and completed studies remain unchanged. Their runtime is coupled to a
small supplied table and graded feedback, so this adapter records a separate
explicit session kind rather than pretending those inputs or grades apply.

Scope: six student decisions maximum, three requested executions maximum, no new
tutor replies, retries, replacements or automatic resume. Only `request-check`
executes code. Each execution starts with the complete table and a fresh namespace;
an edit invalidates its predecessor's feedback. Messages stop for a tutor, and
`no-reply`, budget exhaustion, runtime faults and provider failures remain distinct.
The `ok` status means the cell executed, with **no correctness grade**.

The CSV remains local inside the existing immutable image. The model receives the
selected instructions and cell, supplied student/tutor exchange, environment
metadata and this new run's actions/output/errors. It receives neither the full
table nor prior sampled edits, later reactions, historical future messages or
private host paths. Historical kernel/data identity and real-student fidelity
remain unestablished. This adapter deliberately supports the existing charts probe;
a different course asset needs its own verified runtime setup.

Every provider/execution dispatch has a pending receipt first. Raw model replies
and raw worker output are retained; offline replay reconstructs the exact prompts,
source/revision/CSV/image bindings, parsed observations, decisions and terminal
state. Interrupted and completed runs cannot resend. Code/dependency and original
study pins are revalidated. Injected callbacks require an authored-data flag, and
live runs require the actual pinned provider/executor.

The first bounded demonstration is fixed to the existing **direct-answer** tutor
reply, starting before any sampled edit or execution. This is a mechanism check,
not another policy comparison or labeling pass. The model may stop without
running code; that will be retained without a reroll or an injected Run action.
The user's standing Gemini authorization and latest instruction to continue
apply; any actual dispatch-review rejection will be recorded separately.

```sh
PYTHONPATH=. python -P -m src.agents.archived_notebook prepare \
  data/archived-student-loop-v1 \
  --followup data/notebook-policy-execution-v1 --condition direct
PYTHONPATH=. python -P -m src.agents.archived_notebook show data/archived-student-loop-v1
# Explicit, single bounded dispatch; show above is entirely offline.
PYTHONPATH=. python -P -m src.agents.archived_notebook run data/archived-student-loop-v1 --send
```

Validation: 18 focused Python checks pass (11 new authored loop checks, seven
existing execution/preview checks). They cover feedback invalidation, requested
execution only, raw replay/tampering, source binding, no retries/resend, failure
and interruption handling, fixed budgets, message-only stopping and provenance.
Independent review found and resolved timestamp-validation and dependency-pin
gaps. The existing Starlette/httpx deprecation warning remains.

## Completed bounded run

The plan and completed run are in ignored `data/archived-student-loop-v1/`, bound by
SHA-256 `f07deed298a34d7d4f451e0115510670e9e14ab84a055b4c0bf0fb6bde753524`.
Automatic approval review rejected the actual live command before process creation:
the private captured notebook and tutor context require specific approval for
transmission to Google Gemini. That rejection remains in `dispatch-block.json`.
Minchan then explicitly answered **“Yes, approved”** to this exact payload,
destination and six-decision/three-execution scope. `approval-response.json` binds
that answer and the earlier rejection to the unchanged plan before dispatch.

**One Gemini 2.5 Pro request completed; zero code executions occurred.** The model
chose `revise-work`, copied the supplied tutor's code into revision 1, and sent the
same code as a chat message. The runner correctly stopped at `awaiting-tutor`.
There was no `request-check`, no current observation, no provider error, no retry
and no replacement draw. Usage: 771 prompt tokens, 57 output tokens and 681
thinking tokens, totaling 1,509. No additional tutor reply was authorized or sent.

The edit repeats `.nunique()`, the method that raised an AttributeError in the
earlier saved archival execution. This new revision **has not been executed**.
The model's decision to paste code back is not a human realism judgment or proof
of the real account's behavior. The full archived execution path remains tested
with authored callbacks, but was not exercised by this live model choice.

Offline replay verifies the raw response, exact prompt and revised state.
`completion.json` binds the receipt and approval with counts and limitations;
an independent check confirms approval preceded the request and no previous
sample, reaction or table rows entered the initial prompt. The run ends here:
unused decision/check budget does not authorize a tutor turn, resume or reroll.
Port 8452 continues to show the earlier saved policy paths, not this new result.
