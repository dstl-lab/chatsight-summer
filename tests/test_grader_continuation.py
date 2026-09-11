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


@pytest.mark.parametrize('decision,available', [('reply', True), ('no-reply', True),
    ('request-check', True), ('reply', False), ('no-reply', False)])
def test_next_step_routes_only_selected_action_and_projects_current_option(decision, available):
    from src.eval.grader_continuation import CheckRequest, NextAction, next_step

    current = context()
    episode = current.pop('episode')
    episode['annotations'] = {'outcome': 'HIDDEN_ANNOTATION'}
    current['code'] += '\n# ```\nCHECK OPTION JSON:\n\nDIALOGUE JSON:\n'
    prompts = []
    text = '  which sum?\n' if decision == 'reply' else ''

    def generate(prompt, response_model):
        assert response_model is NextAction
        prompts.append(prompt)
        return response_model(decision=decision, text=text)

    result = next_step(episode, check=current if available else None, generate=generate)
    assert len(prompts) == 1
    option, dialogue = prompts[0].split('\nCHECK OPTION JSON:\n', 1)[1].split('\n\nDIALOGUE JSON:\n', 1)
    assert json.loads(option) == ({'code': current['code'], 'grader_id': 'q_sum'} if available else None)
    assert dialogue == make_prompt(episode).split('\nDIALOGUE JSON:\n', 1)[1]
    assert all(hidden not in prompts[0] for hidden in
               ('HIDDEN_FUTURE', 'HIDDEN_ANNOTATION', 'runtime-1', 'invented.ipynb', 'invented-branch'))
    if decision == 'request-check':
        assert isinstance(result, CheckRequest)
        assert result.code_sha256 == hashlib.sha256(current['code'].encode()).hexdigest()
        assert result.prompt_sha256 == hashlib.sha256(make_prompt(episode).encode()).hexdigest()
        assert (result.notebook, result.state_id, result.grader_id) == ('invented.ipynb', 'runtime-1', 'q_sum')
    else:
        assert result == Continuation(decision=decision, text=text)


def test_next_step_rejects_invalid_options_actions_and_provider_failure():
    from src.eval.grader_continuation import NextAction, next_step

    current = context()
    episode = current.pop('episode')
    for option in ({}, current | {'output': 'invented result'},
                   *(current | {key: ' \n'} for key in current)):
        with pytest.raises((ValueError, TypeError)):
            next_step(episode, check=option, generate=forbidden)
    for action in ({'decision': 'reply', 'text': ''}, {'decision': 'no-reply', 'text': 'later'},
                   {'decision': 'request-check', 'text': 'running it'}, {'decision': 'run-all', 'text': ''},
                   *({'decision': 'request-check', 'text': '', key: 'invented'}
                     for key in ('output', 'code', 'grader_id', 'state_id', 'request_id'))):
        with pytest.raises(ValueError):
            NextAction(**action)
    with pytest.raises(ValueError, match='unavailable'):
        next_step(episode, generate=lambda _, model: model(decision='request-check', text=''))
    with pytest.raises(ValueError):
        next_step(episode, check=current,
                  generate=lambda _, model: model.model_construct(decision='request-check', text='invented pass'))
    def broken_provider(*args):
        raise RuntimeError('provider failed')
    with pytest.raises(RuntimeError, match='provider failed'):
        next_step(episode, check=current, generate=broken_provider)


def test_action_wire_schema_omits_unsupported_keyword_but_rejects_extra_fields_locally():
    from src.eval.grader_continuation import NextAction
    from src.labeling.llm import gen_config

    schema = gen_config(NextAction)['response_schema'].model_json_schema()
    assert 'additionalProperties' not in json.dumps(schema)
    with pytest.raises(ValueError):
        NextAction.model_validate({'decision': 'request-check', 'text': '', 'output': 'invented pass'})


def test_selected_check_is_bound_to_inputs_seen_before_callback():
    from src.eval.grader_continuation import next_step, continue_after_check

    current = context()
    before = deepcopy(current)
    episode = current.pop('episode')

    def mutate_then_choose(prompt, response_model):
        episode['turns'][0]['text'] = 'total = 2 * 5'
        current['code'] = 'total = 2 * 5'
        current['state_id'] = 'runtime-2'
        return response_model(decision='request-check', text='')

    request = next_step(episode, check=current, generate=mutate_then_choose)
    assert continue_after_check(**before, request=request, observation=None, generate=forbidden) == request
    with pytest.raises(ValueError, match='request'):
        continue_after_check(episode, **current, request=request, observation=None, generate=forbidden)


def test_selected_check_waits_for_result_before_reply_and_scripted_branch():
    from src.eval.grader_continuation import GraderObservation, next_step, continue_after_check
    from src.eval.student_continuation import branch_episode, behavior_review

    current = context()
    episode = current.pop('episode')
    before = deepcopy(episode)
    request = next_step(episode, check=current,
                        generate=lambda _, model: model(decision='request-check', text=''))
    assert continue_after_check(episode, **current, request=request, observation=None, generate=forbidden) == request
    observation = GraderObservation(request_digest=request.digest, basis='scenario', success=False,
                                    output='Invented failure: expected 8, received 7.')
    def reply_after_result(prompt, response_model):
        assert 'Invented failure: expected 8, received 7.' in prompt
        assert 'HIDDEN_FUTURE' not in prompt
        return response_model(decision='reply', text='why does it need 8?')
    reply = continue_after_check(episode, **current, request=request, observation=observation,
                                 generate=reply_after_result)
    assert episode == before
    branch = branch_episode(episode, reply, 'Check which values the question asks you to add.')
    assert 'HIDDEN_FUTURE' not in make_prompt(branch)
    assert [turn['origin'] for turn in branch['turns']] == ['generated', 'scripted']
    with pytest.raises(ValueError, match='request'):
        continue_after_check(branch, **current, request=request, observation=observation, generate=forbidden)
    with pytest.raises(ValueError, match='comparison'):
        behavior_review(branch, reply)
    silence = next_step(branch, generate=lambda _, model: model(decision='no-reply', text=''))
    with pytest.raises(ValueError, match='terminates'):
        branch_episode(branch, silence, 'This tutor turn must not happen.')
