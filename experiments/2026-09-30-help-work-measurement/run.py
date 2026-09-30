"""Freeze and consume one human-label measurement audit; never retry or resume."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path

from src.agents import notebook_student as store


ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / 'experiments/2026-09-29-course-account-history/run.py'


def module(path):
    spec = importlib.util.spec_from_file_location('measurement_' + Path(path).stem, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def freeze(folder, verification):
    """Pin the complete local disclosure after legacy review verification."""
    folder = Path(folder).absolute()
    audit = module(Path(__file__).with_name('audit.py'))
    saved = audit.load(folder)
    # The separate verifier binds the old human forms to their closed reports.
    if not verification.get('verified') or not verification.get('files'):
        raise ValueError('Verified legacy review bindings are required.')
    if any(file_hash(path) != expected for path, expected in verification['files'].items()):
        raise ValueError('Legacy review evidence changed.')
    if any(verification['files'].get(pin['path']) != pin['sha256']
           for source in saved['plan']['sources'] for pin in source.values()):
        raise ValueError('Every source packet and human form needs its legacy verification binding.')
    payloads = [{'id': identity, 'prompt': audit.make_prompt(payload)}
                for identity, payload in zip(saved['plan']['ids'], saved['prompts'], strict=True)]
    if len(payloads) != 88:
        raise ValueError('The declared audit contains exactly 88 distinct inputs.')
    if any(len(row['prompt']) > 65536 for row in payloads):
        raise ValueError('Keep full inputs; do not truncate an oversized audit request.')
    transport_paths = (Path(__file__).resolve(), TRANSPORT, Path(store.__file__).resolve())
    plan = {'version': 1, 'kind': 'help-work-measurement-audit', 'requests': len(payloads),
            'model': 'gemini-2.5-flash', 'sdk_version': version('google-genai'),
            'workers': 1, 'sdk_attempts': 1, 'adapter_attempts': 1, 'timeout_ms': 120000,
            'configuration': {'temperature': 0, 'max_output_tokens': 2048,
                'thinking_config': {'thinking_budget': 0}, 'response_mime_type': 'application/json',
                'response_schema': audit.Classification.model_json_schema()},
            'audit_plan_sha256': file_hash(folder / 'plan.json'),
            'payloads_sha256': store.digest(payloads),
            'code_pins': {str(path): file_hash(path) for path in transport_paths},
            'legacy_verification': verification,
            'schedule': [{'slot': slot, 'id': row['id'],
                          'prompt_sha256': sha256(row['prompt'].encode()).hexdigest()}
                         for slot, row in enumerate(payloads, 1)]}
    # A separate create-only dispatch directory leaves offline preparation intact.
    dispatch = folder / 'dispatch'
    dispatch.mkdir(exist_ok=False)
    store._save(dispatch / 'payloads.json', payloads, exclusive=True)
    store._save(dispatch / 'plan.json', plan, exclusive=True)
    disclosure = ['# One fixed help/work coding audit', '',
        'Destination: Google Gemini, gemini-2.5-flash. Maximum 88 requests, one per input.',
        'Payload: previously reviewed private course conversation prefixes and real/generated',
        'candidate messages. Saved human judgments, reviewer notes and origin metadata are excluded.',
        'No new student generation, database reads, notebook execution, retries or follow-up calls.',
        '', '## Exact prompts', '']
    for row in payloads:
        disclosure.extend([f"### Input {row['id']}", '', row['prompt'], ''])
    (dispatch / 'disclosure.md').write_text('\n'.join(disclosure))
    return {'dispatch_plan_sha256': file_hash(dispatch / 'plan.json'), 'requests': len(payloads)}


def inputs(folder, expected):
    folder = Path(folder).absolute()
    audit = module(Path(__file__).with_name('audit.py'))
    saved = audit.load(folder)
    dispatch = folder / 'dispatch'
    if file_hash(dispatch / 'plan.json') != expected:
        raise ValueError('Dispatch plan changed.')
    plan, payloads = store._read(dispatch / 'plan.json'), store._read(dispatch / 'payloads.json')
    if (plan['audit_plan_sha256'] != file_hash(folder / 'plan.json')
            or plan['sdk_version'] != version('google-genai')
            or any(file_hash(path) != expected for path, expected in plan['code_pins'].items())
            or any(file_hash(path) != expected for path, expected in plan['legacy_verification']['files'].items())):
        raise ValueError('Frozen source, review evidence or dependency changed.')
    rebuilt = [{'id': identity, 'prompt': audit.make_prompt(payload)}
               for identity, payload in zip(saved['plan']['ids'], saved['prompts'], strict=True)]
    if (payloads != rebuilt or store.digest(payloads) != plan['payloads_sha256']
            or plan['requests'] != len(payloads) or plan['requests'] != 88
            or (plan['workers'], plan['sdk_attempts'], plan['adapter_attempts']) != (1, 1, 1)
            or plan['schedule'] != [{'slot': slot, 'id': row['id'],
                'prompt_sha256': sha256(row['prompt'].encode()).hexdigest()}
                for slot, row in enumerate(payloads, 1)]):
        raise ValueError('Exact inputs or fixed schedule changed.')
    return audit, plan, payloads


def parse(raw, audit):
    candidates = raw.get('candidates') or []
    if len(candidates) != 1 or candidates[0].get('finish_reason') != 'STOP':
        raise ValueError('One completed STOP candidate required.')
    parts = candidates[0].get('content', {}).get('parts') or []
    text = ''.join(part.get('text', '') for part in parts if not part.get('thought'))
    return audit.Classification.model_validate_json(text).model_dump()


def execute(folder, expected, generate, *, progress=True):
    folder = Path(folder).absolute()
    audit, plan, payloads = inputs(folder, expected)
    out = folder / 'execution'
    out.mkdir(exist_ok=False)  # A launch consumes the batch, including interruption.
    (out / 'receipts').mkdir()
    (out / 'raw').mkdir()
    store._save(out / 'started.json', {'dispatch_plan_sha256': expected, 'started_at': now(),
        'authorization': {'user_request': "Okay, let's do it",
            'standing_preference': 'Project Gemini simulation and labeling runs approved 2026-09-11.',
            'scope': 'One fixed audit of 88 previously reviewed inputs; no retries or automatic follow-up.'}},
        exclusive=True)
    counts = Counter()
    for job, payload in zip(plan['schedule'], payloads, strict=True):
        path = out / 'receipts' / f"{job['slot']:03}.json"
        receipt = {**job, 'status': 'pending', 'started_at': now(), 'dispatch_plan_sha256': expected}
        store._save(path, receipt, exclusive=True)
        try:
            raw = generate(plan, payload['prompt'])
        except Exception as error:
            receipt.update(status='error', error_type=type(error).__name__)
        else:
            raw_path = out / 'raw' / f"{job['slot']:03}.json"
            store._save(raw_path, raw, exclusive=True)
            receipt['raw_sha256'] = file_hash(raw_path)
            store._save(path, receipt)
            try:
                receipt.update(status='complete', labels=parse(raw, audit))
            except (ValueError, TypeError, AttributeError) as error:
                receipt.update(status='error', error_type=type(error).__name__)
        receipt['finished_at'] = now()
        store._save(path, receipt)
        counts[receipt['status']] += 1
        if progress:
            print(json.dumps({'slot': job['slot'], 'scheduled': plan['requests'],
                              'status': receipt['status']}), flush=True)
    completed = {'finished_at': now(), 'counts': dict(counts),
        'receipts': {str(path.relative_to(out)): file_hash(path) for path in sorted((out / 'receipts').glob('*.json'))}}
    store._save(out / 'completed.json', completed, exclusive=True)
    return completed


def report(folder, expected):
    """Reparse saved provider outputs; unfinished slots stay missing, never no."""
    folder = Path(folder).absolute()
    audit, plan, _ = inputs(folder, expected)
    out = folder / 'execution'
    started = store._read(out / 'started.json')
    if started['dispatch_plan_sha256'] != expected:
        raise ValueError('Run started against another plan.')
    completed = store._read(out / 'completed.json') if (out / 'completed.json').exists() else None
    predictions, hashes = [], {}
    for job in plan['schedule']:
        path = out / 'receipts' / f"{job['slot']:03}.json"
        result = {'id': job['id'], 'status': 'missing', 'labels': None, 'error_type': None}
        if path.exists():
            hashes[str(path.relative_to(out))] = file_hash(path)
            row = store._read(path)
            if any(row.get(key) != value for key, value in job.items()) or row['dispatch_plan_sha256'] != expected:
                raise ValueError('Receipt identity changed.')
            if row['status'] not in ('pending', 'complete', 'error'):
                raise ValueError('Unexpected receipt state.')
            if row['status'] != 'pending':
                if row['finished_at'] < row['started_at']:
                    raise ValueError('Receipt chronology changed.')
                result.update(status=row['status'], labels=row.get('labels'), error_type=row.get('error_type'))
                if row['status'] == 'error' and (result['labels'] is not None or not result['error_type']):
                    raise ValueError('Invalid failed request.')
            if row.get('raw_sha256'):
                raw_path = out / 'raw' / path.name
                if file_hash(raw_path) != row['raw_sha256']:
                    raise ValueError('Saved provider response changed.')
                try:
                    parsed = parse(store._read(raw_path), audit)
                except (ValueError, TypeError, AttributeError):
                    if row['status'] == 'complete':
                        raise ValueError('Invalid response accepted.') from None
                else:
                    if row['status'] == 'error' or row['status'] == 'complete' and parsed != result['labels']:
                        raise ValueError('Saved labels differ from raw output.')
            elif row['status'] == 'complete':
                raise ValueError('Successful coding has no raw response.')
        predictions.append(result)
    if completed and (completed['receipts'] != hashes or completed['counts'] != dict(Counter(row['status'] for row in predictions))):
        raise ValueError('Completion record does not reproduce.')
    result = audit.report(folder, predictions)
    result['provenance'] = {'dispatch_plan_sha256': expected, 'started_sha256': file_hash(out / 'started.json'),
        'completed_sha256': file_hash(out / 'completed.json') if completed else None, 'receipts': hashes}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'report'))
    parser.add_argument('folder', type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'run':
            if not os.environ.get('GEMINI_API_KEY'):
                raise ValueError('GEMINI_API_KEY is required.')
            execute(args.folder, args.plan_sha256, module(TRANSPORT).live_generate)
        else:
            result = report(args.folder, args.plan_sha256)
            store._save(args.folder / 'report.json', result, exclusive=True)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except Exception as error:
        raise SystemExit(type(error).__name__) from None
