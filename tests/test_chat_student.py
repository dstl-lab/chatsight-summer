"""Saved chat lifecycle checks use invented dialogue and an injected provider."""
from copy import deepcopy
import importlib
import json
import sys

import pytest

from src.eval import student_continuation as sc


QUERY = {
    'id': 'PRIVATE_QUERY_ID', 'conversation_id': 'PRIVATE_CONVERSATION_ID',
    'student_id': 'PRIVATE_STUDENT_ID',
    'prefix': [
        {'role': 'student', 'text': 'values = [2, 5]\n\nprint(values)'},
        {'role': 'tutor', 'text': 'Those are your two values.'},
        {'role': 'student', 'text': ''},
        {'role': 'student', 'text': 'how do i add them'},
        {'role': 'tutor', 'text': 'Try sum(values).'},
        {'role': 'tutor', 'text': 'What result do you get?'},
    ],
}


def files(folder):
    return {str(path.relative_to(folder)): path.read_bytes()
            for path in folder.rglob('*') if path.is_file() and path.name != '.lock'}


def test_saved_chat_reopens_across_two_tutor_exchanges(tmp_path):
    from src.agents import chat_student as chat

    query = deepcopy(QUERY)
    folder = tmp_path / 'student'
    saved = chat.create(folder, query=query, max_decisions=4)
    assert query == QUERY and saved['state']['status'] == 'ready'
    assert saved['decisions'] == 0 and saved['remaining'] == 4
    assert saved['state']['message'] is None
    expected = {
        'context': [dict(turn, id=f'visible-{index}')
                    for index, turn in enumerate(QUERY['prefix'][:2], 1)],
        'turns': [dict(turn, id=f'visible-{index}',
                       phase='request' if turn['role'] == 'student' else 'response')
                  for index, turn in enumerate(QUERY['prefix'][2:], 3)],
    }
    assert sc.make_prompt(saved['state']['episode']) == sc.make_prompt(expected)
    assert 'PRIVATE_' not in sc.make_prompt(saved['state']['episode'])
    first_episode = deepcopy(saved['state']['episode'])
    calls = []
    responses = [sc.Continuation(decision='reply', text='7?'),
                 sc.Continuation(decision='reply', text='can i use this for 3 values'),
                 sc.Continuation(decision='no-reply', text='')]

    def generate(prompt, schema):
        assert schema is sc.Continuation
        calls.append(prompt)
        return responses[len(calls) - 1]

    saved = chat.step(folder, binding=saved['binding'], generate=generate)
    assert calls == [sc.make_prompt(first_episode)]
    assert saved['state']['status'] == 'awaiting-tutor' and saved['state']['message'] == '7?'
    assert saved['decisions'] == 1 and saved['remaining'] == 3
    assert importlib.reload(chat).show(folder) == saved and len(calls) == 1

    reply = 'Yes, the sum is 7.\nTry another list.'
    expected = sc.branch_episode(first_episode, responses[0], reply)
    saved = chat.step(folder, binding=saved['binding'], generate=generate, tutor_reply=reply)
    assert calls[-1] == sc.make_prompt(expected)
    assert saved['state']['message'] == responses[1].text
    assert saved['decisions'] == 2 and saved['remaining'] == 2
    assert importlib.reload(chat).show(folder) == saved and len(calls) == 2

    reply = 'Yes, sum accepts a list of three values too.'
    expected = sc.branch_episode(expected, responses[1], reply)
    saved = chat.step(folder, binding=saved['binding'], generate=generate, tutor_reply=reply)
    assert calls[-1] == sc.make_prompt(expected)
    assert saved['state']['status'] == 'no-reply' and saved['state']['message'] is None
    assert saved['decisions'] == 3 and saved['remaining'] == 1
    before = files(folder)
    assert chat.show(folder) == saved and files(folder) == before
    with pytest.raises(ValueError):
        chat.step(folder, binding=saved['binding'], generate=generate, tutor_reply='Continue?')
    assert len(calls) == 3 and files(folder) == before


def test_guards_preserve_the_session_and_budget_is_not_silence(tmp_path):
    from src.agents import chat_student as chat

    def forbidden(*args, **kwargs):
        pytest.fail('Rejected operation dispatched a provider')

    for index, extra in enumerate(({'response': 'HIDDEN_FUTURE'}, {'labels': ['help']})):
        folder = tmp_path / f'invalid-{index}'
        with pytest.raises(ValueError):
            chat.create(folder, query=QUERY | extra)
        assert not folder.exists()
    folder = tmp_path / 'student'
    saved = chat.create(folder, query=QUERY, max_decisions=1)
    before = files(folder)
    with pytest.raises(FileExistsError):
        chat.create(folder, query=QUERY)
    with pytest.raises(ValueError):
        chat.step(folder, binding=saved['binding'], generate=forbidden, tutor_reply='Unrequested tutor turn')
    # Reusing the same historical seed must still produce a different session binding.
    other = chat.create(tmp_path / 'other', query=QUERY, max_decisions=1)
    with pytest.raises(ValueError):
        chat.step(folder, binding=other['binding'], generate=forbidden)
    with pytest.raises(ValueError):
        chat.step(folder, binding=saved['binding'] | {'state_sha256': '0' * 64}, generate=forbidden)
    assert files(folder) == before
    saved = chat.step(folder, binding=saved['binding'],
                      generate=lambda *_: sc.Continuation(decision='reply', text='7?'))
    assert saved['decisions'] == 1 and saved['remaining'] == 0
    assert saved['state']['status'] == 'awaiting-tutor' and saved['state']['message'] == '7?'
    before = files(folder)
    with pytest.raises(ValueError):
        chat.step(folder, binding=saved['binding'], generate=forbidden, tutor_reply='Yes.')
    assert chat.show(folder) == saved and files(folder) == before

    # Editing only one saved response must fail exact replay, never regenerate it.
    receipt = folder / 'step-0001.json'
    original = receipt.read_text()
    assert '7?' in original
    receipt.write_text(original.replace('7?', '8?', 1))
    changed = files(folder)
    with pytest.raises(ValueError):
        chat.show(folder)
    with pytest.raises(ValueError):
        chat.step(folder, binding=saved['binding'], generate=forbidden, tutor_reply='Yes.')
    assert files(folder) == changed


@pytest.mark.parametrize('interrupted', [False, True])
def test_provider_failure_and_interruption_cannot_resend(tmp_path, interrupted):
    from src.agents import chat_student as chat

    folder = tmp_path / 'student'
    saved = chat.create(folder, query=QUERY)
    calls = []

    def generate(*_):
        assert json.loads((folder / 'step-0001.json').read_text())['status'] == 'pending'
        calls.append('dispatched')
        if interrupted:
            raise KeyboardInterrupt('authored interruption')
        raise RuntimeError('authored provider failure')

    if interrupted:
        with pytest.raises(KeyboardInterrupt):
            chat.step(folder, binding=saved['binding'], generate=generate)
        assert json.loads((folder / 'step-0001.json').read_text())['status'] == 'pending'
        before = files(folder)
        with pytest.raises(ValueError):
            chat.show(folder)
    else:
        saved = chat.step(folder, binding=saved['binding'], generate=generate)
        assert saved['state']['status'] == 'error' and saved['state']['message'] is None
        assert saved['state']['error'] == {'type': 'RuntimeError', 'message': 'authored provider failure'}
        assert saved['decisions'] == 1 and saved['remaining'] == 5
        before = files(folder)
        assert chat.show(folder) == saved
    with pytest.raises(ValueError):
        chat.step(folder, binding=saved['binding'], generate=generate)
    assert calls == ['dispatched'] and files(folder) == before


def test_cli_inspection_and_context_guards_run_before_credentials(tmp_path, monkeypatch, capsys):
    import dotenv
    from src.agents import chat_student as chat
    from src.labeling import llm

    calls = []

    def forbidden(*args, **kwargs):
        pytest.fail('Offline or rejected CLI operation loaded credentials/provider')

    monkeypatch.setattr(dotenv, 'load_dotenv', forbidden)
    monkeypatch.setattr(llm, 'make_generate', forbidden)
    query = tmp_path / 'query.json'
    query.write_text(json.dumps(QUERY))
    folder = tmp_path / 'student'

    def main(*args):
        monkeypatch.setattr(sys, 'argv', ['chat_student', *(str(arg) for arg in args)])
        chat.main()

    main('create', folder, '--query', query, '--max-decisions', '2')
    capsys.readouterr()
    main('show', folder)
    saved = json.loads(capsys.readouterr().out)
    assert saved == chat.show(folder) and saved['remaining'] == 2
    context = tmp_path / 'context.json'
    context.write_text(json.dumps(saved))
    before = files(folder)
    with pytest.raises((ValueError, SystemExit)):
        main('step', folder, '--context-file', context)
    context.write_text(json.dumps(saved | {'state': saved['state'] | {'message': 'edited preview'}}))
    with pytest.raises((ValueError, SystemExit)):
        main('step', folder, '--context-file', context, '--send')
    context.write_text(json.dumps(saved | {'binding': saved['binding'] | {'session_sha256': '0' * 64}}))
    with pytest.raises((ValueError, SystemExit)):
        main('step', folder, '--context-file', context, '--send')
    assert files(folder) == before
    capsys.readouterr()

    monkeypatch.setenv('GEMINI_API_KEY', 'authored-test-key')
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *args, **kwargs: calls.append('credentials'))

    def factory(key, **kwargs):
        assert key == 'authored-test-key'
        calls.append('factory')

        def generate(prompt, schema):
            assert json.loads((folder / 'step-0001.json').read_text())['status'] == 'pending'
            assert prompt == sc.make_prompt(saved['state']['episode']) and schema is sc.Continuation
            calls.append('generate')
            return sc.Continuation(decision='reply', text='7?')
        return generate

    monkeypatch.setattr(llm, 'make_generate', factory)
    context.write_text(json.dumps(saved))
    main('step', folder, '--context-file', context, '--send')
    output = capsys.readouterr().out
    assert 'authored-test-key' not in output
    assert calls.count('factory') == calls.count('generate') == 1
    assert chat.show(folder)['state']['message'] == '7?'
    before = files(folder)
    with pytest.raises((ValueError, SystemExit)):
        main('step', folder, '--context-file', context, '--send')
    assert calls.count('factory') == calls.count('generate') == 1 and files(folder) == before
