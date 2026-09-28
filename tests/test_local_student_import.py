"""Policy arms archive one authored local call; no MLX/provider is contacted."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from src.agents import chat_student as chat, chat_workspace, local_student
from tests.test_chat_student import files
from tests.test_local_student import setup, read


def source(tmp_path, monkeypatch):
    session, model, adapter, python, query, initial = setup(tmp_path)
    calls = []
    tokenizer = SimpleNamespace(eos_token_ids={99},
        apply_chat_template=lambda *a, **kw: [1, 2, 3],
        decode=lambda *a, **kw: '  authored\n')
    mx = SimpleNamespace(set_memory_limit=lambda _: None, get_peak_memory=lambda: 123,
                         random=SimpleNamespace(seed=lambda _: None))

    def stream(*a, **kw):
        yield SimpleNamespace(text='authored', token=42, generation_tokens=1, finish_reason=None)
        yield SimpleNamespace(text='', token=99, generation_tokens=2, finish_reason='stop')

    monkeypatch.setitem(sys.modules, 'mlx', SimpleNamespace(core=mx))
    monkeypatch.setitem(sys.modules, 'mlx.core', mx)
    monkeypatch.setitem(sys.modules, 'mlx_lm', SimpleNamespace(
        load=lambda *a, **kw: (SimpleNamespace(eval=lambda: None), tokenizer), stream_generate=stream))
    monkeypatch.setitem(sys.modules, 'mlx_lm.utils', SimpleNamespace(load_tokenizer=lambda *a: tokenizer))
    monkeypatch.setitem(sys.modules, 'mlx_lm.sample_utils', SimpleNamespace(make_sampler=lambda **kw: kw))
    monkeypatch.setattr(local_student, 'version', lambda _: 'authored-runtime')
    monkeypatch.setattr(sys, 'executable', str(python))

    def run(command, **kw):
        folder = Path(command[-1])
        calls.append((folder, read(folder / 'request.json')))
        return SimpleNamespace(returncode=0 if local_student.worker(folder) else 1)

    monkeypatch.setattr(local_student.subprocess, 'run', run)
    reply = local_student.make_reply(session, model=model, python=python, adapter=adapter)
    saved = chat_workspace.advance(session, binding=initial['binding'], send=True, generate_reply=reply)
    assert saved['status'] == 'awaiting-tutor'
    return session, model, adapter, python, query, calls


def cached_child(path, session, query, *, text=None):
    initial = chat.create(path, query=query, model='legacy-cloud-label', max_decisions=2)
    original = read(session / 'step-0001.json')['response']
    return chat.step(path, binding=initial['binding'], generate=lambda _, schema:
                     schema.model_validate(original if text is None else {'decision': 'reply', 'text': text}))


def test_import_preserves_receipts_and_each_arm_starts_at_call_two(tmp_path, monkeypatch):
    session, model, adapter, python, query, calls = source(tmp_path, monkeypatch)
    before = files(session)
    assert local_student.validate_start(session) == read(session / 'local-student/backend.json')
    for arm in ('a', 'b'):
        child = tmp_path / arm
        start = cached_child(child, session, query)
        local_student.import_start(session, child)
        root = child / 'local-student'
        assert (root / 'cached-start/session.json').read_bytes() == (session / 'session.json').read_bytes()
        assert (root / 'cached-start/step-0001.json').read_bytes() == (session / 'step-0001.json').read_bytes()
        assert files(root / 'cached-start/local-student') == files(session / 'local-student')
        assert not (root / 'call-0001').exists()
        assert read(root / 'backend.json')['session_sha256'] != read(session / 'local-student/backend.json')['session_sha256']
        imported = files(child)
        reply = local_student.make_reply(child, model=model, python=python, adapter=adapter)
        assert files(child) == imported
        result = chat_workspace.advance(child, binding=start['binding'], tutor_reply=f'Tutor {arm}\n\n',
                                        send=True, generate_reply=reply)
        assert result['pending_message'] == '  authored\n'
        assert calls[-1][0] == root / 'call-0002'
        assert calls[-1][1]['seed'] == 20260929
        assert calls[-1][1]['prefix'] == query['prefix'] + [
            {'role': 'student', 'text': '  authored\n'}, {'role': 'tutor', 'text': f'Tutor {arm}\n\n'}]
        assert list(root.glob('call-*')) == [root / 'call-0002']
    assert len(calls) == 3 and files(session) == before


@pytest.mark.parametrize('change', ['archive', 'imported-step'])
def test_import_tampering_blocks_before_another_call(tmp_path, monkeypatch, change):
    session, model, adapter, python, query, calls = source(tmp_path, monkeypatch)
    child = tmp_path / 'child'
    cached_child(child, session, query)
    local_student.import_start(session, child)
    path = (child / 'local-student/cached-start/local-student/call-0001/result.json'
            if change == 'archive' else child / 'step-0001.json')
    path.write_text(path.read_text() + '\n')
    before = files(child)
    with pytest.raises(ValueError):
        local_student.make_reply(child, model=model, python=python, adapter=adapter)
    assert files(child) == before and len(calls) == 1


@pytest.mark.parametrize('change', ['different-reply', 'extra-call', 'symlink', 'model',
                                     'source-pin', 'runtime', 'seed'])
def test_invalid_start_cannot_create_a_backend(tmp_path, monkeypatch, change):
    session, _, _, _, query, calls = source(tmp_path, monkeypatch)
    child = tmp_path / 'child'
    cached_child(child, session, query, text='different' if change == 'different-reply' else None)
    if change == 'extra-call':
        (session / 'local-student/call-0002').mkdir()
    elif change == 'symlink':
        (session / 'linked').symlink_to(session / 'session.json')
    elif change == 'model':
        (tmp_path / 'model/model.safetensors').write_bytes(b'changed')
    elif change == 'source-pin':
        path = session / 'local-student/backend.json'
        backend = read(path)
        backend['sources'][next(iter(backend['sources']))] = '0' * 64
        path.write_text(json.dumps(backend))
    elif change in ('runtime', 'seed'):
        path = session / 'local-student/call-0001/result.json'
        result = read(path)
        result[change] = {} if change == 'runtime' else 17
        path.write_text(json.dumps(result))
    before = files(child)
    with pytest.raises(ValueError):
        local_student.import_start(session, child)
    assert files(child) == before and not (child / 'local-student').exists() and len(calls) == 1


def test_import_cannot_be_nested_or_repeated(tmp_path, monkeypatch):
    session, _, _, _, query, calls = source(tmp_path, monkeypatch)
    child, grandchild = tmp_path / 'child', tmp_path / 'grandchild'
    cached_child(child, session, query)
    cached_child(grandchild, session, query)
    local_student.import_start(session, child)
    with pytest.raises(FileExistsError):
        local_student.import_start(session, child)
    with pytest.raises(ValueError):
        local_student.import_start(child, grandchild)
    assert not (grandchild / 'local-student').exists() and len(calls) == 1
