"""Workspace continuation keeps chat evidence distinct and cannot resend an exchange."""
import importlib.util
import json

import pytest

from src.agents import chat_student as chat
from src.eval.student_continuation import Continuation
from tests.test_chat_student import QUERY, files


def test_policy_and_manual_continuation_reopen_with_origins_and_fixed_budget(tmp_path):
    assert importlib.util.find_spec('src.agents.chat_workspace'), 'Chat workspace is missing'
    from src.agents import chat_workspace as workspace

    folder = tmp_path / 'scenario'
    saved = chat.create(folder, query=QUERY, max_decisions=3)
    chat.step(folder, binding=saved['binding'], generate=lambda *_: Continuation(decision='reply', text='7?'))
    shown = workspace.snapshot(folder)
    assert shown['work'] is None and shown['changes'] is None and shown['feedback'] is None
    assert shown['pending_message'] == '7?' and shown['decisions_remaining'] == 2
    assert [(t['role'], t['text']) for t in shown['dialogue']] == [
        (t['role'], t['text']) for t in QUERY['prefix']]
    assert {t['origin'] for t in shown['dialogue']} == {'source'}
    calls = []

    def tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        assert payload['policy'] == 'Give concise feedback.'
        assert payload['context']['pending_message'] == '7?'
        assert 'PRIVATE_' not in prompt
        assert [t['text'] for t in payload['context']['dialogue']] == [t['text'] for t in QUERY['prefix']]
        assert '7?' not in [t['text'] for t in payload['context']['dialogue']]
        calls.append('tutor')
        return schema(text='Yes, the sum is 7.')

    def student(prompt, schema):
        assert 'Yes, the sum is 7.' in prompt
        calls.append('student')
        return schema(decision='reply', text='3 values too?')

    options = dict(binding=shown['binding'], policy='Give concise feedback.', send=True,
                   generate_tutor=tutor, generate_student=student)
    before = files(folder)
    for change in ({'send': False}, {'binding': {}}, {'policy': ' '}):
        with pytest.raises(ValueError):
            workspace.respond(folder, **(options | change))
    assert files(folder) == before and not calls
    after = workspace.respond(folder, **options)
    assert calls == ['tutor', 'student'] and after['decisions_remaining'] == 1
    assert after['pending_message'] == '3 values too?'
    assert after['dialogue'][-2:] == [
        {'role': 'student', 'text': '7?', 'origin': 'generated'},
        {'role': 'tutor', 'text': 'Yes, the sum is 7.', 'origin': 'scripted'}]
    assert workspace.snapshot(folder) == after
    receipt = json.loads((folder/'tutor-exchanges'/shown['binding']['state_sha256']/'receipt.json').read_text())
    assert receipt['request']['policy'] == 'Give concise feedback.'
    assert receipt['response']['text'] == 'Yes, the sum is 7.'
    assert receipt['continuation']['status'] == 'complete'
    with pytest.raises(ValueError, match='[Ss]tale'):
        workspace.respond(folder, **options)
    assert calls == ['tutor', 'student']
    stopped = workspace.advance(folder, binding=after['binding'], send=True, tutor_reply='Yes.',
        generate=lambda *_: Continuation(decision='no-reply', text=''))
    assert stopped['status'] == 'no-reply' and stopped['decisions_remaining'] == 0
    assert workspace.snapshot(folder) == stopped
    with pytest.raises(ValueError):
        workspace.respond(folder, **(options | {'binding': stopped['binding']}))
    assert calls == ['tutor', 'student']


def test_interrupted_tutor_cannot_resend_and_concurrent_advance_rejects_delivery(tmp_path):
    assert importlib.util.find_spec('src.agents.chat_workspace'), 'Chat workspace is missing'
    from src.agents import chat_workspace as workspace

    for mode in ('interrupted', 'changed'):
        folder = tmp_path / mode
        saved = chat.create(folder, query=QUERY)
        chat.step(folder, binding=saved['binding'], generate=lambda *_: Continuation(decision='reply', text='7?'))
        shown = workspace.snapshot(folder)
        calls = []

        def tutor(prompt, schema):
            path = folder/'tutor-exchanges'/shown['binding']['state_sha256']/'receipt.json'
            assert json.loads(path.read_text())['status'] == 'pending'
            calls.append('tutor')
            if mode == 'interrupted':
                raise KeyboardInterrupt('Interrupted authored call')
            workspace.advance(folder, binding=shown['binding'], send=True, tutor_reply='Concurrent reply.',
                generate=lambda *_: Continuation(decision='reply', text='another?'))
            return schema(text='Outdated reply.')

        def forbidden(*_):
            pytest.fail('A stale or interrupted operation sent another student request')

        options = dict(binding=shown['binding'], policy='Brief help.', send=True,
                       generate_tutor=tutor, generate_student=forbidden)
        with pytest.raises(KeyboardInterrupt if mode == 'interrupted' else ValueError):
            workspace.respond(folder, **options)
        before = files(folder)
        with pytest.raises((FileExistsError, ValueError)):
            workspace.respond(folder, **options)
        assert files(folder) == before and calls == ['tutor']
        if mode == 'changed':
            assert workspace.snapshot(folder)['pending_message'] == 'another?'
            assert all(t['text'] != 'Outdated reply.' for t in workspace.snapshot(folder)['dialogue'])
