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

Automatic approval review rejected the live dispatch **before process creation**:
the user authorized trying the sequence, but review requires explicit approval
of this private notebook/code/chat/reference payload to Google Gemini. The block
is recorded in `dispatch-block.json`. There is no `run.json`, zero provider calls
and zero executions for this trial. The next step is exact-payload authorization,
then a single dispatch of this unchanged plan. No retry or alternative send path
has been attempted.

Verification: **1,001 Python tests passed, three optional tests skipped**, with
the existing Starlette/httpx deprecation warning. This includes the authored
error → message → tutor → quiet repair → execution → no-reply sequence, global
caps, interrupted/failing calls, exact replay and altered-receipt rejection.
The archive, policy-sampling and browser-workspace Node checks also pass.
Independent backend review found no dispatch blocker; it clarified the budget
wording above. These authored checks are not live model or real-student results.

## Inspecting the saved result

After the authorized run completes, the existing desktop workbench can attach it:

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
cannot appear as completed results. Browser inspection of a live result is still
pending because dispatch has not occurred.
