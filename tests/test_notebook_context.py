"""All notebook/dialogue examples are invented."""
from copy import deepcopy
import hashlib
import json

import pytest


def example():
    from src.labeling.episodes import _hash
    stamp = lambda minute: f'2026-09-01T10:{minute:02}:00+00:00'
    fingerprint = lambda s: hashlib.md5(s.encode()).hexdigest()
    capture = {'id':12, 'conv_id':'invented', 'created_at':stamp(2),
               'student_message':'total?', 'tutor_response':'Add the two values.',
               'initial_notebook_json':json.dumps({'cells':[
                   {'cell_type':'markdown','source':['Add 3 and 4.']},
                   {'cell_type':'code','source':'total = 3\n', 'outputs':['PRIVATE OUTPUT']} ]})}
    queries = [{'id':10, 'case_conv_id':'invented', 'event_conv_id':None,
                'event_type':'tutor_query', 'created_at':stamp(1),
                'question_md5':fingerprint('total?')}]
    responses = [{'id':11,'conv_id':'invented','event_type':'tutor_response',
                  'created_at':stamp(2),'response_md5':fingerprint('Add the two values.')}]
    episode = {'id':'later', 'conversation_key':_hash('invented')[:16], 'context':[], 'turns':[
        {'id':'turn-0','role':'student','phase':'request','text':'check this','at':stamp(5)},
        {'id':'turn-1','role':'tutor','phase':'response','text':'Try adding both values.','at':stamp(6)},
        {'id':'turn-2','role':'student','phase':'followup','text':'HIDDEN FUTURE','at':stamp(8)}]}
    return capture, queries, responses, episode


def test_recovered_history_is_once_and_future_cannot_change_context():
    from src.ingest.notebook_context import recover_initial, context_for
    capture, queries, responses, episode = example()
    original = deepcopy(episode)
    recovered = recover_initial(capture, queries, responses)
    packet = context_for(episode, recovered)
    assert [t['id'] for t in packet['dialogue']['context']] == ['event-10','event-11']
    assert [t['id'] for t in packet['dialogue']['turns']] == ['turn-0','turn-1']
    assert packet['initial_notebook']['cells'][1]['source'] == 'total = 3\n'
    assert packet['current_work'] is None
    assert 'HIDDEN' not in json.dumps(packet) and 'PRIVATE OUTPUT' not in json.dumps(packet)
    assert episode == original
    changed = deepcopy(episode)
    changed['turns'][2]['text'] = 'DIFFERENT FUTURE'
    changed['annotation'] = {'private':'LABEL'}
    assert context_for(changed, recovered) == packet
    episode['context'] = deepcopy(recovered['exchange'])
    assert context_for(episode, recovered) == packet


@pytest.mark.parametrize('problem', ['other-query','ambiguous-query','other-response','late-capture','bad-source','wrong-episode'])
def test_recovery_rejects_unbound_or_unusable_evidence(problem):
    from src.ingest.notebook_context import recover_initial, context_for
    capture, queries, responses, episode = example()
    if problem == 'other-query': queries[0]['event_conv_id'] = 'someone-else'
    elif problem == 'ambiguous-query': queries.append({**queries[0], 'id':9})
    elif problem == 'other-response': responses[0]['conv_id'] = 'someone-else'
    elif problem == 'late-capture': capture['created_at'] = '2026-09-01T10:07:00+00:00'
    elif problem == 'bad-source': capture['initial_notebook_json'] = '{"cells":[{"cell_type":"code","source":123}]}'
    else: episode['conversation_key'] = 'unrelated'
    with pytest.raises(ValueError):
        context_for(episode, recover_initial(capture, queries, responses))


def test_conflicting_event_id_is_not_hidden_by_another_exact_turn():
    from src.ingest.notebook_context import recover_initial, context_for
    capture, queries, responses, episode = example()
    recovered = recover_initial(capture, queries, responses)
    student, tutor = recovered['exchange']
    episode['context'] = [{**student, 'text':'CONFLICTING SOURCE'},
                          {**student, 'id':'different-id'}, tutor]
    with pytest.raises(ValueError, match='conflicts'):
        context_for(episode, recovered)
