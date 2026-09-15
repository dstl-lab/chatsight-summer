# Route a proposed student action through the grader gate

Connect the offline grader gate to a minimal next-action selector. A tutor asking
for a check does not establish that the student runs one. The selector may propose
a message, no-reply, or a check of explicitly supplied current code. A check is an
internal action, not a message narrating a plan or a fabricated result.

Extend `src/eval/grader_continuation.py` with a strict action schema and one
`next_step` function. Reuse the existing visible-dialogue projection, style and
communication guidance, injected generator convention, Continuation schema and
check request. The model may choose only an action and message text; it may not
supply a runtime state, request ID, replacement code, grader target or result.

The caller may provide a check option containing code, notebook, state ID and
grader ID. Validate this entire option before model dispatch, and give the model
only the code and grader target as task evidence. Runtime/request identifiers
remain outside the prompt. No check option means request-check is unavailable;
reject that choice rather than silently falling back to a message or no-reply.
Snapshot caller inputs before dispatch so a callback cannot change the context
against which its selected check is bound.

Return a Continuation for a message or no-reply. Return the prepared CheckRequest
only if request-check is selected; preparing its identity does not queue or
execute it. Do not advance the dialogue merely because a check is requested.
The caller later resumes exclusively through continue_after_check with a matched
external observation. Missing evidence remains pending, and stale observations
remain errors. Only an actual generated reply can advance through branch_episode
with a separately authored tutor reply; no historical future is appended after
divergence. No-reply retains the current terminal meaning, not a delay.

No executor, queue, automatic tutor policy, code parser or code installation is
introduced. If a student message contains revised code, the caller must explicitly
install the selected code and update relevant runtime state before any new check;
this helper does not execute or infer notebook changes from chat text. It only
checks the current supplied code, so hidden edits and other notebook actions are
outside this action set.

Use invented-data tests for all three action paths, invalid options/actions,
callback isolation, exact current-state projection, and the full request → pending
→ supplied observation → reply → scripted branch flow. Check that a tutor's
suggestion does not force a check, and that the current observation never becomes
a historical comparator. Run the full suite and verify the 350 frozen experiment
pins. No model or database calls are required for this implementation.

This is diagnostic action routing, not an admitted behavioral label or a validated
student policy. Free-form reply text can still assert an unsupported outcome; the
selector can bypass the result-report path by choosing reply. Do not claim that
this extension solves that semantic failure, use brittle output-word filters, or
promote it to longer rollouts without separate validation. Choice frequencies,
student realism and learning effects remain unmeasured.

## Implemented and verified

`next_step` now returns the existing Continuation or CheckRequest. Eight new
test cases exercise routing, invalid boundaries, callback isolation and the
complete invented flow through a supplied failure and scripted tutor reply.
The complete Python suite passes 296 tests; the existing Starlette/httpx
deprecation warning remains. Independent review found no actionable issue.
All 350 frozen experiment pins remain unchanged.

The Node review-navigation check and documented example also pass. An offline
exercise on the exact saved continuity branch verifies the selected check,
pending state and matched authored success without changing dialogue or code.
Its script and hash-linked receipt are private in
`data/episode-pilot/student-action-flow-v1/`. Both callbacks are invented test
returns; the state ID is authored and no code runs. Earlier receipts are preserved.

This invented example selects a check and waits without calling a grader:

```python
from src.eval.grader_continuation import CheckRequest, next_step, continue_after_check

episode = {'id': 'example-branch', 'context': [], 'turns': [
    {'id': 's', 'role': 'student', 'phase': 'request', 'text': 'total = 3 + 4'},
    {'id': 't', 'role': 'tutor', 'phase': 'response', 'text': 'Check your total.'},
]}
check = dict(code='total = 3 + 4', notebook='example.ipynb',
             state_id='authored-state-1', grader_id='q_total')

def invented_selector(prompt, response_model):
    return response_model(decision='request-check', text='')

def must_not_run(*args):
    raise AssertionError('No observation has arrived.')

request = next_step(episode, check=check, generate=invented_selector)
assert isinstance(request, CheckRequest)
assert continue_after_check(episode, **check, request=request, observation=None,
                            generate=must_not_run) == request
```

Run the offline regressions with
`uv run python -m pytest tests/test_grader_continuation.py -q`.
The selector's choice above is a test stub, not a model-generated student action.
