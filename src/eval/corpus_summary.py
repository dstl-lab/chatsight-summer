"""Offline, aggregate-only description of the existing development library.

Usage: python -m src.eval.corpus_summary BASELINE_DIR OUTPUT.json
OUTPUT is create-only. No query references, labels, DB, or model are consumed.
"""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from math import ceil
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.episodes import _episodes, _hash


def distribution(groups, *, equal_conversations=False):
    values = sorted((value, Fraction(1, len(group)) if equal_conversations else Fraction(1))
                    for group in groups for value in group)
    if not values:
        return {'mean': None, 'min': None, 'max': None,
                **{f'p{p}': None for p in (25, 50, 75, 90, 95)}}
    total = sum(weight for _, weight in values)
    result = {'mean': float(sum(value * weight for value, weight in values) / total),
              'min': values[0][0], 'max': values[-1][0]}
    for percentile in (25, 50, 75, 90, 95):
        accumulated = Fraction(0)
        for value, weight in values:
            accumulated += weight
            if accumulated >= total * Fraction(percentile, 100):
                result[f'p{percentile}'] = value
                break
    return result


def metadata(conversations):
    students = [t for c in conversations for t in c.student_turns]
    turns = [t for c in conversations for t in c.turns]
    starts = [c.started_at.date().isoformat() for c in conversations if c.started_at]
    return {
        'counts': {'conversations': len(conversations), 'student_messages': len(students),
                   'tutor_messages': len(turns) - len(students)},
        'conversation_start_dates': {'min': min(starts) if starts else None,
                                     'max': max(starts) if starts else None,
                                     'missing': len(conversations) - len(starts)},
        'conversation_start_months': dict(sorted(Counter(d[:7] for d in starts).items())),
        'notebook_metadata_missing': sum(not c.notebook for c in conversations),
        'turn_timestamp_missing': sum(t.at is None for t in turns),
        'student_timestamp_missing': sum(t.at is None for t in students),
        'student_modes': dict(Counter(t.mode or 'unknown' for t in students)),
    }


def summarize(conversations):
    groups = [c.student_turns for c in conversations]
    if not groups or any(not group for group in groups):
        raise ValueError('Every included conversation must have student messages.')
    lengths = [[len(t.text) for t in group] for group in groups]
    counts = [len(group) for group in groups]
    predicates = {
        'at_most_40_characters': lambda s: len(s) <= 40,
        '41_to_300_characters': lambda s: 40 < len(s) <= 300,
        'over_300_characters': lambda s: len(s) > 300,
        'contains_newline': lambda s: '\n' in s,
        'contains_backtick': lambda s: '`' in s,
        'contains_non_ascii': lambda s: not s.isascii(),
        'blank_after_stripping': lambda s: not s.strip(),
    }
    rates = {}
    for name, predicate in predicates.items():
        flags = [[int(predicate(t.text)) for t in group] for group in groups]
        rates[name] = {label: distribution(flags, equal_conversations=equal)['mean']
                       for label, equal in [('message_weighted', False), ('conversation_weighted', True)]}
    windows = [ep for c in conversations for ep in _episodes(c, {})]
    follows = [[t for t in ep['turns'] if t['phase'] == 'followup'] for ep in windows]
    earlier = [sum(t['role'] == 'student' for t in ep['context']) for ep in windows]
    top_n = ceil(len(groups) / 10)
    return {
        **metadata(conversations),
        'student_messages_per_conversation': distribution([counts]),
        'characters': {label: distribution(lengths, equal_conversations=equal)
                       for label, equal in [('message_weighted', False), ('conversation_weighted', True)]},
        'literal_rates': rates,
        'concentration': {'largest_tenth_conversations': top_n,
                          'student_message_share': sum(sorted(counts, reverse=True)[:top_n]) / sum(counts)},
        'response_windows': {
            'total': len(windows), 'with_recorded_followup': sum(bool(f) for f in follows),
            'without_recorded_followup': sum(not f for f in follows),
            'with_multi_message_followup': sum(len(f) > 1 for f in follows),
            'with_earlier_student_context': sum(n > 0 for n in earlier),
            'earlier_student_messages_in_six_turn_context': dict(sorted(Counter(earlier).items())),
        },
    }


def build_report(baseline):
    baseline = Path(baseline).resolve()
    pins = {}

    def checked(path, expected=None):
        path = Path(path)
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError(f'Changed source: {path.name}')
        pins[str(path)] = digest
        return raw

    receipt = json.loads(checked(baseline / 'receipt.json'))
    # Hash old evidence without parsing query targets or re-running the baseline.
    for name, digest in receipt.items():
        checked(baseline / name, digest)
    selection = json.loads(checked(baseline / 'selection.json'))
    old_report = json.loads(checked(baseline / 'report.json'))
    inputs = json.loads(checked(baseline / 'inputs.json'))
    library_keys = {row['conversation_id'] for row in inputs['train']}
    query_keys = {row['conversation_id'] for row in inputs['queries']}
    if not library_keys or library_keys & query_keys:
        raise ValueError('Empty library or overlapping conversation split.')
    for key in library_keys:
        if selection['conversations'].get(key) != 'library':
            raise ValueError('Library selection mismatch.')
    for path, digest in selection['source_hashes'].items():
        checked(path, digest)
    audits = [p for p in selection['source_hashes'] if Path(p).name == 'snapshot-audit.json']
    if len(audits) != 1:
        raise ValueError('Expected one pinned canonical-snapshot audit.')
    audit = json.loads(checked(audits[0]))
    conversations, dialogue_hashes, owners, variants = {}, {}, {}, {}
    sources = []
    for entry in sorted(audit['canonical_snapshots'], key=lambda row: row['snapshot_id']):
        path = Path(entry['canonical_conversations_path'])
        manifest = json.loads(checked(path.parent / 'manifest.json', entry['manifest_sha256']))
        rows = [Conversation.model_validate_json(line) for line in
                checked(path, entry['conversations_sha256']).splitlines() if line.strip()]
        if len(rows) != entry['conversations'] or len({c.conv_id for c in rows}) != len(rows):
            raise ValueError('Invalid snapshot conversation counts.')
        if sum(len(c.turns) for c in rows) != entry['turns']:
            raise ValueError('Invalid snapshot turn counts.')
        before = len(conversations)
        for c in rows:
            key = _hash(c.conv_id)[:16]
            if [t.index for t in c.turns] != list(range(len(c.turns))):
                raise ValueError('Non-contiguous turn indexes.')
            dialogue = _hash([(t.index, t.role, t.text) for t in c.turns])
            if key in conversations and (conversations[key].conv_id != c.conv_id or dialogue_hashes[key] != dialogue):
                raise ValueError('Conflicting conversation identity or dialogue.')
            if owners.setdefault(dialogue, key) != key:
                raise ValueError('Identical dialogue across conversation IDs.')
            dialogue_hashes[key] = dialogue
            variants.setdefault(key, set()).add(_hash(c.model_dump(mode='json')))
            conversations[key] = c
        sources.append({'snapshot_id': entry['snapshot_id'], 'export_date': manifest['export_date'],
                        'conversations': len(rows), 'turns': entry['turns'],
                        'new_conversation_ids_in_sorted_order': len(conversations) - before,
                        'has_authored_course_profile': 'course_profile' in manifest})
    if set(conversations) != set(selection['conversations']):
        raise ValueError('Corpus identity set changed.')
    if len(library_keys) != old_report['counts']['library_conversations']:
        raise ValueError('Development library count changed.')
    library = [conversations[key] for key in sorted(library_keys)]
    summary = summarize(library)
    if summary['response_windows']['with_recorded_followup'] != len(inputs['train']):
        raise ValueError('Library response-window count changed.')
    for path in [Path(__file__), Path(__file__).parents[1] / 'ingest/rawlog.py',
                 Path(__file__).parents[1] / 'labeling/episodes.py',
                 Path(__file__).parents[1] / 'labeling/qref.py']:
        checked(path)
    return {
        'scope': 'Previously exposed saved exports; fresh text statistics use only the existing development library.',
        'method': 'Raw Unicode character counts. Quantiles use the inverse empirical CDF. Equal-conversation weights give each message 1 / messages-in-its-conversation.',
        'sources': sources,
        'inventory': {'snapshot_records': sum(s['conversations'] for s in sources),
                      'unique_conversations': len(conversations),
                      'duplicate_memberships': sum(s['conversations'] for s in sources) - len(conversations),
                      'metadata_variant_conversations': sum(len(v) > 1 for v in variants.values()),
                      'dialogue_conflicts': 0,
                      'existing_split_assignments': dict(Counter(selection['conversations'].values())),
                      'existing_usable_library_conversations': len(library_keys),
                      'existing_usable_query_conversations': len(query_keys),
                      'prior_baseline_exclusions': old_report['exclusions']},
        'all_conversation_metadata': metadata(list(conversations.values())),
        'development_library': summary,
        'source_hashes': pins,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline_dir', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve the existing report; use a new output path.')
    report = build_report(args.baseline_dir)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(f'Wrote aggregate report: {args.output}')


if __name__ == '__main__':
    main()
