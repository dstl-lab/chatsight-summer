"""Authored probability checks; no empirical calibration or generated replies."""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.agents import behavior_policy as policy
from tests.test_behavior_policy import request


def module():
    assert importlib.util.find_spec('src.agents.behavior_distribution'), 'Distribution-only interface is missing'
    from src.agents import behavior_distribution
    return behavior_distribution


def test_pure_repeatable_probabilities_without_sampling_rendering_or_io(monkeypatch):
    api, value = module(), request()
    original = deepcopy(value)
    def forbidden(*args, **kwargs):
        pytest.fail('Distribution prediction sampled, rendered or accessed files')
    monkeypatch.setattr(policy, 'select', forbidden)
    monkeypatch.setattr(policy.random, 'Random', forbidden)
    monkeypatch.setattr(policy, '_render', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    result = api.predict_distribution(value)
    assert value == original
    assert result == api.predict_distribution(value)
    value['seed'] = 99
    value['examples'].reverse()
    assert result == api.predict_distribution(value)
    assert result['status'] == 'available'
    assert not {'selection', 'rendering', 'seed'} & result.keys()
    assert {tuple(r['behavior']['assistance']): r['fraction'] for r in result['distribution']} == {
        ('hint',): '1/3', ('checking',): '2/3'}
    assert sum(Fraction(r['fraction']) for r in result['distribution']) == 1
    assert sum(r['probability'] for r in result['distribution']) == pytest.approx(1)
    assert {r['id']: r['weight'] for r in result['examples']} == {'a1': '1/6', 'a2': '1/6', 'a3': '1/6', 'b1': '1/2'}


@pytest.mark.parametrize('mode', ['exact', 'fallback', 'unknown', 'insufficient', 'excluded', 'joint'])
def test_same_distribution_and_evidence_as_original_selector(mode):
    api, value = module(), request()
    if mode == 'fallback':
        value['query']['context']['last_assistance'] = []
    elif mode == 'unknown':
        value['query']['context']['last_assistance'] = None
    elif mode == 'insufficient':
        value['examples'] = value['examples'][:3]
    elif mode == 'excluded':
        for i, origin in enumerate(('recorded', 'generated', 'assistant-labeled')):
            row = deepcopy(value['examples'][0])
            row.update(id=f'x{i}', source_ref=f'x{i}', origin=origin)
            value['examples'].append(row)
        value['examples'][1]['behavior']['material'] = None
        value['examples'][2]['account_id'] = value['query']['account_id']
    elif mode == 'joint':
        for row in value['examples']:
            row['behavior'] = {'assistance': ['hint', 'explanation'], 'material': ['work', 'diagnostic'], 'task_relation': 'different'}
    before = policy._receipt(value)
    predicted = api.predict_distribution(value)
    for key in ('query', 'matching', 'weighting', 'counts', 'examples', 'distribution', 'limits'):
        assert predicted[key] == before['result'][key]
    assert policy._receipt(value) == before
    for seed in (0, 4, 19):
        value['seed'] = seed
        selected = policy.select(value)
        assert selected['distribution'] == predicted['distribution']
    if mode in ('fallback', 'unknown'):
        assert predicted['matching']['pool'] == 'broader-fallback'
        assert 'Fewer than two accounts' in predicted['matching']['reason']
    if mode == 'insufficient':
        assert predicted['status'] == 'insufficient-evidence'
        assert predicted['distribution'] == []
    if mode == 'excluded':
        assert {r['id'] for r in predicted['examples'] if r['included']} == {'a1', 'b1'}


@pytest.mark.parametrize('invalid', ['duplicate', 'future', 'seed'])
def test_validation_keeps_existing_input_contract(invalid):
    api, value = module(), request()
    if invalid == 'duplicate':
        value['examples'][1]['source_ref'] = value['examples'][0]['source_ref']
    elif invalid == 'future':
        value['query']['recorded_next_message'] = 'target'
    else:
        value['seed'] = True
    with pytest.raises(ValueError):
        api.predict_distribution(value)


def test_report_binds_context_input_and_sources_and_cli_is_read_only(tmp_path):
    api, value = module(), request()
    report = api.report(value)
    assert report['version'] == 1
    assert report['input_sha256'] == sha256(policy._json(policy.Request.model_validate(value).model_dump()).encode()).hexdigest()
    assert report['context_sha256'] == sha256(policy._json(value['query']['context']).encode()).hexdigest()
    assert report['sources']['behavior_policy.py'] == sha256(Path(policy.__file__).read_bytes()).hexdigest()
    assert report['sources']['behavior_distribution.py'] == sha256(Path(api.__file__).read_bytes()).hexdigest()
    value['query']['context']['feedback'] = 'fail'
    assert api.report(value)['context_sha256'] != report['context_sha256']
    path = tmp_path / 'authored.json'
    path.write_text(json.dumps(value))
    before = path.read_bytes()
    command = [sys.executable, '-m', 'src.agents.behavior_distribution', str(path)]
    assert json.loads(subprocess.check_output(command, text=True)) == api.report(value)
    markdown = subprocess.check_output([*command, '--format', 'markdown'], text=True)
    assert '1/3' in markdown and '2/3' in markdown
    assert 'broader-fallback' in markdown and 'a1' in markdown
    assert 'not measured student behavior' in markdown
    assert path.read_bytes() == before and list(tmp_path.iterdir()) == [path]
