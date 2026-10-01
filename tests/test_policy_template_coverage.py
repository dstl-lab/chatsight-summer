"""Authored labels protect uncertainty, exact bundles and missing-input reporting."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import markdown


def test_coverage_preserves_unknowns_disagreements_and_required_inputs():
    path = Path(__file__).parents[1] / 'experiments/2026-10-02-policy-template-coverage.py'
    assert path.is_file(), 'The recorded-pattern coverage comparison is missing'
    spec = importlib.util.spec_from_file_location('policy_template_coverage', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def labels(assistance, material, task):
        return {field: {'value': value} for field, value in
                zip(('assistance', 'material', 'task_relation'), (assistance, material, task))}

    hint = labels(['hint'], [], 'same')
    absent = labels([], [], 'same')
    unknown = labels(None, [], 'same')
    work = labels(['checking'], ['work'], 'same')
    changed_task = labels(['hint'], [], 'different')
    multi = labels(['hint', 'explanation'], [], 'same')
    unclear_task = labels(['checking'], [], 'unclear')
    rows = [{'case_alias': i, 'judgments': {'coder-a': a, 'coder-b': b}}
            for i, (a, b) in enumerate([(hint, hint), (absent, unknown), (work, work),
                                        (changed_task, changed_task), (multi, multi),
                                        (unclear_task, unclear_task)], 1)]
    before = deepcopy(rows)
    result = module.compare(rows)
    assert rows == before
    assert result['by_coder'] == {
        'coder-a': {'template-present': 3, 'template-missing': 2, 'unresolved-labels': 1},
        'coder-b': {'template-present': 3, 'template-missing': 1, 'unresolved-labels': 2}}
    assert result['agreed_resolved'] == {
        'messages': 4, 'template-present': 3, 'template-missing': 1}
    compared = result['rows']
    assert compared[1]['coders']['coder-a']['status'] == 'template-missing'
    assert compared[1]['coders']['coder-b']['status'] == 'unresolved-labels'
    assert compared[1]['coders']['coder-b']['behavior']['assistance'] is None
    assert compared[2]['coders']['coder-a']['template']['required_inputs'] == ['work']
    assert compared[3]['coders']['coder-a']['template']['required_inputs'] == ['next_task']
    assert compared[4]['coders']['coder-a']['behavior']['assistance'] == ['explanation', 'hint']
    assert not compared[1]['labels_agree']
    assert compared[5]['labels_agree'] and compared[5]['coders']['coder-a']['unknown_fields'] == ['task_relation']
    assert all('text' not in row['coders']['coder-a'] for row in compared)

    # Raw HTML containers must not turn recorded text into active markup.
    attack = '<img src=x onerror="attack()"><script>attack()</script>'
    for row in result['rows']:
        row['source'] = {'message': attack, 'prefix': [{'role': 'student', 'text': attack}],
                         'audit_id': 'authored-test', 'event_id': 1}
    result['templates'] = []
    rendered = markdown.Markdown(extensions=['fenced_code', 'tables']).convert(
        module.markdown({'result': result, 'limits': []}))
    assert '<img ' not in rendered and '<script>' not in rendered
    assert '&lt;img ' in rendered and '&lt;script&gt;' in rendered
