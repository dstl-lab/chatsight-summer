from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from src.eval.corpus_summary import build_report, summarize
from src.ingest.rawlog import Conversation, Turn
from src.labeling.episodes import _hash


def test_conversation_weighting_and_observation_boundaries():
    # Unequal conversation sizes must not become unequal person-level weights.
    def conversation(name, turns):
        return Conversation(conv_id=name, chatlog_id=1, notebook=None,
                            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                            turns=[Turn(index=i, **t) for i, t in enumerate(turns)])

    small = conversation('invented-small', [
        {'role': 'student', 'text': 'x' * 10},
        {'role': 'tutor', 'text': 'Can you check?'}])
    large = conversation('invented-large', [
        {'role': 'student', 'text': 'x' * 100, 'mode': 'chatgpt'},
        {'role': 'student', 'text': 'x' * 100},
        {'role': 'tutor', 'text': 'Can you check?'},
        {'role': 'student', 'text': 'x' * 100},
        {'role': 'tutor', 'text': 'Can you check?'}])
    result = summarize([small, large])
    assert result['counts'] == {'conversations': 2, 'student_messages': 4, 'tutor_messages': 3}
    assert result['characters']['message_weighted']['mean'] == 77.5
    assert result['characters']['conversation_weighted']['mean'] == 55
    assert result['characters']['message_weighted']['p50'] == 100
    assert result['characters']['conversation_weighted']['p50'] == 10
    assert result['literal_rates']['at_most_40_characters'] == {
        'message_weighted': 0.25, 'conversation_weighted': 0.5}
    assert result['student_modes'] == {'unknown': 3, 'chatgpt': 1}
    assert result['student_timestamp_missing'] == 4
    assert result['response_windows']['with_recorded_followup'] == 1
    assert result['response_windows']['without_recorded_followup'] == 2
    assert result['response_windows']['with_earlier_student_context'] == 1
    assert result['response_windows']['with_multi_message_followup'] == 0
    assert result['student_messages_per_conversation']['max'] == 3
    assert summarize([large, small]) == result
    with pytest.raises(ValueError, match='student messages'):
        summarize([])


def test_frozen_sources_and_library_filter(tmp_path):
    def write(name, value):
        (tmp_path / name).write_text(json.dumps(value))

    def digest(name):
        return sha256((tmp_path / name).read_bytes()).hexdigest()

    rows = [Conversation(conv_id=name, chatlog_id=i, notebook=None,
                         started_at=None, turns=[
                             Turn(index=0, role='student', text=f'invented request {i}'),
                             Turn(index=1, role='tutor', text='invented response'),
                             Turn(index=2, role='student', text='invented followup')])
            for i, name in enumerate(['PRIVATE-LIBRARY', 'PRIVATE-QUERY'])]
    library_key, query_key = [_hash(c.conv_id)[:16] for c in rows]
    write('inputs.json', {'train': [{'conversation_id': library_key}],
                          'queries': [{'conversation_id': query_key}]})
    write('report.json', {'counts': {'library_conversations': 1}, 'exclusions': {}})
    # Valid hashing must not entail decoding excluded query references.
    (tmp_path / 'references.json').write_text('INTENTIONALLY NOT JSON')

    def freeze():
        (tmp_path / 'conversations.jsonl').write_text(
            '\n'.join(c.model_dump_json() for c in rows))
        write('manifest.json', {'export_date': '2026-01-01'})
        write('snapshot-audit.json', {'canonical_snapshots': [{
            'snapshot_id': 'invented', 'conversations': 2, 'turns': 6,
            'canonical_conversations_path': str(tmp_path / 'conversations.jsonl'),
            'conversations_sha256': digest('conversations.jsonl'),
            'manifest_sha256': digest('manifest.json')}]})
        write('selection.json', {'conversations': {library_key: 'library', query_key: 'query'},
                                'source_hashes': {str(tmp_path / 'snapshot-audit.json'):
                                                  digest('snapshot-audit.json')}})
        write('receipt.json', {name: digest(name) for name in
                               ['inputs.json', 'selection.json', 'report.json', 'references.json']})

    freeze()
    result = build_report(tmp_path)
    assert result['development_library']['counts']['student_messages'] == 2
    assert result['inventory']['unique_conversations'] == 2
    assert 'PRIVATE-' not in json.dumps(result)
    rows[1].turns[2].text = 'QUERY_ONLY' * 1000
    freeze()  # An independently authored corpus with a different excluded target.
    changed = build_report(tmp_path)
    assert changed['development_library'] == result['development_library']
    assert 'QUERY_ONLY' not in json.dumps(changed)
    (tmp_path / 'inputs.json').write_text('{}')
    with pytest.raises(ValueError, match='Changed source: inputs.json'):
        build_report(tmp_path)
