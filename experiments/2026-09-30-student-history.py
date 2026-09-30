"""One student-only history development comparison; reuse frozen transport/scoring."""
import argparse
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
from statistics import mean

from src.agents import notebook_student as store
from src.eval import student_history

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / 'experiments/2026-09-29-course-account-history'


def module(name):
    spec = importlib.util.spec_from_file_location('student_history_' + name, LEGACY / f'{name}.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


protocol, transport, scoring = (module(name) for name in ('protocol', 'run', 'report'))


def prepare(previous, expected_plan, expected_prompts, out, reference, expected_reference):
    """Derive new prompts from the same frozen queries, never from recorded targets."""
    previous, out = Path(previous).resolve(), Path(out)
    original, old_bank = transport.inputs(previous, expected_plan, expected_prompts)
    queries = store._read(Path(original['input_path']))
    if (len(queries) != 10 or any(q['student_id'] is None for q in queries)
            or any(len({q[key] for q in queries}) != 10 for key in ('id', 'student_id', 'conversation_id'))):
        raise ValueError('Keep all ten distinct frozen development accounts.')
    bank, cases = [], []
    for query in queries:
        rendered = student_history.prompts(query)
        if rendered['current-exchange'] != old_bank[query['id'], 'current-exchange']:
            raise ValueError('Current exchange must match the original byte-for-byte.')
        if max(map(len, rendered.values())) > protocol.PROMPT_LIMIT:
            raise ValueError('Full prompt exceeds ceiling; do not truncate or replace the case.')
        identical = rendered['current-exchange'] == rendered['student-history']
        cases.append({'id': query['id'], 'identical_prompts': identical})
        bank.extend({'case_id': query['id'], 'condition': condition, 'prompt': prompt,
                     'prompt_sha256': protocol.sha256(prompt.encode()).hexdigest()}
                    for condition, prompt in rendered.items())
    plan = deepcopy(original)
    plan.update(kind='student-only-history-development', prepared_at=transport.now(), cases=cases,
        reference_path=str(Path(reference).resolve()), reference_sha256=expected_reference,
        primary='Equal-account student-history minus current-exchange fair multicategory form Brier',
        population='Ten previously exposed provisional course accounts; development only',
        schedule=[slot | {'condition': 'student-history' if slot['condition'] == 'history' else slot['condition']}
                  for slot in original['schedule']],
        prompt_hashes={f"{row['case_id']}:{row['condition']}": row['prompt_sha256'] for row in bank},
        stopping_rule='One 100-request batch and one report; no retries, replacements, tuning, '
                      'new labels, automatic follow-up or adoption. Interrupted batches stay consumed.')
    plan['code_pins'].update({str(Path(path).resolve()): transport.file_hash(path) for path in
        (__file__, student_history.__file__, transport.__file__, scoring.__file__,
         previous / 'plan.json', previous / 'prompts.json')})
    out.mkdir(parents=True, exist_ok=False)
    store._save(out / 'plan.json', plan, exclusive=True)
    store._save(out / 'prompts.json', bank, exclusive=True)
    disclosure = ['# Student-only history development comparison', '',
        'Destination: Google Gemini 2.5 Pro. Maximum 100 requests: ten existing development',
        'cases × two conditions × five draws. Private conversation prefixes only.',
        'Current exchange is complete in both arms; student-history additionally contains',
        'earlier student turns. No recorded next messages, notebook execution, new labels,',
        'retries, replacement cases, model tuning or automatic follow-up. Temperature 1.0;',
        '8192 output tokens maximum per request; one worker, one attempt per slot.', '', '## Exact prompts', '']
    for row in bank:
        disclosure.extend([f"### {row['case_id']} / {row['condition']}", '', row['prompt'], ''])
    (out / 'disclosure.md').write_text('\n'.join(disclosure))
    return {'plan_sha256': transport.file_hash(out / 'plan.json'),
        'prompts_sha256': transport.file_hash(out / 'prompts.json'),
        'requests': 100, 'identical_prompt_cases': sum(case['identical_prompts'] for case in cases),
        'provider_calls': 0}


def inputs(folder, expected_plan, expected_prompts):
    plan, bank = transport.inputs(folder, expected_plan, expected_prompts)
    queries = store._read(Path(plan['input_path']))
    expected = {(query['id'], condition): prompt for query in queries
                for condition, prompt in student_history.prompts(query).items()}
    slots = {(s['case_id'], s['condition'], s['draw']) for s in plan['schedule']}
    if (plan.get('kind') != 'student-only-history-development' or bank != expected or
            slots != {(q['id'], c, d) for q in queries for c in student_history.CONDITIONS for d in range(1, 6)}):
        raise ValueError('Student-only prompt reconstruction or fixed schedule changed.')
    return plan, bank


def execute(folder, expected_plan, expected_prompts, generate, *, progress=True):
    plan, bank = inputs(folder, expected_plan, expected_prompts)
    out = folder / 'execution'
    out.mkdir(exist_ok=False)
    (out / 'receipts').mkdir()
    (out / 'raw').mkdir()
    approval = folder / 'approval.json'
    store._save(out / 'started.json', {'plan_sha256': expected_plan, 'prompts_sha256': expected_prompts,
        'started_at': transport.now(), 'authorization': {
            'user_request': "Sounds good, let's go back to simulator development after having done experiments regarding this.",
            'standing_preference': 'Continue authorized project work until user input is needed; Gemini project runs approved 2026-09-11.',
            'approval_sha256': transport.file_hash(approval) if approval.exists() else None,
            'scope': plan['stopping_rule']},
        'code_pins': {str(Path(path).resolve()): transport.file_hash(path) for path in
                      (__file__, student_history.__file__, transport.__file__, store.__file__)}}, exclusive=True)
    counts = Counter()
    for slot in plan['schedule']:
        prompt = bank[slot['case_id'], slot['condition']]
        receipt = {**slot, 'status': 'pending', 'started_at': transport.now(), 'plan_sha256': expected_plan,
                   'prompt_sha256': protocol.sha256(prompt.encode()).hexdigest()}
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
            print(json.dumps({'slot': slot['slot'], 'scheduled': 100, 'status': receipt['status']}), flush=True)
    result = {'finished_at': transport.now(), 'scheduled': 100, 'complete': counts['complete'], 'errors': counts['error'],
        'receipt_sha256': {f'receipts/{i:03d}.json': transport.file_hash(out / f'receipts/{i:03d}.json')
                           for i in range(1, 101)}}
    store._save(out / 'completed.json', result, exclusive=True)
    return result


def report(folder):
    """Verify/replay saved responses; keep no-reply and errors as distinct outcomes."""
    started = store._read(folder / 'execution/started.json')
    plan, _ = inputs(folder, started['plan_sha256'], started['prompts_sha256'])
    _, records = transport.read_receipts(folder)
    if transport.file_hash(plan['reference_path']) != plan['reference_sha256']:
        raise ValueError('Frozen reference changed.')
    queries = store._read(Path(plan['input_path']))
    refs = store._read(Path(plan['reference_path']))
    references = {r['id']: r for r in refs}
    if len(refs) != 10 or set(references) != {q['id'] for q in queries}:
        raise ValueError('References must cover the same ten cases exactly once.')
    cases = []
    for query in queries:
        ref = references[query['id']]
        if ref['conversation_id'] != query['conversation_id'] or not ref['text'].strip():
            raise ValueError('Reference does not match the frozen case.')
        arms = {condition: scoring._arm([r for r in records if r['case_id'] == query['id']
                                       and r['condition'] == condition], ref['text'])
                for condition in student_history.CONDITIONS}
        a, b = (arms[c]['form_score'] for c in student_history.CONDITIONS)
        cases.append({'id': query['id'], 'conditions': arms,
            'student_history_minus_current': b-a if a is not None and b is not None else None,
            'baseline_form_score': protocol.empirical_form_score(
                [t['text'] for t in query['prefix'] if t['role'] == 'student'], ref['text'])})
    deltas = [case['student_history_minus_current'] for case in cases]
    paired = [case for case in cases if case['student_history_minus_current'] is not None]
    primary = protocol.paired_summary(deltas)
    primary.update(condition_means={c: mean(case['conditions'][c]['form_score'] for case in paired)
                                    if paired else None for c in student_history.CONDITIONS},
        improved=sum(d < 0 for d in deltas if d is not None),
        worsened=sum(d > 0 for d in deltas if d is not None), tied=sum(d == 0 for d in deltas))
    models = Counter()
    for receipt in records:
        if 'raw_file' in receipt:
            raw = store._read(folder / 'execution' / receipt['raw_file'])
            models[raw.get('model_version') or 'unreported'] += 1
    return {'kind': plan['kind'], 'scheduled_requests': 100, 'primary': primary, 'cases': cases,
        'counts': {c: {s: sum(case['conditions'][c]['counts'][s] for case in cases)
                      for s in ('reply', 'no-reply', 'error')} for c in student_history.CONDITIONS},
        'baseline_form_score': mean(case['baseline_form_score'] for case in cases),
        'model_versions': dict(models), 'identical_prompt_cases': sum(c['identical_prompts'] for c in plan['cases']),
        'provenance': {'plan_sha256': started['plan_sha256'], 'prompts_sha256': started['prompts_sha256'],
            'reference_sha256': plan['reference_sha256'], 'report_code_sha256': transport.file_hash(__file__),
            'completed_sha256': transport.file_hash(folder / 'execution/completed.json')},
        'limits': ['Literal message-form score, not semantic accuracy, learning or overall realism.',
            'Ten exposed development accounts; five draws per arm; no population or significance claim.',
            'Negative contrast favors student-only history on this form measure; no automatic adoption.',
            'The fair-score correction assumes independent stationary draws; prompt order is balanced, seeds unpaired.',
            'No-reply stays category 12; errors leave missing pairs with bounds, never silently become silence.',
            'References condition on returning to chat; real no-reply probabilities are unmeasured.',
            'Identical-prompt cases stay in the analysis and expose sampling variation.',
            'One report closes the batch. No relabeling, retries, replacements, tuning or automatic follow-up.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'report'))
    parser.add_argument('folder', type=Path)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--prompts-sha256')
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'run':
            if not args.send or not os.environ.get('GEMINI_API_KEY'):
                raise ValueError('--send and API key required.')
            execute(args.folder, args.plan_sha256, args.prompts_sha256, transport.live_generate)
        else:
            result = report(args.folder)
            store._save(args.folder / 'report.json', result, exclusive=True)
            print(json.dumps({k: result[k] for k in ('primary', 'counts', 'baseline_form_score', 'model_versions')}))
    except Exception as error:
        parser.exit(1, f'{type(error).__name__}: stopped; private details omitted; no automatic restart.\n')
