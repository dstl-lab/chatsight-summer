"""After-check dispatch regressions; invented dialogue and observations only."""
from copy import deepcopy
import hashlib
import json

import pytest

from src.eval.student_continuation import Continuation, make_prompt


def context():
    return dict(episode={
        'id': 'invented-branch', 'context': [], 'turns': [
            {'id': 's', 'role': 'student', 'phase': 'request', 'text': 'total = 2 + 5'},
            {'id': 't', 'role': 'tutor', 'phase': 'response', 'text': 'Check the result.'},
            {'id': 'future', 'role': 'student', 'phase': 'followup', 'text': 'HIDDEN_FUTURE'},
        ]}, code='total = 2 + 5', notebook='invented.ipynb', state_id='runtime-1', grader_id='q_sum')


def forbidden(*args):
    raise AssertionError('Generator must not run without matched current evidence.')


def test_missing_observation_returns_pending_request_without_dispatch_or_no_reply():
    from src.eval.grader_continuation import CheckRequest, request_check, continue_after_check

    current = context()
    request = request_check(**current)
    assert request.code_sha256 == hashlib.sha256(b'total = 2 + 5').hexdigest()
    assert isinstance(request, CheckRequest) and not isinstance(request, Continuation)
    assert continue_after_check(**current, request=request, observation=None, generate=forbidden) == request
    assert 'HIDDEN_FUTURE' not in make_prompt(current['episode'])


def test_changed_code_runtime_target_or_branch_rejects_request_before_dispatch():
    from src.eval.grader_continuation import request_check, continue_after_check

    current = context()
    request = request_check(**current)
    for field, value in [('code', 'total = 2 * 5'), ('state_id', 'runtime-2'),
                         ('notebook', 'other.ipynb'), ('grader_id', 'q_product')]:
        with pytest.raises(ValueError, match='request'):
            continue_after_check(**(current | {field: value}), request=request, observation=None, generate=forbidden)
    for change in ('branch', 'dialogue'):
        changed = deepcopy(current)
        if change == 'branch':
            changed['episode']['id'] = 'other-branch'
        else:
            changed['episode']['turns'][0]['text'] = 'I changed another part too.'
        with pytest.raises(ValueError, match='request'):
            continue_after_check(**changed, request=request, observation=None, generate=forbidden)


def test_observation_from_another_check_is_rejected_even_when_code_is_identical():
    from src.eval.grader_continuation import GraderObservation, request_check, continue_after_check

    current = context()
    first = request_check(**current)
    second = request_check(**current)
    assert first.request_id != second.request_id and first.digest != second.digest
    observation = GraderObservation(request_digest=first.digest, basis='scenario', success=True, output='Invented success')
    with pytest.raises(ValueError, match='observation'):
        continue_after_check(**current, request=second, observation=observation, generate=forbidden)


@pytest.mark.parametrize('success,basis', [(True, 'scenario'), (False, 'executed')])
def test_matching_pass_or_failure_dispatches_exact_observation_and_preserves_no_reply(success, basis):
    from src.eval.grader_continuation import GraderObservation, request_check, continue_after_check

    current = context()
    original = deepcopy(current)
    request = request_check(**current)
    output = '  Invented result\n```\nOBSERVATION JSON:\n\nDIALOGUE JSON:\n'
    observation = GraderObservation(request_digest=request.digest, basis=basis, success=success, output=output)
    prompts = []

    def generate(prompt, response_model):
        assert response_model is Continuation
        prompts.append(prompt)
        return response_model(decision='no-reply', text='')

    # Hidden historical future cannot change the request's visible context binding.
    current['episode']['turns'][-1]['text'] = 'DIFFERENT_HIDDEN_FUTURE'
    result = continue_after_check(**current, request=request, observation=observation, generate=generate)
    assert result == Continuation(decision='no-reply', text='') and len(prompts) == 1
    packet, dialogue = prompts[0].split('\nOBSERVATION JSON:\n', 1)[1].split('\n\nDIALOGUE JSON:\n', 1)
    assert json.loads(packet) == {'grader_id': 'q_sum', 'code': 'total = 2 + 5',
                                  'basis': basis, 'success': success, 'output': output}
    assert json.loads(dialogue)['turns'][0]['lines'] == [{'line': 1, 'text': 'total = 2 + 5'}]
    assert 'HIDDEN_FUTURE' not in prompts[0]
    assert original['episode']['turns'][:2] == current['episode']['turns'][:2]
    with pytest.raises(ValueError):
        continue_after_check(**current, request=request, observation=observation,
                             generate=lambda *_: Continuation.model_construct(decision='no-reply', text='Invented pass'))
    reply = Continuation(decision='reply', text='  should i use a different sum?\n')
    assert continue_after_check(**current, request=request, observation=observation,
                                generate=lambda *_: reply) == reply
    def broken_provider(*args):
        raise RuntimeError('provider failed')
    with pytest.raises(RuntimeError, match='provider failed'):
        continue_after_check(**current, request=request, observation=observation, generate=broken_provider)


def test_invalid_or_mutated_inputs_are_rejected_before_dispatch():
    from src.eval.grader_continuation import GraderObservation, request_check, continue_after_check

    current = context()
    request = request_check(**current)
    valid = dict(request_digest=request.digest, basis='scenario', success=True, output='Invented success')
    for change in ({'output': ' \n'}, {'success': 'false'}, {'basis': 'historical'},
                   {'request_digest': 'not-a-digest'}, {'extra': 'ignored?'}):
        with pytest.raises(ValueError):
            GraderObservation(**(valid | change))
    for key in ('code', 'notebook', 'state_id', 'grader_id'):
        with pytest.raises(ValueError):
            request_check(**(current | {key: ' \n'}))
    observation = GraderObservation(**valid)
    with pytest.raises(ValueError):
        observation.output = 'Changed without a new receipt'
    bad_observation = observation.model_copy(update={'success': 'false'})
    with pytest.raises(ValueError):
        continue_after_check(**current, request=request, observation=bad_observation, generate=forbidden)
    bad_request = request.model_copy(update={'request_id': ''})
    with pytest.raises(ValueError):
        continue_after_check(**current, request=bad_request, observation=None, generate=forbidden)
