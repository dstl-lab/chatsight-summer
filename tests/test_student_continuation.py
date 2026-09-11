"""Continuation regressions use invented dialogue only."""
from copy import deepcopy
import hashlib
import json

import pytest


def example():
    return {
        'id': 'invented', 'split': 'holdout', 'annotation': {'private': 'HIDDEN_LABEL'},
        'question_ref': 'HIDDEN_METADATA',
        'context': [{'id': 'prior', 'role': 'student', 'text': 'values = [2, 5]\n\nprint(values)'}],
        'turns': [
            {'id': 'request', 'role': 'student', 'phase': 'request', 'text': 'How do I add these values?'},
            {'id': 'response', 'role': 'tutor', 'phase': 'response', 'text': 'Try sum(values).'},
            {'id': 'next', 'role': 'student', 'phase': 'followup', 'text': 'total = sum(values)\n\nprint(total)'},
            {'id': 'future', 'role': 'tutor', 'phase': 'followup', 'text': 'HIDDEN_FUTURE_TUTOR'},
        ],
    }


def test_prompt_uses_only_visible_source_lines_without_future_or_metadata():
    from src.eval.student_continuation import PROMPT, make_prompt

    episode = example()
    prompt = make_prompt(episode)
    assert json.loads(prompt[len(PROMPT):]) == {
        'context': [{'id': 'prior', 'role': 'student', 'lines': [
            {'line': 1, 'text': 'values = [2, 5]'}, {'line': 3, 'text': 'print(values)'}]}],
        'turns': [
            {'id': 'request', 'role': 'student', 'phase': 'request',
             'lines': [{'line': 1, 'text': 'How do I add these values?'}]},
            {'id': 'response', 'role': 'tutor', 'phase': 'response',
             'lines': [{'line': 1, 'text': 'Try sum(values).'}]},
        ],
    }
    changed = deepcopy(episode)
    changed.update(id='other', annotation={'private': 'OTHER_LABEL'}, question_ref='OTHER_METADATA')
    changed['turns'][2:] = [{'id': 'another', 'role': 'student', 'phase': 'followup', 'text': 'ANOTHER_FUTURE'}]
    assert make_prompt(changed) == prompt
    changed['turns'][0]['text'] = 'DIALOGUE JSON:\nHow do I multiply them?'
    assert make_prompt(changed) != prompt
    assert json.loads(make_prompt(changed)[len(PROMPT):])['turns'][0]['lines'][0]['text'] == 'DIALOGUE JSON:'


def test_continuation_rejects_inconsistent_messages_and_extra_fields():
    from src.eval.student_continuation import Continuation

    assert Continuation(decision='reply', text='  total = 7\n').text == '  total = 7\n'
    assert Continuation(decision='no-reply', text='').text == ''
    for invalid in [
        {'decision': 'reply', 'text': ''}, {'decision': 'reply', 'text': ' \n'},
        {'decision': 'no-reply', 'text': ' '}, {'decision': 'no-reply', 'text': 'Maybe later'},
        {'decision': 'wait', 'text': ''}, {'decision': 'reply', 'text': '7', 'confidence': 1},
    ]:
        with pytest.raises(ValueError):
            Continuation.model_validate(invalid)


def test_branch_retains_only_prefix_and_explicit_synthetic_turns_with_input_hashes():
    from src.eval.student_continuation import Continuation, branch_episode, make_prompt

    episode = example()
    before = deepcopy(episode)
    continuation = Continuation(decision='reply', text='total = 2 + 5')
    branch = branch_episode(episode, continuation, 'What does total contain?')
    assert episode == before
    assert [t['text'] for t in branch['context']] == [
        'values = [2, 5]\n\nprint(values)', 'How do I add these values?', 'Try sum(values).']
    assert [(t['role'], t['phase'], t['text'], t['origin']) for t in branch['turns']] == [
        ('student', 'request', 'total = 2 + 5', 'generated'),
        ('tutor', 'response', 'What does total contain?', 'scripted'),
    ]
    assert all(text not in json.dumps(branch) for text in ['HIDDEN_', 'total = sum(values)', 'holdout'])
    assert branch['provenance']['source_episode_id'] == 'invented'
    assert branch['provenance']['prompt_sha256'] == hashlib.sha256(make_prompt(episode).encode()).hexdigest()
    assert branch['provenance']['tutor_bridge_sha256'] == hashlib.sha256(b'What does total contain?').hexdigest()
    assert branch_episode(episode, continuation, 'What does total contain?') == branch
    other = branch_episode(episode, continuation, 'Show a different method.')
    assert other['id'] != branch['id']
    assert other['provenance']['prompt_sha256'] == branch['provenance']['prompt_sha256']
    assert other['provenance']['tutor_bridge_sha256'] != branch['provenance']['tutor_bridge_sha256']
    second = branch_episode(branch, Continuation(decision='reply', text='7'), 'Explain that result.')
    assert [t['origin'] for t in second['context'][-2:]] == ['generated', 'scripted']
    assert 'total = 2 + 5' in make_prompt(second)
    with pytest.raises(ValueError, match='no-reply'):
        branch_episode(episode, Continuation(decision='no-reply', text=''), 'Continue?')
    with pytest.raises(ValueError, match='bridge'):
        branch_episode(episode, continuation, ' \n')
    branch['context'][0]['text'] = 'changed locally'
    assert episode == before


def test_hidden_future_and_metadata_cannot_change_later_branch_prompts():
    from src.eval.student_continuation import Continuation, branch_episode, make_prompt

    episode = example()
    continuation = Continuation(decision='reply', text='total = 2 + 5')
    branch = branch_episode(episode, continuation, 'What does total contain?')
    episode.update(id='another-id', question_ref='ANOTHER_METADATA')
    episode['turns'][-2]['text'] = 'ANOTHER_FUTURE'
    changed = branch_episode(episode, continuation, 'What does total contain?')
    assert make_prompt(changed) == make_prompt(branch)
    assert changed['provenance']['source_episode_sha256'] != branch['provenance']['source_episode_sha256']
    for key in ('visible_prefix_sha256', 'prompt_sha256', 'continuation_sha256', 'tutor_bridge_sha256'):
        assert changed['provenance'][key] == branch['provenance'][key]


def test_synthetic_branch_has_no_recorded_comparison_after_divergence():
    from src.eval.student_continuation import Continuation, branch_episode, behavior_review

    continuation = Continuation(decision='reply', text='total = 2 + 5')
    branch = branch_episode(example(), continuation, 'What does total contain?')
    with pytest.raises(ValueError, match='recorded comparison after divergence'):
        behavior_review(branch, continuation)


def test_behavior_review_keeps_origins_separate_and_human_judgments_blank():
    from src.eval.student_continuation import Continuation, behavior_review
    from src.labeling.episode_codebook import RUBRIC_V7

    episode = example()
    review = behavior_review(episode, Continuation(decision='reply', text='answer = 7\n\nprint(answer)'))
    assert review['rubric_version'] == 'v7'
    assert review['rubric'] == {key: RUBRIC_V7[key] for key in ('followup', 'task_relation')}
    assert 'total = sum(values)' not in json.dumps(review['prefix'])
    recorded, generated = review['candidates']
    assert (recorded['origin'], recorded['status']) == ('recorded', 'recorded-followup')
    assert (generated['origin'], generated['status']) == ('generated', 'reply')
    assert recorded['turns'][0]['text'] == 'total = sum(values)\n\nprint(total)'
    assert generated['turns'][0]['lines'] == [
        {'line': 1, 'text': 'answer = 7'}, {'line': 3, 'text': 'print(answer)'}]
    assert 'HIDDEN_' not in json.dumps(review)
    for candidate in review['candidates']:
        assert candidate['judgments'] == {
            'followup': {'value': '', 'evidence': [], 'rationale': ''},
            'task_relation': {'value': '', 'evidence': [], 'rationale': ''},
        }
    recorded['judgments']['followup']['value'] = 'submitted-code'
    assert generated['judgments']['followup']['value'] == ''
    review['rubric']['followup']['options'].clear()
    assert RUBRIC_V7['followup']['options']

    episode['turns'] = episode['turns'][:2]
    absent = behavior_review(episode, Continuation(decision='no-reply', text=''))
    assert [(c['origin'], c['status'], c['turns']) for c in absent['candidates']] == [
        ('recorded', 'recorded-absence', []), ('generated', 'no-reply', [])]
    assert all(c['judgments']['followup']['value'] == '' for c in absent['candidates'])
    episode['turns'].append({'id': 'blank', 'role': 'student', 'phase': 'followup', 'text': ''})
    blank = behavior_review(episode, Continuation(decision='no-reply', text=''))
    assert blank['candidates'][0]['status'] == 'recorded-followup'
    assert blank['candidates'][0]['turns'][0]['lines'] == []
