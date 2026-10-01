"""Reverify exposed policy evidence without recoding, dispatch or holdout target reads."""
import argparse
from collections import Counter
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile

from src.labeling.episodes import _hash

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/policy-evidence-audit-v1/audit.json'
FIELDS = ('assistance', 'material', 'task_relation')


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pins_checked(pins):
    require(all(digest(path) == pin for path, pin in pins.items()), 'An evidence source hash changed.')


def excluded(groups, reserved):
    require(all(account for group in groups for account in group), 'Unknown account linkage.')
    require(not set().union(*groups) & reserved, 'A development account overlaps the reserved holdout.')


def module(name):
    path = ROOT / 'experiments' / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def pilot(frozen):
    """Bind existing assistant judgments to the same already-exposed recorded events."""
    runner = module('2026-10-01-behavior-pilot.py')
    folder, examples, study = (ROOT / 'data' / name for name in
        ('behavior-pilot-v1', 'behavior-examples-v1', 'cross-notebook-cards-v1'))
    result = runner.report(folder)  # Pure validator; never invoke the writing CLI.
    require(result == read(folder / 'report.json'), 'Frozen pilot report changed.')
    mapping, packet = read(folder / 'mapping.json'), read(folder / 'packet.json')
    require(packet == {'rubric_id': runner.SEED, 'instructions': runner.RULES,
        'schema': runner.Selection.model_json_schema(), 'items': sorted([
            {'id': row['id'], 'sources': runner.sources._sources(runner.sources.Input.model_validate(row['data']))}
            for row in mapping], key=lambda row: row['id'])}, 'Pilot packet does not reconstruct.')
    findings, receipt = read(examples / 'findings.json'), read(examples / 'events.json')
    pins = {str((ROOT / name).resolve()): pin for name, pin in findings['source_sha256'].items()}
    pins.update(read(folder / 'plan.json')['source_sha256'])
    pins.update({str((ROOT / name).resolve()): pin for name, pin in frozen['source_sha256'].items()})
    pins_checked(pins)
    probe = ROOT.parent / 'episode-pilot/data/episode-pilot/notebook-context-v1/ingestion_probe.py'
    require(receipt['read_only'] is True
        and receipt['params_sha256'] == digest(examples / 'params.json')
        and receipt['query_sha256'] == digest(ROOT / 'experiments/2026-10-01-cross-notebook-content.sql')
        and receipt['probe_sha256'] == digest(probe), 'Database receipt bindings changed.')
    events = {row['id']: row for row in receipt['rows']}
    old = {row['id']: row for name in ('content.json', 'reference-content.json')
           for row in read(study / name)['rows']}
    require(len(events) == len(receipt['rows']) == 134
        and set(events) == set(json.loads(read(examples / 'params.json')['event_ids']))
        and all(old[key] == row for key, row in events.items()), 'Saved database recheck differs.')
    cases = {row['id']: row for row in frozen['cases']}
    queries = read(study / 'prepared/inputs.json')['queries']
    refs = {row['id']: row for row in read(study / 'references.json')}
    recorded = {row['case']: row for row in mapping if row['origin'] == 'recorded'}
    require(len(cases) == len(queries) == len(recorded) == 10
        and set(events) == {eid for case in cases.values()
            for eid in [*case['prefix_event_ids'], case['target_event_id']]}, 'Pilot cohort changed.')
    coders = {name: {row['id']: row['judgments'] for row in read(folder / f'{name}.json')}
              for name in ('coder-a', 'coder-b')}
    rows = []
    for alias, query in enumerate(queries, 1):
        case, item = cases[query['id']], recorded[alias]
        target = events[case['target_event_id']]
        prefix = [{'role': 'student' if events[eid]['event_type'] == 'tutor_query' else 'tutor',
                   'text': events[eid]['text']} for eid in case['prefix_event_ids']]
        require(target['event_type'] == 'tutor_query'
            and target['conv_id'] == case['conv_id'] == query['conversation_id'] == refs[query['id']]['conversation_id']
            and target['account_id'] == case['account_id'] == query['student_id']
            and target['text'] == item['data']['message'] == refs[query['id']]['text']
            and prefix == query['prefix'] == item['data']['prefix']
            and case['target_event_id'] not in case['prefix_event_ids']
            and all(events[eid]['conv_id'] == case['conv_id'] and events[eid]['account_id'] == case['account_id']
                    for eid in case['prefix_event_ids']), 'Recorded target or prefix linkage changed.')
        rows.append({'id': item['id'], 'case_alias': alias, 'origin': 'recorded', 'label_origin': 'assistant',
            'account_id': case['account_id'], 'conversation_id': _hash(case['conv_id'])[:16],
            'event_id': target['id'], 'event_sha256': canonical(target), 'prefix_sha256': canonical(prefix),
            'judgments': {name: values[item['id']] for name, values in coders.items()},
            'permitted_uses': ['Source-linked qualitative examples', 'Exploratory assistant-label disagreement'],
            'not_established': ['Human label accuracy', 'Policy-training admission', 'Population frequencies']})
    example_refs = 0
    for example in findings['examples']:
        case = frozen['cases'][example['case_alias'] - 1]
        student_ids = [eid for eid in [*case['prefix_event_ids'], case['target_event_id']]
                       if events[eid]['event_type'] == 'tutor_query']
        for position, eid, pin in zip(example['student_positions'], example['event_ids'], example['event_sha256'], strict=True):
            require(student_ids[position - 1] == eid and canonical(events[eid]) == pin, 'Illustrative source changed.')
            example_refs += 1
    agreement = {}
    for field in FIELDS:
        values = [pair['observations']['recorded'] for pair in result['pairs']]
        agreement[field] = {'matched': sum(row['coder-a'][field]['value'] == row['coder-b'][field]['value'] for row in values),
            'total': 10, 'unknowns': {name: sum(row[name][field]['value'] in (None, 'unclear') for row in values)
                                    for name in coders},
            'counts': {name: result['counts'][name]['recorded'][field] for name in coders}}
    paths = [Path(runner.__file__), probe, *[folder / name for name in
        ('plan.json', 'coder-a.json', 'coder-b.json', 'report.json')], examples / 'findings.json',
        study / 'prepared/inputs.json']
    pins.update({str(path.resolve()): digest(path) for path in paths})
    joint = sum(all(row['coder-a'][field]['value'] == row['coder-b'][field]['value']
                    for field in FIELDS) for row in values)
    resolved = sum(all(row['coder-a'][field]['value'] == row['coder-b'][field]['value']
                      and row['coder-a'][field]['value'] not in (None, 'unclear')
                      for field in FIELDS) for row in values)
    return rows, {'recorded_labels': agreement, 'recorded_joint_agreement': joint,
                  'recorded_joint_resolved_agreement': resolved, 'database_events': 134,
                  'illustrative_entries': len(findings['examples']), 'illustrative_event_refs': example_refs}, pins


def collect():
    # Only account/conversation metadata is examined until both cohorts clear this guard.
    human_path = ROOT / 'data/real-policy-calibration-v2/inputs.json'
    frozen_path = ROOT / 'data/cross-notebook-cards-v1/frozen.json'
    selection_path = ROOT / 'data/context-work-holdout-v1/selection.json'
    metadata_paths = (human_path, frozen_path, selection_path)
    pins = {str(path): digest(path) for path in metadata_paths}
    historical, frozen, reserved = map(read, metadata_paths)
    human_accounts = {row['account_id'] for row in historical['observations']}
    pilot_accounts = {row['account_id'] for row in frozen['cases']}
    reserved_accounts = {row['account_id'] for row in reserved['cases']}
    require(len(historical['observations']) == 16 and len(human_accounts) == 15
        and len(frozen['cases']) == len(pilot_accounts) == 10 and len(reserved_accounts) == 24, 'Metadata coverage changed.')
    excluded((human_accounts, pilot_accounts), reserved_accounts)
    calibration = module('2026-10-01-real-policy-calibration.py')
    human = calibration.collect()
    require(human == historical, 'The sixteen saved calibration inputs no longer reproduce.')
    rows, checks, pilot_pins = pilot(frozen)
    require({row['account_id'] for row in rows} == pilot_accounts, 'Inspected pilot differs from guarded metadata.')
    pins.update(human['provenance']['source_sha256'])
    pins.update(pilot_pins)
    pins[str(Path(__file__).resolve())] = digest(__file__)
    human_rows = [dict(row, permitted_uses=['Source-bound human help/work development reference'],
        not_established=['Richer assistance/material/task labels', 'Population frequencies', 'Notebook actions'])
        for row in human['observations']]
    human_conversations = {row['conversation_id'] for row in human_rows}
    pilot_conversations = {row['conversation_id'] for row in rows}
    summary = {'human_messages': len(human_rows), 'human_accounts': len(human_accounts),
        'pilot_messages': len(rows), 'pilot_accounts': len(pilot_accounts),
        'cohort_account_overlap': len(human_accounts & pilot_accounts),
        'cohort_conversation_overlap': len(human_conversations & pilot_conversations),
        'union_accounts': len(human_accounts | pilot_accounts), 'reserved_accounts': len(reserved_accounts),
        'reserved_account_overlap': 0, 'human_help': dict(Counter(row['help_request'] for row in human_rows)),
        'human_work': dict(Counter(row['work_present'] for row in human_rows)), **checks}
    pins_checked(pins)
    return {'version': 1, 'summary': summary, 'human_rows': human_rows, 'assistant_rows': rows,
        'source_sha256': dict(sorted(pins.items())),
        'limits': ['Course accounts are not independently verified persons.',
            'Both cohorts are selected, previously exposed development data.',
            'Assistant agreement is not human accuracy; unresolved original judgments remain unchanged.',
            'No labels, contexts, personas, or probabilities were inferred or converted.',
            'Authored-only policy admission is unchanged; no recorded examples were promoted into it.',
            'Only reserved holdout selection metadata was read, never holdout messages or judgments.']}


def self_check():
    excluded(({'development'},), {'reserved'})
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'source'
        path.write_text('original')
        pins = {str(path): digest(path)}
        pins_checked(pins)
        path.write_text('changed')
        for check in (lambda: pins_checked(pins), lambda: excluded(({'reserved'},), {'reserved'})):
            try:
                check()
            except ValueError:
                continue
            raise AssertionError('Audit guard accepted changed evidence or a reserved account.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify', 'self-check'))
    args = parser.parse_args()
    if args.command == 'self-check':
        self_check()
        print('Source-change and reserved-account guards passed.')
        return
    if args.command == 'run':
        require(not OUT.exists(), 'Audit output already exists; use verify.')
    else:
        pins_checked(read(OUT)['source_sha256'])
    audit = collect()
    if args.command == 'run':
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open('x') as stream:
            json.dump(audit, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    else:
        require(read(OUT) == audit, 'Saved evidence audit differs from its recomputation.')
    print(json.dumps({'status': args.command, 'summary': audit['summary'], 'source_pins': len(audit['source_sha256'])}))


if __name__ == '__main__':
    main()
