"""Authored cases protect the hidden continuation and paired comparison."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json

import pytest


def module():
    assert importlib.util.find_spec('src.eval.continuation_selection'), 'Selection module is missing'
    from src.eval import continuation_selection
    return continuation_selection


def row(key, response=None, history=True, conversation=None):
    value = {'id': key, 'conversation_id': conversation or key, 'prefix': [
        {'role': 'student', 'text': 'loop help'}, {'role': 'tutor', 'text': 'try a loop'}]}
    if history:
        value['prefix'][:0] = [{'role': 'student', 'text': 'HISTORY_CANARY'},
                               {'role': 'tutor', 'text': 'earlier guidance'}]
    if response is not None:
        value['response'] = response
    return value


def inputs(count=4):
    data = {'train': [row('z', 'help'), row('a', 'result'), row('b', 'Ｂ  value'),
                      row('c', 'b\nvalue'), row('d', 'another', conversation='b'),
                      row('e', 'loop help loop'), row('f', '  ')],
            'queries': [row(f'q{i}') for i in range(count)]}
    refs = [{'id': q['id'], 'conversation_id': q['conversation_id'], 'text': 'recorded result'}
            for q in data['queries']]
    return data, refs


def test_preparation_is_balanced_deterministic_and_history_cannot_change_options():
    m = module()
    data, refs = inputs()
    before = deepcopy(data), deepcopy(refs)
    prepared = m.prepare(data, refs)
    assert (data, refs) == before
    assert not prepared['excluded']
    assert Counter(c['answer'] for c in prepared['cases']) == dict.fromkeys('ABCD', 1)
    for case in prepared['cases']:
        assert {o['text'] for o in case['options']} == {
            'recorded result', 'result', 'Ｂ  value', 'loop help loop'}
        sources = [s for s in case['option_sources'].values() if s['origin'] == 'library']
        assert {s['source_id'] for s in sources} == {'a', 'b', 'e'}
        assert len({s['conversation_id'] for s in sources}) == 3
        prompt = m.make_prompt(case, 'history')
        payload = json.loads(prompt.split('\n', 1)[1])
        assert set(payload) == {'earlier_context', 'current_exchange', 'options'}
        assert 'HISTORY_CANARY' in prompt
        assert 'HISTORY_CANARY' not in m.make_prompt(case, 'current')
        assert 'option_sources' not in prompt and 'query_id' not in prompt and 'answer' not in payload
        poisoned = deepcopy(case)
        poisoned.update(answer='SECRET_ANSWER', query_id='SECRET_ID', option_sources={'SECRET': 'hidden'})
        poisoned['options'][0]['source_id'] = 'SECRET_OPTION_ID'
        poisoned['context'][0]['id'] = 'SECRET_TURN_ID'
        poisoned['turns'][0]['origin'] = 'SECRET_TURN_ORIGIN'
        assert m.make_prompt(poisoned, 'history') == prompt
        texts = {option['label']: option['text'] for option in case['options']}
        assert texts[case['baselines']['lexical']] == 'loop help loop'
    data['train'].reverse()
    for item in data['train'] + data['queries']:
        item['prefix'][0]['text'] = 'different history '*100
    changed = m.prepare(data, refs)
    assert [c['options'] for c in changed['cases']] == [c['options'] for c in prepared['cases']]
    assert before[1] == refs
    assert before[0] != data
    assert [j['condition'] for j in m.jobs(prepared)] == [
        'history', 'current', 'current', 'history', 'history', 'current', 'current', 'history']


def test_split_reference_guards_and_explicit_exclusions():
    m = module()
    mutations = [
        lambda d, r: d['train'].append(deepcopy(d['train'][0])),
        lambda d, r: d['train'][0].update(conversation_id='q0'),
        lambda d, r: (d['train'][0].update(student_id='learner'),
                      d['queries'][0].update(student_id='learner')),
        lambda d, r: r.append(deepcopy(r[0])),
        lambda d, r: r[0].update(conversation_id='wrong'),
        lambda d, r: r[0].update(text=' \n'),
        lambda d, r: r[0].update(hidden='unexpected'),
        lambda d, r: r.pop(),
        lambda d, r: (d['queries'][1].update(conversation_id='q0'), r[1].update(conversation_id='q0')),
    ]
    for mutate in mutations:
        data, refs = inputs()
        mutate(data, refs)
        with pytest.raises(ValueError):
            m.prepare(data, refs)
    data, refs = inputs(2)
    data['queries'][0] = row('q0', history=False)
    result = m.prepare(data, refs)
    assert [c['case'] for c in result['cases']] == [2]
    assert result['excluded'][0]['reason'] == 'No earlier student turn.'
    data['train'] = data['train'][:2]
    result = m.prepare(data, refs)
    assert not result['cases']
    assert result['excluded'][1]['reason'] == 'Fewer than three eligible library conversations with distinct responses.'


def test_scoring_retains_errors_and_rejects_missing_duplicate_or_changed_jobs():
    m = module()
    prepared = m.prepare(*inputs(3))
    calls = []
    for job in m.jobs(prepared):
        case = prepared['cases'][job['case'] - 1]
        answer = case['answer']
        wrong = next(label for label in 'ABCD' if label != answer)
        call = {'request': job, 'status': 'complete', 'response': {'choice': answer}}
        if (job['case'], job['condition']) == (1, 'current'):
            call['response']['choice'] = wrong
        if (job['case'], job['condition']) == (2, 'history'):
            call['response']['choice'] = wrong
        if (job['case'], job['condition']) == (3, 'current'):
            call = {'request': job, 'status': 'error', 'error': {'type': 'TimeoutError', 'message': 'failed'}}
        calls.append(call)
    report = m.score(prepared, calls)
    assert report['paired']['cases'] == 2
    assert report['paired']['accuracy'] == {'history': .5, 'current': .5}
    assert report['paired']['history_minus_current'] == 0
    assert (report['paired']['wins'], report['paired']['losses'], report['paired']['ties']) == (1, 1, 0)
    assert report['all_cases_delta_bounds'] == {'lower': 0, 'upper': pytest.approx(1/3)}
    assert len(report['failures']) == 1
    assert report['chance_accuracy'] == .25
    for name in ('lexical', 'shortest', 'longest'):
        assert set(report['baselines'][name]) == {'paired_accuracy', 'all_accuracy'}
    for change in (lambda c: c.pop(), lambda c: c.append(deepcopy(c[0])),
                   lambda c: c[0]['request'].update(prompt='different prompt'),
                   lambda c: c[0]['response'].update(explanation='extra')):
        malformed = deepcopy(calls)
        change(malformed)
        with pytest.raises(ValueError):
            m.score(prepared, malformed)
    for call in calls:
        call.clear()
    assert report['failures'][0]['error']['message'] == 'failed'
    all_failed = [{'request': job, 'status': 'error', 'error': {'type': 'Error', 'message': ''}}
                  for job in m.jobs(prepared)]
    report = m.score(prepared, all_failed)
    assert report['paired']['accuracy'] == {'history': None, 'current': None}
    assert report['paired']['history_minus_current'] is None
    assert report['all_cases_delta_bounds'] == {'lower': -1, 'upper': 1}
    prepared['cases'][0]['answer'] = ''
    with pytest.raises(ValueError):
        m.score(prepared, all_failed)
