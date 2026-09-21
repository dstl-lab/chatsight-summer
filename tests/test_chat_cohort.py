"""One fixed cohort round composes independent saved policy pairs."""
from copy import deepcopy
import importlib.util
import json
import shutil

import pytest

from src.agents import chat_student as chat, notebook_student as store
from tests.test_chat_student import QUERY, files


POLICIES = {'a': 'Give one concise hint.', 'b': 'Give the answer directly.'}
ORDER = [(1, 'a'), (1, 'b'), (2, 'b'), (2, 'a'), (3, 'a'), (3, 'b')]


def forbidden(*_args, **_kwargs):
    pytest.fail('Offline, finished or blocked scenarios must not dispatch a provider')


def sources(tmp_path):
    folders = []
    for case in range(1, 4):
        query = deepcopy(QUERY)
        query.update(id=f'authored-query-{case}', conversation_id=f'authored-conversation-{case}')
        folder = tmp_path / f'source-{case}'
        initial = chat.create(folder, query=query, model='authored-model')
        chat.step(folder, binding=initial['binding'],
                  generate=lambda _, schema: schema(decision='reply', text=f'case {case}?'))
        folders.append(folder)
    return folders


def module(monkeypatch):
    assert importlib.util.find_spec('src.agents.chat_cohort'), 'Fixed cohort coordinator is missing'
    from src.agents import chat_cohort
    monkeypatch.setattr(store.llm, 'make_generate', forbidden)
    return chat_cohort


@pytest.mark.parametrize('failure', ['tutor', 'student', 'interrupted'])
def test_one_fixed_round_retains_failure_without_repeating_or_changing_sources(tmp_path, monkeypatch, failure):
    cohort = module(monkeypatch)
    original = sources(tmp_path)
    before = [files(path) for path in original]
    folder = tmp_path / 'cohort'
    created = cohort.create(folder, sources=original, policies=POLICIES)
    assert created == cohort.show(folder)
    assert [(job['case'], job['condition']) for job in created['order']] == ORDER
    assert len(created['cases']) == 3 and all(row['status'] == 'ready' for row in created['cases'])
    for row in created['cases']:
        assert row['comparison']['max_new_decisions'] == 1
        assert set(row['comparison']['conditions']) == {'a', 'b'}
    with pytest.raises(ValueError):
        cohort.run(folder, generate_tutor=forbidden, generate_student=forbidden)
    calls = []

    def tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        case = int(payload['context']['pending_message'].split()[1][:-1])
        condition = next(name for name, policy in POLICIES.items() if policy == payload['policy'])
        calls.append((case, condition))
        if (case, condition) == (2, 'b') and failure == 'tutor':
            raise RuntimeError('Authored tutor failure')
        if (case, condition) == (2, 'b') and failure == 'interrupted':
            raise KeyboardInterrupt('Authored interrupted tutor')
        return schema(text=f'Authored reply for {case}{condition}.')

    def student(prompt, schema):
        if 'Authored reply for 2b.' in prompt and failure == 'student':
            raise RuntimeError('Authored student failure')
        if 'Authored reply for 3b.' in prompt:
            return schema(decision='no-reply', text='')
        return schema(decision='reply', text='next?')

    if failure == 'interrupted':
        with pytest.raises(KeyboardInterrupt):
            cohort.run(folder, send=True, generate_tutor=tutor, generate_student=student)
        assert calls == [(1, 'a'), (1, 'b'), (2, 'b')]
    saved = cohort.run(folder, send=True, generate_tutor=tutor, generate_student=student)
    assert calls == ORDER
    assert [row['status'] for row in saved['cases']] == ['finished', 'needs-inspection', 'finished']
    failed = saved['cases'][1]['comparison']['conditions']['b']
    if failure == 'student':
        assert failed['snapshot']['status'] == 'error'
    else:
        assert failed['error']
    assert ('incomplete' if failure == 'interrupted' else 'failure') in failed['history'].lower()
    assert saved['cases'][2]['comparison']['conditions']['b']['snapshot']['status'] == 'no-reply'
    for row in saved['cases']:
        for condition in row['comparison']['conditions'].values():
            if not condition['error']:
                assert condition['snapshot']['decisions_remaining'] == 0
    assert [files(path) for path in original] == before
    after = files(folder)
    assert cohort.run(folder, send=True, generate_tutor=forbidden, generate_student=forbidden) == saved
    assert cohort.show(folder) == saved and files(folder) == after


def test_rejects_invalid_group_and_keeps_corrupt_pair_from_hiding_others(tmp_path, monkeypatch):
    cohort = module(monkeypatch)
    original = sources(tmp_path)
    before = [files(path) for path in original]
    for index, chosen in enumerate((original[:2], [original[0], original[0], original[2]])):
        folder = tmp_path / f'rejected-{index}'
        with pytest.raises(ValueError):
            cohort.create(folder, sources=chosen, policies=POLICIES)
        assert not folder.exists()
    with pytest.raises(ValueError):
        cohort.create(original[0] / 'nested', sources=original, policies=POLICIES)
    assert [files(path) for path in original] == before
    folder = tmp_path / 'cohort'
    saved = cohort.create(folder, sources=original, policies=POLICIES)
    with pytest.raises(FileExistsError):
        cohort.create(folder, sources=original, policies=POLICIES)
    path = folder / 'comparisons/case-02/comparison.json'
    path.write_text('{}')
    damaged = cohort.show(folder)
    assert damaged['cases'][0] == saved['cases'][0] and damaged['cases'][2] == saved['cases'][2]
    assert damaged['cases'][1]['status'] == 'needs-inspection' and damaged['cases'][1]['error']
    path = folder / 'cohort.json'
    receipt = store._read(path)
    receipt['plan']['policies']['a'] = 'Changed policy'
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        cohort.show(folder)
    with pytest.raises(ValueError):
        cohort.run(folder, send=True, generate_tutor=forbidden, generate_student=forbidden)


def test_changed_manifest_stops_dispatch_after_the_current_exchange(tmp_path, monkeypatch):
    cohort = module(monkeypatch)
    folder = tmp_path / 'cohort'
    cohort.create(folder, sources=sources(tmp_path), policies=POLICIES)
    calls = []

    def tutor(_, schema):
        calls.append('tutor')
        path = folder / 'cohort.json'
        receipt = store._read(path)
        receipt['plan']['policies']['a'] = 'A later policy.'
        receipt['plan_sha256'] = store.digest(receipt['plan'])
        store._save(path, receipt)
        return schema(text='First tutor reply.')

    with pytest.raises(ValueError, match='changed'):
        cohort.run(folder, send=True, generate_tutor=tutor,
                   generate_student=lambda _, schema: schema(decision='reply', text='next?'))
    assert calls == ['tutor']


def test_failure_before_a_saved_receipt_is_not_silently_hidden(tmp_path, monkeypatch):
    cohort = module(monkeypatch)
    folder = tmp_path / 'cohort'
    created = cohort.create(folder, sources=sources(tmp_path), policies=POLICIES)

    def unwritten(*_args, **_kwargs):
        raise PermissionError('Authored failure before writing a receipt')

    monkeypatch.setattr(cohort.pair, 'respond', unwritten)
    with pytest.raises(PermissionError, match='before writing'):
        cohort.run(folder, send=True, generate_tutor=forbidden, generate_student=forbidden)
    assert cohort.show(folder) == created


@pytest.mark.parametrize('escape', ['session', 'tutor-exchanges'])
def test_external_symlink_cannot_advance_or_change_its_target(tmp_path, monkeypatch, escape):
    cohort = module(monkeypatch)
    folder = tmp_path / 'cohort'
    cohort.create(folder, sources=sources(tmp_path), policies=POLICIES)
    child = folder / 'comparisons/case-02/sessions/a'
    external = tmp_path / 'outside-student'
    if escape == 'session':
        shutil.copytree(child, external)
        shutil.rmtree(child)
    else:
        external.mkdir()
        child = child / 'tutor-exchanges'
    child.symlink_to(external, target_is_directory=True)
    before = files(external)
    blocked = cohort.show(folder)['cases'][1]
    assert blocked['status'] == 'needs-inspection' and blocked['comparison'] is None
    calls = []

    def tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        calls.append(payload['context']['pending_message'])
        return schema(text='Authored tutor reply.')

    cohort.run(folder, send=True, generate_tutor=tutor,
               generate_student=lambda _, schema: schema(decision='no-reply', text=''))
    assert calls == ['case 1?', 'case 1?', 'case 3?', 'case 3?']
    assert cohort.show(folder)['cases'][1] == blocked and files(external) == before
