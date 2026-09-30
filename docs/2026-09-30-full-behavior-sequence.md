# One continuous captured-notebook encounter

Minchan asked to try the full behavioral sequence after reviewing the limits of
chat-form scores and next-capture notebook forecasts. This is one bounded
development demonstration of sustained action generation, not a new fidelity
benchmark or a repeat of a closed sampling study. No human labels are requested.

## Question and fixed probe

Can the existing captured-notebook student carry its work, execution feedback and
dialogue through multiple decisions and tutor exchanges without a researcher
manually supplying each next turn?

Start at the existing captured revision zero with the already saved **guided-hint**
tutor reply in `data/notebook-policy-execution-v1`. Keep the declared immutable
archive runtime and complete local CSV. The model receives the selected task,
source, visible exchange, runtime description and this run's subsequent actions
and feedback. It does not receive prior sampled edits, prior execution results,
later recorded messages, the historical target notebook or CSV rows. The course
API reference is supplied to the tutor only.

Use Gemini 2.5 Pro for both roles, with the existing prompts/action schema and
one SDK attempt per request. One fresh run permits at most **eight student
decisions, three new tutor replies and four requested local executions**. The
initial saved tutor reply consumes no new request. Student messages trigger the
next tutor reply automatically while budget remains. Only `request-check` runs
code. A quiet edit clears current feedback; real cell errors become visible to
the next decision. All executions use the existing isolated local container.

Stop at explicit no-reply, a provider/infrastructure failure, or when the next
required operation would exceed its budget. The eighth student decision ends the
run; using the last permitted tutor reply or execution still allows other student
actions within the remaining limits. No automatic retries, resuming, replacement draws or
forcing a run/help request to obtain a more interesting trajectory. A short or
unhelpful sequence is a result. An interrupted attempt stays interrupted.

## What will be evaluated

- The actual ordered decisions, edits, requested executions and tutor exchanges.
- Whether each result is bound to the source revision actually run, and edits
  remove stale current results without erasing history.
- Whether both roles retain the preceding visible interaction and receive only
  current feedback; chat alone does not change code or establish an execution.
- Execution outcomes and terminal reason, with no-reply, budget stops and faults
  kept distinct. An archive `ok` result means execution completed, not correctness.
- Exact offline replay from the retained raw provider and executor receipts.

There is no matched real-student action sequence here, so no behavioral accuracy,
calibrated stopping probability, learning claim or tutor-policy comparison will
be computed. The unchanged initial work is the source-diff reference, not an
empirical behavioral baseline. This trial ends after reporting its one outcome.

## Implementation and authorization

Reuse the existing action schema/application, tutor prompt/schema, archive
executor, storage, locks and read-only workbench renderer. A small separate
orchestrator is needed because the frozen archive runner stops at every message
and resets history/feedback when started again. Preserve those historical engines
and artifacts. Keep all private prompts and receipts in ignored
`data/full-behavior-sequence-v1` and publish only aggregate mechanics/results here.

The user's request to try this and standing project authorization cover the
bounded work. Any actual dispatch-review rejection will be recorded before
requesting the exact additional authorization it requires.

## Prepared implementation and dispatch status

`src/agents/archive_sequence.py` now prepares, runs and independently replays the
continuous sequence. Its raw-call receipts retain full provider responses and
worker output; snapshots expose current work, dialogue, pending message,
observation, attempt counts and stop reason to the existing workbench. Global
limits count attempts, including failed calls. A pending or completed run cannot
be sent again. Historical archive engines and saved studies remain unchanged.

The fixed private plan is prepared with digest
`9c885f7b2fc005b3c25d6fd37dad50c25b51ed31a508a93553ba4852ba64d73f`.
Its original protocol snapshot and standing authorization are saved beside it.
Fifteen code dependencies and the source/runtime/reference inputs verify. The
immutable runtime image is available locally. Preparation sent no data and ran
no candidate code.

Automatic approval review initially rejected the live dispatch **before process creation**:
the user authorized trying the sequence, but review requires explicit approval
of this private notebook/code/chat/reference payload to Google Gemini. The block
is recorded in `dispatch-block.json`. At that point there was no `run.json`, and
zero provider calls or executions. Minchan then answered **“Yes, approved”** to
the exact notebook/code/chat/reference and subsequent actions/feedback transfer
to Google Gemini 2.5 Pro, with the fixed eight/three/four limits and no retries.
`approval-response.json` binds that answer and disclosure to the unchanged plan
and rejection before the single live dispatch. The approved run is now closed.

Verification: **1,001 Python tests passed, three optional tests skipped**, with
the existing Starlette/httpx deprecation warning. This includes the authored
error → message → tutor → quiet repair → execution → no-reply sequence, global
caps, interrupted/failing calls, exact replay and altered-receipt rejection.
The archive, policy-sampling and browser-workspace Node checks also pass.
Independent backend review found no dispatch blocker; it clarified the budget
wording above. These authored checks are not live model or real-student results.

## Live outcome: chat proposals diverged from installed work

The run completed in **53.46 seconds**, with **three student decisions, two new
tutor replies, zero execution requests and no provider failures or retries**.
All five provider responses were complete, valid structured outputs from
`gemini-2.5-pro`. Usage totaled 11,206 tokens: 5,590 prompt, 241 output and
5,375 thinking tokens. Final no-reply was an explicit model choice with budget
remaining, not a timeout or imposed stop.

| Stage | Saved behavior | Notebook / execution evidence |
| --- | --- | --- |
| Initial | Captured work and reused guided hint | Revision zero, no execution feedback |
| Student 1 | Edit plus code pasted in chat | The replacement-source field contained a generic one-word placeholder, not the proposed chat code |
| Tutor 1 | Discussed the chat proposal and asked for another approach | Saw the installed placeholder; no execution occurred |
| Student 2 | Another edit plus revised code pasted in chat | Repeated the same placeholder; revision advanced but source did not change |
| Tutor 2 | Praised the chat proposal as correct | Did not address its mismatch with installed work; no execution occurred |
| Student 3 | Explicit no-reply | Placeholder still installed, no observed output or grade |

This is a **failed notebook-action outcome despite a coherent-looking chat**.
Both raw student responses contain the misplaced fields, and saved work exactly
matches them. It is not a parser, edit-application or display corruption. The
schema validates field types but does not establish that the model understood
which field contains replacement code. One trial does not establish the cause
or prevalence of that confusion.

Both new tutors received the installed source as well as the chat proposal.
Their feedback addresses the proposal without resolving the discrepancy. The
course reference supports the described operation; this is not an established
API hallucination or fabricated execution claim. Neither role claimed a run or
test had actually passed. The meaningful failure is the divergence of conversation
and notebook state, followed by termination with that divergence unresolved.

The live run exercises tutor handoffs, state persistence and model-selected
termination, but **does not exercise student-requested execution or error
recovery**. Those paths still have authored regression coverage, not a new live
result from this trial. No real-student action accuracy or learning outcome is
established.

Exact offline replay and independent audit verify all raw calls, action/state
bindings, source pins, approval-before-dispatch chronology and limits. Six frames
retain revisions 0, 1, 1, 2, 2, 2 and no execution observations. The private
`completion.json` records the aggregate result and supporting receipt hashes.
The run remains unchanged; no further batch or replacement draw is queued.

The next development target is an explicit separation of replacement code and
chat text, plus tutor feedback that distinguishes a pasted proposal from installed
work. A separately versioned change should be checked against this failure before
another live trial. Do not silently move chat code into the notebook, force a run,
or ban ordinary student coding mistakes to make the outcome appear successful.

## Inspecting the saved result

The completed authorized run is available in the existing desktop workbench:

```sh
PYTHONPATH=. python -P apps/archive_message_preview.py \
  data/archived-student-loop-v1 --branch data/notebook-source-branch-v1/branch \
  --continuation data/archived-tutor-continuation-v1 \
  --include-policy-samples --history-benchmark data/course-account-history-v1 \
  --sequence data/full-behavior-sequence-v1 --port 8455
```

**Full sequence** opens as the latest encounter, with code and chat beside one
timeline. Its initial hint is marked as a reused reply. Earlier continuations and
policy samples remain separate choices. The view verifies the saved run on each
data request, displays each pending message only once, clears stale current
output after edits and makes no generation/execution requests. Unfinished runs
cannot appear as completed results. Browser inspection at
<http://127.0.0.1:8455/> confirmed the default final stage, all six timeline events,
the first pending student message appearing once, the installed placeholder beside
the proposed chat code, and no inferred execution output or grade. The final stage
is left open for inspection. Opening and navigating the replay did not add calls.
