"""Synthetic fixtures test admission boundaries, never real student evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


def module():
    assert importlib.util.find_spec('src.agents.behavior_evidence'), 'Evidence adapter is missing'
    from src.agents import behavior_evidence
    return behavior_evidence


def packet():
    return json.loads((Path(__file__).parents[1] / 'docs/examples/behavior-evidence-synthetic.json').read_text())


def test_synthetic_complete_partial_and_rejected_records():
    api = module()
    result = api.admit(packet())
    rows = {r['id']: r for r in result['records']}
    assert rows['complete']['status'] == 'accepted'
    assert rows['complete']['joint_fit']['ready_for_protocol_review']
    assert rows['partial']['status'] == 'partial'
    assert rows['partial']['targets']['material']['candidate_reference']
    assert not rows['partial']['targets']['assistance']['candidate_reference']
    assert rows['leaked']['status'] == 'rejected'
    assert 'target-in-prefix' in rows['leaked']['issues']
    assert all(not r['joint_fit']['eligible'] for r in rows.values())
    assert all(not t['empirical_reference'] for r in rows.values() for t in r['targets'].values())
    assert result['synthetic'] is True


def test_pure_repeatability_no_mutation_and_target_is_not_context(monkeypatch):
    api, value = module(), packet()
    original = deepcopy(value)
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('Admission read filesystem'))
    first = api.admit(value)
    assert first == api.admit(value) and value == original
    row = first['records'][0]
    assert 'outcome' not in row['prefix_context']
    assert 'text' not in row['prefix_context']


@pytest.mark.parametrize('kind,reason', [
    ('hash', 'source-hash-mismatch'), ('account', 'event-account-mismatch'),
    ('time', 'prefix-after-cutoff'), ('target_time', 'target-not-after-cutoff'),
    ('overlap', 'account-partition-overlap'), ('reserved', 'reserved-account'),
    ('exposed', 'test-account-exposed'), ('context_target', 'context-uses-nonprefix-evidence'),
    ('outcome_evidence', 'outcome-missing-target-evidence'),
])
def test_rejects_leakage_overlap_and_invalid_provenance(kind, reason):
    api, value = module(), packet()
    value['records'] = [value['records'][0]]
    row = value['records'][0]
    if kind == 'hash':
        value['events'][0]['sha256'] = '0' * 64
    elif kind in ('account', 'time', 'target_time'):
        event = value['events'][1 if kind == 'target_time' else 0]
        event['account_id' if kind == 'account' else 'timestamp'] = 'other' if kind == 'account' else ('2026-09-01T12:01:00Z' if kind == 'time' else '2026-09-01T11:59:00Z')
        event['sha256'] = api.event_digest(event)
    elif kind == 'overlap':
        value['test_accounts'].append(row['account_id'])
    elif kind == 'reserved':
        value['reserved_accounts'].append(row['account_id'])
    elif kind == 'exposed':
        value['development_accounts'].remove(row['account_id'])
        value['test_accounts'].append(row['account_id'])
        value['exposed_accounts'].append(row['account_id'])
        row['membership'] = 'test'
    elif kind == 'context_target':
        row['context'][0]['evidence_event_ids'] = [row['outcome_event_id']]
    else:
        row['annotations'][0]['evidence_event_ids'] = row['prefix_event_ids']
    found = api.admit(value)['records'][0]
    assert found['status'] == 'rejected' and reason in found['issues']
    assert not any(t['candidate_reference'] for t in found['targets'].values())


def test_assistant_disagreement_and_coarse_rubric_are_not_promoted():
    api, value = module(), packet()
    value['records'] = [value['records'][0]]
    row = value['records'][0]
    row['annotations'][0]['origin'] = 'assistant'
    row['annotations'].append(dict(row['annotations'][0], coder='second', value=['solution']))
    row['annotations'].append({'field': 'work_present', 'value': True, 'rubric': 'help-work-v1',
        'origin': 'human', 'coder': 'reviewer', 'evidence_event_ids': [row['outcome_event_id']]})
    result = api.admit(value)['records'][0]
    assert result['targets']['assistance']['status'] == 'disputed'
    assert not result['targets']['assistance']['candidate_reference']
    assert result['targets']['work_present']['candidate_reference']
    assert result['annotations'] == row['annotations']
    assert not result['joint_fit']['ready_for_protocol_review']
    row['annotations'][1]['rubric'] = 'help-work-v1'
    assert api.admit(value)['records'][0]['targets']['material']['status'] == 'incompatible-rubric'


def test_missing_context_and_partial_outcome_do_not_fabricate_joint_labels():
    api, value = module(), packet()
    row = value['records'][0]
    row['context'] = []
    row['annotations'][2]['value'] = None
    result = api.admit(value)['records'][0]
    assert result['targets']['assistance']['candidate_reference']
    assert result['targets']['task_relation']['status'] == 'unknown'
    assert result['prefix_context']['last_assistance']['status'] == 'missing'
    assert not result['joint_fit']['ready_for_protocol_review']
    assert result['student_eligibility'] == 'not-assessed'


def test_invalid_schema_and_unaware_timestamps_fail_closed():
    api, value = module(), packet()
    value['records'][0]['cutoff'] = '2026-09-01T12:00:00'
    with pytest.raises(ValueError):
        api.admit(value)
    value = packet()
    value['records'][0]['annotations'][0]['value'] = ['invented-label']
    with pytest.raises(ValueError):
        api.admit(value)


def test_report_bindings_and_readonly_cli(tmp_path):
    api, value = module(), packet()
    result = api.report(value)
    assert result['source_sha256'] == sha256(Path(api.__file__).read_bytes()).hexdigest()
    assert result['input_sha256'] == sha256(api.canonical(value).encode()).hexdigest()
    path = tmp_path / 'input.json'
    path.write_text(json.dumps(value))
    command = [sys.executable, '-m', 'src.agents.behavior_evidence', str(path)]
    assert json.loads(subprocess.check_output(command, text=True)) == result
    text = subprocess.check_output([*command, '--format', 'markdown'], text=True)
    assert 'SYNTHETIC' in text and 'partial' in text and 'target-in-prefix' in text
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('kind,issue', [
    ('feedback', 'feedback-not-revision-bound'), ('origin', 'nonrecorded-content'),
    ('missing', 'missing-source-event'), ('conversation', 'event-conversation-mismatch'),
    ('unknown_account', 'unknown-account'), ('synthetic', 'synthetic-source-in-recorded-packet'),
])
def test_additional_admission_boundaries(kind, issue):
    api, value = module(), packet()
    row = value['records'][0]
    if kind == 'feedback':
        row['revision_sha256'] = 'b' * 64
    elif kind == 'origin':
        value['events'][1]['origin'] = 'generated'
        value['events'][1]['sha256'] = api.event_digest(value['events'][1])
    elif kind == 'missing':
        row['prefix_event_ids'].append('missing-event')
    elif kind == 'conversation':
        value['events'][0]['conversation_id'] = 'another-conversation'
        value['events'][0]['sha256'] = api.event_digest(value['events'][0])
    elif kind == 'unknown_account':
        row['account_id'] = None
    else:
        value['synthetic'] = False
    result = api.admit(value)['records'][0]
    assert issue in result['issues'] and result['status'] == 'rejected'


def test_source_references_are_visible_and_assistant_only_stays_exploratory():
    api, value = module(), packet()
    row = value['records'][0]
    row['annotations'][0]['origin'] = 'assistant'
    result = api.admit(value)['records'][0]
    source = result['source_bindings'][row['outcome_event_id']]
    assert source['source_ref'] == 'synthetic:complete-target'
    assert source['sha256'] == value['events'][1]['sha256']
    assert result['targets']['assistance']['status'] == 'exploratory-only'
    assert not result['targets']['assistance']['candidate_reference']
    assert result['targets']['material']['candidate_reference']
    assert result['status'] == 'partial'


def test_test_membership_can_support_reference_but_never_joint_fitting():
    api, value = module(), packet()
    row = value['records'][0]
    row['membership'] = 'test'
    value['development_accounts'].remove(row['account_id'])
    value['test_accounts'].append(row['account_id'])
    result = api.admit(value)['records'][0]
    assert result['targets']['material']['candidate_reference']
    assert not result['joint_fit']['ready_for_protocol_review']
    assert 'test-record-never-fit' in result['joint_fit']['reasons']


def test_last_student_assistance_cannot_be_supported_only_by_tutor_turn():
    api, value = module(), packet()
    # The source is intact and before cutoff, but it is the wrong speaker.
    value['events'][0]['kind'] = 'tutor'
    value['events'][0]['sha256'] = api.event_digest(value['events'][0])
    row = api.admit(value)['records'][0]
    assert row['status'] == 'rejected'
    assert 'context-assistance-missing-student-evidence' in row['issues']
    assert not row['joint_fit']['ready_for_protocol_review']


def test_coarse_human_observations_remain_usable_without_fine_outcomes_or_context():
    api, value = module(), packet()
    row = value['records'][0]
    row['context'] = []
    row['annotations'] = [dict(field=field, value=val, origin='human', coder='original-reviewer',
        rubric='help-work-v1', evidence_event_ids=[row['outcome_event_id']])
        for field, val in [('help_requested', True), ('work_present', False)]]
    result = api.admit(value)['records'][0]
    assert result['status'] == 'partial'
    assert {k for k, v in result['targets'].items() if v['candidate_reference']} == {'help_requested', 'work_present'}
    assert all(result['targets'][f]['status'] == 'missing' for f in ('assistance','material','task_relation'))
    assert not result['joint_fit']['eligible']
