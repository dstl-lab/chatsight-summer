"""Read-only projection of the closed ten-account history benchmark."""
from collections import Counter
from hashlib import sha256
import importlib.util
import json
from pathlib import Path


STUDY = Path(__file__).resolve().parents[1] / 'experiments/2026-09-29-course-account-history'


def _read(path, expected=None):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('Benchmark artifacts must be regular files without symlinks.')
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024 or (expected is not None and sha256(raw).hexdigest() != expected):
        raise ValueError('A frozen benchmark artifact changed or exceeds the supported size.')
    value = json.loads(raw)
    json.dumps(value, allow_nan=False)
    return value


def load(folder):
    """Verify saved receipts and reproduce existing scores; never dispatch or write."""
    folder = Path(folder).absolute()
    saved = _read(folder / 'report/report.json')
    provenance = saved['provenance']
    for name in ('report', 'protocol'):
        if sha256((STUDY / f'{name}.py').read_bytes()).hexdigest() != provenance[f'{name}_source_sha256']:
            raise ValueError('The frozen benchmark scorer changed.')
    # Import only this fixed public scorer, never an artifact-supplied script.
    spec = importlib.util.spec_from_file_location('saved_course_history_report', STUDY / 'report.py')
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    protocol = report.protocol
    plan = _read(folder / 'plan.json', provenance['plan_sha256'])
    _read(folder / 'execution/completed.json', provenance['completed_sha256'])
    _read(folder / 'execution/started.json')
    bank = _read(folder / 'prompts.json')
    source = Path(plan['input_path'])
    queries = _read(source, provenance['queries_sha256'])
    references = _read(source.parent.parent / 'references/recorded-next.json', provenance['reference_sha256'])
    for slot in range(1, 101):
        _read(folder / f'execution/receipts/{slot:03}.json')
        raw = folder / f'execution/raw/{slot:03}.json'
        if raw.exists() or raw.is_symlink():
            _read(raw)
    verified_plan, records = report._module('run').read_receipts(folder)
    if verified_plan != plan or provenance['queries_sha256'] != plan['input_sha256']:
        raise ValueError('The benchmark inputs changed during verification.')
    scores = report.summarize(plan, records, queries, references)
    if any(saved.get(key) != value for key, value in scores.items()):
        raise ValueError('The saved benchmark scores do not reproduce.')
    query_map = {q['id']: q for q in queries}
    reference_map = {r['id']: r for r in references}
    prompt_map = {(p['case_id'], p['condition']): p['prompt'] for p in bank}
    cases = []
    for number, (case, detail) in enumerate(zip(scores['cases'], plan['cases']), 1):
        query = query_map[case['id']]
        prompts, counts = protocol.prompts(query)
        if (detail != {'id': case['id'], **counts}
                or any(prompt_map[case['id'], condition] != prompt for condition, prompt in prompts.items())):
            raise ValueError('The displayed prefix differs from the frozen generation inputs.')
        prefix = [{'role': t['role'], 'text': t['text']} for t in query['prefix']]
        category_counts = Counter(protocol.form(t['text']) for t in prefix if t['role'] == 'student')
        baseline = case['baseline']
        conditions = []
        for condition, title in zip(protocol.CONDITIONS, ('Current exchange only', 'With earlier dialogue')):
            draws = []
            for row in records:
                if row['case_id'] != case['id'] or row['condition'] != condition:
                    continue
                parsed = row.get('parsed')
                literal = None
                if parsed is not None:
                    text = parsed['text']
                    literal = ({'category': protocol.form(text), 'characters': len(text),
                                'newline': '\n' in text, 'backtick': '`' in text}
                               if parsed['decision'] == 'reply' else
                               {'category': 12, 'characters': None, 'newline': None, 'backtick': None})
                draws.append({'slot': row['slot'], 'draw': row['draw'], 'status': row['status'],
                              'decision': parsed['decision'] if parsed else None,
                              'text': parsed['text'] if parsed else None, 'form': literal,
                              'error_type': row.get('error_type')})
            conditions.append({'id': condition, 'title': title, **case['conditions'][condition],
                               'draws': sorted(draws, key=lambda d: d['draw'])})
        cases.append({'id': f'course-account-v1-{number:02}', 'number': number, 'title': f'Case {number}',
            'prefix': prefix, 'current_start': counts['earlier_turns'],
            'reference': {**case['reference'], 'text': reference_map[case['id']]['text']},
            'baseline': {**baseline, 'category_counts': [category_counts[c] for c in range(13)],
                         'category_probabilities': [category_counts[c] / baseline['visible_student_messages']
                                                    for c in range(13)]},
            'conditions': conditions, 'history_minus_current_exchange': case['history_minus_current_exchange']})
    return {'version': 1, 'model': plan['model'], 'draws_per_condition': protocol.DRAWS,
            'limits': scores['limits'], 'study': {key: value for key, value in scores.items()
                                                if key not in ('version', 'cases')}, 'cases': cases}
