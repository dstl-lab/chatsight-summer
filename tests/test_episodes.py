"""Pilot regressions use invented conversations, never student data."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.labeling import episodes


def snapshot(tmp_path):
    folder = tmp_path / 'snapshot'
    folder.mkdir()
    convs = []
    labels = []
    for n in range(4):
        turns = [
            {'index': 0, 'role': 'student', 'text': 'Help with question 2.', 'student_index': 0},
            {'index': 1, 'role': 'tutor', 'text': 'What should the loop stop at?'},
            {'index': 2, 'role': 'student', 'text': 'It should stop before five.', 'student_index': 1},
            {'index': 3, 'role': 'tutor', 'text': 'Try that condition.'},
        ]
        convs.append({'conv_id': f'c{n}', 'chatlog_id': n, 'notebook': 'lab', 'started_at': None, 'turns': turns})
        labels.extend({'chatlog_id': n, 'message_index': i, 'labels': {'old-label': True}} for i in (0, 2))
    (folder / 'conversations.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in convs))
    (folder / 'labels.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in labels))
    (folder / 'schema.json').write_text('{"labels": []}')
    (folder / 'manifest.json').write_text(json.dumps({'snapshot_id': 'test-snapshot', 'classifier_hash': 'old', 'schema_version': 'old-schema', 'row_counts': {'conversations': 4, 'turns': 16, 'label_applications': 8}}))
    return folder


def test_preparation_is_disjoint_deterministic_and_preserves_unknowns(tmp_path):
    source = snapshot(tmp_path)
    bundle = episodes.build_bundle(source, development=2, holdout=2, seed=7)
    assert bundle == episodes.build_bundle(source, development=2, holdout=2, seed=7)
    assert len(bundle['episodes']) == 4
    assert len({e['conversation_key'] for e in bundle['episodes']}) == 4
    assert {e['split'] for e in bundle['episodes']} == {'development', 'holdout'}
    for ep in bundle['episodes']:
        assert ep['annotation'] is None
        assert ep['question_link'] != 'verified'
        assert ep['limitations']
        assert [t['phase'] for t in ep['turns']][:2] == ['request', 'response']
        assert not any('passed' in t for t in ep)
    # Content changes alter the immutable source identity.
    p = source / 'conversations.jsonl'
    p.write_text(p.read_text().replace('before five', 'before six'))
    assert episodes.build_bundle(source, development=2, holdout=2, seed=7)['manifest']['bundle_id'] != bundle['manifest']['bundle_id']


def test_snapshot_rejects_wrong_counts_and_orphan_labels(tmp_path):
    source = snapshot(tmp_path)
    rows = (source / 'labels.jsonl').read_text().splitlines()
    row = json.loads(rows[0]); row['message_index'] = 99; rows[0] = json.dumps(row)
    (source / 'labels.jsonl').write_text('\n'.join(rows))
    with pytest.raises(ValueError, match='label'):
        episodes.build_bundle(source, development=2, holdout=2)
    source.joinpath('conversations.jsonl').write_text('')
    with pytest.raises(ValueError):
        episodes.build_bundle(source, development=2, holdout=2)


def test_model_evidence_must_match_the_right_turn_phase(tmp_path):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=2, holdout=2)
    ep = next(e for e in bundle['episodes'] if any(t['phase'] == 'followup' for t in e['turns']))
    by_phase = {p: next(t for t in ep['turns'] if t['phase'] == p) for p in ('request', 'response', 'followup')}
    annotation = {
        'request': {'value': 'unclear', 'evidence': [], 'rationale': 'The type of help is unspecified.'},
        'tutor_response': {'value': 'asks-question', 'evidence': [{'turn_id': by_phase['response']['id'], 'quote': 'What should the loop stop at?'}], 'rationale': 'Asks the student to reason.'},
        'followup': {'value': 'substantive-contribution', 'evidence': [{'turn_id': by_phase['followup']['id'], 'quote': 'It should stop before five.'}], 'rationale': 'Proposes a condition; correctness is not judged.'},
    }
    episodes.validate_annotation(annotation, ep, bundle['rubric'])
    annotation['followup']['evidence'][0]['turn_id'] = by_phase['response']['id']
    with pytest.raises(ValueError, match='evidence'):
        episodes.validate_annotation(annotation, ep, bundle['rubric'])
    annotation['followup'] = {'value': 'no-followup-observed', 'evidence': [], 'rationale': 'Missing'}
    with pytest.raises(ValueError, match='follow'):
        episodes.validate_annotation(annotation, ep, bundle['rubric'])


def test_annotation_resumes_development_without_touching_holdout(tmp_path):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=2, holdout=2)
    path = tmp_path / 'bundle.json'
    episodes.write_bundle(path, bundle)
    prompts = []
    def generate(prompt, response_model):
        prompts.append(prompt)
        ep = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        has_followup = any(t['phase'] == 'followup' for t in ep['turns'])
        return response_model.model_validate({
            'request': {'value': 'unclear', 'evidence': [], 'rationale': 'Insufficient evidence.'},
            'tutor_response': {'value': 'unclear', 'evidence': [], 'rationale': 'Insufficient evidence.'},
            'followup': {'value': 'insufficient-evidence' if has_followup else 'no-followup-observed', 'evidence': [], 'rationale': 'Insufficient evidence.'},
        })
    episodes.annotate_bundle(path, generate, split='development')
    episodes.annotate_bundle(path, generate, split='development')
    assert len(prompts) == 2
    assert all('legacy_labels' not in p and 'old-label' not in p for p in prompts)
    saved = episodes.load_bundle(path)
    assert all(e['annotation'] is None for e in saved['episodes'] if e['split'] == 'holdout')
    assert all(e['annotation'] is not None for e in saved['episodes'] if e['split'] == 'development')
    saved['rubric']['followup']['title'] = 'Changed definition'
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match='rubric'):
        episodes.load_bundle(path)


def test_bundle_detects_changed_dialogue_and_preserves_failed_annotation(tmp_path):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=2, holdout=2)
    path = tmp_path / 'bundle.json'
    episodes.write_bundle(path, bundle)
    def unavailable(prompt, response_model):
        raise RuntimeError('service unavailable')
    result = episodes.annotate_bundle(path, unavailable)
    assert all(e.get('annotation_error') == 'RuntimeError' for e in result['episodes'] if e['split'] == 'development')
    assert all(e.get('annotation_error') is None for e in result['episodes'] if e['split'] == 'holdout')
    assert episodes.load_bundle(path)['manifest']['bundle_id'] == bundle['manifest']['bundle_id']
    result['episodes'][0]['turns'][0]['text'] = 'Altered after sampling'
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match='content'):
        episodes.load_bundle(path)


def test_empty_annotation_is_invalid_not_a_completed_draft(tmp_path):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=2, holdout=2)
    bundle['episodes'][0]['annotation'] = {}
    path = tmp_path / 'bundle.json'
    episodes.write_bundle(path, bundle)
    with pytest.raises(ValueError):
        episodes.load_bundle(path)


def test_model_selects_source_lines_without_rewriting_evidence(tmp_path):
    source = snapshot(tmp_path)
    conversations = source / 'conversations.jsonl'
    text = conversations.read_text()
    for response in ('What should the loop stop at?', 'Try that condition.'):
        text = text.replace(response, 'Check **this loop**.\\n原样保留 `code`。')
    conversations.write_text(text)
    bundle = episodes.build_bundle(source, development=2, holdout=2)
    path = tmp_path / 'bundle.json'
    episodes.write_bundle(path, bundle)
    calls = 0

    def generate(prompt, response_model):
        nonlocal calls
        calls += 1
        ep = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        turn = next(t for t in ep['turns'] if t['phase'] == 'response')
        assert 'text' not in turn
        assert all(set(line) == {'line', 'text'} for line in turn['lines'])
        followup = any(t['phase'] == 'followup' for t in ep['turns'])
        return response_model.model_validate({
            'request': {'value': 'unclear', 'evidence': [], 'rationale': 'Unspecified request.'},
            'tutor_response': {'value': 'hint', 'evidence': [
                {'turn_id': turn['id'], 'line': 999 if calls == 1 else line['line']}
                for line in turn['lines'] if line['text'].strip()
            ], 'rationale': 'Points at a next step.'},
            'followup': {'value': 'insufficient-evidence' if followup else 'no-followup-observed',
                         'evidence': [], 'rationale': 'Not established.'},
        })

    first = episodes.annotate_bundle(path, generate)
    assert sum(e['annotation'] is not None for e in first['episodes']) == 1
    after = episodes.annotate_bundle(path, generate)
    assert calls == 3
    for ep in after['episodes']:
        if ep['split'] == 'holdout':
            assert ep['annotation'] is None
            continue
        assert [e['quote'] for e in ep['annotation']['tutor_response']['evidence']] == [
            'Check **this loop**.', '原样保留 `code`。']
        for evidence in ep['annotation']['tutor_response']['evidence']:
            original = next(t for t in ep['turns'] if t['id'] == evidence['turn_id'])
            assert evidence['quote'] in original['text']
            assert set(evidence) == {'turn_id', 'quote'}
        episodes.validate_annotation(ep['annotation'], ep, after['rubric'])


def test_new_rubric_preserves_v3_bundle_and_sampling(tmp_path):
    source = snapshot(tmp_path)
    old = episodes.build_bundle(source, development=2, holdout=2, seed=7)
    # This saved classifier identity predates the version dispatcher.
    old['manifest']['rubric_hash'] = '7c6c01c2737d1ea03029d3c1ec31971c32c4b0d59fbffd34d465da503805b464'
    path = tmp_path / 'v3.json'
    episodes.write_bundle(path, old)
    before = path.read_bytes()
    revised = episodes.build_bundle(source, development=2, holdout=2, seed=7, version='v4')
    assert episodes.load_bundle(path) == old
    assert path.read_bytes() == before
    assert revised['manifest']['rubric_version'] == 'v4'
    assert revised['manifest']['rubric_hash'] != old['manifest']['rubric_hash']
    assert revised['manifest']['bundle_id'] != old['manifest']['bundle_id']
    assert revised['episodes'] == old['episodes']
    episodes.write_bundle(tmp_path / 'v4.json', revised)
    assert episodes.load_bundle(tmp_path / 'v4.json') == revised
    assert revised['manifest']['rubric_hash'] == 'b829c815f81e52fd34e37669e84cd5e040c997674c7ab29cc371b0255d654334'
    staged = episodes.build_bundle(source, development=2, holdout=2, seed=7, version='v5')
    assert staged['episodes'] == revised['episodes']
    assert staged['rubric'] == revised['rubric']
    assert staged['manifest']['rubric_hash'] != revised['manifest']['rubric_hash']
    assert staged['manifest']['rubric_hash'] == 'bee5e3fdb5f3b7fa602bf2b637f1ea009d6c3638d59f27342373a4f4308fc09c'
    episodes.write_bundle(tmp_path / 'v5.json', staged)
    v6 = episodes.build_bundle(source, development=2, holdout=2, seed=7, version='v6')
    assert v6['episodes'] == staged['episodes']
    assert v6['manifest']['rubric_hash'] != staged['manifest']['rubric_hash']
    assert 'checks-work' in v6['rubric']['tutor_response']['options']
    assert 'checks-work' not in staged['rubric']['tutor_response']['options']
    assert episodes.load_bundle(tmp_path / 'v5.json') == staged
    assert v6['manifest']['rubric_hash'] == '7785fe56ca0b215038012e21577964067416a83ab6da06bfae1c9c68ed93a6db'
    episodes.write_bundle(tmp_path / 'v6.json', v6)
    v7 = episodes.build_bundle(source, development=2, holdout=2, seed=7, version='v7')
    assert v7['episodes'] == v6['episodes']
    assert v7['manifest']['rubric_hash'] != v6['manifest']['rubric_hash']
    assert episodes.load_bundle(tmp_path / 'v6.json') == v6
    assert episodes.load_bundle(path) == old
    assert episodes.load_bundle(tmp_path / 'v4.json') == revised


def v4_example():
    episode = {
        'context': [{'id': 'turn-0', 'role': 'student', 'text': 'for i in range(6): print(i)'}],
        'turns': [
            {'id': 'turn-2', 'role': 'student', 'phase': 'request', 'text': 'for i in range(6): print(i)\nWhy does this print six numbers?'},
            {'id': 'turn-3', 'role': 'tutor', 'phase': 'response', 'text': 'Check the stop value.'},
            {'id': 'turn-4', 'role': 'student', 'phase': 'followup', 'text': 'for i in range(5): print(i)'},
        ],
    }
    def verdict(value, *turns):
        return {'value': value, 'rationale': 'Invented example.',
                'evidence': [{'turn_id': t['id'], 'quote': t['text']} for t in turns]}
    request, response, followup = episode['turns']
    return episode, {
        'student_action': verdict('submitted-code', request),
        'request': verdict('debugging', request, episode['context'][0]),
        'tutor_response': verdict('hint', response),
        'followup': verdict('revised-code', request, followup),
        'task_relation': verdict('same-task', request, followup),
    }


@pytest.mark.parametrize('version', ['v4', 'v5', 'v6', 'v7'])
def test_v4_evidence_respects_cutoffs_and_requires_both_sides(version):
    from src.labeling.episode_codebook import RUBRIC_V4
    episode, annotation = v4_example()
    episodes.validate_annotation(annotation, episode, RUBRIC_V4, version=version)
    # Current intention cannot cite the future tutor reply, or only prior context.
    invalid = [
        ('request', [{'turn_id': 'turn-3', 'quote': 'Check the stop value.'}]),
        ('request', annotation['request']['evidence'][1:]),
        ('student_action', annotation['request']['evidence'][1:]),
        ('followup', annotation['followup']['evidence'][1:]),
        ('followup', annotation['followup']['evidence'][:1]),
        ('task_relation', annotation['task_relation']['evidence'][:1]),
        ('task_relation', annotation['task_relation']['evidence'][1:]),
    ]
    for field, evidence in invalid:
        changed = deepcopy(annotation)
        changed[field]['evidence'] = evidence
        with pytest.raises(ValueError, match='evidence'):
            episodes.validate_annotation(changed, episode, RUBRIC_V4, version=version)
    annotation['followup']['evidence'][0] = annotation['request']['evidence'][1]
    annotation['task_relation'] = {'value': 'uncertain', 'evidence': [], 'rationale': 'Task cannot be linked.'}
    episodes.validate_annotation(annotation, episode, RUBRIC_V4, version=version)


@pytest.mark.parametrize('version', ['v4', 'v5', 'v6', 'v7'])
def test_v4_no_followup_matches_both_observability_fields(version):
    from src.labeling.episode_codebook import RUBRIC_V4
    episode, annotation = v4_example()
    annotation['followup'] = {'value': 'no-followup-observed', 'evidence': [], 'rationale': 'No later turn.'}
    annotation['task_relation'] = {'value': 'not-observable', 'evidence': [], 'rationale': 'No later turn.'}
    with pytest.raises(ValueError, match='followup'):
        episodes.validate_annotation(annotation, episode, RUBRIC_V4, version=version)
    episode['turns'].pop()
    episodes.validate_annotation(annotation, episode, RUBRIC_V4, version=version)
    annotation['task_relation']['value'] = 'uncertain'
    with pytest.raises(ValueError, match='followup'):
        episodes.validate_annotation(annotation, episode, RUBRIC_V4, version=version)


def test_v4_materializes_context_lines_and_resumes_without_annotating_holdout(tmp_path):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=2, holdout=2, seed=1, version='v4')
    path = tmp_path / 'v4.json'
    episodes.write_bundle(path, bundle)
    calls = 0

    def generate(prompt, response_model):
        nonlocal calls
        calls += 1
        ep = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        request = next(t for t in ep['turns'] if t['phase'] == 'request')
        assert all('lines' in t and 'text' not in t for t in ep['context'])
        has_followup = any(t['phase'] == 'followup' for t in ep['turns'])
        evidence = [{'turn_id': request['id'], 'line': 999 if calls == 1 else 1}]
        evidence.extend({'turn_id': t['id'], 'line': 1} for t in ep['context'] if t['role'] == 'student')
        return response_model.model_validate({
            'student_action': {'value': 'unclear', 'evidence': [], 'rationale': 'Unclear.'},
            'request': {'value': 'explanation', 'evidence': evidence, 'rationale': 'Invented selection.'},
            'tutor_response': {'value': 'unclear', 'evidence': [], 'rationale': 'Unclear.'},
            'followup': {'value': 'insufficient-evidence' if has_followup else 'no-followup-observed', 'evidence': [], 'rationale': 'Unknown.'},
            'task_relation': {'value': 'uncertain' if has_followup else 'not-observable', 'evidence': [], 'rationale': 'Unknown.'},
        })

    first = episodes.annotate_bundle(path, generate)
    assert sum(e['annotation'] is not None for e in first['episodes']) == 1
    after = episodes.annotate_bundle(path, generate)
    assert calls == 3
    context_quotes = []
    for ep in after['episodes']:
        if ep['split'] == 'holdout':
            assert ep['annotation'] is None and 'annotation_error' not in ep
            continue
        assert ep['annotation'] is not None and 'annotation_error' not in ep
        context_ids = {t['id'] for t in ep['context']}
        context_quotes.extend(e['quote'] for e in ep['annotation']['request']['evidence'] if e['turn_id'] in context_ids)
    assert context_quotes == ['Help with question 2.']
    assert episodes.load_bundle(path) == after


def staged_draft(visible, response_model):
    def judgment(value, turn=None, rationale='Synthetic observation.'):
        return {'value': value, 'rationale': rationale,
                'evidence': [{'turn_id': turn['id'], 'line': 1}] if turn else []}
    request = next(t for t in visible['turns'] if t['phase'] == 'request')
    if set(response_model.model_fields) == {'student_action', 'request'}:
        return {'student_action': judgment('submitted-code', request),
                'request': judgment('unclear', rationale='FIRST_STAGE_PRIVATE_PREDICTION')}
    response = next(t for t in visible['turns'] if t['phase'] == 'response')
    if set(response_model.model_fields) == {'tutor_response'}:
        return {'tutor_response': judgment('hint', response)}
    assert set(response_model.model_fields) == {'tutor_response', 'followup', 'task_relation'}
    followup = next((t for t in visible['turns'] if t['phase'] == 'followup'), None)
    return {'tutor_response': judgment('hint', response),
            'followup': judgment('submitted-code', followup) if followup else judgment('no-followup-observed'),
            'task_relation': judgment('uncertain' if followup else 'not-observable')}


@pytest.mark.parametrize('version', ['v5', 'v6', 'v7'])
def test_v5_actual_intent_prompt_is_invariant_to_future_turns_and_metadata(tmp_path, version):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=1, holdout=3, version=version)
    ep = bundle['episodes'][0]
    ep.update(v4_example()[0])
    variants = [bundle, deepcopy(bundle)]
    changed = variants[1]['episodes'][0]
    changed['turns'] = [t for t in changed['turns'] if t['phase'] != 'followup']
    changed['turns'][1].update(id='turn-999', text='FUTURE_RESPONSE_MARKER', mode='FUTURE_MODE')
    for field in ('question_ref', 'question_link', 'limitations', 'legacy_labels'):
        changed[field] = 'FUTURE_METADATA_MARKER'
    before_prompts, after_prompts = [], []

    def generate(prompt, response_model):
        visible = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        rubric = json.loads(prompt.split('Rubric:\n', 1)[1].split('\nEPISODE JSON:', 1)[0])
        assert set(rubric) == set(response_model.model_fields)
        if 'student_action' in response_model.model_fields:
            before_prompts.append(prompt)
            assert set(visible) == {'context', 'turns'}
            assert all(t['phase'] == 'request' for t in visible['turns'])
            assert all(set(t) <= {'id', 'role', 'phase', 'lines'} for t in visible['context'] + visible['turns'])
        else:
            after_prompts.append(prompt)
            assert 'FIRST_STAGE_PRIVATE_PREDICTION' not in prompt
        return response_model.model_validate(staged_draft(visible, response_model))

    for i, variant in enumerate(variants):
        variant['manifest']['episode_content_hash'] = episodes.episode_content_hash(variant['episodes'])
        path = tmp_path / f'v5-{i}.json'
        episodes.write_bundle(path, variant)
        result = episodes.annotate_bundle(path, generate)
        annotation = result['episodes'][0]['annotation']
        assert annotation is not None
        assert annotation['request']['value'] == 'unclear'
        assert annotation['request']['rationale'] == 'FIRST_STAGE_PRIVATE_PREDICTION'
        assert annotation['student_action']['evidence'] == [{'turn_id': 'turn-2', 'quote': 'for i in range(6): print(i)'}]
        assert annotation['tutor_response']['value'] == 'hint'
        assert episodes.load_bundle(path) == result
        assert result['episodes'][1:] == variant['episodes'][1:]
    assert len(before_prompts) == len(after_prompts) == 2
    assert before_prompts[0] == before_prompts[1]
    assert after_prompts[0] != after_prompts[1]


@pytest.mark.parametrize('version', ['v5', 'v6', 'v7'])
def test_v5_failed_second_stage_never_saves_or_overwrites_intent_and_retries_both(tmp_path, version):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=1, holdout=3, version=version)
    path = tmp_path / 'v5.json'
    episodes.write_bundle(path, bundle)
    original_holdout = deepcopy(bundle['episodes'][1:])
    calls = []

    def generate(prompt, response_model):
        calls.append(response_model.__name__)
        visible = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        draft = staged_draft(visible, response_model)
        if len(calls) == 2:
            draft['request'] = {'value': 'solution', 'evidence': [], 'rationale': 'Override attempt.'}
        return response_model.model_validate(draft)

    failed = episodes.annotate_bundle(path, generate)
    assert failed['episodes'][0]['annotation'] is None
    assert failed['episodes'][0]['annotation_error'] == 'ValidationError'
    assert failed['episodes'][1:] == original_holdout
    assert episodes.load_bundle(path) == failed
    resumed = episodes.annotate_bundle(path, generate)
    assert resumed['episodes'][0]['annotation']['request']['value'] == 'unclear'
    assert 'annotation_error' not in resumed['episodes'][0]
    assert resumed['episodes'][1:] == original_holdout
    episodes.annotate_bundle(path, generate)
    assert calls == ['BeforeHelpSelection', 'AfterHelpSelection'] * 2


@pytest.mark.parametrize('model', [episodes.BeforeHelpSelection, episodes.AfterHelpSelection])
def test_v5_gemini_schema_omits_unsupported_keyword_but_local_validation_stays_strict(model, monkeypatch):
    from src.labeling.episode_codebook import RUBRIC_V4
    from src.labeling.llm import gen_config
    config = gen_config(model)
    wire_schema = config['response_schema'].model_json_schema()
    assert 'additionalProperties' not in json.dumps(wire_schema)
    visible = {'turns': [{'id': 'turn-0', 'phase': 'request'}, {'id': 'turn-1', 'phase': 'response'}]}
    draft = staged_draft(visible, model)
    draft['unexpected_stage_field'] = {'value': 'solution', 'evidence': [], 'rationale': 'Must be rejected.'}
    with pytest.raises(ValueError, match='extra_forbidden'):
        model.model_validate_json(json.dumps(draft))
    before = episodes.rubric_hash(RUBRIC_V4, 'v5')
    monkeypatch.setitem(model.model_config, 'extra', 'ignore')
    assert episodes.rubric_hash(RUBRIC_V4, 'v5') != before


def test_v6_omits_blank_selectors_preserving_source_ids_and_rejects_invented_evidence(tmp_path):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=1, holdout=3, version='v6')
    ep = bundle['episodes'][0]
    ep.update(v4_example()[0])
    ep['context'][0]['text'] = '\n   \n'
    for turn in ep['turns']:
        turn['text'] = '  First source line.  \n\n\t\n原样保留 `code`。'
    bundle['manifest']['episode_content_hash'] = episodes.episode_content_hash(bundle['episodes'])
    original = deepcopy(bundle['episodes'])
    path = tmp_path / 'v6.json'
    episodes.write_bundle(path, bundle)
    response_line = 2

    def generate(prompt, response_model):
        visible = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        assert visible['context'][0]['lines'] == []  # Keep the turn, even when empty.
        for turn in visible['turns']:
            assert turn['lines'] == [{'line': 1, 'text': '  First source line.  '},
                                     {'line': 4, 'text': '原样保留 `code`。'}]
        draft = staged_draft(visible, response_model)
        if 'tutor_response' in draft:
            draft['tutor_response']['value'] = 'checks-work'
            draft['tutor_response']['evidence'][0]['line'] = response_line
        return response_model.model_validate(draft)

    for response_line, error in [(2, 'ValueError'), (999, 'KeyError')]:
        failed = episodes.annotate_bundle(path, generate)
        assert failed['episodes'][0]['annotation'] is None
        assert failed['episodes'][0]['annotation_error'] == error
    response_line = 4
    saved = episodes.annotate_bundle(path, generate)
    annotation = saved['episodes'][0]['annotation']
    assert annotation['tutor_response']['value'] == 'checks-work'
    assert annotation['tutor_response']['evidence'] == [{'turn_id': 'turn-3', 'quote': '原样保留 `code`。'}]
    assert saved['episodes'][0]['turns'] == original[0]['turns']
    assert saved['episodes'][0]['context'] == original[0]['context']
    assert saved['episodes'][1:] == original[1:]
    assert episodes.load_bundle(path) == saved
    from src.labeling.episode_codebook import RUBRIC_V4
    with pytest.raises(ValueError, match='category'):
        episodes.validate_annotation(annotation, saved['episodes'][0], RUBRIC_V4, 'v5')


@pytest.mark.parametrize('has_blank_followup', [False, True])
def test_v7_derives_absence_but_does_not_erase_blank_student_turns(tmp_path, has_blank_followup):
    bundle = episodes.build_bundle(snapshot(tmp_path), development=1, holdout=3, version='v7')
    ep = bundle['episodes'][0]
    ep.update(v4_example()[0])
    if has_blank_followup:
        ep['turns'][-1]['text'] = '\n  \n'
    else:
        ep['turns'].pop()
    bundle['manifest']['episode_content_hash'] = episodes.episode_content_hash(bundle['episodes'])
    path = tmp_path / 'v7.json'
    episodes.write_bundle(path, bundle)

    def generate(prompt, response_model):
        visible = json.loads(prompt.split('EPISODE JSON:\n', 1)[1])
        draft = staged_draft(visible, response_model)
        if 'student_action' not in response_model.model_fields:
            expected = {'tutor_response', 'followup', 'task_relation'} if has_blank_followup else {'tutor_response'}
            assert set(response_model.model_fields) == expected
            rubric = json.loads(prompt.split('Rubric:\n', 1)[1].split('\nEPISODE JSON:', 1)[0])
            assert set(rubric) == expected
            if has_blank_followup:
                draft['followup'] = {'value': 'insufficient-evidence', 'evidence': [], 'rationale': 'Blank contribution.'}
            else:
                assert 'Return tutor_response only' in prompt
                assert 'additionalProperties' not in json.dumps(response_model.model_json_schema())
                with pytest.raises(ValueError, match='extra_forbidden'):
                    response_model.model_validate({**draft, 'followup': {}})
        return response_model.model_validate(draft)

    result = episodes.annotate_bundle(path, generate)
    annotation = result['episodes'][0]['annotation']
    assert annotation is not None
    assert annotation['followup']['value'] == ('insufficient-evidence' if has_blank_followup else 'no-followup-observed')
    assert annotation['task_relation']['value'] == ('uncertain' if has_blank_followup else 'not-observable')
    assert annotation['followup']['evidence'] == annotation['task_relation']['evidence'] == []
    assert result['episodes'][1:] == bundle['episodes'][1:]
    assert episodes.load_bundle(path) == result
