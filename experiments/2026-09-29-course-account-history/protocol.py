"""Offline preparation and literal-form scores; deliberately no provider dispatch."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from itertools import product
import json
from math import isclose, isfinite
from pathlib import Path
from tempfile import TemporaryDirectory

from src.agents import chat_student
from src.eval import corpus_summary, retrieval_baseline, student_continuation
from src.labeling import episodes, llm, tutor_moves

CONDITIONS = ('current-exchange', 'history')
DRAWS = 5
PROMPT_LIMIT = 65536


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def form(text):
    """The corpus summary's three length bins, newline and backtick indicators."""
    if not isinstance(text, str):
        raise ValueError('Expected text')
    return (0 if len(text) <= 40 else 1 if len(text) <= 300 else 2) * 4 + 2 * ('\n' in text) + ('`' in text)


def fair_form_score(draws, reference):
    if len(draws) != DRAWS or not isinstance(reference, str) or not reference.strip():
        raise ValueError('Expected five valid decisions and a nonblank recorded message')
    values = [student_continuation.Continuation.model_validate(d) for d in draws]
    counts = Counter(form(d.text) if d.decision == 'reply' else 12 for d in values)
    numerator = (DRAWS * (DRAWS - 1) - 2 * counts[form(reference)] * (DRAWS - 1)
                 + sum(c * (c - 1) for c in counts.values()))
    return numerator / (2 * DRAWS * (DRAWS - 1))


def empirical_form_score(student_texts, reference):
    if not student_texts or not isinstance(reference, str) or not reference.strip():
        raise ValueError('Expected visible student messages and a recorded message')
    counts = Counter(map(form, student_texts))
    n = len(student_texts)
    return 0.5 * (1 - 2 * counts[form(reference)] / n + sum((c / n) ** 2 for c in counts.values()))


def paired_summary(deltas):
    if len(deltas) != 10 or any(d is not None and
            (type(d) not in (float, int) or not isfinite(d) or not -1 <= d <= 1) for d in deltas):
        raise ValueError('Expected ten bounded paired deltas or missing values')
    complete = [d for d in deltas if d is not None]
    missing = 10 - len(complete)
    return {'complete_pairs': len(complete),
            'all_ten_mean': sum(complete) / 10 if not missing else None,
            'complete_pair_mean': sum(complete) / len(complete) if complete else None,
            'missing_outcome_bounds': [(sum(complete) - missing) / 10, (sum(complete) + missing) / 10]}


def prompts(query):
    episode = deepcopy(chat_student._initial(query)['episode'])
    for i, turn in enumerate(episode['context'], 1):
        turn['id'] = f'context-{i}'
    counts = Counter()
    for turn in episode['turns']:
        counts[turn['phase']] += 1
        turn['id'] = f"{turn['phase']}-{counts[turn['phase']]}"
    current = deepcopy(episode)
    current['context'] = []
    rendered = {name: student_continuation.make_prompt(value)
                for name, value in zip(CONDITIONS, (current, episode))}
    if not episode['context'] or rendered['history'] == rendered['current-exchange']:
        raise ValueError('No history intervention; retain the case and amend before running')
    if max(map(len, rendered.values())) > PROMPT_LIMIT:
        raise ValueError('Prompt exceeds preparation ceiling; no truncation or replacement')
    return rendered, {'earlier_turns': len(episode['context']),
                      'earlier_student_turns': sum(t['role'] == 'student' for t in episode['context']),
                      'current_turns': len(episode['turns'])}


def prepare(source, expected, out):
    source, out = Path(source).resolve(strict=True), Path(out)
    if file_hash(source) != expected:
        raise ValueError('Frozen query input hash changed')
    queries = [retrieval_baseline.Query.model_validate(q).model_dump() for q in json.loads(source.read_text())]
    if (len(queries) != 10 or any(q['student_id'] is None for q in queries)
            or any(len({q[key] for q in queries}) != 10 for key in ('id', 'conversation_id', 'student_id'))):
        raise ValueError('Expected ten distinct frozen accounts and cases')
    bank, cases = [], []
    for q in queries:
        rendered, detail = prompts(q)
        cases.append({'id': q['id'], **detail})
        for condition, prompt in rendered.items():
            bank.append({'case_id': q['id'], 'condition': condition, 'prompt': prompt,
                         'prompt_sha256': sha256(prompt.encode()).hexdigest()})
    schedule = []
    for draw in range(1, DRAWS + 1):
        for index, q in enumerate(queries):
            order = CONDITIONS if (index + draw - 1) % 2 == 0 else CONDITIONS[::-1]
            base = len(schedule)
            schedule.extend({'slot': base + offset + 1, 'case_id': q['id'],
                             'draw': draw, 'condition': name} for offset, name in enumerate(order))
    assert len(schedule) == len({(s['case_id'], s['condition'], s['draw']) for s in schedule}) == 100
    assert [s['slot'] for s in schedule] == list(range(1, 101))
    plan = {'version': 1, 'status': 'prepared-not-run', 'prepared_at': datetime.now(timezone.utc).isoformat(),
            'input_path': str(source), 'input_sha256': expected, 'population': 'provisional course accounts',
            'model': 'gemini-2.5-pro', 'sdk_version': version('google-genai'),
            'configuration': {'temperature': 1.0, 'max_output_tokens': 8192,
                              'response_mime_type': 'application/json',
                              'response_schema': student_continuation.Continuation.model_json_schema()},
            'omitted_settings': ['top_p', 'top_k', 'seed', 'thinking_config'],
            'timeout_ms': 120000, 'sdk_attempts': 1, 'adapter_attempts': 1, 'workers': 1,
            'prompt_character_limit': PROMPT_LIMIT, 'draws_per_condition': DRAWS,
            'requests': 100, 'cases': cases, 'schedule': schedule,
            'prompt_hashes': {f"{r['case_id']}:{r['condition']}": r['prompt_sha256'] for r in bank},
            'primary': 'Equal-account history-minus-current-exchange fair multicategory form Brier',
            'no_reply_category': 12, 'form_categories': 12,
            'stopping_rule': 'One fixed batch and report; no retries, replacements, tuning or automatic follow-up',
            'code_pins': {str(p): file_hash(p) for p in (Path(__file__).resolve(), *(
                Path(m.__file__).resolve() for m in (chat_student, retrieval_baseline,
                    student_continuation, corpus_summary, episodes, llm, tutor_moves)))}}
    if file_hash(source) != expected:
        raise ValueError('Source changed during preparation')
    out.mkdir(parents=True, exist_ok=False)
    for name, value in (('prompts.json', bank), ('plan.json', plan)):
        with (out / name).open('x') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return {'cases': len(cases), 'prompts': len(bank), 'planned_requests': len(schedule),
            'prompt_characters_min': min(len(r['prompt']) for r in bank),
            'prompt_characters_max': max(len(r['prompt']) for r in bank),
            'earlier_student_history_cases': sum(c['earlier_student_turns'] > 0 for c in cases),
            'plan_sha256': file_hash(out / 'plan.json'), 'prompts_sha256': file_hash(out / 'prompts.json'),
            'provider_calls': 0}


def self_test():
    assert [form('x' * n) for n in (40, 41, 300, 301)] == [0, 4, 4, 8]
    assert form('`\n') == 3 and form('学' * 40) == 0
    short = {'decision': 'reply', 'text': 'ok'}
    long = {'decision': 'reply', 'text': 'x' * 301}
    assert fair_form_score([short] * 5, 'ok') == 0
    assert fair_form_score([short] * 4 + [long], 'ok') == 0
    assert fair_form_score([long] * 5, 'ok') == 1
    assert fair_form_score([{'decision': 'no-reply', 'text': ''}] * 5, 'ok') == 1
    # Exhaustively verify the finite-draw correction against a known binary forecast.
    expectation = sum(0.25 ** sum(bits) * 0.75 ** (5 - sum(bits)) *
                      fair_form_score([short if bit else long for bit in bits], 'ok')
                      for bits in product((0, 1), repeat=5))
    assert isclose(expectation, 0.75 ** 2)
    assert empirical_form_score(['ok', 'x' * 301], 'ok') == 0.25
    assert paired_summary([None] * 10)['missing_outcome_bounds'] == [-1, 1]
    assert paired_summary([0] * 9 + [None])['missing_outcome_bounds'] == [-0.1, 0.1]
    fake = {'id': 'not-visible', 'conversation_id': 'not-visible', 'student_id': 'not-visible',
            'prefix': [{'role': role, 'text': text} for role, text in (
                ('student', 'earlier'), ('tutor', 'earlier reply'), ('student', 'part one'),
                ('student', 'part two'), ('tutor', 'reply one'), ('tutor', 'reply two'))]}
    pair, detail = prompts(fake)
    visible = {k: json.loads(p[len(student_continuation.PROMPT):]) for k, p in pair.items()}
    assert detail == {'earlier_turns': 2, 'earlier_student_turns': 1, 'current_turns': 4}
    assert visible['current-exchange']['context'] == []
    assert visible['current-exchange']['turns'] == visible['history']['turns']
    assert all('not-visible' not in p for p in pair.values())
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / 'queries.json'
        source.write_text(json.dumps([fake | {'id': str(i), 'conversation_id': str(i),
                                             'student_id': str(i)} for i in range(10)]))
        result = prepare(source, file_hash(source), root / 'prepared')
        plan = json.loads((root / 'prepared/plan.json').read_text())
        assert result['planned_requests'] == 100 and result['prompts'] == 20
        assert Counter(s['condition'] for s in plan['schedule'][::2]) == dict.fromkeys(CONDITIONS, 25)
        try:
            prepare(source, file_hash(source), root / 'prepared')
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing preparation overwritten')
    print('Authored scoring and prompt-isolation checks passed; no provider calls.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--queries', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.queries and args.sha256 and args.out:
        try:
            print(json.dumps(prepare(args.queries, args.sha256, args.out), indent=2))
        except (OSError, ValueError) as error:
            parser.error(type(error).__name__ + ': preparation failed; private input details omitted')
    else:
        parser.error('Supply --self-test or --queries, --sha256 and --out')
