"""Authored boundaries for deterministic wording; these are not realism tests."""
from copy import deepcopy
import importlib.util
import json
import socket

import pytest

from src.agents import behavior_policy as policy
from tests.test_behavior_policy import request


def templates():
    assert importlib.util.find_spec('src.agents.behavior_templates'), 'Deterministic template extension is missing'
    from src.agents import behavior_templates
    return behavior_templates


@pytest.mark.parametrize('behavior,slots,expected', [
    ({'assistance': ['unspecified'], 'material': [], 'task_relation': 'same'}, {},
     'can you help me with this?'),
    ({'assistance': ['solution'], 'material': [], 'task_relation': 'different'},
     {'next_task': 'Q2: return {x}\nwithout changing x'},
     'Q2: return {x}\nwithout changing x\ncan you show me the solution?'),
    ({'assistance': ['solution'], 'material': ['work'], 'task_relation': 'different'},
     {'next_task': 'Q2: sum these values', 'work': "partial = {'x': 1}\nresult = ..."},
     "partial = {'x': 1}\nresult = ...\nQ2: sum these values\ncan you show me the solution?"),
])
def test_new_patterns_preserve_choice_and_literal_inputs(behavior, slots, expected):
    module, value = templates(), request()
    for row in value['examples']:
        row['behavior'] = behavior
    value['query'].update(slots)
    selected = policy.select(value)
    before = deepcopy(selected)
    assert selected['rendering']['status'] == 'unsupported'
    rendered = module.express(selected)
    assert rendered['status'] == 'rendered' and rendered['text'] == expected
    assert selected == before
    for field in slots:
        missing = deepcopy(value)
        missing['query'].pop(field)
        blocked_choice = policy.select(missing)
        blocked = module.express(blocked_choice)
        assert blocked['status'] == 'missing-input' and blocked['missing'] == [field]
        assert blocked['text'] is None
        assert blocked_choice['selection'] == selected['selection']
        assert blocked_choice['distribution'] == selected['distribution']
    if slots:
        missing = deepcopy(value)
        for field in slots:
            missing['query'].pop(field)
        blocked = module.express(policy.select(missing))
        assert blocked['text'] is None and set(blocked['missing']) == set(slots)


def test_saved_extension_replays_offline_and_detects_tampering(tmp_path, monkeypatch):
    module, value = templates(), request()
    monkeypatch.setattr(socket.socket, 'connect', lambda *args: pytest.fail('Deterministic renderer used network'))
    for row in value['examples']:
        row['behavior'] = {'assistance': ['unspecified'], 'material': [], 'task_relation': 'same'}
    source, output = tmp_path / 'source', tmp_path / 'rendering'
    saved = policy.run(value, source)
    original = {p.name: p.read_bytes() for p in source.iterdir()}
    receipt = module.run(source, output)
    assert receipt['rendering']['text'] == 'can you help me with this?'
    assert policy.verify(output / 'policy') == saved
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original
    source.rename(tmp_path / 'moved-source')
    assert module.verify(output) == receipt
    with pytest.raises(FileExistsError):
        module.run(tmp_path / 'moved-source', output)
    path = output / 'rendering.json'
    changed = json.loads(path.read_text())
    changed['rendering']['text'] = 'invented different behavior'
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        module.verify(output)


def test_existing_patterns_and_unrenderable_states_keep_their_meaning():
    module, value = templates(), request()
    selected = policy.select(value)
    assert module.express(selected) == selected['rendering']
    for behavior in ({'assistance': [], 'material': [], 'task_relation': 'same'},
                     {'assistance': ['checking'], 'material': [], 'task_relation': None}):
        for row in value['examples']:
            row['behavior'] = behavior
        selected = policy.select(value)
        assert module.express(selected) == selected['rendering']
        assert module.express(selected)['text'] is None
