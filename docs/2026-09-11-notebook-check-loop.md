# Connect quiet edits to requested, computed feedback

Minchan accepted the displayed notebook-action-v1 quiet edit as plausible. Preserve
that judgment separately from correctness, execution and reply probability. The
next bounded step is an action loop over the accepted generated revision: choose
an edit, a check, chat or no further action; feedback follows only a requested
check of the current revision. Stop when a tutor response would be needed.

Reuse the existing notebook action validator and application function. Keep them
and all completed experiments unchanged. A small task-specific checker evaluates
only two supported count expressions on supplied authored string data: distinct
values versus all rows. It computes a value from the expression's recognized
meaning, without eval/exec of candidate code. Reject arbitrary or unsupported
source as unavailable, not incorrect. The authored expected count is explicit;
include duplicate values so counting rows can fail. This is a limited computed
fixture, not the deployed course, Otter, a Python kernel or a general grader.

Bind the request/result to the branch, revision, source, fixture and checker.
Editing invalidates current feedback; earlier checks remain history. Chat cannot
modify work or establish an outcome. New schema fields do not let the model
supply its own result. Do not route computed feedback through the older grader
observation type, whose bases are executed/scenario; that completed gate remains
unchanged. One invented regression must demonstrate failed check -> edit -> stale
feedback rejected/cleared -> passed check -> optional chat, plus unsupported source
receiving no grade.

Run the accepted generated code through the fixture offline as an explicitly
scripted engineering check. This does not mean the model chose to check. Then
prepare one bounded live trajectory with at most four model decisions from the
same accepted revision. The model may decline the check. Retain all actions and
failures, with pending receipts and exact replay; no semantic rerolls. Initial
private context and any proposed send scope remain reviewable. Standing permission
persists, subject to any automatic review of this concrete new payload.

## Implementation and offline checks

`src/eval/notebook_check.py` reuses the frozen action validator/application path.
Only a requested check produces a current observation; work edits clear it, and
chat ends the encounter awaiting an external tutor response. A silent edit can
instead end with no reply. Source, branch, revision, fixture and checker changes
invalidate feedback. The model cannot supply a result through its action schema;
free-form chat remains unaudited and cannot establish an outcome.

The private seed selects the first of two identical, human-reviewed generated
revisions. It includes only the original initial task/exchange and that revision;
no later real history enters the loop. The fixture is four authored string rows
with three distinct values. Scripted checks produce three for the accepted
revision and four for a deliberately wrong row-count expression. The original
captured expression is unsupported and receives no grade; the checker does not
claim to reproduce its Python error. These controls test the mechanism, not a
student's choice to check or a deployed assignment outcome.

All 316 Python tests pass, with the existing Starlette/httpx warning. Regressions
cover requested failure -> edit -> requested success, stale feedback, unsupported
source never executing, edits with optional chat, and future-metadata isolation.
The last regression initially exposed a branch hash that included omitted task
metadata; projecting the input before hashing fixes that leak. Independent review
also checked changed branches/data and unsupported extra code. Completed recovery,
action and comparison artifacts still verify; both older authored live traces
reproduce with zero model dispatch. No frozen implementation was changed.

## Prepared trajectory and automatic approval checkpoint

`data/episode-pilot/notebook-check-v1/` preserves the seed and parent review,
authored fixture, scripted controls, exact initial request, schema, disclosure,
runner and 31 file pins. The existing adapter allows up to four transport attempts
per logical request; this trajectory permits at most four logical requests.
Subsequent prompts contain only the same private initial context plus this run's
generated actions/work and computed fixture feedback. The runner reserves a new
execution directory and writes each pending receipt before dispatch. Exact replay
never sends or resumes a request; incomplete traces remain incomplete. An
invented-input runner check passed with five mocked calls and zero real calls,
covering success, provider failure and changed/pending evidence rejection.

Automatic approval review rejected the prepared send before process launch. Its
stated reason was that the private assignment, student–tutor dialogue and generated
code need specific new-payload/destination approval; the standing grant and latest
plausibility answer did not satisfy that requirement. No execution directory or
new model request exists. The rejection, current preparation and hash-bound
approval question are preserved separately. Do not bypass or resubmit before the
specific response. This is an automatic-review requirement, not a withdrawal of
Minchan's standing permission. All unaffected implementation and offline work is
complete; live check selection and subsequent behavior remain unobserved.

## Specifically approved run and review

Minchan answered “Yes” to sending the disclosed private excerpt and generated
work to Gemini 2.5 Pro for one run of at most four decisions. The separate
`approval-response.json` binds that answer to the unchanged question, scope,
experiment and payload hashes. It predates both model requests; the original
rejection and preparation files remain intact.

The unchanged runner completed two logical requests without failure. The model
first requested a check of the previously reviewed revision. The authored
fixture computed its expected distinct count and returned passing feedback. The
model then selected no-reply. It made no further edit, sent no chat message and
claimed no outcome. The four-action cap did not force the stop. This connects the
accepted quiet edit to a model-selected check and subsequent silence, although
the edit came from the earlier probe rather than one uninterrupted model run.

Exact offline replay reproduces both actions and feedback with no dispatch. All
31 preparation pins verify. Independent review confirms approval timing, the
current observation's branch/revision/source/fixture/checker bindings and input
isolation: the second prompt adds only this run's generated request and computed
result to the initial context. Private review and completion artifacts preserve
the sequence with blank human judgment; the earlier approval of a quiet edit is
not silently extended to this new check-and-stop behavior. Production code is
unchanged in this checkpoint; the latest suite remains 316 passing tests.

This is one exposed development trajectory. A fixture pass is neither code
execution nor a course result. No-reply does not establish that the student moved
on, understood, or abandoned the task. This run contains no failed feedback and
does not establish failure recovery, a response probability, course transfer or
cohort fidelity. The review asks only whether the displayed sequence is plausible.
