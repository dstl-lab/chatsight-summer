"""Student history must not remove the current tutor reply or leak future text."""
import importlib.util
import json
from pathlib import Path

import pytest

from src.eval import student_continuation


def module(path):
    spec = importlib.util.spec_from_file_location('student_history_check_' + path.stem, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def query():
    return {'id': 'PRIVATE_CASE', 'conversation_id': 'PRIVATE_CONVERSATION', 'student_id': 'PRIVATE_ACCOUNT',
        'prefix': [{'role': role, 'text': text} for role, text in (
            ('tutor', 'EARLIER_TUTOR_ONE'), ('student', 'earlier\n\n student'),
            ('tutor', 'EARLIER_TUTOR_TWO'), ('student', 'older question'),
            ('tutor', 'EARLIER_TUTOR_THREE'), ('student', 'current one'),
            ('student', 'current two'), ('tutor', 'current reply one'), ('tutor', 'current reply two'))]}


def test_student_history_preserves_current_blocks_and_empty_history():
    root = Path(__file__).parents[1]
    path = root / 'src/eval/student_history.py'
    assert path.exists(), 'Student-only history is not implemented.'
    candidate = module(path)
    original = module(root / 'experiments/2026-09-29-course-account-history/protocol.py')
    q = query()
    before = json.dumps(q)
    old, _ = original.prompts(q)
    prompts = candidate.prompts(q)
    visible = {k: json.loads(p[len(student_continuation.PROMPT):]) for k, p in prompts.items()}
    assert prompts['current-exchange'] == old['current-exchange']
    assert visible['student-history']['turns'] == json.loads(old['history'][len(student_continuation.PROMPT):])['turns']
    assert [t['role'] for t in visible['student-history']['turns']] == ['student', 'student', 'tutor', 'tutor']
    assert [t['id'] for t in visible['student-history']['context']] == ['context-1', 'context-2']
    assert visible['student-history']['context'][0]['lines'] == [
        {'line': 1, 'text': 'earlier'}, {'line': 3, 'text': ' student'}]
    assert all(secret not in prompts['student-history'] for secret in ('EARLIER_TUTOR', 'PRIVATE_'))
    assert json.dumps(q) == before
    for prefix in (q['prefix'][-4:], [q['prefix'][0], *q['prefix'][-4:]]):
        pair = candidate.prompts(q | {'prefix': prefix})
        assert pair['current-exchange'] == pair['student-history']
    with pytest.raises(ValueError):
        candidate.prompts(q | {'response': 'FUTURE_SECRET'})


def test_bounded_student_history_run_replays_without_retries_or_target_leakage(tmp_path):
    root = Path(__file__).parents[1]
    path = root / 'experiments/2026-09-30-student-history.py'
    assert path.exists(), 'Student-only comparison runner is not implemented.'
    run = module(path)
    queries = [query() | {'id': str(i), 'conversation_id': 'c' + str(i), 'student_id': 's' + str(i)}
               for i in range(10)]
    queries[-1]['prefix'] = [queries[-1]['prefix'][0], *queries[-1]['prefix'][-4:]]
    source, refs = tmp_path / 'queries.json', tmp_path / 'references.json'
    source.write_text(json.dumps(queries))
    refs.write_text(json.dumps([{'id': q['id'], 'conversation_id': q['conversation_id'],
                                'text': 'FUTURE_SECRET'} for q in queries]))
    previous, folder = tmp_path / 'previous', tmp_path / 'new'
    old = run.protocol.prepare(source, run.transport.file_hash(source), previous)
    frozen = run.prepare(previous, old['plan_sha256'], old['prompts_sha256'],
                         folder, refs, run.transport.file_hash(refs))
    plan, bank = run.inputs(folder, frozen['plan_sha256'], frozen['prompts_sha256'])
    assert frozen['identical_prompt_cases'] == 1
    assert len(plan['schedule']) == 100 and len(bank) == 20
    first_conditions = [slot['condition'] for slot in plan['schedule'][::2]]
    assert first_conditions.count('current-exchange') == first_conditions.count('student-history') == 25
    assert all('FUTURE_SECRET' not in prompt for prompt in bank.values())
    calls = []

    def generate(_plan, prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise TimeoutError('DO_NOT_SAVE_PRIVATE_EXCEPTION')
        choice = {'decision': 'reply', 'text': 'ok'} if len(calls) % 2 else {'decision': 'no-reply', 'text': ''}
        return {'candidates': [{'finish_reason': 'STOP', 'content': {'parts': [{'text': json.dumps(choice)}]}}]}

    run.execute(folder, frozen['plan_sha256'], frozen['prompts_sha256'], generate, progress=False)
    assert len(calls) == 100
    result = run.report(folder)
    assert result['primary']['complete_pairs'] == 9
    assert result['primary']['all_ten_mean'] is None
    assert result['counts']['current-exchange']['error'] == 1
    assert sum(c['no-reply'] for c in result['counts'].values()) == 50
    assert 'DO_NOT_SAVE_PRIVATE_EXCEPTION' not in (folder / 'execution/receipts/001.json').read_text()
    with pytest.raises(FileExistsError):
        run.execute(folder, frozen['plan_sha256'], frozen['prompts_sha256'], generate, progress=False)
    assert len(calls) == 100
    with pytest.raises(FileExistsError):
        run.prepare(previous, old['plan_sha256'], old['prompts_sha256'], folder, refs, run.transport.file_hash(refs))
    refs.write_text('[]')
    with pytest.raises(ValueError):
        run.report(folder)
