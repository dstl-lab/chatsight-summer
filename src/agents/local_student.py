"""Offline MLX student callback for one saved chat; model loading runs in a child."""
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eval import student_training


MEMORY_LIMIT = 16 * 1024**3
SETTINGS = {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20,
            'enable_thinking': False, 'context_limit': 4096, 'max_tokens': 256,
            'memory_limit_bytes': MEMORY_LIMIT, 'prefill_step_size': 256,
            'timeout_seconds': 120, 'seed_base': 20260928}
OFFLINE = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
           'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HUB_DISABLE_IMPLICIT_TOKEN': '1',
           'TOKENIZERS_PARALLELISM': 'false', 'PYTHONDONTWRITEBYTECODE': '1'}
TOKENIZER_CONFIG = {'trust_remote_code': False, 'local_files_only': True}


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n')


def _digest(path):
    result = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def _files(folder):
    if not folder.is_dir():
        raise ValueError('Supply an existing local model or adapter directory.')
    result = {str(path.relative_to(folder)): _digest(path)
              for path in sorted(folder.rglob('*')) if path.is_file()}
    if not result:
        raise ValueError('The local model or adapter directory is empty.')
    return result


def _configuration(session, model, python, adapter):
    manifest = session / 'session.json'
    value = _read(manifest)
    if value.get('version') != 1 or not isinstance(value.get('session_id'), str):
        raise ValueError('Supply one saved chat session.')
    student_training.messages(value['query']['prefix'])
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('Supply an existing executable Python runtime.')
    config = {'version': 1, 'role': 'student', 'session_sha256': _digest(manifest),
            'model': str(model), 'adapter': str(adapter) if adapter else None,
            'python': str(python), 'python_sha256': _digest(python),
            'model_files': _files(model), 'adapter_files': _files(adapter) if adapter else None,
            'sources': {str(Path(path).resolve()): _digest(Path(path))
                        for path in (__file__, student_training.__file__)},
            'settings': SETTINGS, 'tokenizer_config': TOKENIZER_CONFIG}
    backend = session / 'local-student/backend.json'
    if backend.exists() and 'cached_start' in (saved := _read(backend)):
        _check_import(session, config, saved['cached_start'])
        config['cached_start'] = saved['cached_start']
    return config


def _complete(folder):
    result = _read(folder / 'result.json')
    tokens, eos = result.get('generated_token_ids'), result.get('eos_token_ids')
    if (result.get('status') != 'complete' or result.get('finish_reason') != 'stop'
            or not isinstance(result.get('text'), str) or not result['text'].strip()
            or result.get('request_sha256') != _digest(folder / 'request.json')
            or not isinstance(tokens, list) or not tokens or not isinstance(eos, list)
            or tokens[-1] not in eos or result.get('generation_tokens') != len(tokens)
            or len(tokens) > SETTINGS['max_tokens']):
        raise ValueError('Local student did not complete a nonblank message at EOS; inspect its saved call.')
    return result['text']


def _no_symlinks(folder):
    if folder.is_symlink() or any(path.is_symlink() for path in folder.rglob('*')):
        raise ValueError('Cached local starts cannot contain symbolic links.')


def _identity(config):
    # A copied start has a new session and current worker, but the same generation setup.
    return {key: value for key, value in config.items()
            if key not in ('session_sha256', 'sources', 'cached_start')}


def _original_backend(source, current=None):
    root = source / 'local-student'
    backend = _read(root / 'backend.json')
    if 'cached_start' in backend or {path.name for path in root.iterdir()} != {'backend.json', 'call-0001'}:
        raise ValueError('Use one original local call, without nested imports or later calls.')
    if current is None:
        current = _configuration(source, Path(backend['model']), Path(backend['python']),
                                 Path(backend['adapter']) if backend['adapter'] else None)
    if (_identity(backend) != _identity(current)
            or backend['session_sha256'] != _digest(source / 'session.json')
            or {Path(path).name for path in backend['sources']} != {'local_student.py', 'student_training.py'}
            or any(_digest(Path(path)) != expected for path, expected in backend['sources'].items())):
        raise ValueError('The original local model, runtime, settings or sources changed.')
    call = root / 'call-0001'
    request, result = _read(call / 'request.json'), _read(call / 'result.json')
    step, manifest = _read(source / 'step-0001.json'), _read(source / 'session.json')
    prepared, started = _read(call / 'prepared.json'), _read(call / 'started.json')
    request_hash, backend_hash = _digest(call / 'request.json'), _digest(root / 'backend.json')
    expected_request = {'role': 'student', 'prefix': manifest['query']['prefix'],
        'messages': student_training.messages(manifest['query']['prefix']), 'backend_sha256': backend_hash,
        'seed': SETTINGS['seed_base'], 'max_tokens': SETTINGS['max_tokens']}
    if (request != expected_request or _read(call / 'returncode.json') != {'returncode': 0, 'timeout': False}
            or step['status'] != 'complete' or step['response'] != {'decision': 'reply', 'text': _complete(call)}
            or result.get('backend_sha256') != backend_hash or result.get('settings') != SETTINGS
            or result.get('role') != 'student' or result.get('seed') != SETTINGS['seed_base']
            or result.get('model') != backend['model'] or result.get('adapter') != backend['adapter']
            or started.get('request_sha256') != request_hash
            or prepared != {'request_sha256': request_hash, 'backend_sha256': backend_hash,
                'runtime': result['runtime'], 'settings': SETTINGS, 'seed': SETTINGS['seed_base'],
                'messages': request['messages'], 'prompt_tokens': result['prompt_tokens']}):
        raise ValueError('The original local call does not match its saved student reply.')
    chunks = [json.loads(line) for line in (call / 'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    if (not chunks or [chunk['token'] for chunk in chunks] != result['generated_token_ids']
            or chunks[-1]['finish_reason'] != 'stop'
            or [chunk['generation_tokens'] for chunk in chunks] != list(range(1, len(chunks) + 1))):
        raise ValueError('The original local token receipts changed.')
    return backend


def _single_start(folder):
    # Parent-side validation only; the MLX child never imports the chat engine.
    from src.agents import chat_student

    _no_symlinks(folder)
    if list(sorted(path.name for path in folder.glob('step-*.json'))) != ['step-0001.json'] or (folder / 'tutor-exchanges').exists():
        raise ValueError('Use exactly one completed student step without a tutor intervention.')
    manifest, state, decisions = chat_student._load(folder)
    if decisions != 1 or state['status'] != 'awaiting-tutor':
        raise ValueError('A cached local start needs one completed pending student reply.')
    return manifest, state, _read(folder / 'step-0001.json')


def validate_start(source):
    """Read-only verification of one original local student call for a policy pair."""
    source = Path(source).absolute()
    _single_start(source)
    return _original_backend(source)


def _check_import(session, current, record):
    archive = session / 'local-student/cached-start'
    _no_symlinks(session / 'local-student')
    if (set(record) != {'files', 'first_step_sha256'} or _files(archive) != record['files']
            or _digest(session / 'step-0001.json') != record['first_step_sha256']):
        raise ValueError('The archived local start or imported first step changed.')
    _original_backend(archive, current)
    original, imported = _read(archive / 'step-0001.json'), _read(session / 'step-0001.json')
    if (original['result'] != imported['result'] or original['response'] != imported['response']
            or original['request']['prompt'] != imported['request']['prompt']
            or imported['request']['tutor_reply'] is not None):
        raise ValueError('The imported first step differs from the archived local reply.')


def import_start(source, child):
    """Archive one original local call beside an already imported first chat step."""
    source, child = Path(source).absolute(), Path(child).absolute()
    root = child / 'local-student'
    if root.exists() or root.is_symlink():
        raise FileExistsError(root)
    backend = validate_start(source)
    source_manifest, source_state, first = _single_start(source)
    child_manifest, child_state, imported = _single_start(child)
    if (child.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(child.resolve())
            or child_manifest['session_id'] == source_manifest['session_id']
            or child_manifest['query'] != source_manifest['query'] or child_state != source_state
            or imported['response'] != first['response'] or imported['request']['prompt'] != first['request']['prompt']):
        raise ValueError('Import the same first reply into a separate fresh child session.')
    current = _configuration(child, Path(backend['model']), Path(backend['python']),
                             Path(backend['adapter']) if backend['adapter'] else None)
    original_files = {name: _digest(source / name) for name in ('session.json', 'step-0001.json')}
    original_files.update({'local-student/' + path: digest for path, digest in _files(source / 'local-student').items()})
    root.mkdir()
    archive = root / 'cached-start'
    archive.mkdir()
    for name in ('session.json', 'step-0001.json'):
        shutil.copyfile(source / name, archive / name)
    shutil.copytree(source / 'local-student', archive / 'local-student')
    record = {'files': original_files, 'first_step_sha256': _digest(child / 'step-0001.json')}
    _check_import(child, current, record)
    _save(root / 'backend.json', current | {'cached_start': record})
    return _read(root / 'backend.json')


def _previous_call(root, index):
    if index == 1 and 'cached_start' in _read(root / 'backend.json'):
        return root / 'cached-start/local-student/call-0001'
    return root / f'call-{index:04}'


def make_reply(session, *, model: Path, python: Path, adapter: Path | None = None):
    """Validate without writes; bind and dispatch only inside a pending chat step."""
    session, model = Path(session).resolve(), Path(model).resolve()
    # Keep the venv executable path: resolving its symlink loses the selected environment.
    python = Path(os.path.abspath(python))
    adapter = Path(adapter).resolve() if adapter is not None else None
    config = _configuration(session, model, python, adapter)
    root = session / 'local-student'
    backend = root / 'backend.json'
    if backend.exists():
        if _read(backend) != config:
            raise ValueError('The saved local backend changed; use a fresh chat session.')
    elif root.exists() or any(session.glob('step-*.json')):
        raise ValueError('A local backend must start with a fresh chat session.')

    def reply(prefix):
        messages = student_training.messages(prefix)
        if _configuration(session, model, python, adapter) != config:
            raise ValueError('The selected local model, runtime, session or sources changed.')
        steps = sorted(session.glob('step-*.json'))
        index = len(steps)
        if (not steps or [p.name for p in steps] != [f'step-{i:04}.json' for i in range(1, index + 1)]
                or _read(steps[-1]).get('status') != 'pending'):
            raise ValueError('Local generation requires the current pending chat step.')
        if backend.exists():
            if _read(backend) != config:
                raise ValueError('The saved local backend changed.')
        else:
            if index != 1:
                raise ValueError('Cannot attach a local backend to earlier generated steps.')
            root.mkdir(exist_ok=False)
            _save(backend, config)
        for earlier in range(1, index):
            _complete(_previous_call(root, earlier))
        folder = root / f'call-{index:04}'
        folder.mkdir(exist_ok=False)
        _save(folder / 'request.json', {'role': 'student', 'prefix': prefix, 'messages': messages,
              'backend_sha256': _digest(backend), 'seed': SETTINGS['seed_base'] + index - 1,
              'max_tokens': SETTINGS['max_tokens']})
        receipt = {'returncode': None, 'timeout': False}
        try:
            with (folder / 'stdout.log').open('x') as stdout, (folder / 'stderr.log').open('x') as stderr:
                process = subprocess.run([str(python), str(Path(__file__).resolve()), 'worker', str(folder)],
                    cwd=Path(__file__).resolve().parents[2], env=dict(os.environ, **OFFLINE),
                    stdout=stdout, stderr=stderr, timeout=SETTINGS['timeout_seconds'], check=False)
            receipt['returncode'] = process.returncode
        except Exception as error:
            receipt.update(timeout=isinstance(error, subprocess.TimeoutExpired), error=type(error).__name__)
            raise RuntimeError('Local student worker failed; inspect its saved call. No retry was made.') from error
        finally:
            _save(folder / 'returncode.json', receipt)
            if not (folder / 'result.json').exists():
                _save(folder / 'result.json', {'status': 'error', 'text': '',
                    'request_sha256': _digest(folder / 'request.json'),
                    'error': 'Worker returned no result; inspect returncode.json and logs.'})
        if receipt['returncode'] != 0:
            raise RuntimeError('Local student worker failed; inspect its saved call. No retry was made.')
        return _complete(folder)

    return reply


def worker(folder):
    """One reserved call; only this child imports MLX or loads weights."""
    folder = Path(folder).resolve()
    if (folder.parent.name != 'local-student' or not folder.name.startswith('call-')
            or not folder.name[5:].isdigit() or int(folder.name[5:]) < 1):
        raise ValueError('Supply a reserved local student call directory.')
    index = int(folder.name[5:])
    if folder.name != f'call-{index:04}':
        raise ValueError('Invalid local call index.')
    started = time.time()
    request_hash = _digest(folder / 'request.json')
    _save(folder / 'started.json', {'started_at_unix': started, 'request_sha256': request_hash})
    result = {'status': 'error', 'text': '', 'streamed_text': '', 'finish_reason': None,
              'prompt_tokens': [], 'generated_token_ids': [], 'generation_tokens': 0,
              'peak_memory_bytes': 0, 'request_sha256': request_hash}
    mx = None
    try:
        os.environ.update(OFFLINE)
        backend = folder.parent / 'backend.json'
        config, request = _read(backend), _read(folder / 'request.json')
        if (set(request) != {'role', 'prefix', 'messages', 'backend_sha256', 'seed', 'max_tokens'}
                or request['role'] != 'student' or request['max_tokens'] != SETTINGS['max_tokens']
                or type(request['seed']) is not int or request['seed'] != SETTINGS['seed_base'] + index - 1
                or request['messages'] != student_training.messages(request['prefix'])
                or request['backend_sha256'] != _digest(backend)):
            raise ValueError('The local student request or backend binding changed.')
        session = folder.parent.parent
        if _read(session / f'step-{index:04}.json').get('status') != 'pending':
            raise ValueError('The local student call needs its pending chat step.')
        model, python = Path(config['model']), Path(config['python'])
        adapter = Path(config['adapter']) if config['adapter'] else None
        if (Path(sys.executable).absolute() != python
                or config != _configuration(session, model, python, adapter)):
            raise ValueError('The pinned local backend or selected runtime changed.')
        result.update(backend_sha256=request['backend_sha256'], settings=SETTINGS,
                      seed=request['seed'], role='student', model=str(model),
                      adapter=str(adapter) if adapter else None,
                      runtime={'python': sys.version, 'prefix': sys.prefix,
                               'packages': {name: version(name) for name in
                                            ('mlx', 'mlx-lm', 'transformers', 'tokenizers')}})
        if index > 1 and result['runtime'] != _read(_previous_call(folder.parent, index - 1) / 'result.json')['runtime']:
            raise ValueError('The local runtime changed since the earlier call.')
        import mlx.core as mx
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
        from mlx_lm.utils import load_tokenizer

        mx.set_memory_limit(MEMORY_LIMIT)

        def check_memory(*_):
            result['peak_memory_bytes'] = int(mx.get_peak_memory())
            if result['peak_memory_bytes'] > MEMORY_LIMIT:
                raise MemoryError('Reported peak memory exceeded 16 GiB.')

        tokenizer = load_tokenizer(model, TOKENIZER_CONFIG)
        tokens = tokenizer.apply_chat_template(request['messages'], tokenize=True,
                                               add_generation_prompt=True, enable_thinking=False)
        result['prompt_tokens'] = tokens
        if not tokens or len(tokens) + SETTINGS['max_tokens'] > SETTINGS['context_limit']:
            raise ValueError('Prompt plus fixed output budget exceeds the context limit.')
        _save(folder / 'prepared.json', {'request_sha256': request_hash, 'backend_sha256': request['backend_sha256'],
              'runtime': result['runtime'], 'settings': SETTINGS, 'seed': request['seed'],
              'messages': request['messages'], 'prompt_tokens': tokens})
        model_instance, tokenizer = load(str(model), tokenizer_config=TOKENIZER_CONFIG,
                                          adapter_path=str(adapter) if adapter else None)
        model_instance.eval()
        check_memory()
        if tokenizer.apply_chat_template(request['messages'], tokenize=True,
                add_generation_prompt=True, enable_thinking=False) != tokens:
            raise ValueError('Loaded model tokenizer changed the prepared prompt.')
        result['eos_token_ids'] = sorted(tokenizer.eos_token_ids)
        with (folder / 'chunks.jsonl').open('x', encoding='utf-8') as chunks:
            # Adapter loading consumes randomness; seed sampling after loading.
            mx.random.seed(request['seed'])
            for chunk in stream_generate(model_instance, tokenizer, tokens, max_tokens=SETTINGS['max_tokens'],
                    sampler=make_sampler(temp=0.7, top_p=0.8, top_k=20), prefill_step_size=256,
                    prompt_progress_callback=check_memory):
                result['streamed_text'] += chunk.text
                result['generated_token_ids'].append(int(chunk.token))
                result['generation_tokens'] = int(chunk.generation_tokens)
                result['finish_reason'] = chunk.finish_reason
                content = result['generated_token_ids']
                if chunk.finish_reason == 'stop':
                    if content[-1] not in tokenizer.eos_token_ids:
                        raise ValueError('Stop did not end at a tokenizer message boundary.')
                    content = content[:-1]
                # Streaming detokenization strips leading space; decode actual token IDs.
                result['text'] = tokenizer.decode(content, skip_special_tokens=False,
                                                  clean_up_tokenization_spaces=False)
                chunks.write(json.dumps({'text': chunk.text, 'token': int(chunk.token),
                    'generation_tokens': int(chunk.generation_tokens), 'finish_reason': chunk.finish_reason},
                    ensure_ascii=False, allow_nan=False) + '\n')
                chunks.flush()
                check_memory()
        if (result['finish_reason'] != 'stop' or not result['text'].strip()
                or not result['generated_token_ids']
                or result['generation_tokens'] != len(result['generated_token_ids'])
                or result['generation_tokens'] > SETTINGS['max_tokens']):
            raise ValueError('Local generation requires a complete nonblank EOS message.')
        result['status'] = 'complete'
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if mx is not None:
            result['peak_memory_bytes'] = int(mx.get_peak_memory())
        result['elapsed_seconds'] = time.time() - started
        _save(folder / 'result.json', result)
    return result['status'] == 'complete'


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'worker':
        raise SystemExit(0 if worker(Path(sys.argv[2])) else 1)
    raise SystemExit('Usage: local_student.py worker CALL_DIR')
