"""Local student boundaries use authored sessions and fake subprocesses, never MLX."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from src.agents import chat_student as chat, chat_workspace
from tests.test_chat_student import QUERY, files


def read(path):
    return json.loads(path.read_text())


def setup(tmp_path):
    session, model, adapter = [tmp_path / name for name in ('session', 'model', 'adapter')]
    model.mkdir()
    adapter.mkdir()
    (model / 'config.json').write_text('{"model_type":"authored"}')
    (model / 'model.safetensors').write_bytes(b'authored base weights')
    (adapter / 'adapter_config.json').write_text('{}')
    (adapter / 'adapters.safetensors').write_bytes(b'authored adapter weights')
    python = tmp_path / 'python'
    python.write_text('#!/bin/sh\nexit 1\n')
    python.chmod(0o755)
    query = deepcopy(QUERY)
    query['prefix'][0]['text'] = ' 中文\n\n  values = [2, 5]\n'
    initial = chat.create(session, query=query, model='legacy-cloud-label', max_decisions=3)
    return session, model, adapter, python, query, initial


def test_local_callback_preserves_history_and_binds_only_on_first_dispatch(tmp_path, monkeypatch):
    from src.agents import local_student

    session, model, adapter, python, query, initial = setup(tmp_path)
    calls = []

    def run(command, **kwargs):
        assert command[0] == str(python)
        assert command[-2] == 'worker'
        assert kwargs['timeout'] == 120 and kwargs['check'] is False
        assert kwargs['env']['HF_HUB_OFFLINE'] == '1'
        folder = Path(command[-1])
        request = read(folder / 'request.json')
        calls.append(request)
        text = '  学生\n\nreply ' + str(len(calls)) + '\n'
        (folder / 'result.json').write_text(json.dumps({
            'status': 'complete', 'text': text, 'finish_reason': 'stop',
            'request_sha256': sha256((folder / 'request.json').read_bytes()).hexdigest(),
            'generated_token_ids': [42, 99], 'eos_token_ids': [99], 'generation_tokens': 2,
        }))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(local_student.subprocess, 'run', run)
    monkeypatch.setattr(chat.llm, 'make_generate', lambda *a, **kw: pytest.fail('Cloud fallback'))
    before = files(session)
    reply = local_student.make_reply(session, model=model, python=python, adapter=adapter)
    assert files(session) == before and not calls
    first = chat_workspace.advance(session, binding=initial['binding'], send=True, generate_reply=reply)
    assert first['pending_message'] == '  学生\n\nreply 1\n'
    assert calls[0]['prefix'] == query['prefix']
    serialized = calls[0]['messages'][0]['content']
    assert json.loads(serialized[serialized.index('[{'):]) == query['prefix']
    assert calls[0]['seed'] == 20260928
    identity = read(session / 'local-student/backend.json')
    assert identity['model'] == str(model) and identity['adapter'] == str(adapter)
    before = files(session)
    reopened = local_student.make_reply(session, model=model, python=python, adapter=adapter)
    assert files(session) == before
    second = chat_workspace.advance(session, binding=first['binding'], tutor_reply=' 保留\n\n空白 \n',
                                    send=True, generate_reply=reopened)
    assert second['pending_message'] == '  学生\n\nreply 2\n'
    assert calls[1]['prefix'] == query['prefix'] + [
        {'role': 'student', 'text': first['pending_message']},
        {'role': 'tutor', 'text': ' 保留\n\n空白 \n'}]
    assert calls[1]['seed'] == 20260929
    assert len(list((session / 'local-student').glob('call-*'))) == 2


@pytest.mark.parametrize('outcome', ['timeout', 'exit', 'missing', 'length', 'blank', 'wrong-hash'])
def test_failed_calls_are_terminal_and_never_fall_back_or_retry(tmp_path, monkeypatch, outcome):
    from src.agents import local_student

    session, model, _, python, _, initial = setup(tmp_path)
    dispatched = []

    def run(command, **kwargs):
        dispatched.append(command)
        folder = Path(command[-1])
        if outcome == 'timeout':
            raise local_student.subprocess.TimeoutExpired(command, 120)
        if outcome not in ('exit', 'missing'):
            (folder / 'result.json').write_text(json.dumps({
                'status': 'complete', 'text': ' \n' if outcome == 'blank' else 'authored',
                'finish_reason': 'length' if outcome == 'length' else 'stop',
                'request_sha256': 'wrong' if outcome == 'wrong-hash' else
                    sha256((folder / 'request.json').read_bytes()).hexdigest(),
                'generated_token_ids': [42, 99], 'eos_token_ids': [99], 'generation_tokens': 2,
            }))
        return SimpleNamespace(returncode=1 if outcome == 'exit' else 0)

    monkeypatch.setattr(local_student.subprocess, 'run', run)
    monkeypatch.setattr(chat.llm, 'make_generate', lambda *a, **kw: pytest.fail('Cloud fallback'))
    reply = local_student.make_reply(session, model=model, python=python)
    failed = chat_workspace.advance(session, binding=initial['binding'], send=True, generate_reply=reply)
    assert failed['status'] == 'error' and len(dispatched) == 1
    before = files(session)
    with pytest.raises(ValueError):
        chat_workspace.advance(session, binding=failed['binding'], send=True, generate_reply=reply)
    assert files(session) == before and len(dispatched) == 1
    call = session / 'local-student/call-0001'
    assert (call / 'result.json').exists() and (call / 'returncode.json').exists()


def test_unbound_old_sessions_and_mutated_model_reject_before_dispatch(tmp_path, monkeypatch):
    from src.agents import local_student

    session, model, _, python, query, initial = setup(tmp_path)
    monkeypatch.setattr(local_student.subprocess, 'run', lambda *a, **kw: pytest.fail('Unexpected dispatch'))
    reply = local_student.make_reply(session, model=model, python=python)
    with pytest.raises(ValueError):
        reply(query['prefix'])
    (model / 'model.safetensors').write_bytes(b'changed weights')
    result = chat_workspace.advance(session, binding=initial['binding'], send=True, generate_reply=reply)
    assert result['status'] == 'error' and not (session / 'local-student').exists()
    with pytest.raises(ValueError):
        local_student.make_reply(session, model=model, python=python)


@pytest.mark.parametrize('change', ['adapter', 'python', 'weights'])
def test_bound_backend_cannot_switch_configuration_on_reopen(tmp_path, monkeypatch, change):
    from src.agents import local_student

    session, model, adapter, python, _, initial = setup(tmp_path)
    monkeypatch.setattr(local_student.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1))
    reply = local_student.make_reply(session, model=model, python=python)
    chat_workspace.advance(session, binding=initial['binding'], send=True, generate_reply=reply)
    options = {'model': model, 'python': python}
    if change == 'adapter':
        options['adapter'] = adapter
    elif change == 'python':
        other = tmp_path / 'other-python'
        other.write_bytes(python.read_bytes())
        other.chmod(0o755)
        options['python'] = other
    else:
        (model / 'model.safetensors').write_bytes(b'changed after binding')
    before = files(session)
    with pytest.raises(ValueError, match='backend changed'):
        local_student.make_reply(session, **options)
    assert files(session) == before


@pytest.mark.parametrize('failure', [None, 'length', 'non-eos', 'blank', 'context', 'memory'])
def test_worker_decodes_exact_tokens_and_enforces_generation_bounds(tmp_path, monkeypatch, failure):
    from src.agents import local_student

    session, model, adapter, python, query, initial = setup(tmp_path)
    events, token_messages = [], []
    tokenizer = SimpleNamespace(eos_token_ids={99})

    def template(messages, **kwargs):
        assert kwargs == {'tokenize': True, 'add_generation_prompt': True, 'enable_thinking': False}
        token_messages.append(messages)
        return [1] * (3841 if failure == 'context' else 3)

    def decode(tokens, **kwargs):
        assert kwargs == {'skip_special_tokens': False, 'clean_up_tokenization_spaces': False}
        assert 99 not in tokens
        return ' \n' if failure == 'blank' else '  中文\n\n'

    tokenizer.apply_chat_template, tokenizer.decode = template, decode

    def load(path, **kwargs):
        assert path == str(model) and kwargs['adapter_path'] == str(adapter)
        assert kwargs['tokenizer_config'] == {'trust_remote_code': False, 'local_files_only': True}
        events.append('load')
        return SimpleNamespace(eval=lambda: events.append('eval')), tokenizer

    def stream(*args, **kwargs):
        assert events[-1] == ('seed', 20260928)
        assert kwargs['max_tokens'] == 256 and kwargs['prefill_step_size'] == 256
        kwargs['prompt_progress_callback']()
        yield SimpleNamespace(text='中文', token=42, generation_tokens=1, finish_reason=None)
        yield SimpleNamespace(text='', token=43 if failure in ('length', 'non-eos') else 99,
                              generation_tokens=2, finish_reason='length' if failure == 'length' else 'stop')

    mx = SimpleNamespace(set_memory_limit=lambda size: events.append(('limit', size)),
        get_peak_memory=lambda: 16 * 1024**3 + 1 if failure == 'memory' else 123,
        random=SimpleNamespace(seed=lambda seed: events.append(('seed', seed))))
    monkeypatch.setitem(sys.modules, 'mlx', SimpleNamespace(core=mx))
    monkeypatch.setitem(sys.modules, 'mlx.core', mx)
    monkeypatch.setitem(sys.modules, 'mlx_lm', SimpleNamespace(load=load, stream_generate=stream))
    monkeypatch.setitem(sys.modules, 'mlx_lm.utils', SimpleNamespace(load_tokenizer=lambda *a: tokenizer))
    monkeypatch.setitem(sys.modules, 'mlx_lm.sample_utils', SimpleNamespace(make_sampler=lambda **kw: kw))
    monkeypatch.setattr(local_student, 'version', lambda _: 'authored-runtime')
    monkeypatch.setattr(sys, 'executable', str(python))
    dispatches = []

    def run(command, **kwargs):
        dispatches.append(command)
        return SimpleNamespace(returncode=0 if local_student.worker(Path(command[-1])) else 1)

    monkeypatch.setattr(local_student.subprocess, 'run', run)
    reply = local_student.make_reply(session, model=model, python=python, adapter=adapter)
    result = chat_workspace.advance(session, binding=initial['binding'], send=True, generate_reply=reply)
    saved = read(session / 'local-student/call-0001/result.json')
    assert len(dispatches) == 1
    if failure is None:
        assert result['pending_message'] == '  中文\n\n'
        assert saved['text'] != saved['streamed_text'] and saved['generated_token_ids'] == [42, 99]
        assert saved['status'] == 'complete' and saved['finish_reason'] == 'stop'
        content = token_messages[0][0]['content']
        assert json.loads(content[content.index('[{'):]) == query['prefix']
    else:
        assert result['status'] == 'error' and saved['status'] == 'error'
    with pytest.raises(FileExistsError):
        local_student.worker(session / 'local-student/call-0001')
