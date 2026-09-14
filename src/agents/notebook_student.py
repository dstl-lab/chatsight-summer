"""A saved, bounded notebook student that can receive a tutor's next reply."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile

from src.eval import notebook_action, notebook_check, notebook_runtime, notebook_session
from src.eval import student_continuation
from src.eval.student_task import RecordedFailure
from src.labeling import llm

Action = notebook_session.Action
digest = student_continuation._digest
V1_SOURCE = 'b8d4f639d7640b838b423e7df02cb3b096606b2fb8e645fa7ed557f740a61232'  # b2a417b


def _engine():
    modules = [notebook_session, notebook_action, notebook_check, notebook_runtime, student_continuation, llm]
    return {'schema': Action.model_json_schema(), 'sources': {
        Path(p).name: digest(Path(p).read_text()) for p in [__file__, *(m.__file__ for m in modules)]}}


def _compatible_engine(saved):
    current = _engine()
    legacy = deepcopy(current)
    legacy['sources']['notebook_student.py'] = V1_SOURCE
    return saved == current or saved == legacy


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f'Unreadable or incomplete session record: {path.name}') from exc


def _save(path, value, *, exclusive=False):
    encoded = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    if exclusive:
        with path.open('x') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        return
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _locked(folder):
    # ponytail: one local POSIX session lock; use a service store for multiple hosts.
    with (Path(folder) / '.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('This student session is busy.') from exc
        yield


def create(folder, *, task, activity, branch_id, model='gemini-2.5-pro', max_decisions=12, timeout=10):
    if type(max_decisions) is not int or not 1 <= max_decisions <= 100:
        raise ValueError('Set a session budget between 1 and 100 model decisions.')
    if not isinstance(model, str) or not model.strip():
        raise ValueError('Supply a model name.')
    initial = notebook_session.initial_state(task, activity=activity, branch_id=branch_id, timeout=timeout)
    dialogue = initial['dialogue']
    if (not isinstance(dialogue, list) or not dialogue or dialogue[-1].get('role') != 'tutor'
            or any(t.get('role') not in ('student', 'tutor') or not isinstance(t.get('text'), str)
                   or not t['text'].strip() for t in dialogue)):
        raise ValueError('Supply visible student/tutor dialogue ending with a tutor reply.')
    manifest = {'version': 1, 'engine': _engine(), 'initial': initial, 'model': model,
                'provenance': {key: deepcopy(task[key]) for key in ('captured_at', 'omitted') if key in task},
                'max_decisions': max_decisions,
                'authorization': 'Standing project Gemini approval; supplied tutor turns are interventions.'}
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    _save(folder / 'session.json', manifest, exclusive=True)
    return deepcopy(initial)


def _prepare(state, tutor_reply, max_actions):
    if type(max_actions) is not int or not 1 <= max_actions <= 6:
        raise ValueError('Use one to six decisions per step.')
    if state['status'] not in ('active', 'awaiting-tutor'):
        raise ValueError('A terminal student encounter cannot resume.')
    state = deepcopy(state)
    if state['status'] == 'awaiting-tutor':
        if not isinstance(tutor_reply, str) or not tutor_reply.strip():
            raise ValueError('Supply the next tutor reply before continuing.')
        if not isinstance(state['message'], str) or not state['message'].strip():
            raise ValueError('Awaiting-tutor state has no student message.')
        state['dialogue'].extend([
            {'role': 'student', 'text': state['message'], 'origin': 'generated'},
            {'role': 'tutor', 'text': tutor_reply, 'origin': 'supplied'},
        ])
        state.update(message=None, status='active')
    elif tutor_reply is not None:
        raise ValueError('A tutor reply requires a pending student message.')
    notebook_session.make_prompt(state)  # Validate the carried observation before any dispatch.
    return state


def _run(state, generate, check, max_actions):
    for _ in range(max_actions):
        try:
            state = notebook_session.advance(state, generate(notebook_session.make_prompt(state), Action),
                                             check=check, origin='model')
        except Exception as exc:
            state = deepcopy(state)
            state.update(status='error', error=deepcopy(exc.error) if isinstance(exc, RecordedFailure)
                         else {'type': type(exc).__name__, 'message': str(exc)})
        if state['status'] != 'active':
            break
    return {'state': state, 'stop_reason': 'action-limit' if state['status'] == 'active' else state['status']}


def _load(folder):
    manifest = _read(folder / 'session.json')
    if manifest.get('version') != 1 or not _compatible_engine(manifest.get('engine')):
        raise ValueError('Session implementation/schema changed; preserve its original environment.')
    state, decisions = manifest['initial'], 0
    paths = sorted(folder.glob('step-*.json'))
    for index, path in enumerate(paths, 1):
        if path.name != f'step-{index:04}.json':
            raise ValueError('Session operation sequence is incomplete.')
        receipt = _read(path)
        if 'version' not in receipt:
            if 'engine' in receipt or manifest['engine']['sources']['notebook_student.py'] != V1_SOURCE:
                raise ValueError('Missing operation version/engine outside the legacy receipt format.')
        elif receipt['version'] != 2 or receipt.get('engine') != _engine():
            raise ValueError('Saved operation engine changed or is unsupported.')
        request = receipt['request']
        if receipt['status'] != 'complete':
            raise ValueError('An incomplete operation cannot automatically resend; inspect its receipt.')
        if request['state_sha256'] != digest(state) or request['session_sha256'] != digest(manifest):
            raise ValueError('Saved operation does not match the current session state.')
        if request['max_actions'] > manifest['max_decisions'] - decisions:
            raise ValueError('Saved operation exceeds the session budget.')
        state = _prepare(state, request['tutor_reply'], request['max_actions'])
        calls, position = receipt['calls'], 0
        replay_mismatches = []

        def replay(kind, expected):
            nonlocal position
            if position >= len(calls):
                replay_mismatches.append('missing')
                raise ValueError('Missing saved call.')
            call = calls[position]
            position += 1
            if call['kind'] != kind or call['request'] != expected or call['status'] not in ('complete', 'error'):
                replay_mismatches.append('changed')
                raise ValueError('Changed or incomplete saved call.')
            if call['status'] == 'error':
                raise RecordedFailure(call['error'])
            return deepcopy(call['response'])

        result = _run(state,
            lambda prompt, schema: schema.model_validate(replay('model', {'prompt': prompt, 'schema': schema.model_json_schema()})),
            lambda work, **kwargs: replay('check', {'work': work, **kwargs}), request['max_actions'])
        if replay_mismatches or position != len(calls) or result != receipt['result']:
            raise ValueError('Saved operation does not reproduce; no calls were dispatched.')
        decisions += sum(call['kind'] == 'model' for call in calls)
        state = result['state']
    return manifest, deepcopy(state), paths, decisions


def load(folder):
    """Rebuild from saved choices and checks; never invoke Gemini or Docker."""
    with _locked(folder):
        return _load(Path(folder))[1]


def step(folder, *, generate, check, tutor_reply=None, max_actions=3,
         expected_state_sha256=None, expected_session_sha256=None):
    """Persist one bounded operation. Interrupted dispatch blocks automatic resending."""
    folder = Path(folder)
    with _locked(folder):
        manifest, state, paths, decisions = _load(folder)
        if (expected_state_sha256 is None) != (expected_session_sha256 is None):
            raise ValueError('Supply both expected session and state hashes.')
        if expected_state_sha256 is not None and (
                expected_state_sha256 != digest(state) or expected_session_sha256 != digest(manifest)):
            raise ValueError('Stale tutor context: inspect the current student before replying.')
        prepared = _prepare(state, tutor_reply, max_actions)
        remaining = manifest['max_decisions'] - decisions
        if remaining <= 0:
            raise ValueError('Session model-decision budget exhausted; this is not student silence.')
        max_actions = min(max_actions, remaining)
        receipt = {'version': 2, 'engine': _engine(), 'status': 'pending',
                   'started_at': datetime.now(timezone.utc).isoformat(), 'calls': [],
                   'request': {'state_sha256': digest(state), 'session_sha256': digest(manifest),
                               'tutor_reply': tutor_reply, 'max_actions': max_actions}}
        path = folder / f'step-{len(paths)+1:04}.json'
        _save(path, receipt, exclusive=True)

        def exchange(kind, request, dispatch):
            call = {'kind': kind, 'request': request, 'status': 'pending',
                    'started_at': datetime.now(timezone.utc).isoformat()}
            receipt['calls'].append(call)
            _save(path, receipt)
            try:
                response = dispatch()
                call.update(status='complete', response=response)
            except Exception as exc:
                call.update(status='error', error={'type': type(exc).__name__, 'message': str(exc)})
                call['finished_at'] = datetime.now(timezone.utc).isoformat()
                _save(path, receipt)
                raise RecordedFailure(call['error']) from exc
            call['finished_at'] = datetime.now(timezone.utc).isoformat()
            _save(path, receipt)
            return response

        result = _run(prepared,
            lambda prompt, schema: schema.model_validate(exchange('model', {'prompt': prompt, 'schema': schema.model_json_schema()},
                lambda: schema.model_validate(generate(prompt, schema).model_dump()).model_dump())),
            lambda work, **kwargs: exchange('check', {'work': work, **kwargs}, lambda: check(work, **kwargs)), max_actions)
        receipt.update(status='complete', result=result, finished_at=datetime.now(timezone.utc).isoformat())
        _save(path, receipt)
        return result


def main():
    import argparse
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create', 'show', 'step'])
    parser.add_argument('folder', type=Path)
    parser.add_argument('--task', type=Path)
    parser.add_argument('--activity', type=Path)
    parser.add_argument('--max-decisions', type=int, default=12)
    parser.add_argument('--max-actions', type=int, default=3)
    parser.add_argument('--tutor-file', type=Path, help='Exact supplied tutor reply, read as UTF-8.')
    parser.add_argument('--context-file', type=Path, help='Bind the reply to an exported tutor context.')
    parser.add_argument('--send', action='store_true', help='Allow this step to call Gemini and requested local checks.')
    args = parser.parse_args()
    if args.context_file and (args.command != 'step' or not args.tutor_file):
        parser.error('--context-file requires step with --tutor-file.')
    if args.command == 'create':
        if not args.task or not args.activity or args.send or args.tutor_file:
            parser.error('create requires --task and --activity, without --send or --tutor-file.')
        state = create(args.folder, task=_read(args.task), activity=_read(args.activity),
                       branch_id='synthetic/' + args.folder.name, max_decisions=args.max_decisions)
        result = {'state': state, 'stop_reason': 'initialized'}
    elif args.command == 'show':
        if args.send or args.tutor_file:
            parser.error('show is read-only.')
        result = {'state': load(args.folder), 'stop_reason': 'saved-state'}
    else:
        if not args.send:
            parser.error('step requires --send; use show for offline replay.')
        tutor = args.tutor_file.read_text(encoding='utf-8') if args.tutor_file else None
        binding = {}
        if args.context_file:
            from src.agents.tutor_context import read_handoff
            binding = {'expected_' + key:value for key,value in read_handoff(args.context_file)['binding'].items()}
        provider = None

        def generate(prompt, schema):
            nonlocal provider
            if provider is None:
                load_dotenv(Path.cwd() / '.env')
                load_dotenv(Path(__file__).resolve().parents[3] / 'main/.env')
                provider = llm.make_generate(os.environ['GEMINI_API_KEY'], model=_read(args.folder / 'session.json')['model'])
            return provider(prompt, schema)

        result = step(args.folder, generate=generate, check=notebook_runtime.check_work,
                      tutor_reply=tutor, max_actions=args.max_actions, **binding)
    state = result['state']
    print(json.dumps({key: state[key] for key in ('status', 'message', 'work', 'observation')} |
                     {'stop_reason': result['stop_reason'], 'actions': len(state['history'])}, ensure_ascii=False, indent=2))
    if state['status'] in ('error', 'environment-error', 'execution-limit'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
