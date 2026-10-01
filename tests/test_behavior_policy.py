"""Authored examples test policy mechanics, not student fidelity."""
from copy import deepcopy
import importlib.util
import json
import socket

import pytest


HINT = {'assistance': ['hint'], 'material': [], 'task_relation': 'same'}
CHECK = {'assistance': ['checking'], 'material': [], 'task_relation': 'same'}


def policy():
    assert importlib.util.find_spec('src.agents.behavior_policy'), 'Offline policy is missing'
    from src.agents import behavior_policy
    return behavior_policy


def request():
    context = {'last_assistance': ['hint'], 'feedback': None}
    examples = [{'id': name, 'account_id': account, 'source_ref': 'authored:' + name,
                 'origin': 'authored', 'context': deepcopy(context), 'behavior': deepcopy(behavior)}
                for name, account, behavior in [('a1', 'a', HINT), ('a2', 'a', HINT),
                                                ('a3', 'a', CHECK), ('b1', 'b', CHECK)]]
    return {'seed': 4, 'query': {'id': 'q', 'account_id': 'q-account',
            'source_ref': 'authored:q', 'context': context}, 'examples': examples}


def test_account_balanced_joint_distribution_replay_and_order():
    module, raw = policy(), request()
    before = deepcopy(raw)
    result = module.select(raw)
    assert raw == before
    assert result['status'] == 'selected'
    assert result['matching']['pool'] == 'matching-context'
    assert result['matching']['fields'] == ['last_assistance']
    assert result['matching']['unknown_fields'] == ['feedback']
    probabilities = {tuple(r['behavior']['assistance']): r['probability']
                     for r in result['distribution']}
    assert probabilities == {('hint',): pytest.approx(1 / 3), ('checking',): pytest.approx(2 / 3)}
    assert {r['id']: r['weight'] for r in result['examples']} == {
        'a1': '1/6', 'a2': '1/6', 'a3': '1/6', 'b1': '1/2'}
    assert result['selection']['example_id'] in {'a1', 'a2', 'a3', 'b1'}
    assert result['rendering']['status'] == 'rendered'
    raw['examples'].reverse()
    assert module.select(raw) == result


def test_unknown_context_and_sparse_matches_report_broader_fallback():
    module, raw = policy(), request()
    raw['query']['context']['last_assistance'] = []
    result = module.select(raw)
    assert result['matching']['pool'] == 'broader-fallback'
    assert result['matching']['exact_accounts'] == 0
    assert all(r['mismatched_fields'] == ['last_assistance'] for r in result['examples'])
    raw['query']['context']['last_assistance'] = None
    result = module.select(raw)
    assert result['matching']['fields'] == []
    assert result['matching']['pool'] == 'broader-fallback'
    raw['query']['context']['last_assistance'] = ['hint']
    raw['examples'][-1]['context']['last_assistance'] = None
    assert module.select(raw)['matching']['exact_accounts'] == 1
    assert module.select(raw)['matching']['pool'] == 'broader-fallback'


def test_exclusions_never_become_absence_or_silence():
    module, raw = policy(), request()
    for index, origin in enumerate(['recorded', 'generated', 'assistant-labeled']):
        row = deepcopy(raw['examples'][0])
        row.update(id=f'excluded-{index}', source_ref=f'authored:excluded-{index}', origin=origin)
        raw['examples'].append(row)
    raw['examples'][1]['behavior']['material'] = None
    raw['examples'][2]['account_id'] = 'q-account'
    result = module.select(raw)
    assert result['counts']['eligible_examples'] == 2
    assert {r['id'] for r in result['examples'] if r['included']} == {'a1', 'b1'}
    assert all(r['exclusion'] for r in result['examples'] if not r['included'])
    raw['examples'][3]['behavior'] = None
    result = module.select(raw)
    assert result['status'] == 'insufficient-evidence'
    assert result['selection'] is None and result['distribution'] == []
    assert result['rendering']['status'] == 'not-selected'
    assert result['rendering']['text'] is None


def test_multilabel_bundles_remain_together_and_missing_render_inputs_do_not_resample():
    module, raw = policy(), request()
    for row in raw['examples']:
        row['behavior'] = {'assistance': ['hint', 'explanation'], 'material': [],
                           'task_relation': 'same'}
    result = module.select(raw)
    assert len(result['distribution']) == 1
    assert result['selection']['behavior']['assistance'] == ['explanation', 'hint']
    assert result['rendering']['status'] == 'unsupported'
    for row in raw['examples']:
        row['behavior'] = {'assistance': ['checking'], 'material': ['work'], 'task_relation': 'same'}
    missing = module.select(raw)
    assert missing['rendering']['status'] == 'missing-input'
    assert missing['rendering']['missing'] == ['work']
    assert missing['rendering']['text'] is None
    raw['query']['work'] = 'answer = 3'
    rendered = module.select(raw)
    assert rendered['selection'] == missing['selection']
    assert 'answer = 3' in rendered['rendering']['text']
    for row in raw['examples']:
        row['behavior'] = {'assistance': ['hint'], 'material': [], 'task_relation': 'different'}
    assert module.select(raw)['rendering']['missing'] == ['next_task']


@pytest.mark.parametrize('change', [
    lambda x: x.update(seed=True),
    lambda x: x.update(seed=-1),
    lambda x: x['query'].update(recorded_next_message='future'),
    lambda x: x['examples'][1].update(id='a1'),
    lambda x: x['examples'][1].update(source_ref='authored:a1'),
    lambda x: x['examples'][0]['behavior'].update(assistance=['hint', 'hint']),
    lambda x: x['examples'][0]['context'].update(last_assistance=['hint', 'hint']),
    lambda x: x['query'].update(work='   '),
])
def test_reject_invalid_inputs(change):
    module, raw = policy(), request()
    change(raw)
    with pytest.raises(ValueError):
        module.select(raw)


def test_save_verify_without_network_never_overwrites_and_detects_tampering(tmp_path, monkeypatch):
    module = policy()
    monkeypatch.setattr(socket.socket, 'connect', lambda *args: pytest.fail('Offline policy used network'))
    folder = tmp_path / 'run'
    receipt = module.run(request(), folder)
    assert module.verify(folder) == receipt
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(FileExistsError):
        module.run(request(), folder)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    saved = json.loads((folder / 'trace.json').read_text())
    saved['result']['selection']['example_id'] = 'invented'
    (folder / 'trace.json').write_text(json.dumps(saved))
    with pytest.raises(ValueError, match='reproduce'):
        module.verify(folder)


def test_empty_library_is_insufficient_not_a_random_default():
    raw = request()
    raw['examples'] = []
    result = policy().select(raw)
    assert result['status'] == 'insufficient-evidence' and result['selection'] is None
