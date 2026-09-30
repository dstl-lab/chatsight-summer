"""One create-only smoke batch on authored examples; no student data or retries."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path

from src.agents.notebook_student import _save
from src.eval import message_content as scorer
from src.eval import retrieval_baseline
from src.labeling import episodes

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / 'experiments/2026-09-29-course-account-history/run.py'


def authored_cases():
    question = [{'role': 'tutor', 'text': 'What is 6 divided by 3?'}]
    rows = [
        ('code-only', [], 'total = sum(values)', 'yes', 'no'),
        ('explanation-request', [], 'Please explain this function.', 'no', 'yes'),
        ('answer', question, '2.', 'yes', 'no'),
        ('confirmation', question, '2?', 'yes', 'yes'),
        ('fragment', [], '2?', 'unclear', 'unclear'),
        ('check-code', [], 'Can you check this? `total = sum(values)`', 'yes', 'yes'),
        ('task-only', [], 'Exercise: Write a loop that prints three numbers.', 'no', 'unclear'),
        ('solve-task', [], 'Can you solve this? Exercise: Write a loop that prints three numbers.', 'no', 'yes'),
        ('work-claim', [], 'I have a function. How do I apply it?', 'no', 'yes'),
        ('execution-claim', [], 'I ran the tests; they passed.', 'no', 'no'),
        ('diagnostic', [], 'AssertionError: expected 6, got 9', 'yes', 'no'),
        ('acknowledgment', [], "Thanks, I'll try that.", 'no', 'no'),
    ]
    return [{'id': name, 'input': {'prefix': prefix, 'message': message},
             'expected': {'content_supplied': content, 'expressed_request': request}}
            for name, prefix, message, content, request in rows]


def checksum(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def execute(folder, generate):
    folder = Path(folder)
    cases = authored_cases()
    configuration = {'temperature': 0, 'max_output_tokens': 2048,
        'thinking_config': {'thinking_budget': 0}, 'response_mime_type': 'application/json',
        'response_json_schema': scorer.Selection.model_json_schema()}
    wire = {'model': 'gemini-2.5-flash', 'configuration': configuration, 'timeout_ms': 120000}
    pins = {str(path): checksum(path) for path in (
        Path(__file__).resolve(), Path(scorer.__file__).resolve(),
        Path(retrieval_baseline.__file__).resolve(), Path(episodes.__file__).resolve(), TRANSPORT)}
    jobs = [{**case, 'prompt': scorer.make_prompt(case['input'])} for case in cases]
    plan = {'kind': 'authored-message-content-smoke', 'scheduled': len(jobs),
        'created_at': datetime.now(timezone.utc).isoformat(), 'sdk_version': version('google-genai'),
        'sdk_attempts': 1, 'adapter_attempts': 1, 'wire': wire, 'code_pins': pins, 'cases': jobs,
        'scope': 'Twelve authored specification examples, once each. No real student data. '
                 'Stop at first technical error; no resends, tuning or follow-up calls.'}
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'raw').mkdir()
    _save(folder / 'plan.json', plan, exclusive=True)
    rows = [{'id': job['id'], 'status': 'unattempted'} for job in jobs]
    for index, job in enumerate(jobs):
        row = {'id': job['id'], 'status': 'pending'}
        rows[index] = row
        _save(folder / 'progress.json', rows)

        def recorded_generate(prompt, response_model):
            if prompt != job['prompt'] or response_model is not scorer.Selection:
                raise ValueError('Scorer input changed after freezing the authored plan.')
            # Expected judgments and other examples never enter the transport.
            raw = generate(wire, prompt)
            raw_path = folder / 'raw' / f'{index + 1:02}.json'
            _save(raw_path, raw, exclusive=True)
            row['raw_sha256'] = checksum(raw_path)
            candidates = raw.get('candidates') or []
            if len(candidates) != 1 or candidates[0].get('finish_reason') != 'STOP':
                raise ValueError('One completed STOP candidate is required.')
            parts = candidates[0].get('content', {}).get('parts') or []
            text = ''.join(part.get('text', '') for part in parts if not part.get('thought'))
            return response_model.model_validate_json(text)

        try:
            row['observation'] = scorer.score(job['input'], recorded_generate)
        except Exception as error:
            row.update(status='error', error_type=type(error).__name__)
            if type(getattr(error, 'code', None)) is int:
                row['status_code'] = error.code
        else:
            row.update(status='complete', matches={
                flag: row['observation'][flag]['value'] == expected
                for flag, expected in job['expected'].items()})
        _save(folder / 'progress.json', rows)
        if row['status'] == 'error':
            break
    if any(checksum(path) != expected for path, expected in pins.items()):
        raise ValueError('Source changed during the smoke run; preserve saved evidence.')
    counts = Counter(row['status'] for row in rows)
    complete = [row for row in rows if row['status'] == 'complete']
    matches = {flag: sum(row['matches'][flag] for row in complete)
               for flag in ('content_supplied', 'expressed_request')}
    matches['both'] = sum(all(row['matches'].values()) for row in complete)
    report = {'kind': plan['kind'], 'finished_at': datetime.now(timezone.utc).isoformat(),
        'plan_sha256': checksum(folder / 'plan.json'), 'scheduled': len(jobs),
        'attempted': counts['complete'] + counts['error'],
        'counts': {key: counts[key] for key in ('complete', 'error', 'unattempted')},
        'matches': matches, 'comparison_denominator': len(complete),
        'clean_smoke': matches['both'] == len(jobs), 'cases': rows,
        'limit': 'Authored development checks only. No real-data validity, independent human '
                 'agreement or simulated-student fidelity is established. No automatic follow-up.'}
    _save(folder / 'report.json', report, exclusive=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--send', action='store_true', help='Send only these twelve authored examples.')
    args = parser.parse_args()
    if not args.send or not os.environ.get('GEMINI_API_KEY'):
        parser.error('--send and GEMINI_API_KEY are required; no requests made.')
    spec = importlib.util.spec_from_file_location('single_attempt_transport', TRANSPORT)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    try:
        result = execute(args.output, transport.live_generate)
    except Exception as error:
        parser.exit(1, f'{type(error).__name__}: stopped; no automatic restart.\n')
    print(json.dumps({k: result[k] for k in ('scheduled', 'attempted', 'counts', 'matches', 'clean_smoke')}))
