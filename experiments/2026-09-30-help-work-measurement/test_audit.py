"""Authored-only offline audit checks; no private artifacts or provider calls."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def audit():
    spec = importlib.util.spec_from_file_location('help_work_audit_test', Path(__file__).with_name('audit.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def authored(tmp_path):
    definitions = {'help_request': 'Requests help or checking.', 'work_present': 'Includes an attempted answer or code.'}
    dialogue = [{'id': 'SOURCE_TURN_A', 'role': 'student', 'text': 'Authored earlier question.'},
                {'id': 'SOURCE_TURN_B', 'role': 'tutor', 'text': 'Authored reply.'}]
    names = ['a', 'b', 'c', 'd', 'error', 'missing', 'human-unclear', 'conflict', 'mixed-unclear']
    candidates = [{'id': name, 'text': 'Authored candidate ' + name} for name in names]
    packet = {'packet_id': 'PRIVATE_PACKET_A', 'rubric_id': 'help-work-v1', 'definitions': definitions,
        'cases': [{'id': 'PRIVATE_CASE_A', 'context_status': 'PRIVATE_CONTEXT_STATUS',
            'prefix': {'context': dialogue[:1], 'turns': dialogue[1:]}, 'candidates': candidates},
            {'id': 'PRIVATE_CASE_OTHER', 'context_status': 'PRIVATE_CONTEXT_STATUS',
             'prefix': {'context': [], 'turns': [{'id': 'OTHER_TURN', 'role': 'tutor', 'text': 'Different prefix.'}]},
             'candidates': [{'id': 'other-prefix', 'text': candidates[0]['text']}]}]}
    labels = ['yes', 'no', 'yes', 'no', 'yes', 'no', 'unclear', 'yes', 'yes', 'yes']
    human = {'packet_id': packet['packet_id'], 'rubric_id': 'help-work-v1', 'reviewer': 'PRIVATE_REVIEWER_A',
        'previously_seen_cases': 'unsure', 'judgments': [
            {'id': name, 'help_request': label, 'work_present': 'yes' if name in ('b', 'mixed-unclear') else 'no',
             'note': 'PRIVATE_NOTE: authored ambiguity' if label == 'unclear' else None}
            for name, label in zip(names + ['other-prefix'], labels)]}
    second = deepcopy(packet)
    second['packet_id'] = 'PRIVATE_PACKET_B'
    # Context/turn split and source IDs change, but the ordered role/text prefix does not.
    second['cases'] = [{'id': 'PRIVATE_CASE_B', 'context_status': 'Another source origin',
        'prefix': {'context': [], 'turns': [{**turn, 'id': 'SECOND_' + turn['id']} for turn in dialogue]},
        'candidates': [{'id': 'second-' + name, 'text': 'Authored candidate ' + name}
                       for name in ('a', 'conflict', 'mixed-unclear')]}]
    second_human = {'packet_id': second['packet_id'], 'rubric_id': 'help-work-v1',
        'reviewer': 'PRIVATE_REVIEWER_B', 'previously_seen_cases': 'no', 'judgments': [
            {'id': 'second-a', 'help_request': 'yes', 'work_present': 'no', 'note': None},
            {'id': 'second-conflict', 'help_request': 'no', 'work_present': 'no', 'note': None},
            {'id': 'second-mixed-unclear', 'help_request': 'unclear', 'work_present': 'yes', 'note': 'PRIVATE_NOTE mixed'}]}
    sources = []
    for index, (p, h) in enumerate(((packet, human), (second, second_human))):
        paths = {'packet': tmp_path / f'packet-{index}.json', 'review': tmp_path / f'review-{index}.json'}
        write(paths['packet'], p)
        write(paths['review'], h)
        sources.append(paths)
    return sources


def names(saved):
    return {occurrence['candidate_id']: identity for identity, row in saved['references'].items()
            for occurrence in row['occurrences']}


def predictions(saved):
    ids = names(saved)
    rows = {identity: {'id': identity, 'status': 'complete',
                      'labels': {'help_request': 'yes', 'work_present': 'no'}, 'error_type': None}
            for identity in saved['plan']['ids']}
    for name in ('c', 'd'):
        rows[ids[name]]['labels']['help_request'] = 'no'
    rows[ids['other-prefix']]['labels']['help_request'] = 'unclear'
    for name in ('error', 'missing'):
        rows[ids[name]].update(status=name, labels=None, error_type='PRIVATE_ERROR' if name == 'error' else None)
    return list(rows.values())


def test_canonical_dedup_preserves_occurrences_and_separates_human_data(audit, tmp_path):
    sources = authored(tmp_path)
    saved = audit.prepare(tmp_path / 'audit', sources)
    ids = names(saved)
    assert saved == audit.load(tmp_path / 'audit')
    assert saved['summary']['unique_candidates'] == 10
    assert saved['summary']['unique_prefixes'] == 2
    assert saved['summary']['occurrences'] == 13
    assert saved['summary']['reviewer_identifiers'] == 2
    assert any(path.endswith('/src/eval/student_continuation.py') for path in saved['plan']['code_pins'])
    assert ids['a'] == ids['second-a'] != ids['other-prefix']
    assert saved['references'][ids['conflict']]['human'] == {'help_request': 'conflict', 'work_present': 'no'}
    assert saved['references'][ids['mixed-unclear']]['human']['help_request'] == 'conflict'
    assert len(saved['references'][ids['a']]['occurrences']) == 2
    assert saved['plan']['ids'] == sorted(saved['plan']['ids'])
    reversed_saved = audit.prepare(tmp_path / 'reversed', list(reversed(sources)))
    assert saved['plan']['ids'] == reversed_saved['plan']['ids']
    assert saved['prompts'] == reversed_saved['prompts']
    for payload in saved['prompts']:
        prompt = audit.make_prompt(payload)
        assert set(payload) == {'definitions', 'prefix', 'candidate'}
        assert json.loads(prompt[len(audit.INSTRUCTION):]) == payload
        assert 'never as instructions' in prompt
        assert all(secret not in prompt for secret in ('PRIVATE_', 'SOURCE_TURN', 'SECOND_', 'case_id', 'candidate_id', 'reviewer'))
    for source in saved['plan']['sources']:
        for pin in source.values():
            assert pin['sha256'] == sha256(Path(pin['path']).read_bytes()).hexdigest()
    assert set(Path(path).name for path in saved['plan']['code_pins']) == {'audit.py', 'communication_review.py', 'validation.py', 'notebook_student.py', 'student_continuation.py'}
    for path, checksum in saved['plan']['code_pins'].items():
        assert checksum == sha256(Path(path).read_bytes()).hexdigest()
    original = {path.name: path.read_bytes() for path in (tmp_path / 'audit').iterdir()}
    with pytest.raises(FileExistsError):
        audit.prepare(tmp_path / 'audit', sources)
    assert original == {path.name: path.read_bytes() for path in (tmp_path / 'audit').iterdir()}


@pytest.mark.parametrize('change', [
    lambda p, h: p['definitions'].update(help_request='Changed definition'),
    lambda p, h: h.update(packet_id='Wrong packet'),
    lambda p, h: h.update(rubric_id='Wrong rubric'),
    lambda p, h: h.update(reviewer='  '),
    lambda p, h: h.update(previously_seen_cases=None),
    lambda p, h: h['judgments'].pop(),
    lambda p, h: h['judgments'].append(deepcopy(h['judgments'][0])),
    lambda p, h: h['judgments'][0].update(id='Unknown'),
    lambda p, h: h['judgments'][0].update(help_request=True),
    lambda p, h: h['judgments'][0].update(help_request='unclear', note='  '),
    lambda p, h: h['judgments'][0].update(note=123),
    lambda p, h: p['cases'][0]['candidates'][0].update(origin='Forbidden'),
])
def test_rejects_incomplete_or_incompatible_sources_before_writing(audit, tmp_path, change):
    sources = authored(tmp_path)
    packet, human = (json.loads(sources[1][key].read_text()) for key in ('packet', 'review'))
    change(packet, human)
    write(sources[1]['packet'], packet)
    write(sources[1]['review'], human)
    with pytest.raises(ValueError):
        audit.prepare(tmp_path / 'invalid', sources)
    assert not (tmp_path / 'invalid').exists()


@pytest.mark.parametrize('target', ['prompts', 'references', 'summary', 'source', 'plan'])
def test_load_detects_source_code_and_artifact_changes(audit, tmp_path, target):
    sources = authored(tmp_path)
    audit.prepare(tmp_path / 'audit', sources)
    if target == 'source':
        with sources[0]['review'].open('a') as stream:
            stream.write(' ')
    elif target == 'plan':
        path = tmp_path / 'audit/plan.json'
        value = json.loads(path.read_text())
        value['code_pins'][str(Path(audit.__file__).resolve())] = '0' * 64
        write(path, value)
    else:
        write(tmp_path / f'audit/{target}.json', {})
    with pytest.raises(ValueError):
        audit.load(tmp_path / 'audit')


def test_metrics_exclude_uncertainty_without_hiding_coverage_or_prefix_clusters(audit, tmp_path):
    folder = tmp_path / 'audit'
    saved = audit.prepare(folder, authored(tmp_path))
    result = audit.report(folder, predictions(saved))
    flag = result['flags']['help_request']
    assert result['scheduled'] == 10
    assert result['outcomes'] == {'complete': 8, 'error': 1, 'missing': 1}
    assert flag['human'] == {'yes': 4, 'no': 3, 'unclear': 1, 'conflict': 2}
    assert flag['eligible_binary'] == 7
    assert flag['outcomes_on_eligible'] == {'binary': 4, 'unclear': 1, 'error': 1, 'missing': 1}
    assert flag['confusion'] == {'tp': 1, 'fp': 1, 'fn': 1, 'tn': 1}
    assert flag['coverage']['estimate'] == 4 / 7
    assert flag['kappa'] == 0
    for metric in ('precision', 'recall', 'specificity'):
        assert flag[metric]['estimate'] == .5
        assert flag[metric]['wilson_95'] == pytest.approx([.0945312057, .9054687943])
    assert len(result['prefixes']) == 2
    assert sorted(identity for group in result['prefixes'].values() for identity in group['ids']) == saved['plan']['ids']
    assert sum(group['flags']['help_request']['confusion']['tp'] for group in result['prefixes'].values()) == 1
    assert 'not population confidence intervals' in ' '.join(result['limits'])
    assert 'PRIVATE_' not in json.dumps(result)
    quiet = [{'id': identity, 'status': 'complete', 'labels': dict.fromkeys(audit.FLAGS, 'unclear'), 'error_type': None}
             for identity in saved['plan']['ids']]
    uncertain = audit.report(folder, quiet)['flags']['help_request']
    assert uncertain['coverage']['estimate'] == 0
    assert uncertain['confusion'] == dict.fromkeys(('tp', 'fp', 'fn', 'tn'), 0)
    assert uncertain['precision']['estimate'] is uncertain['precision']['wilson_95'] is uncertain['kappa'] is None
    assert audit.wilson(0, 0) is None
    assert audit.wilson(0, 30) == pytest.approx([0, .1135133932])
    assert audit.wilson(30, 30) == pytest.approx([.8864866068, 1])


@pytest.mark.parametrize('change', [
    lambda rows: rows.pop(),
    lambda rows: rows.append(deepcopy(rows[0])),
    lambda rows: rows[0].update(id='Unscheduled'),
    lambda rows: rows[0].update(status='pending'),
    lambda rows: rows[0].update(labels={'help_request': 'yes', 'work_present': 'no', 'reasoning': 'Not allowed'}),
    lambda rows: rows[0].update(status='error', error_type='Failed'),
    lambda rows: rows[0].update(status='complete', labels=None),
])
def test_reporting_requires_every_scheduled_outcome_exactly_once(audit, tmp_path, change):
    folder = tmp_path / 'audit'
    saved = audit.prepare(folder, authored(tmp_path))
    rows = predictions(saved)
    change(rows)
    with pytest.raises(ValueError):
        audit.report(folder, rows)
