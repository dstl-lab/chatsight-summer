"""The pilot reuses source validation; check its new list and task boundaries."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('behavior_pilot', Path(__file__).parents[1] / 'experiments/2026-10-01-behavior-pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def selection(expected, data):
    current = [{'turn_id': 'message', 'line': n} for n, line in enumerate(data['message'].splitlines(), 1) if line.strip()]
    return {field: dict(judgment, evidence=current +
            ([{'turn_id': 'p2', 'line': 1}] if judgment['basis'] == 'preceding_context' else []))
            for field, judgment in expected.items()}


def test_authored_contract_preserves_overlap_context_and_uncertainty():
    for data, expected in pilot.authored():
        result = pilot.materialize(data, selection(expected, data))
        for field in pilot.FIELDS:
            assert {k: result[field][k] for k in ('value', 'basis')} == expected[field]
            assert any(e['turn_id'] == 'message' for e in result[field]['evidence'])
    # A bare answer is not automatically an expressed checking request.
    assert pilot.authored()[0][1]['assistance']['value'] == []
    assert pilot.authored()[2][1]['material']['basis'] == 'preceding_context'
    assert pilot.authored()[3][1]['material']['value'] is None


@pytest.mark.parametrize('mutation', [
    lambda x: x['assistance'].update(value=['hint', 'hint']),
    lambda x: x['assistance'].update(value=['personality']),
    lambda x: x['material'].update(value=None, basis='message_only'),
    lambda x: x['task_relation'].update(basis='message_only'),
    lambda x: x['task_relation'].update(value='unclear'),
    lambda x: x['assistance']['evidence'].append({'turn_id': 'future', 'line': 1}),
    lambda x: x['assistance']['evidence'].pop(),
    lambda x: x.update(origin='recorded'),
])
def test_invalid_labels_evidence_and_absence_are_rejected(mutation):
    data = {'prefix': [{'role': 'student', 'text': 'Q1'}, {'role': 'tutor', 'text': 'Q1'}],
            'message': 'Thanks.\nI will try it.'}
    expected = {'assistance': {'value': [], 'basis': 'message_only'},
                'material': {'value': [], 'basis': 'message_only'},
                'task_relation': {'value': 'same', 'basis': 'preceding_context'}}
    value = selection(expected, data)
    mutation(value)
    with pytest.raises(ValueError):
        pilot.materialize(data, value)


def test_reconstructs_quotes_without_mutating_source_or_accepting_future():
    data, expected = pilot.authored()[7]
    values = selection(expected, data)
    original = deepcopy((data, values))
    observation = pilot.materialize(data, values)
    assert observation['material']['value'] == ['diagnostic', 'work']
    assert observation['material']['evidence'][0]['quote'] == data['message'].splitlines()[0]
    assert (data, values) == original
    with pytest.raises(ValueError):
        pilot.materialize(dict(data, future='Not permitted'), values)


def test_report_retains_coder_disagreement_and_unresolved_in_denominator(tmp_path):
    data, expected = pilot.authored()[0]
    mapping = [{'id': f'{origin}-{i}', 'case': i, 'origin': origin, 'data': data}
               for origin in ('recorded', 'generated') for i in range(1, 11)]
    mapping += [{'id': f'authored-{i}', 'case': i, 'origin': 'authored', 'data': d, 'expected': e}
                for i, (d, e) in enumerate(pilot.authored(), 1)]
    pilot.save(tmp_path / 'mapping.json', mapping)
    pilot.save(tmp_path / 'plan.json', {'source_sha256': {str(tmp_path / 'mapping.json'): pilot.digest(tmp_path / 'mapping.json')}})
    annotations = [{'id': r['id'], 'judgments': selection(r.get('expected', expected), r['data'])} for r in mapping]
    pilot.save(tmp_path / 'coder-a.json', annotations)
    changed = deepcopy(annotations)
    changed[0]['judgments']['material'].update(value=None, basis='unresolved')
    pilot.save(tmp_path / 'coder-b.json', changed)
    result = pilot.report(tmp_path)
    assert result['agreement']['material']['matched'] == 19
    assert result['agreement']['material']['total'] == 20
    assert result['counts']['coder-b']['recorded']['material'] == {'unclear': 1, 'work': 9}
    assert result['authored']['coder-a']['assistance']['values_match'] == 8
    changed.pop()
    (tmp_path / 'coder-b.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='exactly'):
        pilot.report(tmp_path)
