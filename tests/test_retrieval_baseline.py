"""An offline reference baseline must not retrieve from a query's hidden future."""
from copy import deepcopy
import importlib.util
import json
import subprocess
import sys

import pytest


def retrieve():
    assert importlib.util.find_spec('src.eval.retrieval_baseline'), 'Retrieval baseline is missing'
    from src.eval.retrieval_baseline import predict
    return predict


def example(key, words, response=None):
    row = {'id': key, 'conversation_id': key, 'student_id': None,
           'prefix': [{'role': 'student', 'text': words},
                      {'role': 'tutor', 'text': words}]}
    if response is not None:
        row['response'] = response
    return row


def test_retrieval_uses_prefix_only_with_stable_ties_and_no_match():
    predict = retrieve()
    data = {'train': [example('z', 'coffee', 'coffee response'),
                      example('a', 'coffee', ''),
                      example('b', 'loop', 'coffee coffee coffee')],
            'queries': [example('q', 'coffee'), example('r', 'penguin')]}
    before = deepcopy(data)
    rows = predict(data)['predictions']
    assert rows[0] == {'id': 'q', 'status': 'recorded-blank', 'source_id': 'a',
                       'source_conversation_id': 'a', 'similarity': pytest.approx(1),
                       'text': ''}
    assert rows[1] == {'id': 'r', 'status': 'no-match', 'source_id': None,
                       'source_conversation_id': None, 'similarity': 0.0, 'text': None}
    # If indexed responses influence selection, this deliberate distractor wins.
    data['train'][2]['response'] = 'coffee ' * 1000
    data['train'].reverse()
    assert predict(data)['predictions'] == rows
    data = deepcopy(before)
    data['train'][1]['response'] = '  please help\n'
    row = predict(data)['predictions'][0]
    assert row['status'] == 'matched' and row['text'] == '  please help\n'
    assert before['train'][1]['response'] == ''
    empty = {'train': [example('a', '???', 'recorded')], 'queries': [example('q', 'coffee')]}
    assert predict(empty)['predictions'][0]['status'] == 'no-match'


def test_hidden_targets_and_split_leakage_are_rejected():
    predict = retrieve()
    base = {'train': [example('a', 'loop', 'help')], 'queries': [example('q', 'loop')]}
    mutations = [
        lambda p: p['queries'][0].update(response='hidden future'),
        lambda p: p['queries'][0].update(conversation_id='a'),
        lambda p: (p['train'][0].update(student_id='s'), p['queries'][0].update(student_id='s')),
        lambda p: p['queries'][0].update(id='a'),
        lambda p: p['train'].append(deepcopy(p['train'][0])),
        lambda p: p['train'][0].update(student_id=' '),
        lambda p: p['queries'][0].update(prefix=[]),
        lambda p: p['queries'][0]['prefix'][-1].update(role='student'),
        lambda p: p['queries'][0]['prefix'][0].update(text=None),
        lambda p: p['train'].clear(),
    ]
    for mutate in mutations:
        data = deepcopy(base)
        mutate(data)
        with pytest.raises(ValueError):
            predict(data)
    # Conflicting learner IDs within a conversation cannot defeat the split guard.
    data = deepcopy(base)
    data['train'][0]['student_id'] = 's1'
    data['train'].append(example('b', 'loop', 'help'))
    data['train'][1].update(conversation_id='a', student_id='s2')
    with pytest.raises(ValueError):
        predict(data)


def test_command_keeps_sources_and_existing_output_unchanged(tmp_path):
    retrieve()
    source, output = tmp_path / 'input.json', tmp_path / 'output.json'
    source.write_text(json.dumps({'train': [example('a', 'loop', 'help')],
                                 'queries': [example('q', 'loop')]}))
    before = source.read_bytes()
    command = [sys.executable, '-m', 'src.eval.retrieval_baseline', str(source), str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    saved = output.read_bytes()
    assert json.loads(saved)['predictions'][0]['text'] == 'help'
    assert json.loads(saved)['provenance']['input_sha256']
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == saved and source.read_bytes() == before
