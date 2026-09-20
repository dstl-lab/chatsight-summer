"""Saved results explain real receipts without dispatching or changing them."""
import importlib.util
import json

import pytest

from src.agents import chat_student as chat, chat_workspace, notebook_student as notebook
from src.eval.student_continuation import Continuation
from tests.test_chat_student import QUERY, files
from tests.test_notebook_session import ACTIVITY, TASK, observation


def test_saved_policy_and_manual_results_reopen_without_calls(tmp_path, monkeypatch):
    assert importlib.util.find_spec('src.agents.workspace_history'), 'Saved results view is missing'
    from src.agents.workspace_history import render

    folder = tmp_path/'chat'
    first = chat.create(folder, query=QUERY, max_decisions=3)
    chat.step(folder, binding=first['binding'], generate=lambda *_: Continuation(decision='reply', text='7?'))
    after = chat_workspace.respond(folder, binding=chat.show(folder)['binding'], send=True,
        policy='Use one hint.\nKeep `sum` visible.',
        generate_tutor=lambda _, schema: schema(text='Try the same function.'),
        generate_student=lambda _, schema: schema(decision='reply', text='3 values too?'))
    chat_workspace.advance(folder, binding=after['binding'], send=True, tutor_reply='Yes.',
        generate=lambda _, schema: schema(decision='no-reply', text=''))
    before = files(folder)
    monkeypatch.setattr(notebook.llm, 'make_generate', lambda *_a, **_k: pytest.fail('Inspection contacted provider'))
    text = render(folder)
    assert text.count('Use one hint.') == text.count('Try the same function.') == 1
    assert 'Keep `sum` visible.' in text and '3 values too?' in text
    assert 'Supplied tutor reply' in text and 'Yes.' in text
    assert 'Student chose no reply' in text and '0 decisions remaining' in text
    assert 'No tutor intervention' in text and 'Saved record time' in text
    assert 'PRIVATE_' not in text
    assert render(folder) == text and files(folder) == before
    budget_folder = tmp_path/'budget'
    initial = chat.create(budget_folder, query=QUERY, max_decisions=1)
    chat.step(budget_folder, binding=initial['binding'],
              generate=lambda *_: Continuation(decision='reply', text='7?'))
    paused = render(budget_folder)
    assert 'Decision budget exhausted' in paused and 'not student silence' in paused
    assert 'Student chose no reply' not in paused
    # A damaged policy receipt must not attribute a different answer to this step.
    path = next((folder/'tutor-exchanges').glob('*/receipt.json'))
    changed = json.loads(path.read_text())
    changed['response']['text'] = 'A different saved answer.'
    path.write_text(json.dumps(changed))
    text = render(folder)
    assert 'Tutor policy used' not in text and 'no confirmed policy link' in text
    assert 'A different saved answer.' in text and 'Try the same function.' in text


@pytest.mark.parametrize('mode', ['tutor-interrupted', 'tutor-error', 'student-interrupted', 'student-error', 'stale'])
def test_failed_or_incomplete_exchange_remains_visible(tmp_path, mode):
    assert importlib.util.find_spec('src.agents.workspace_history'), 'Saved results view is missing'
    from src.agents.workspace_history import render

    folder = tmp_path/mode
    first = chat.create(folder, query=QUERY)
    chat.step(folder, binding=first['binding'], generate=lambda *_: Continuation(decision='reply', text='7?'))
    binding = chat.show(folder)['binding']

    def tutor(_, schema):
        if mode == 'tutor-interrupted':
            raise KeyboardInterrupt('authored interruption')
        if mode == 'tutor-error':
            raise RuntimeError('authored tutor failure')
        if mode == 'stale':
            chat_workspace.advance(folder, binding=binding, send=True, tutor_reply='Concurrent manual reply.',
                generate=lambda _, schema: schema(decision='reply', text='manual result'))
        return schema(text='Saved tutor answer.')

    def student(*_):
        if mode == 'student-interrupted':
            raise KeyboardInterrupt('authored interruption')
        raise RuntimeError('authored student failure')

    try:
        chat_workspace.respond(folder, binding=binding, send=True, policy='A saved policy.',
                               generate_tutor=tutor, generate_student=student)
    except (KeyboardInterrupt, RuntimeError, ValueError):
        pass
    before = files(folder)
    text = render(folder)
    assert 'A saved policy.' in text
    if mode in ('tutor-interrupted', 'student-interrupted'):
        assert 'incomplete' in text.lower() and 'automatically retried' in text
    if mode == 'tutor-error':
        assert 'authored tutor failure' in text and 'No saved tutor reply' in text
    if mode in ('student-interrupted', 'student-error', 'stale'):
        assert 'Saved tutor answer.' in text
    if mode == 'student-error':
        assert 'authored student failure' in text and 'Student generation failed' in text
    if mode == 'stale':
        assert 'Concurrent manual reply.' in text and 'manual result' in text
        assert 'Delivery failed' in text
        assert text.count('Saved tutor answer.') == 1
    assert files(folder) == before
    # One damaged receipt must not hide the other saved evidence or become a no-reply.
    (folder/'tutor-exchanges'/binding['state_sha256']/'receipt.json').write_text('{')
    text = render(folder)
    assert 'unreadable' in text.lower() and '7?' in text
    if mode == 'tutor-interrupted':
        # Reserving a tutor exchange can itself be interrupted before its receipt exists.
        (folder/'tutor-exchanges'/binding['state_sha256']/'receipt.json').unlink()
        assert 'unreadable' in render(folder).lower()


def test_notebook_result_shows_quiet_actions_and_local_check(tmp_path):
    assert importlib.util.find_spec('src.agents.workspace_history'), 'Saved results view is missing'
    from src.agents.workspace_history import render
    from src.agents import student_workspace, tutor_context

    folder = tmp_path/'notebook'
    notebook.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/history', max_decisions=4)
    notebook.step(folder, generate=lambda _, schema: schema(decision='reply', source=None, text='this?'),
                  check=observation, max_actions=1)
    student_workspace.respond(folder, binding=tutor_context.snapshot(folder)['binding'], send=True,
        policy='Show a distinct count.', generate_tutor=lambda _, schema: schema(text='Count each shade once.'),
        generate_student=lambda _, schema: schema(decision='revise-work', source='n_shades = 2', text=''),
        check=observation)
    actions = iter([notebook.Action(decision='request-check', source=None, text=''),
                    notebook.Action(decision='no-reply', source=None, text='')])
    notebook.step(folder, generate=lambda *_: next(actions), check=observation, max_actions=2)
    before = files(folder)
    text = render(folder)
    assert 'Show a distinct count.' in text and 'Count each shade once.' in text
    assert 'Work edited' in text and 'n_shades = 2' in text
    assert 'Local check' in text and 'Student chose no reply' in text
    assert '0 decisions remaining' in text and files(folder) == before
    # A crash after a call is saved but before the operation closes is still incomplete.
    path = folder/'step-0003.json'
    pending = json.loads(path.read_text())
    pending['status'] = 'pending'
    pending.pop('result')
    path.write_text(json.dumps(pending))
    partial = render(folder)
    assert 'Local check' in partial and 'Operation incomplete' in partial
    assert '0 decisions remaining' not in partial
