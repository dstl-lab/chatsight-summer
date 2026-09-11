# Require a matching observation before continuing after a grader check

The environment-conditioned diagnostic produced unsupported current-result
claims when no new grader observation was supplied. Implement a small dispatch
gate for the path where a check has already been requested. Preserve the frozen
continuation module, experiments and negative result.

A check request binds an opaque fresh request ID to the visible branch/prefix,
submitted code hash, notebook, grader question and caller-supplied environment
state ID. The state ID must change when relevant runtime state, data, other
cells or grader configuration changes; a code string cannot identify a live
notebook state. A new check always gets a new request ID, even with identical
code. Keep this as explicit caller-owned provenance, not inferred state from
chat text or a promise that runtime snapshots already exist.

An observation carries the exact request digest, success flag, verbatim output
and basis: executed or authored scenario. Historical notebook/time joins cannot
be converted into synthetic post-revision observations; they lack this binding.
The caller supplying an executed observation is responsible for its provenance.
Neither a hash nor the executed tag proves that a grader actually ran.

Before any generator callback, validate the current context against the request
and the observation against its digest. Missing observation returns the check
request as pending. A mismatched request/result raises an error before dispatch.
Pending is an environment requirement, never a student no-reply, failure or delay
prediction. A matching failed test is valid evidence and can reach generation.
The student may reply or send no further message after a matching observation.

Use the existing visible-prefix projection, strict Continuation schema and
injected generator convention. Keep the observation separate from dialogue;
include its origin so authored scenarios cannot masquerade as executed results.
Retain historical context, but supply only the matched current observation and
explicit submitted code in the new observation block. Ordinary student questions remain on the existing path;
this helper does not infer that a tutor suggestion means the student ran a check.

Implement in `src/eval/grader_continuation.py` with invented-data regressions in
`tests/test_grader_continuation.py`. The regressions must show zero callback calls
for missing/stale/wrong-scope evidence, distinct repeated requests, matching pass
and failure handling, preserved reply/no-reply semantics, unchanged future
isolation and strict input/output validation. Run the existing suite and frozen
experiment verification. No new dependency, database/model call, notebook
executor, action-selection policy or label taxonomy is needed for this step.

This gate establishes a necessary dispatch condition, not semantic truthfulness
of every generated sentence. The model can still misstate a supplied result or
invent another outcome after dispatch; that needs separate validation. It also
does not implement the complete student action/execution loop or calibrate reply
probability. Longer rollouts remain unvalidated.

## Implemented and verified

The gate is available as `request_check` and `continue_after_check`. It is an
opt-in offline helper; there is no production rollout caller or executor yet.
The frozen experiment runners remain unchanged for reproduction. No model or
database calls were made for this implementation.

The subsequent [student action flow](2026-09-11-student-action-flow.md) adds an
opt-in selector before this gate. The verification below describes commit
`3b7bc9b`; its private receipt remains historical and has not been overwritten.

Six new regressions cover the dispatch boundary. The complete suite passes
288 tests, and the Node review-navigation check passes. The one pre-existing
Starlette/httpx deprecation warning remains. Independent code review found no
blocking issue. All 350 frozen experiment pins still verify.

An offline exercise on the saved continuity branch preserves its exact dialogue,
returns a pending request without calling the callback when the result is unknown,
and rejects an old observation after a state change. A matched authored success
reaches an invented callback. Its no-reply return is a test stub, not a new model
sample or behavioral finding. The script and hash-linked receipt are private in
`data/episode-pilot/grader-gate-v1/`.

This invented example runs without network or notebook execution:

```sh
uv run python - <<'PY'
from src.eval.grader_continuation import (
    CheckRequest, GraderObservation, request_check, continue_after_check,
)

episode = {'id': 'example-branch', 'context': [], 'turns': [
    {'id': 's', 'role': 'student', 'phase': 'request', 'text': 'total = 3 + 4'},
    {'id': 't', 'role': 'tutor', 'phase': 'response', 'text': 'Check your total.'},
]}
current = dict(episode=episode, code='total = 3 + 4', notebook='example.ipynb',
               state_id='authored-state-1', grader_id='q_total')
request = request_check(**current)

def invented_generator(prompt, response_model):
    return response_model(decision='no-reply', text='')

pending = continue_after_check(**current, request=request, observation=None,
                               generate=invented_generator)
assert isinstance(pending, CheckRequest)
observation = GraderObservation(request_digest=request.digest, basis='scenario',
                                success=True, output='Invented successful check')
result = continue_after_check(**current, request=request, observation=observation,
                              generate=invented_generator)
assert result.decision == 'no-reply'  # Invented callback result, not a behavioral finding.
print('Missing result stays pending; matching scenario reaches the callback.')
PY
```
