"""Only invented text; tests packet boundaries, not human judgments."""
import importlib.util
import json
from pathlib import Path
from copy import deepcopy
import pytest
from tests.test_behavior_evidence import packet


def module():
    assert importlib.util.find_spec('src.eval.assistance_review'), 'Review exporter is missing'
    from src.eval import assistance_review
    return assistance_review


def fixture():
    raw=packet();raw['records']=raw['records'][:1]
    # Keep valid supplied source metadata for this wholly synthetic test.
    raw['events']=raw['events'][:3]
    return raw


def test_prefix_hides_outcome_labels_and_identifiers_and_preserves_sources():
    api,raw=module(),fixture()
    before=deepcopy(raw)
    raw['events'][1]['text']='FUTURE SECRET'
    from src.agents import behavior_evidence
    raw['events'][1]['sha256']=behavior_evidence.event_digest(raw['events'][1])
    initial=deepcopy(raw)
    built=api.prepare(raw)
    prefix=json.dumps(built['prefix']);outcome=json.dumps(built['outcome'])
    assert 'FUTURE SECRET' not in prefix and 'FUTURE SECRET' in outcome
    assert 'synthetic-complete' not in prefix and 'annotations' not in prefix
    assert 'coder' not in outcome and 'last_assistance' not in prefix
    assert raw==initial
    assert built['prefix']['cases'][0]['id']==built['outcome']['cases'][0]['id']
    assert all(t['role']!='execution' for t in built['prefix']['cases'][0]['turns'])
    assert built['prefix']['cases'][0]['turns'][-1]['role']=='student'
    assert built['mapping']['cases'][0]['source_record_id']==before['records'][0]['id']
    for stage in ('prefix','outcome'):
        response=api.blank(built[stage])
        assert response['reviewer_alias'] is None
        assert all(r['status'] is None and r['labels'] is None and r['evidence']==[] for r in response['judgments'])


def test_redaction_safe_embedding_and_create_only_export(tmp_path):
    api,raw=module(),fixture()
    from src.agents import behavior_evidence
    raw['events'][0]['text']='Write to student@example.com at https://example.com/secret </script><img src=x onerror=alert(1)>'
    raw['events'][0]['sha256']=behavior_evidence.event_digest(raw['events'][0])
    built=api.prepare(raw)
    output=tmp_path/'review'
    api.write(built,output)
    html=(output/'01-prefix.html').read_text()
    assert 'student@example.com' not in html and 'https://example.com/secret' not in html
    assert '[EMAIL REDACTED]' in html and '[URL REDACTED]' in html
    assert '</script><img' not in html
    assert "connect-src 'none'" in html
    assert (output/'02-outcome.html').exists()
    with pytest.raises(FileExistsError):api.write(built,output)
    assert (output/'private-mapping.json').exists()


def test_packet_binding_changes_when_displayed_text_changes():
    api,raw=module(),fixture()
    from src.agents import behavior_evidence
    first=api.prepare(raw)
    raw['events'][0]['text']='Please explain this.'
    raw['events'][0]['sha256']=behavior_evidence.event_digest(raw['events'][0])
    second=api.prepare(raw)
    assert first['prefix']['packet_id']!=second['prefix']['packet_id']
    assert first['outcome']['prefix_packet_id']==first['prefix']['packet_id']


def test_rejected_or_reserved_record_cannot_be_exported():
    api,raw=module(),fixture()
    raw['reserved_accounts'].append(raw['records'][0]['account_id'])
    with pytest.raises(ValueError):api.prepare(raw)
