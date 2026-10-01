"""Create-only preparation from selected prefix/history events; no reference reads."""
import importlib.util
import itertools
import json
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from src.agents import chat_student, student_evidence
from src.eval import retrieval_baseline, student_continuation
from src.labeling import episodes, tutor_moves

sys.path.insert(0, str(Path('experiments/2026-09-29-course-account-history').resolve()))
from protocol import form

ROOT = Path('data/cross-notebook-cards-v1')
GUIDANCE = '''Additional communication evidence from earlier conversations on other
notebook identities follows. Treat these aggregate observations as a weak guide
alongside the current conversation, not a required response style. They are not
evidence of ability, emotion, enduring personality, understanding or silence
probabilities. Do not force brevity, mistakes or unnecessary explanations.
No earlier answer text or notebook contents are supplied in this card.

EARLIER COMMUNICATION STATISTICS:
'''


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def load_script(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_prompt(query):
    episode = deepcopy(chat_student._initial(query)['episode'])
    for i, turn in enumerate(episode['context'], 1):
        turn['id'] = f'context-{i}'
    counts = Counter()
    for turn in episode['turns']:
        counts[turn['phase']] += 1
        turn['id'] = f"{turn['phase']}-{counts[turn['phase']]}"
    return student_continuation.make_prompt(episode)


def statistics(texts):
    evidence = student_evidence.card([{'role': 'student', 'text': text} for text in texts])
    return {key: evidence[key] for key in ('student_messages', 'statistics')}


def check():
    query = {'id': 'HIDDEN_ID', 'conversation_id': 'HIDDEN_ID', 'student_id': 'HIDDEN_ID',
             'prefix': [{'role': role, 'text': text} for role, text in (
                 ('student', 'earlier'), ('tutor', 'earlier response'), ('student', 'part1'),
                 ('student', 'part2'), ('tutor', 'answer1'), ('tutor', 'answer2'))]}
    prompt = base_prompt(query)
    assert 'HIDDEN_ID' not in prompt and all(t['text'] in prompt for t in query['prefix'])
    evidence = statistics(['PRIVATE_HISTORY_EXAMPLE', 'short\n`'])
    assert 'PRIVATE_HISTORY_EXAMPLE' not in json.dumps(evidence) and 'examples' not in evidence
    assert evidence['student_messages'] == 2
    assert [form('x' * n) for n in (40, 41, 300, 301)] == [0, 4, 4, 8]


def prepare():
    frozen, receipt, metadata = [read(ROOT / name) for name in ('frozen.json', 'content.json', 'events.json')]
    selection = read(ROOT / 'selection.json')
    for record in (selection, frozen):
        for name, expected in record['source_sha256'].items():
            assert digest(name) == expected, name
    expected, params = load_script('experiments/2026-10-01-cross-notebook-select.py').freeze_result()
    assert expected == frozen and params == read(ROOT / 'content-params.json')
    assert frozen['status'] == 'frozen-before-content' and not frozen['failures']
    assert receipt['read_only'] is True
    assert receipt['query_sha256'] == digest('experiments/2026-10-01-cross-notebook-content.sql')
    assert receipt['params_sha256'] == digest(ROOT / 'content-params.json')
    assert receipt['probe_sha256'] == digest('../episode-pilot/data/episode-pilot/notebook-context-v1/ingestion_probe.py')
    rows = {r['id']: r for r in receipt['rows']}
    meta = {r['id']: r for r in metadata['rows']}
    assert len(rows) == len(receipt['rows']) and set(rows) == set(frozen['input_event_ids'])
    assert not set(rows) & set(frozen['reference_event_ids'])
    for key, row in rows.items():
        assert set(row) == set(meta[key]) | {'text'}
        assert all(row[k] == v for k, v in meta[key].items())
        assert isinstance(row['text'], str) and row['text'].strip(), 'Unusable selected input; no replacement'
    queries, histories, cards, donors, bank = [], {}, {}, {}, []
    contrasts = []
    for case in frozen['cases']:
        cid = case['id']
        prefix = [dict(role='student' if rows[e]['event_type'] == 'tutor_query' else 'tutor',
                       text=rows[e]['text']) for e in case['prefix_event_ids']]
        query = retrieval_baseline.Query(id=cid, conversation_id=case['conv_id'],
            student_id=case['account_id'], prefix=prefix).model_dump()
        queries.append(query)
        histories[cid] = [rows[e]['text'] for e in case['history_event_ids']]
        assert 10 <= len(histories[cid]) <= 20
        assert len({rows[e]['notebook_id'] for e in case['history_event_ids']}) >= 2
        assert all(rows[e]['event_type'] == 'tutor_query' for e in case['history_event_ids'])
        cards[cid] = statistics(histories[cid])
        donors[cid] = case['donor_account_id']
        base = base_prompt(query)
        rendered = {'generic': base, 'matched': GUIDANCE + json.dumps(cards[cid], sort_keys=True) + '\n\n' + base}
        if donors[cid] is not None:
            texts = [rows[e]['text'] for e in case['donor_history_event_ids']]
            assert len(texts) == len(histories[cid])
            donor_card = statistics(texts)
            rendered['other-account'] = GUIDANCE + json.dumps(donor_card, sort_keys=True) + '\n\n' + base
            own, other = Counter(map(form, histories[cid])), Counter(map(form, texts))
            contrasts.append({'id': cid, 'identical_visible_card': cards[cid] == donor_card,
                'form_total_variation': sum(abs(own[k] - other[k]) for k in range(12)) / (2 * len(texts))})
        for condition, prompt in rendered.items():
            assert len(prompt) <= 65536, 'Selected prompt exceeds fixed ceiling; no truncation'
            bank.append(dict(case_id=cid, condition=condition, prompt=prompt, prompt_sha256=sha256(prompt.encode()).hexdigest()))
    assert len(queries) == len({q['student_id'] for q in queries}) == 10
    assert len({json.dumps(c, sort_keys=True) for c in cards.values()}) > 1, 'All matched cards identical; close preparation'
    inputs = dict(queries=queries, history=histories, cards=cards, donors=donors)
    prepared = ROOT / 'prepared'
    prepared.mkdir(exist_ok=False)
    save(prepared / 'inputs.json', inputs)
    orders = list(itertools.permutations(('generic', 'matched', 'other-account')))
    schedule = []
    for draw in range(1, 6):
        for index, query in enumerate(queries):
            for condition in orders[((draw - 1) * 10 + index) % 6]:
                if condition == 'other-account' and donors[query['id']] is None:
                    continue
                schedule.append(dict(slot=len(schedule) + 1, case_id=query['id'], draw=draw, condition=condition))
    runner = load_script('experiments/2026-10-01-cross-notebook-run.py')
    pins = runner.required_pins()
    for path in [Path(__file__), Path('docs/2026-10-01-cross-notebook-cards.md'),
                 ROOT / 'frozen.json', ROOT / 'content.json', ROOT / 'events.json',
                 ROOT / 'selection.json', ROOT / 'content-params.json',
                 Path('experiments/2026-10-01-cross-notebook-select.py'),
                 Path('experiments/2026-10-01-cross-notebook-content.sql'),
                 *[Path(m.__file__) for m in (chat_student, student_evidence, retrieval_baseline,
                                            student_continuation, episodes, tutor_moves)]]:
        pins[str(path.resolve())] = digest(path)
    plan = dict(kind='cross-notebook-cards-v1', prepared_at=datetime.now(timezone.utc).isoformat(),
        input_path=str((prepared / 'inputs.json').resolve()), input_sha256=digest(prepared / 'inputs.json'),
        model='gemini-2.5-pro', sdk_version=version('google-genai'),
        configuration=dict(temperature=1.0, max_output_tokens=8192, response_mime_type='application/json',
                           response_json_schema=student_continuation.Continuation.model_json_schema()),
        omitted_settings=['top_p', 'top_k', 'seed', 'thinking_config'], timeout_ms=120000,
        workers=1, sdk_attempts=1, adapter_attempts=1, draws_per_condition=5,
        requests=len(schedule), cases=[{'id': q['id']} for q in queries], schedule=schedule,
        prompt_hashes={f"{r['case_id']}:{r['condition']}": r['prompt_sha256'] for r in bank}, code_pins=pins,
        stopping_rule='One fixed batch and report; no retries, resume, replacements, tuning or automatic follow-up.',
        primary='Equal-account matched minus generic fair form Brier; ten-account missing-outcome bounds')
    save(prepared / 'prompts.json', bank)
    save(prepared / 'plan.json', plan)
    save(prepared / 'contrast.json', {'comparisons': contrasts,
         'unique_matched_cards': len({json.dumps(c, sort_keys=True) for c in cards.values()})})
    with (prepared / 'disclosure.md').open('x') as stream:
        stream.write(f'# Prepared provider payload\n\nGoogle Gemini 2.5 Pro; at most {len(schedule)} requests.\n'
            'Ten private current-conversation prefixes plus aggregate statistics from earlier student queries.\n'
            'No recorded next messages, verbatim historical examples, notebook source export, or raw account IDs.\n'
            'One attempt per slot, five draws per available arm; no retries or follow-up batches.\n\n')
        for row in bank:
            stream.write(f"## {row['case_id']} / {row['condition']}\n\n{row['prompt']}\n\n")
    return dict(cases=len(queries), prompts=len(bank), requests=len(schedule),
                matched_message_counts=[len(t) for t in histories.values()],
                donor_comparisons=contrasts, plan_sha256=digest(prepared / 'plan.json'),
                prompts_sha256=digest(prepared / 'prompts.json'), provider_calls=0)


if __name__ == '__main__':
    check()
    if sys.argv[1:] == ['check']:
        print('Authored full-prefix and statistics-only card checks passed.')
    else:
        assert not sys.argv[1:]
        print(json.dumps(prepare(), indent=2))
