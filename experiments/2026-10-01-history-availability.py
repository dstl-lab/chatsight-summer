"""Metadata-only inventory. Run from the worktree; results stay in ignored data/."""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible(rows):
    blocked = {
        account for row in rows for account in row['account_ids']
        if any(row[key] for key in ('exposed_account', 'known_diagnostic_account',
                                    'test_name_hint', 'explicit_test_marker',
                                    'missing_identity_events'))
        or len(row['account_ids']) != 1
    }
    return [row for row in rows if len(row['account_ids']) == 1
            and row['account_ids'][0] not in blocked and row['within_historical_window']]


def stamp(value):
    if value is None:
        return None
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert result.tzinfo is not None
    return result


def earlier(history, target):
    start = stamp(target['chat_start'])
    return [row for row in history if start is not None
            and row['conv_id'] != target['conv_id']
            and stamp(row['chat_end']) is not None and stamp(row['chat_end']) < start]


def check():
    base = dict(account_ids=['a'], exposed_account=False, known_diagnostic_account=False,
                test_name_hint=False, explicit_test_marker=False, missing_identity_events=0,
                within_historical_window=True, chat_start='2026-03-01T00:00:00Z')
    rows = [dict(base, conv_id='prior', chat_end='2026-02-28T23:59:59Z'),
            dict(base, conv_id='same-time', chat_end=base['chat_start']),
            dict(base, conv_id='missing', chat_end=None)]
    assert [r['conv_id'] for r in earlier(rows, dict(base, conv_id='target'))] == ['prior']
    assert eligible(rows + [dict(base, exposed_account=True)]) == []
    assert eligible([dict(base, account_ids=['a', 'b']), *rows]) == []
    assert eligible([dict(base, within_historical_window=False)]) == []


def inventory():
    root = Path('data/learner-linkage-recovery-v1')
    selection_path = Path('data/course-account-checkpoints-v1/selection.json')
    selection = json.loads(selection_path.read_text())
    sources = [root / name for name in ('linkage.json', 'candidate-accounts.json',
                                        'local-exposure.json', 'existing-split-linkage.json')]
    for path in sources:
        assert digest(path) == selection['source_sha256'][str(path.resolve())], path.name
    receipt = json.loads(sources[0].read_text())
    assert receipt['read_only'] is True
    all_rows = receipt['rows']
    assert len({r['conv_id'] for r in all_rows}) == len(all_rows)
    for row in all_rows:
        start, end = stamp(row['chat_start']), stamp(row['chat_end'])
        assert start is None or end is None or start <= end
    valid = eligible(all_rows)
    old = json.loads(sources[1].read_text())['conversations']
    assert {r['conv_id'] for r in valid if r['eligible_checkpoints'] > 0} == {
        r['conv_id'] for r in old}
    original_accounts = {a for r in old for a in r['account_ids']}
    excluded = {case['account_id'] for case in selection['cases']}
    assert len(excluded) == len(selection['cases']) and excluded <= original_accounts
    retained = original_accounts - excluded
    by_account = defaultdict(list)
    for row in valid:
        if row['account_ids'][0] in retained:
            by_account[row['account_ids'][0]].append(row)
    cases = []
    for account, history in sorted(by_account.items()):
        for target in sorted(history, key=lambda r: r['conv_id']):
            if target['eligible_checkpoints'] <= 0:
                continue
            prior = earlier(history, target)
            cases.append(dict(account_id=account, conv_id=target['conv_id'],
                              chat_start=target['chat_start'],
                              structural_checkpoints=target['eligible_checkpoints'],
                              prior_conversations=len(prior),
                              prior_queries=sum(r['queries'] for r in prior),
                              prior_conversation_ids=sorted(r['conv_id'] for r in prior)))
    summary = dict(original_accounts=len(original_accounts), excluded_accounts=len(excluded),
                   retained_accounts=len(retained), history_pool_conversations=sum(map(len, by_account.values())),
                   target_conversations=len(cases), structural_checkpoints=sum(r['structural_checkpoints'] for r in cases))
    def count(predicate):
        subset = [r for r in cases if predicate(r)]
        return dict(accounts=len({r['account_id'] for r in subset}), conversations=len(subset))
    summary['prior_conversations_at_least'] = {str(n): count(lambda r: r['prior_conversations'] >= n) for n in (1, 2, 5)}
    summary['prior_queries_at_least'] = {str(n): count(lambda r: r['prior_queries'] >= n) for n in (5, 10, 20)}
    summary['two_conversations_ten_queries'] = count(lambda r: r['prior_conversations'] >= 2 and r['prior_queries'] >= 10)
    summary['max_prior_conversations_per_account'] = {str(k): v for k, v in sorted(Counter(
        max(r['prior_conversations'] for r in cases if r['account_id'] == account)
        for account in retained).items())}
    summary['missing_times_in_history_pool'] = sum(r['chat_start'] is None or r['chat_end'] is None for rows in by_account.values() for r in rows)
    return dict(source_sha256={str(p): digest(p) for p in [*sources, selection_path, Path(__file__)]},
                summary=summary, cases=cases)


if __name__ == '__main__':
    check()
    if sys.argv[1:] == ['check']:
        print('Authored exclusion and cutoff checks passed.')
    else:
        result = inventory()
        output = Path('data/history-availability-v1/conversations.json')
        if sys.argv[1:] == ['verify']:
            assert json.loads(output.read_text()) == result
        else:
            assert not sys.argv[1:]
            output.parent.mkdir(exist_ok=True)
            with output.open('x') as stream:
                json.dump(result, stream, indent=2)
                stream.write('\n')
        print(json.dumps(result['summary'], indent=2))
