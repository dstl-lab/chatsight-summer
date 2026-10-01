"""Freeze metadata selection and input IDs without fetching any message content."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/cross-notebook-cards-v1'
AVAILABLE = ROOT / 'data/history-availability-v1'
RECOVERY = ROOT / 'data/learner-linkage-recovery-v1'
SQL = Path(__file__).with_name('2026-10-01-cross-notebook-events.sql')
PROBE = ROOT.parent / 'episode-pilot/data/episode-pilot/notebook-context-v1/ingestion_probe.py'
SEED = 'cross-notebook-cards-v1-20261001'


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def checked_pins(pins):
    for name, expected in pins.items():
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        if digest(path) != expected:
            raise ValueError(f'Source changed: {path.name}')


def pins(paths):
    return {str(Path(p).resolve()): digest(p) for p in paths}


def save(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def rank(kind, value):
    return sha256(f'{SEED}:{kind}:{value}'.encode()).hexdigest()


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp lacks timezone')
    return result


def event_key(row):
    return stamp(row['created_at']), row['id']


def notebook(row):
    values = row['notebook_ids'] or []
    if row['missing_notebook_events'] or len(values) != 1:
        raise ValueError('History notebook identity is missing or mixed')
    return values[0]


def history_ids(case, rows, excluded):
    target = rows[case['conv_id']]
    current = target['first_chat_notebook_id']
    if current is None:
        raise ValueError('Target starting notebook is missing')
    result = []
    for cid in case['query_bearing_history_ids']:
        row = rows[cid]
        if (cid not in excluded and row['queries'] > 0
                and row['account_ids'] == [case['account_id']]
                and stamp(row['chat_end']) < stamp(target['chat_start'])
                and row['missing_notebook_events'] == 0
                and len(row['notebook_ids'] or []) == 1
                and notebook(row) != current):
            result.append(cid)
    return sorted(result)


def select():
    paths = [AVAILABLE / name for name in ('notebook-readiness.json', 'notebook-plan.json',
             'notebooks.json', 'conversations.json')]
    readiness, plan, receipt, availability = map(read, paths)
    for record in (readiness, plan, availability):
        checked_pins(record['source_sha256'])
    old_selection = read(ROOT / 'data/course-account-checkpoints-v1/selection.json')
    checked_pins(old_selection['source_sha256'])
    exposure = read(RECOVERY / 'local-exposure.json')
    checked_pins(exposure['source_pins'])
    rows = {r['conv_id']: r for r in receipt['rows']}
    if len(rows) != len(receipt['rows']) or receipt['read_only'] is not True:
        raise ValueError('Invalid notebook metadata receipt')
    eligible_ids = {c['conv_id'] for c in readiness['cases']
                    if c['distinct_earlier_notebooks'] >= 2 and c['different_queries'] >= 10}
    candidates = [c for c in plan['cases'] if c['conv_id'] in eligible_ids]
    accounts = sorted({c['account_id'] for c in candidates}, key=lambda a: (rank('account', a), a))
    if len(accounts) != 72 or len(candidates) != 741 or len(eligible_ids) != 741:
        raise ValueError('Expected the frozen 72-account / 741-conversation pool')
    chosen = [min((c for c in candidates if c['account_id'] == a),
                  key=lambda c: (rank('conversation', c['conv_id']), c['conv_id'])) for a in accounts[:10]]
    excluded = {c['conv_id'] for c in chosen}
    cases = []
    for i, original in enumerate(chosen, 1):
        histories = history_ids(original, rows, excluded)
        cases.append({'id': f'cross-notebook-v1-{i:02}', 'account_id': original['account_id'],
                      'conv_id': original['conv_id'], 'history_conversation_ids': histories})
    requested = sorted(excluded | {h for c in cases for h in c['history_conversation_ids']})
    old_params = read(RECOVERY / 'linkage-params.json')
    params = {k: old_params[k] for k in ('salt', 'until')}
    params['conversation_ids'] = json.dumps(requested)
    source_paths = [*paths, RECOVERY / 'linkage.json', RECOVERY / 'linkage-params.json',
                    RECOVERY / 'local-exposure.json', ROOT / 'data/course-account-checkpoints-v1/selection.json',
                    Path(__file__), SQL, PROBE]
    selection = {'version': 1, 'seed': SEED, 'population': 'History-rich provisional course accounts',
                 'status': 'selected-before-event-metadata', 'cases': cases,
                 'window': {k: old_params[k] for k in ('start_at', 'end_at', 'until')},
                 'source_sha256': pins(source_paths)}
    OUT.mkdir(exist_ok=False)
    save(OUT / 'selection.json', selection)
    save(OUT / 'events-params.json', params)
    return {'selected_accounts': len(cases), 'requested_conversations': len(requested),
            'selection_sha256': digest(OUT / 'selection.json')}


def capped_queries(events, count):
    queries = [r for r in events if r['event_type'] == 'tutor_query']
    if not 2 <= count <= 20 or len(queries) < count:
        raise ValueError('Insufficient query count for fixed history sample')
    latest = {}
    for row in queries:
        key = row['notebook_id']
        if key is None:
            raise ValueError('Missing history notebook')
        if key not in latest or event_key(row) > event_key(latest[key]):
            latest[key] = row
    if len(latest) < 2:
        raise ValueError('Fewer than two earlier notebook identities')
    reserved = sorted(latest.values(), key=event_key, reverse=True)[:2]
    ids = {r['id'] for r in reserved}
    remaining = [r for r in sorted(queries, key=event_key, reverse=True) if r['id'] not in ids]
    selected = reserved + remaining[:count - 2]
    if len({r['id'] for r in selected}) != count:
        raise ValueError('Repeated event identity')
    return sorted(selected, key=event_key)


def checkpoint(case, events, window):
    ordered = sorted(events, key=lambda r: r['id'])
    candidates, prior_queries = [], 0
    for i, row in enumerate(ordered):
        if row['event_type'] != 'tutor_query':
            continue
        if (i and ordered[i - 1]['event_type'] == 'tutor_response' and prior_queries >= 2
                and stamp(window['start_at']) <= stamp(row['created_at']) < stamp(window['end_at'])):
            candidates.append((i, prior_queries))
        prior_queries += 1
    if not candidates:
        raise ValueError('Selected conversation has no structural checkpoint')
    i, prior_queries = min(candidates, key=lambda v: (
        rank('checkpoint', f"{case['conv_id']}:{ordered[v[0]]['id']}"), ordered[v[0]]['id']))
    target, prefix = ordered[i], ordered[:i]
    # Select first; an anomalous selected prefix must not be repaired or reranked.
    temporal_ok = all(event_key(a) <= event_key(b) for a, b in zip(ordered[:i + 1], ordered[1:i + 1]))
    return {'prefix_event_ids': [r['id'] for r in prefix], 'target_event_id': target['id'],
            'tutor_event_id': prefix[-1]['id'], 'prior_queries': prior_queries,
            'target_at': target['created_at']}, temporal_ok, len(candidates)


def metadata(selection, params, receipt):
    checked_pins(selection['source_sha256'])
    if receipt['read_only'] is not True or any(receipt[key] != digest(path) for key, path in (
        ('query_sha256', SQL), ('params_sha256', OUT / 'events-params.json'), ('probe_sha256', PROBE))):
        raise ValueError('Metadata receipt does not bind to the frozen query')
    expected = sorted({c['conv_id'] for c in selection['cases']} |
                      {h for c in selection['cases'] for h in c['history_conversation_ids']})
    if json.loads(params['conversation_ids']) != expected:
        raise ValueError('Requested conversation set changed')
    old_params = read(RECOVERY / 'linkage-params.json')
    if any(params[k] != old_params[k] for k in ('salt', 'until')):
        raise ValueError('Account salt or cutoff changed')
    notebooks = {r['conv_id']: r for r in read(AVAILABLE / 'notebooks.json')['rows']}
    grouped = defaultdict(list)
    seen = set()
    for row in receipt['rows']:
        if set(row) != {'id', 'event_type', 'created_at', 'conv_id', 'account_id', 'notebook_id'}:
            raise ValueError('Unexpected metadata field')
        if type(row['id']) is not int or row['id'] in seen or row['conv_id'] not in expected:
            raise ValueError('Duplicate or unrequested metadata event')
        seen.add(row['id'])
        if row['event_type'] not in ('tutor_query', 'tutor_response'):
            raise ValueError('Unexpected event type')
        saved = notebooks[row['conv_id']]
        if saved['account_ids'] != [row['account_id']] or notebook(saved) != row['notebook_id']:
            raise ValueError('Event account/notebook binding changed')
        if not stamp(saved['chat_start']) <= stamp(row['created_at']) <= stamp(saved['chat_end']) < stamp(params['until']):
            raise ValueError('Event outside frozen conversation times')
        grouped[row['conv_id']].append(row)
    if set(grouped) != set(expected):
        raise ValueError('Missing requested conversation')
    for cid, values in grouped.items():
        saved = notebooks[cid]
        counts = Counter(r['event_type'] for r in values)
        if counts['tutor_query'] != saved['queries'] or counts['tutor_response'] != saved['responses']:
            raise ValueError('Nonempty event counts changed')
        if len(values) == saved['chat_events']:
            first, last = min(values, key=event_key), max(values, key=event_key)
            if (stamp(first['created_at']) != stamp(saved['chat_start'])
                    or stamp(last['created_at']) != stamp(saved['chat_end'])
                    or first['id'] != saved['first_chat_event_id']):
                raise ValueError('Complete chat timestamps or first event changed')
    return grouped, notebooks


def freeze_result():
    selection, params, receipt = [read(OUT / name) for name in ('selection.json', 'events-params.json', 'events.json')]
    grouped, notebooks = metadata(selection, params, receipt)
    linkage = {r['conv_id']: r for r in read(RECOVERY / 'linkage.json')['rows']}
    targets = {c['conv_id'] for c in selection['cases']}
    cases, failures, pools = [], [], {}
    for chosen in selection['cases']:
        current = notebooks[chosen['conv_id']]
        boundary, temporal_ok, candidate_count = checkpoint(chosen, grouped[chosen['conv_id']], selection['window'])
        if candidate_count != linkage[chosen['conv_id']]['eligible_checkpoints']:
            raise ValueError('Structural checkpoint count changed')
        history = []
        for cid in chosen['history_conversation_ids']:
            prior = notebooks[cid]
            if (cid in targets or prior['account_ids'] != [chosen['account_id']]
                    or not stamp(prior['chat_end']) < stamp(current['chat_start'])
                    or notebook(prior) == current['first_chat_notebook_id']):
                raise ValueError('Selected history crosses its frozen boundary')
            history.extend(grouped[cid])
        query_count = sum(r['event_type'] == 'tutor_query' for r in history)
        sample = []
        try:
            if query_count < 10:
                raise ValueError('Fewer than ten historical queries')
            sample = capped_queries(history, min(20, query_count))
        except ValueError as error:
            failures.append({'id': chosen['id'], 'reason': str(error)})
        if not temporal_ok:
            failures.append({'id': chosen['id'], 'reason': 'Selected prefix has timestamp inversions; no reranking'})
        cases.append({k: chosen[k] for k in ('id', 'account_id', 'conv_id')} | boundary |
                     {'history_event_ids': [r['id'] for r in sample], 'donor_account_id': None,
                      'donor_history_event_ids': []})
        pools[chosen['account_id']] = history
    if not failures:
        for recipient in cases:
            current = notebooks[recipient['conv_id']]
            own_notebooks = {r['notebook_id'] for r in pools[recipient['account_id']]}
            choices = []
            for donor in cases:
                if donor['account_id'] == recipient['account_id']:
                    continue
                donor_target = notebooks[donor['conv_id']]['first_chat_notebook_id']
                available = [r for r in pools[donor['account_id']]
                             if stamp(notebooks[r['conv_id']]['chat_end']) < stamp(current['chat_start'])
                             and r['notebook_id'] not in (current['first_chat_notebook_id'], donor_target)]
                try:
                    sample = capped_queries(available, len(recipient['history_event_ids']))
                except ValueError:
                    continue
                donor_notebooks = {r['notebook_id'] for r in available}
                overlap = Fraction(len(own_notebooks & donor_notebooks), len(own_notebooks | donor_notebooks))
                choices.append((-overlap, rank('donor', f"{recipient['account_id']}:{donor['account_id']}"),
                                donor['account_id'], sample))
            if choices:
                _, _, donor_id, sample = min(choices, key=lambda choice: choice[:3])
                recipient.update(donor_account_id=donor_id, donor_history_event_ids=[r['id'] for r in sample])
    inputs = sorted({event for c in cases for key in ('prefix_event_ids', 'history_event_ids', 'donor_history_event_ids') for event in c[key]})
    references = sorted(c['target_event_id'] for c in cases)
    if set(inputs) & set(references):
        raise ValueError('Reference event leaked into input selection')
    result = {'version': 1, 'seed': SEED, 'status': 'unusable' if failures else 'frozen-before-content',
              'cases': cases, 'failures': failures, 'input_event_ids': inputs, 'reference_event_ids': references,
              'source_sha256': pins([OUT / name for name in ('selection.json', 'events-params.json', 'events.json')])}
    content_params = {k: params[k] for k in ('salt', 'until')} | {'event_ids': json.dumps(inputs)}
    return result, content_params


def check():
    def event(i, book, role='tutor_query', day=1):
        return dict(id=i, notebook_id=book, event_type=role, created_at=f'2026-03-{day:02}T00:00:00Z')
    sample = capped_queries([event(i, 'old' if i == 1 else 'recent', day=1 if i == 1 else 2)
                             for i in range(1, 31)], 20)
    assert len(sample) == 20 and len({r['notebook_id'] for r in sample}) == 2
    assert [r['id'] for r in sample] == [1, *range(12, 31)]
    rows = [event(1, 'a'), event(2, 'a', 'tutor_response'), event(3, 'a'),
            event(4, 'a', 'tutor_response'), event(5, 'a')]
    window = {'start_at': '2026-02-01T00:00:00Z', 'end_at': '2026-08-07T00:00:00Z'}
    frozen, valid, count = checkpoint({'conv_id': 'authored'}, rows, window)
    assert frozen['prefix_event_ids'] == [1, 2, 3, 4] and frozen['target_event_id'] == 5 and valid and count == 1
    rows[2]['created_at'] = '2026-03-02T00:00:00Z'
    invalid, valid, _ = checkpoint({'conv_id': 'authored'}, rows, window)
    assert invalid == frozen and not valid
    target = dict(first_chat_notebook_id='a', chat_start='2026-03-03T00:00:00Z')
    previous = dict(account_ids=['x'], queries=1, chat_end='2026-03-02T00:00:00Z', missing_notebook_events=0, notebook_ids=['b'])
    assert history_ids(dict(account_id='x', conv_id='target', query_bearing_history_ids=['prior', 'excluded']),
                       {'target': target, 'prior': previous, 'excluded': previous}, {'excluded'}) == ['prior']
    previous['chat_end'] = target['chat_start']
    assert history_ids(dict(account_id='x', conv_id='target', query_bearing_history_ids=['prior']),
                       {'target': target, 'prior': previous}, set()) == []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('check', 'select', 'freeze', 'verify'))
    args = parser.parse_args()
    check()
    if args.mode == 'check':
        print('Authored history-cap, notebook diversity, target exclusion and temporal checks passed.')
    elif args.mode == 'select':
        print(json.dumps(select(), indent=2))
    else:
        result, content_params = freeze_result()
        if args.mode == 'verify':
            if read(OUT / 'frozen.json') != result:
                raise ValueError('Frozen metadata does not reproduce')
            if not result['failures'] and read(OUT / 'content-params.json') != content_params:
                raise ValueError('Content parameters changed')
        else:
            save(OUT / 'frozen.json', result)
            if not result['failures']:
                save(OUT / 'content-params.json', content_params)
        print(json.dumps({'status': result['status'], 'cases': len(result['cases']),
                          'failures': result['failures'], 'input_events': len(result['input_event_ids']),
                          'references_unfetched': len(result['reference_event_ids']),
                          'available_donors': sum(c['donor_account_id'] is not None for c in result['cases'])}, indent=2))
