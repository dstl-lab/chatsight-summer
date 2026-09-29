"""Consume one frozen 100-slot plan once; no targets, retries, or resume path."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path

from src.agents import notebook_student as store
from src.eval.student_continuation import Continuation


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def inputs(prepared, expected_plan, expected_prompts):
    if (file_hash(prepared / 'plan.json') != expected_plan or
            file_hash(prepared / 'prompts.json') != expected_prompts):
        raise ValueError('Frozen preparation changed')
    plan = store._read(prepared / 'plan.json')
    if (file_hash(plan['input_path']) != plan['input_sha256'] or
            version('google-genai') != plan['sdk_version'] or
            any(file_hash(p) != h for p, h in plan['code_pins'].items())):
        raise ValueError('Frozen input, dependency, or SDK changed')
    bank = store._read(prepared / 'prompts.json')
    prompts = {(r['case_id'], r['condition']): r['prompt'] for r in bank}
    hashes = {f'{case}:{condition}': sha256(prompt.encode()).hexdigest()
              for (case, condition), prompt in prompts.items()}
    if len(bank) != len(prompts) or hashes != plan['prompt_hashes']:
        raise ValueError('Prompt bank differs from plan')
    if (plan['requests'] != 100 or plan['workers'] != 1 or plan['sdk_attempts'] != 1 or
            plan['adapter_attempts'] != 1 or len(plan['schedule']) != 100 or
            [s['slot'] for s in plan['schedule']] != list(range(1, 101))):
        raise ValueError('Unexpected request budget or schedule')
    return plan, prompts


def parse_response(raw):
    candidates = raw.get('candidates') or []
    if len(candidates) != 1 or candidates[0].get('finish_reason') != 'STOP':
        raise ValueError('Exactly one completed STOP candidate required')
    parts = candidates[0].get('content', {}).get('parts') or []
    text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
    return Continuation.model_validate_json(text).model_dump()


def execute(prepared, expected_plan, expected_prompts, generate, *, progress=True):
    plan, prompts = inputs(prepared, expected_plan, expected_prompts)
    out = prepared / 'execution'
    # A launch consumes this batch, including interruption; never resume or replace it.
    out.mkdir(exist_ok=False)
    (out / 'receipts').mkdir()
    (out / 'raw').mkdir()
    store._save(out / 'started.json', {
        'plan_sha256': expected_plan, 'prompts_sha256': expected_prompts, 'started_at': now(),
        'authorization': {'user_request': "Let's do the bounded run then",
            'scope': '100 scheduled Google Gemini requests maximum using the twenty frozen private '
                     'course-conversation prompts. Recorded next messages excluded. No retries, '
                     'replacement samples, resume, prompt changes, labels or automatic follow-up.'},
        'code_pins': {str(p): file_hash(p) for p in (Path(__file__).resolve(), Path(store.__file__).resolve())}},
        exclusive=True)
    counts = Counter()
    for slot in plan['schedule']:
        prompt = prompts[slot['case_id'], slot['condition']]
        receipt = {**slot, 'status': 'pending', 'started_at': now(), 'plan_sha256': expected_plan,
                   'prompt_sha256': sha256(prompt.encode()).hexdigest()}
        path = out / 'receipts' / f"{slot['slot']:03d}.json"
        store._save(path, receipt, exclusive=True)
        try:
            raw = generate(plan, prompt)
        except Exception as error:
            # Exception messages and HTTP bodies may echo private input or credentials.
            receipt.update(status='error', error_type=type(error).__name__)
        else:
            raw_file = f"raw/{slot['slot']:03d}.json"
            store._save(out / raw_file, raw, exclusive=True)
            receipt.update(raw_file=raw_file, raw_sha256=file_hash(out / raw_file))
            store._save(path, receipt)
            try:
                receipt.update(status='complete', parsed=parse_response(raw))
            except (ValueError, TypeError, AttributeError) as error:
                receipt.update(status='error', error_type=type(error).__name__)
        receipt['finished_at'] = now()
        store._save(path, receipt)
        counts[receipt['status']] += 1
        if progress:
            print(json.dumps({'slot': slot['slot'], 'scheduled': 100, 'status': receipt['status']}), flush=True)
    result = {'finished_at': now(), 'scheduled': 100, 'complete': counts['complete'], 'errors': counts['error'],
              'receipt_sha256': {f'receipts/{i:03d}.json': file_hash(out / f'receipts/{i:03d}.json')
                                 for i in range(1, 101)}}
    store._save(out / 'completed.json', result, exclusive=True)
    return result


def read_receipts(prepared):
    out = prepared / 'execution'
    started, completed = store._read(out / 'started.json'), store._read(out / 'completed.json')
    plan, _ = inputs(prepared, started['plan_sha256'], started['prompts_sha256'])
    if any(file_hash(p) != h for p, h in started['code_pins'].items()):
        raise ValueError('Dispatch code changed')
    records = []
    for slot in plan['schedule']:
        relative = f"receipts/{slot['slot']:03d}.json"
        if file_hash(out / relative) != completed['receipt_sha256'][relative]:
            raise ValueError('Receipt changed after completion')
        r = store._read(out / relative)
        if (any(r[k] != v for k, v in slot.items()) or r['plan_sha256'] != started['plan_sha256'] or
                r['prompt_sha256'] != plan['prompt_hashes'][f"{r['case_id']}:{r['condition']}"] or
                r['status'] not in ('complete', 'error') or r['finished_at'] < r['started_at']):
            raise ValueError('Mismatched or unfinished receipt')
        if 'raw_file' in r:
            if (r['raw_file'] != f"raw/{slot['slot']:03d}.json" or
                    file_hash(out / r['raw_file']) != r['raw_sha256']):
                raise ValueError('Provider response changed')
            try:
                parsed = parse_response(store._read(out / r['raw_file']))
            except (ValueError, TypeError, AttributeError):
                if r['status'] != 'error':
                    raise ValueError('Invalid provider output accepted') from None
            else:
                if r['status'] != 'complete' or parsed != r.get('parsed'):
                    raise ValueError('Parsed output differs from raw provider response')
        elif r['status'] != 'error':
            raise ValueError('Accepted output has no provider response')
        if r['status'] == 'error' and ('parsed' in r or not r.get('error_type')):
            raise ValueError('Invalid error disposition')
        records.append(r)
    counts = Counter(r['status'] for r in records)
    if (completed['scheduled'], completed['complete'], completed['errors']) != (100, counts['complete'], counts['error']):
        raise ValueError('Completion counts differ from receipts')
    return plan, records


def live_generate(plan, prompt):
    from google import genai
    with genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=genai.types.HttpOptions(
            timeout=plan['timeout_ms'], retry_options={'attempts': 1})) as client:
        response = client.models.generate_content(model=plan['model'], contents=prompt,
                                                  config=plan['configuration'])
        return response.model_dump(mode='json', exclude_none=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'verify'))
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--prompts-sha256')
    args = parser.parse_args()
    try:
        if args.command == 'run':
            if not os.environ.get('GEMINI_API_KEY') or not args.plan_sha256 or not args.prompts_sha256:
                raise ValueError('API key and both frozen hashes are required')
            result = execute(args.prepared, args.plan_sha256, args.prompts_sha256, live_generate)
            print(json.dumps({k: result[k] for k in ('scheduled', 'complete', 'errors')}))
        else:
            _, records = read_receipts(args.prepared)
            print(json.dumps({'verified': len(records), 'statuses': dict(Counter(r['status'] for r in records))}))
    except Exception as error:
        parser.exit(1, f'{type(error).__name__}: stopped; private details omitted. No automatic restart.\n')
