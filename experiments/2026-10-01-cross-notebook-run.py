"""One frozen cross-notebook history-card comparison; no retries or resume."""
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
from statistics import mean

from src.agents import notebook_student as store

LEGACY = Path(__file__).resolve().parent / '2026-09-29-course-account-history'
CONDITIONS = ('generic', 'matched', 'other-account')


def module(name):
    spec = importlib.util.spec_from_file_location('cross_notebook_' + name, LEGACY / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


protocol, transport, scoring = (module(name) for name in ('protocol', 'run', 'report'))


def required_pins():
    modules = (protocol, transport, scoring, store, protocol.chat_student,
               protocol.retrieval_baseline, protocol.student_continuation,
               protocol.corpus_summary, protocol.episodes, protocol.llm, protocol.tutor_moves)
    return {str(Path(path).resolve()): transport.file_hash(path)
            for path in [__file__, *(m.__file__ for m in modules)]}


def inputs(folder, expected_plan, expected_prompts):
    folder = Path(folder)
    if (transport.file_hash(folder / 'plan.json') != expected_plan or
            transport.file_hash(folder / 'prompts.json') != expected_prompts):
        raise ValueError('Frozen preparation changed')
    plan, bank = store._read(folder / 'plan.json'), store._read(folder / 'prompts.json')
    if (transport.file_hash(plan['input_path']) != plan['input_sha256'] or
            transport.version('google-genai') != plan['sdk_version'] or
            any(plan['code_pins'].get(p) != h for p, h in required_pins().items()) or
            any(transport.file_hash(p) != h for p, h in plan['code_pins'].items())):
        raise ValueError('Frozen source, implementation, or SDK changed')
    data = store._read(Path(plan['input_path']))
    queries = [protocol.retrieval_baseline.Query.model_validate(q).model_dump() for q in data['queries']]
    ids = [q['id'] for q in queries]
    if (len(ids) != 10 or any(len({q[k] for q in queries}) != 10 for k in ('id', 'student_id', 'conversation_id'))
            or any(q['student_id'] is None for q in queries) or [c['id'] for c in plan['cases']] != ids
            or any(set(data[k]) != set(ids) for k in ('history', 'cards', 'donors'))
            or any(not data['history'][i] or any(not isinstance(t, str) or not t.strip()
                   for t in data['history'][i]) for i in ids)
            or any(d is not None and (not isinstance(d, str) or not d) for d in data['donors'].values())
            or any(d is not None and d not in {q['student_id'] for q in queries} for d in data['donors'].values())
            or any(data['donors'][q['id']] == q['student_id'] for q in queries)):
        raise ValueError('Expected ten distinct cases with bound history and donor availability')
    schema = protocol.student_continuation.Continuation.model_json_schema()
    config = dict(plan['configuration'])
    schema_value = config.pop('response_json_schema', None) if 'response_json_schema' in config else config.pop('response_schema', None)
    if (schema_value != schema or config != {'temperature': 1.0, 'max_output_tokens': 8192,
            'response_mime_type': 'application/json'} or plan['model'] != 'gemini-2.5-pro'
            or plan['timeout_ms'] != 120000 or any(plan[k] != 1 for k in ('workers', 'sdk_attempts', 'adapter_attempts'))):
        raise ValueError('Unexpected model or request configuration')
    expected = {(i, c, d) for i in ids for c in CONDITIONS
                if c != 'other-account' or data['donors'][i] is not None for d in range(1, 6)}
    schedule = plan['schedule']
    if (plan['requests'] != len(expected) or len(schedule) != len(expected)
            or [s['slot'] for s in schedule] != list(range(1, len(expected) + 1))
            or {(s['case_id'], s['condition'], s['draw']) for s in schedule} != expected):
        raise ValueError('Fixed 100–150 request schedule changed')
    prompts = {(r['case_id'], r['condition']): r['prompt'] for r in bank}
    hashes = {f'{i}:{c}': protocol.sha256(p.encode()).hexdigest() for (i, c), p in prompts.items()}
    if (len(bank) != len(prompts) or set(prompts) != {(i, c) for i, c, _ in expected}
            or hashes != plan['prompt_hashes'] or any(not r['prompt'] or len(r['prompt']) > protocol.PROMPT_LIMIT
               or r['prompt_sha256'] != hashes[f"{r['case_id']}:{r['condition']}"] for r in bank)):
        raise ValueError('Prompt bank differs from frozen schedule')
    return plan, prompts, data


def execute(folder, expected_plan, expected_prompts, generate, *, progress=True):
    folder = Path(folder)
    plan, prompts, _ = inputs(folder, expected_plan, expected_prompts)
    out = folder / 'execution'
    out.mkdir(exist_ok=False)
    (out / 'receipts').mkdir()
    (out / 'raw').mkdir()
    store._save(out / 'started.json', {'plan_sha256': expected_plan, 'prompts_sha256': expected_prompts,
        'started_at': transport.now(), 'code_pins': required_pins(), 'authorization': {
            'user_request': "Let's continue", 'standing_preference': 'Project continuation and Gemini runs approved 2026-09-11.',
            'scope': plan['stopping_rule']}}, exclusive=True)
    counts = Counter()
    for slot in plan['schedule']:
        prompt = prompts[slot['case_id'], slot['condition']]
        receipt = dict(slot, status='pending', started_at=transport.now(), plan_sha256=expected_plan,
                       prompt_sha256=protocol.sha256(prompt.encode()).hexdigest())
        path = out / 'receipts' / f"{slot['slot']:03d}.json"
        store._save(path, receipt, exclusive=True)
        try:
            raw = generate(plan, prompt)
        except Exception as error:
            receipt.update(status='error', error_type=type(error).__name__)
        else:
            raw_file = f"raw/{slot['slot']:03d}.json"
            store._save(out / raw_file, raw, exclusive=True)
            receipt.update(raw_file=raw_file, raw_sha256=transport.file_hash(out / raw_file))
            store._save(path, receipt)
            try:
                receipt.update(status='complete', parsed=transport.parse_response(raw))
            except (ValueError, TypeError, AttributeError) as error:
                receipt.update(status='error', error_type=type(error).__name__)
        receipt['finished_at'] = transport.now()
        store._save(path, receipt)
        counts[receipt['status']] += 1
        if progress:
            print(json.dumps({'slot': slot['slot'], 'scheduled': plan['requests'], 'status': receipt['status']}), flush=True)
    result = {'finished_at': transport.now(), 'scheduled': plan['requests'], 'complete': counts['complete'],
        'errors': counts['error'], 'receipt_sha256': {f"receipts/{s['slot']:03d}.json":
        transport.file_hash(out / 'receipts' / f"{s['slot']:03d}.json") for s in plan['schedule']}}
    store._save(out / 'completed.json', result, exclusive=True)
    return result


def read_receipts(folder):
    folder = Path(folder)
    out = folder / 'execution'
    started = store._read(out / 'started.json')
    plan, _, data = inputs(folder, started['plan_sha256'], started['prompts_sha256'])
    if started['code_pins'] != required_pins():
        raise ValueError('Dispatch implementation changed')
    completed = store._read(out / 'completed.json') if (out / 'completed.json').exists() else None
    records, ended = [], False
    expected_paths = {f"{s['slot']:03d}.json" for s in plan['schedule']}
    if any(p.name not in expected_paths for p in (out / 'receipts').iterdir()):
        raise ValueError('Unexpected receipt')
    for slot in plan['schedule']:
        relative = f"receipts/{slot['slot']:03d}.json"
        path = out / relative
        if not path.exists():
            ended = True
            records.append(dict(slot, status='not-attempted'))
            continue
        r = store._read(path)
        if (ended or any(r.get(k) != v for k, v in slot.items()) or r['plan_sha256'] != started['plan_sha256']
                or r['prompt_sha256'] != plan['prompt_hashes'][f"{r['case_id']}:{r['condition']}"]
                or r['status'] not in ('complete', 'error', 'pending')
                or (r['status'] != 'pending' and r['finished_at'] < r['started_at'])):
            raise ValueError('Receipt chronology or binding changed')
        ended = r['status'] == 'pending'
        if 'raw_file' in r:
            if r['raw_file'] != f"raw/{slot['slot']:03d}.json" or transport.file_hash(out / r['raw_file']) != r['raw_sha256']:
                raise ValueError('Provider response changed')
            if r['status'] != 'pending':
                try:
                    parsed = transport.parse_response(store._read(out / r['raw_file']))
                except (ValueError, TypeError, AttributeError):
                    if r['status'] != 'error':
                        raise ValueError('Invalid provider output accepted') from None
                else:
                    if r['status'] != 'complete' or r.get('parsed') != parsed:
                        raise ValueError('Parsed result differs from raw response')
        elif r['status'] == 'complete':
            raise ValueError('Accepted output lacks raw response')
        if r['status'] != 'complete' and ('parsed' in r or (r['status'] == 'error' and not r.get('error_type'))):
            raise ValueError('Invalid failure or pending disposition')
        if completed and transport.file_hash(path) != completed['receipt_sha256'][relative]:
            raise ValueError('Completed receipt changed')
        records.append(r)
    counts = Counter(r['status'] for r in records)
    if completed and (completed['scheduled'], completed['complete'], completed['errors']) != (
            plan['requests'], counts['complete'], counts['error']):
        raise ValueError('Completion counts differ')
    if completed and (counts['pending'] or counts['not-attempted']):
        raise ValueError('Completed batch has missing outcomes')
    return plan, records, data


def arm(rows, reference):
    # The legacy scorer treats terminal failures as missing; preserve other dispositions separately.
    result = scoring._arm([r if r['status'] in ('complete', 'error') else dict(r, status='error',
                          error_type=r['status']) for r in rows], reference)
    result['counts']['error'] = sum(r['status'] == 'error' for r in rows)
    for status in ('pending', 'not-attempted'):
        result['counts'][status] = sum(r['status'] == status for r in rows)
    result['errors'] = [{'slot': r['slot'], 'error_type': r['error_type']} for r in rows if r['status'] == 'error']
    return result


def report(folder, references, reference_hash, inputs_path=None):
    folder, references = Path(folder), Path(references)
    plan, records, data = read_receipts(folder)
    if inputs_path is not None and Path(inputs_path).resolve() != Path(plan['input_path']).resolve():
        raise ValueError('Report inputs differ from prepared inputs')
    if transport.file_hash(references) != reference_hash:
        raise ValueError('Reference hash differs')
    refs = store._read(references)
    targets = {r['id']: r for r in refs}
    if len(refs) != 10 or set(targets) != {q['id'] for q in data['queries']}:
        raise ValueError('Expected ten unique bound references')
    cases = []
    for query in data['queries']:
        i, ref = query['id'], targets[query['id']]
        if ref['conversation_id'] != query['conversation_id'] or not isinstance(ref['text'], str) or not ref['text'].strip():
            raise ValueError('Reference does not match case')
        arms = {c: arm([r for r in records if r['case_id'] == i and r['condition'] == c], ref['text'])
                for c in CONDITIONS if c != 'other-account' or data['donors'][i] is not None}
        def delta(a, b):
            x, y = (arms.get(c, {}).get('form_score') for c in (a, b))
            return x - y if x is not None and y is not None else None
        cases.append({'id': i, 'conditions': arms, 'matched_minus_generic': delta('matched', 'generic'),
            'matched_minus_other_account': delta('matched', 'other-account'),
            'other_account_minus_generic': delta('other-account', 'generic'),
            'history_baseline': protocol.empirical_form_score(data['history'][i], ref['text']),
            'current_prefix_baseline': protocol.empirical_form_score(
                [t['text'] for t in query['prefix'] if t['role'] == 'student'], ref['text'])})
    primary = protocol.paired_summary([c['matched_minus_generic'] for c in cases])
    paired = [c for c in cases if c['matched_minus_generic'] is not None]
    primary['condition_means'] = {a: mean(c['conditions'][a]['form_score'] for c in paired) if paired else None
                                  for a in ('generic', 'matched')}
    versions, usage, reporting = Counter(), Counter(), Counter()
    for row in records:
        if 'raw_file' not in row:
            continue
        raw = store._read(folder / 'execution' / row['raw_file'])
        versions[raw.get('model_version') or 'unreported'] += 1
        for k, v in (raw.get('usage_metadata') or {}).items():
            if type(v) is int:
                usage[k] += v
                reporting[k] += 1
    return {'scheduled_requests': plan['requests'], 'primary': primary, 'cases': cases,
        'secondary': {key: protocol.paired_summary([c[key] for c in cases]) for key in
                      ('matched_minus_other_account', 'other_account_minus_generic')},
        'counts': {a: {s: sum(c['conditions'].get(a, {}).get('counts', {}).get(s, 0) for c in cases)
                      for s in ('reply', 'no-reply', 'error', 'pending', 'not-attempted')} for a in CONDITIONS},
        'available_donor_cases': sum(v is not None for v in data['donors'].values()),
        'history_baseline_mean': mean(c['history_baseline'] for c in cases),
        'current_prefix_baseline_mean': mean(c['current_prefix_baseline'] for c in cases),
        'provider': {'model_versions': dict(versions), 'raw_responses': sum(versions.values()),
                     'usage_integer_totals': dict(usage), 'usage_reporting_counts': dict(reporting)},
        'provenance': {'reference_sha256': reference_hash, 'input_sha256': plan['input_sha256'],
                       'plan_sha256': transport.file_hash(folder / 'plan.json'),
                       'prompts_sha256': transport.file_hash(folder / 'prompts.json'), 'code_pins': required_pins()},
        'limits': ['Literal message-form prediction, not semantic behavior or notebook action fidelity.',
            'Five draws per arm; fair scoring assumes independent stationary draws.',
            'Equal account weighting; missing-outcome bounds are not confidence intervals.',
            'Unavailable donors remain unmeasured; secondary bounds cover all ten cases.',
            'Reference selection conditions on return to chat; silence probabilities are not measured.',
            'No-reply is valid category 12; errors, pending and unattempted slots are missing outcomes.',
            'One fixed report; no retry, resume, reroll, new labels or automatic adoption.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify', 'report'))
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--prompts-sha256')
    parser.add_argument('--references', type=Path)
    parser.add_argument('--reference-sha256')
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'run':
            if not args.send or not os.environ.get('GEMINI_API_KEY') or not args.plan_sha256 or not args.prompts_sha256:
                raise ValueError('Explicit send, API key, and both preparation hashes required')
            result = execute(args.prepared, args.plan_sha256, args.prompts_sha256, transport.live_generate)
            print(json.dumps({k: result[k] for k in ('scheduled', 'complete', 'errors')}))
        elif args.command == 'verify':
            _, rows, _ = read_receipts(args.prepared)
            print(json.dumps(dict(Counter(r['status'] for r in rows))))
        else:
            if args.references is None or args.reference_sha256 is None:
                raise ValueError('Reference file and frozen hash required')
            result = report(args.prepared, args.references, args.reference_sha256, args.inputs)
            store._save(args.prepared / 'report.json', result, exclusive=True)
            print(json.dumps({k: result[k] for k in ('primary', 'counts', 'available_donor_cases')}))
    except Exception as error:
        parser.exit(1, f'{type(error).__name__}: stopped; private details omitted; no automatic restart.\n')
