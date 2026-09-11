"""Tutor-component regressions use invented dialogue only."""
from copy import deepcopy
import json

import pytest

from src.labeling import episodes
from src.labeling.episode_codebook import RUBRIC_V7


def example():
    return {
        'id': 'invented-episode', 'conversation_key': 'invented-conversation',
        'split': 'development', 'annotation': None, 'legacy_labels': {'HIDDEN_LEGACY': True},
        'question_ref': 'HIDDEN_METADATA', 'question_link': 'unverified', 'limitations': [],
        'context': [{'id': 'turn-0', 'role': 'tutor', 'text': 'Show me your attempt.'}],
        'turns': [
            {'id': 'turn-1', 'role': 'student', 'phase': 'request', 'text': 'Why is the total wrong?'},
            {'id': 'turn-2', 'role': 'tutor', 'phase': 'response',
             'text': 'The loop stops early.\n\nWhich bound would include the last item?\nThat earlier addition is correct.\nIt combines both counts.'},
            {'id': 'turn-3', 'role': 'student', 'phase': 'followup', 'text': 'HIDDEN_FUTURE'},
        ],
    }


def draft():
    def move(labels, *lines):
        return {'labels': labels, 'evidence': [{'turn_id': 'turn-2', 'line': n} for n in lines],
                'rationale': 'Invented component.'}
    return {
        'tutor_moves': [move(['explanation'], 1), move(['hint', 'asks-question'], 3),
                        move(['checks-work', 'explanation'], 4, 5)],
        'tutor_task_relation': {'value': 'addresses-request', 'rationale': 'Addresses the reported total.',
                               'evidence': [{'turn_id': 'turn-1', 'line': 1}, {'turn_id': 'turn-2', 'line': 1}]},
    }


def source_bundle(ep):
    reserved = deepcopy(ep)
    reserved.update(id='reserved', conversation_key='reserved-conversation', split='holdout')
    bundle = {'rubric': RUBRIC_V7, 'episodes': [ep, reserved], 'manifest': {
        'rubric_version': 'v7', 'rubric_hash': episodes.rubric_hash(RUBRIC_V7, 'v7'),
        'episode_content_hash': episodes.episode_content_hash([ep, reserved]),
        'bundle_id': 'invented-source-bundle', 'snapshot_id': 'invented-snapshot',
        'model': 'gemini-2.5-flash', 'source_files': {},
    }}
    return bundle


def test_moves_keep_overlapping_labels_order_and_exact_lines_without_future_input():
    from src.labeling import tutor_moves as tm
    ep = example()
    changed = deepcopy(ep)
    changed['turns'][-1]['text'] = 'ANOTHER_FUTURE'
    changed['legacy_labels'] = {'OTHER_LEGACY': False}
    changed['question_ref'] = 'ANOTHER_METADATA'
    assert tm.make_prompt(ep) == tm.make_prompt(changed)
    assert all(s not in tm.make_prompt(ep) for s in ('HIDDEN_FUTURE', 'HIDDEN_LEGACY', 'HIDDEN_METADATA'))
    selected = tm.ResponseSelection.model_validate(draft())
    result = tm.materialize(selected, ep)
    tm.validate_response(result, ep)
    assert result['tutor_moves'][1]['labels'] == ['hint', 'asks-question']
    assert result['tutor_moves'][1]['evidence'] == [
        {'turn_id': 'turn-2', 'line': 3, 'quote': 'Which bound would include the last item?'}]
    assert result['tutor_moves'][2]['labels'] == ['checks-work', 'explanation']
    assert result['tutor_task_relation']['value'] == 'addresses-request'
    assert 'additionalProperties' not in json.dumps(tm.ResponseSelection.model_json_schema())
    with pytest.raises(ValueError):
        tm.ResponseSelection.model_validate({**draft(), 'followup': {}})


@pytest.mark.parametrize('problem', ['mixed', 'duplicate-label', 'unknown-with-known', 'blank',
                                     'future', 'wrong-order', 'missing-request', 'altered-quote'])
def test_components_reject_invalid_labels_evidence_and_order(problem):
    from src.labeling import tutor_moves as tm
    ep = example()
    selected = draft()
    if problem == 'mixed': selected['tutor_moves'][0]['labels'] = ['mixed']
    if problem == 'duplicate-label': selected['tutor_moves'][0]['labels'] = ['explanation', 'explanation']
    if problem == 'unknown-with-known': selected['tutor_moves'][0]['labels'] = ['unclear', 'explanation']
    if problem == 'blank': selected['tutor_moves'][0]['evidence'][0]['line'] = 2
    if problem == 'future': selected['tutor_moves'][0]['evidence'][0]['turn_id'] = 'turn-3'
    if problem == 'wrong-order': selected['tutor_moves'].reverse()
    if problem == 'missing-request': selected['tutor_task_relation']['evidence'].pop(0)
    with pytest.raises((ValueError, KeyError)):
        result = tm.materialize(tm.ResponseSelection.model_validate(selected), ep)
        if problem == 'altered-quote': result['tutor_moves'][0]['evidence'][0]['quote'] = 'Rewritten quote.'
        tm.validate_response(result, ep)


def test_component_run_preserves_source_and_resumes_only_failed_development(tmp_path):
    from src.labeling import tutor_moves as tm
    source = tmp_path / 'source.json'
    episodes.write_bundle(source, source_bundle(example()))
    original = source.read_bytes()
    target = tmp_path / 'moves.json'
    calls = []

    def generate(prompt, response_model):
        calls.append(prompt)
        result = draft()
        if len(calls) == 1:
            result['tutor_moves'][0]['evidence'][0]['line'] = 2
        return response_model.model_validate(result)

    failed = tm.annotate_bundle(source, target, generate, model='invented-model')
    assert failed['annotations'] == {} and failed['errors']['invented-episode']
    saved = tm.annotate_bundle(source, target, generate, model='invented-model')
    assert set(saved['annotations']) == {'invented-episode'} and saved['errors'] == {}
    assert tm.annotate_bundle(source, target, generate, model='invented-model') == saved
    assert len(calls) == 2 and calls[0] == calls[1]
    assert source.read_bytes() == original
    assert episodes.load_bundle(source)['episodes'][1]['annotation'] is None
    with pytest.raises(ValueError):
        tm.annotate_bundle(source, target, generate, model='different-model')
    corrupted = deepcopy(saved)
    corrupted['annotations']['invented-episode']['tutor_moves'][0]['evidence'][0].update(
        turn_id='turn-3', quote='HIDDEN_FUTURE')
    target.write_text(json.dumps(corrupted))
    with pytest.raises(ValueError):
        tm.annotate_bundle(source, target, generate, model='invented-model')
    assert len(calls) == 2


def test_blank_response_abstains_without_manufacturing_evidence():
    from src.labeling import tutor_moves as tm
    ep = example()
    ep['turns'][1]['text'] = '\n \n'
    selected = tm.ResponseSelection.model_validate({
        'tutor_moves': [{'labels': ['unclear'], 'evidence': [], 'rationale': 'No visible tutor text.'}],
        'tutor_task_relation': {'value': 'unclear', 'evidence': [], 'rationale': 'No visible reply.'},
    })
    result = tm.materialize(selected, ep)
    assert result['tutor_moves'][0]['evidence'] == []
    ep['turns'][1]['text'] = 'A visible reply.'
    with pytest.raises(ValueError):
        tm.validate_response(result, ep)


@pytest.mark.parametrize('alias', [False, True])
def test_tutor_results_cannot_overwrite_the_source(tmp_path, alias):
    from src.labeling import tutor_moves as tm
    source = tmp_path / 'source.json'
    episodes.write_bundle(source, source_bundle(example()))
    before = source.read_bytes()
    target = source
    if alias:
        target = tmp_path / 'alias.json'
        target.symlink_to(source)
    with pytest.raises(ValueError):
        tm.annotate_bundle(source, target, lambda *args: pytest.fail('Must not generate'), model='test')
    assert source.read_bytes() == before


def test_prompt_revision_is_explicit_isolated_and_cannot_resume_v1(tmp_path):
    from src.labeling import tutor_moves as tm
    ep = example()
    changed = deepcopy(ep)
    changed['turns'][-1]['text'] = 'A DIFFERENT FUTURE'
    assert tm.protocol_hash() == 'ec435087b4bc0d03282b5215c4aace725902616c720b657fc60c9312f48acb68'
    assert tm.protocol_hash('v1') != tm.protocol_hash('v2')
    assert tm.make_prompt(ep) == tm.make_prompt(ep, 'v1')
    assert tm.make_prompt(ep, 'v2') == tm.make_prompt(changed, 'v2')
    with pytest.raises(ValueError):
        tm.make_prompt(ep, 'missing')
    source, target = tmp_path / 'source.json', tmp_path / 'moves.json'
    episodes.write_bundle(source, source_bundle(ep))
    calls = []

    def generate(prompt, response_model):
        calls.append(prompt)
        return response_model.model_validate(draft())

    tm.annotate_bundle(source, target, generate, model='test')
    before = target.read_bytes()
    with pytest.raises(ValueError):
        tm.annotate_bundle(source, target, generate, model='test', version='v2')
    assert target.read_bytes() == before and len(calls) == 1
    revised = tm.annotate_bundle(source, tmp_path / 'v2.json', generate, model='test', version='v2')
    assert revised['manifest']['protocol_hash'] == tm.protocol_hash('v2')
    assert calls[-1] == tm.make_prompt(ep, 'v2')


@pytest.mark.parametrize('version', ['v3', 'v4', 'v5'])
def test_guidance_version_rejects_cross_version_labels_and_results(tmp_path, version):
    from src.labeling import tutor_moves as tm
    ep = example()
    ep['turns'][1]['text'] = 'Use the built-in sum function.\ntotal = sum(values)\nIt adds every value.'
    selected = draft()
    selected['tutor_moves'] = [{
        'labels': ['guidance', 'worked-solution', 'explanation'],
        'evidence': [{'turn_id': 'turn-2', 'line': n} for n in (1, 2, 3)],
        'rationale': 'An invented plan, supplied implementation, and explanation.',
    }]
    selection = tm.ResponseSelection.model_validate(selected)
    annotation = tm.materialize(selection, ep, version=version)
    tm.validate_response(annotation, ep, version=version)
    assert annotation['tutor_moves'][0]['labels'] == ['guidance', 'worked-solution', 'explanation']
    for older_version in ('v1', 'v2'):
        with pytest.raises(ValueError):
            tm.validate_response(annotation, ep, version=older_version)
    stale = deepcopy(annotation)
    stale['tutor_moves'][0]['labels'] = ['hint']
    with pytest.raises(ValueError):
        tm.validate_response(stale, ep, version=version)
    with pytest.raises(ValueError):
        tm.validate_response(annotation, ep, version='missing')
    assert tm.protocol_hash('v2') == '71f6d741b14c9670ba7994007e73bfa97fc23ec9ab292dbe0f22295ddc0430f3'
    assert tm.protocol_hash('v3') == 'e2a690b990c7505c292675f9f548d70b5800f545187b25439a7b028aec63b962'
    assert tm.protocol_hash('v4') == 'c17157b0443896629e391346b51db5bbabb2595d533d01583d576cefa637800f'
    prompt = tm.make_prompt(ep, version)
    if version != 'v3':
        assert tm.protocol_hash(version) != tm.protocol_hash('v3')
        assert tm._definition(version)[1] == tm._definition('v3')[1]
    rubric = json.loads(prompt.split('\nRubric:\n', 1)[1].split('\nEPISODE JSON:\n', 1)[0])
    assert 'guidance' in rubric['tutor_moves'] and 'hint' not in rubric['tutor_moves']
    changed = deepcopy(ep)
    changed['turns'][-1]['text'] = 'CHANGED_FUTURE'
    changed['legacy_labels'] = {'CHANGED_REVIEW': True}
    assert tm.make_prompt(changed, version) == prompt
    assert all(s not in prompt for s in ('HIDDEN_FUTURE', 'HIDDEN_LEGACY', 'HIDDEN_METADATA'))
    source, target = tmp_path / 'source.json', tmp_path / f'{version}.json'
    episodes.write_bundle(source, source_bundle(ep))
    original = source.read_bytes()
    calls = []

    def generate(actual_prompt, response_model):
        calls.append(actual_prompt)
        return response_model.model_validate(selected)

    saved = tm.annotate_bundle(source, target, generate, model='test', version=version)
    assert calls == [prompt]
    assert saved['annotations'] == {'invented-episode': annotation} and not saved['errors']
    no_generate = lambda *_: pytest.fail('Must not regenerate cached or mismatched results')
    assert tm.annotate_bundle(source, target, no_generate, model='test', version=version) == saved
    before = target.read_bytes()
    with pytest.raises(ValueError):
        tm.annotate_bundle(source, target, no_generate, model='test', version='v2')
    for other_version in ('v3', 'v4', 'v5'):
        if other_version != version:
            with pytest.raises(ValueError):
                tm.annotate_bundle(source, target, no_generate, model='test', version=other_version)
    assert target.read_bytes() == before and source.read_bytes() == original
    saved['annotations']['invented-episode'] = stale
    target.write_text(json.dumps(saved))
    with pytest.raises(ValueError):
        tm.annotate_bundle(source, target, no_generate, model='test', version=version)
