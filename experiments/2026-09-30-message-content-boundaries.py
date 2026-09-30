"""One fixed authored context/uncertainty check; no real data or retries."""
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
from src.eval import message_content_context as scorer

ROOT = Path(__file__).resolve().parents[1]
CASES = Path(__file__).with_suffix('.json')
TRANSPORT = ROOT / 'experiments/2026-09-29-course-account-history/run.py'


def checksum(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def execute(folder, generate):
    cases = json.loads(CASES.read_text())
    assert len(cases) == len({case['id'] for case in cases}) == 16
    assert Counter(case['group'] for case in cases) == {'direct': 8, 'context': 4, 'ambiguous': 4}
    wire = {'model': 'gemini-2.5-flash', 'timeout_ms': 120000, 'configuration': {
        'temperature': 0, 'max_output_tokens': 2048, 'thinking_config': {'thinking_budget': 0},
        'response_mime_type': 'application/json', 'response_json_schema': scorer.Selection.model_json_schema()}}
    pins = {str(path): checksum(path) for path in (Path(__file__).resolve(), CASES,
        Path(scorer.__file__), Path(scorer.original.__file__),
        ROOT / 'src/eval/retrieval_baseline.py', Path(scorer.original.episodes.__file__), TRANSPORT)}
    jobs = [{**case, 'prompt': scorer.make_prompt(case['input'])} for case in cases]
    plan = {'kind': 'authored-message-content-context-check', 'scheduled': len(jobs),
        'created_at': datetime.now(timezone.utc).isoformat(), 'sdk_version': version('google-genai'),
        'sdk_attempts': 1, 'adapter_attempts': 1, 'wire': wire, 'code_pins': pins, 'cases': jobs,
        'rule': 'One revision, one fixed batch. All values, bases and required context citations '
                'must match for a clean specification check. Stop on technical failure; no repairs. '
                'Report message-only fallback coverage and unsafe inclusions regardless of result. '
                'No student data, real-data validity claim, automatic follow-up or adoption.'}
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'raw').mkdir()
    _save(folder / 'plan.json', plan, exclusive=True)
    rows = [{'id': job['id'], 'group': job['group'], 'status': 'unattempted'} for job in jobs]
    for index, (row, job) in enumerate(zip(rows, jobs)):
        row['status'] = 'pending'
        _save(folder / 'progress.json', rows)

        def recorded_generate(prompt, response_model):
            if prompt != job['prompt'] or response_model is not scorer.Selection:
                raise ValueError('Prompt or schema changed after freezing.')
            raw = generate(wire, prompt)
            path = folder / 'raw' / f'{index + 1:02}.json'
            _save(path, raw, exclusive=True)
            row['raw_sha256'] = checksum(path)
            candidates = raw.get('candidates') or []
            if len(candidates) != 1 or candidates[0].get('finish_reason') != 'STOP':
                raise ValueError('One STOP candidate required.')
            text = ''.join(part.get('text', '') for part in candidates[0].get('content', {}).get('parts', [])
                           if not part.get('thought'))
            return response_model.model_validate_json(text)

        try:
            row['observation'] = scorer.score(job['input'], recorded_generate)
        except Exception as error:
            row.update(status='error', error_type=type(error).__name__)
        else:
            row.update(status='complete', message_only_values=scorer.message_only_values(row['observation']))
            row['checks'] = {flag: {
                'value': row['observation'][flag]['value'] == job['expected'][flag],
                'basis': row['observation'][flag]['basis'] == job['expected_basis'][flag],
                'context': all(line in [{k: v for k, v in evidence.items() if k != 'quote'}
                    for evidence in row['observation'][flag]['evidence']] for line in job['context_lines'][flag])}
                for flag in scorer.original.DEFINITIONS}
        _save(folder / 'progress.json', rows)
        if row['status'] == 'error':
            break
    if any(checksum(path) != expected for path, expected in pins.items()):
        raise ValueError('Source changed during run; preserve saved files.')
    complete = [row for row in rows if row['status'] == 'complete']
    counts = Counter(row['status'] for row in rows)
    fallback = {}
    for flag in scorer.original.DEFINITIONS:
        included = [(row, job) for row, job in zip(rows, jobs)
                    if row['status'] == 'complete' and row['message_only_values'][flag] is not None]
        fallback[flag] = {'included': len(included), 'excluded': len(complete) - len(included),
            'unavailable': len(jobs) - len(complete),
            'correct_included': sum(row['checks'][flag]['value'] for row, job in included),
            'unsafe_included': sum(job['expected_basis'][flag] != 'message_only' for row, job in included)}
    report = {'kind': plan['kind'], 'plan_sha256': checksum(folder / 'plan.json'),
        'finished_at': datetime.now(timezone.utc).isoformat(), 'scheduled': len(jobs),
        'attempted': counts['complete'] + counts['error'],
        'counts': {key: counts[key] for key in ('complete', 'error', 'unattempted')},
        'matches': {flag: {check: sum(row['checks'][flag][check] for row in complete)
            for check in ('value', 'basis', 'context')} for flag in scorer.original.DEFINITIONS},
        'clean_boundary_check': len(complete) == len(jobs) and all(
            all(checks.values()) for row in complete for checks in row['checks'].values()),
        'fallback': fallback, 'cases': rows,
        'limit': 'Authored specification checks, not human validation or student fidelity. '
                 'Message-only exclusions rely on model-reported basis and may miss ambiguity.'}
    _save(folder / 'report.json', report, exclusive=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    if not args.send or not os.environ.get('GEMINI_API_KEY'):
        parser.error('--send and GEMINI_API_KEY required; no requests made.')
    spec = importlib.util.spec_from_file_location('single_attempt_transport', TRANSPORT)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    try:
        result = execute(args.output, transport.live_generate)
    except Exception as error:
        parser.exit(1, f'{type(error).__name__}: stopped; no automatic restart.\n')
    print(json.dumps({k: result[k] for k in ('scheduled', 'attempted', 'counts', 'matches',
                                          'clean_boundary_check', 'fallback')}))
