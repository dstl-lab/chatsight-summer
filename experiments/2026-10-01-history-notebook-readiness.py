"""Verify the frozen metadata export and count conservative notebook separation."""
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path('data/history-availability-v1')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def different_history(target, history):
    current = target['first_chat_notebook_id']
    if current is None:
        return []
    return [row for row in history if row['missing_notebook_events'] == 0
            and len(row['notebook_ids'] or []) == 1 and row['notebook_ids'][0] != current]


def check():
    target = dict(first_chat_notebook_id='a', notebook_ids=['a', 'b'])
    history = [dict(notebook_ids=ids, missing_notebook_events=missing)
               for ids, missing in [(['a'], 0), (['b'], 0), (['b'], 1), (['b', 'c'], 0), (None, 2)]]
    assert different_history(target, history) == [history[1]]
    assert different_history(dict(target, first_chat_notebook_id=None), history) == []


def analyze():
    plan_path, receipt_path = ROOT / 'notebook-plan.json', ROOT / 'notebooks.json'
    plan, receipt = [json.loads(p.read_text()) for p in (plan_path, receipt_path)]
    for name, expected in plan['source_sha256'].items():
        assert digest(name) == expected, name
    for key, path in (
        ('query_sha256', 'experiments/2026-10-01-history-notebooks.sql'),
        ('params_sha256', ROOT / 'notebook-params.json'),
        ('probe_sha256', '../episode-pilot/data/episode-pilot/notebook-context-v1/ingestion_probe.py'),
    ):
        assert receipt[key] == digest(path), key
    assert receipt['read_only'] is True
    rows = {r['conv_id']: r for r in receipt['rows']}
    requested = json.loads(json.loads((ROOT / 'notebook-params.json').read_text())['conversation_ids'])
    assert len(rows) == len(receipt['rows']) and set(rows) == set(requested)
    frozen = {r['conv_id']: r for r in json.loads(Path(
        'data/learner-linkage-recovery-v1/linkage.json').read_text())['rows']}
    fields = {'conv_id', 'chat_events', 'chat_start', 'chat_end', 'queries', 'responses',
              'notebook_ids', 'missing_notebook_events', 'first_chat_notebook_id',
              'first_chat_event_id', 'events', 'account_ids', 'missing_identity_events'}
    for cid, row in rows.items():
        assert set(row) == fields
        for key in ('events', 'queries', 'responses', 'missing_identity_events'):
            assert row[key] == frozen[cid][key], key
        assert set(row['account_ids']) == set(frozen[cid]['account_ids'])
        for key in ('chat_start', 'chat_end'):
            assert datetime.fromisoformat(row[key]) == datetime.fromisoformat(frozen[cid][key])
        assert row['queries'] + row['responses'] <= row['chat_events'] <= row['events']
        assert 0 <= row['missing_notebook_events'] <= row['chat_events']
        ids = row['notebook_ids'] or []
        assert ids == sorted(set(ids)) and all(re.fullmatch('[0-9a-f]{64}', n) for n in ids)
        assert row['first_chat_notebook_id'] is None or row['first_chat_notebook_id'] in ids
    cases = []
    for case in plan['cases']:
        target = rows[case['conv_id']]
        history = [rows[c] for c in case['query_bearing_history_ids']]
        different = different_history(target, history)
        cases.append(dict(account_id=case['account_id'], conv_id=case['conv_id'],
                          target_identity_missing=target['first_chat_notebook_id'] is None,
                          different_conversations=len(different),
                          different_queries=sum(r['queries'] for r in different),
                          distinct_earlier_notebooks=len({r['notebook_ids'][0] for r in different}),
                          ambiguous_history_conversations=sum(r['missing_notebook_events'] > 0 or len(r['notebook_ids'] or []) != 1 for r in history)))
    def count(predicate):
        subset = [r for r in cases if predicate(r)]
        return dict(accounts=len({r['account_id'] for r in subset}), conversations=len(subset))
    summary = dict(exported_conversations=len(rows), target_conversations=len(cases),
                   target_identity_missing=count(lambda r: r['target_identity_missing']),
                   any_ambiguous_history=count(lambda r: r['ambiguous_history_conversations'] > 0),
                   any_different_notebook_history=count(lambda r: r['different_conversations'] >= 1),
                   two_different_conversations_ten_queries=count(lambda r: r['different_conversations'] >= 2 and r['different_queries'] >= 10),
                   two_distinct_earlier_notebooks_ten_queries=count(lambda r: r['distinct_earlier_notebooks'] >= 2 and r['different_queries'] >= 10),
                   missing_identity_conversations=sum(r['missing_notebook_events'] > 0 for r in rows.values()),
                   multiple_identity_conversations=sum(len(r['notebook_ids'] or []) > 1 for r in rows.values()))
    paths = [Path(__file__), plan_path, receipt_path]
    return dict(source_sha256={str(p): digest(p) for p in paths}, summary=summary, cases=cases)


if __name__ == '__main__':
    check()
    if sys.argv[1:] == ['check']:
        print('First-event identity and missing/mixed-history checks passed.')
    else:
        result = analyze()
        output = ROOT / 'notebook-readiness.json'
        if sys.argv[1:] == ['verify']:
            assert json.loads(output.read_text()) == result
        else:
            assert not sys.argv[1:]
            with output.open('x') as stream:
                json.dump(result, stream, indent=2)
                stream.write('\n')
        print(json.dumps(result['summary'], indent=2))
