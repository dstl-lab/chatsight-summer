"""Save and continue a dialogue-only student; no notebook or label state is inferred."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from src.agents import notebook_student as store
from src.eval import retrieval_baseline, student_continuation as continuation
from src.labeling import episodes, llm, tutor_moves


def _engine():
    return {'schema': continuation.Continuation.model_json_schema(), 'sources': {
        Path(path).name: store.digest(Path(path).read_text()) for path in [__file__, *(
            module.__file__ for module in (store, continuation, retrieval_baseline, episodes, tutor_moves, llm))]}}


def _initial(query):
    query = retrieval_baseline.Query.model_validate(query)
    turns = [{'id': f'visible-{i}', 'role': t.role, 'text': t.text, 'origin': 'source'}
             for i, t in enumerate(query.prefix, 1)]
    response = len(turns)
    while response and turns[response - 1]['role'] == 'tutor':
        response -= 1
    request = response
    while request and turns[request - 1]['role'] == 'student':
        request -= 1
    episode = {'id': 'chat-seed', 'context': turns[:request], 'turns': [
        turn | {'phase': 'request' if i < response else 'response'}
        for i, turn in enumerate(turns) if i >= request]}
    continuation.make_prompt(episode)
    return {'episode': episode, 'status': 'ready', 'message': None}


def _snapshot(manifest, state, decisions):
    return {'state': deepcopy(state), 'decisions': decisions,
            'remaining': manifest['max_decisions'] - decisions,
            'binding': {'session_sha256': store.digest(manifest), 'state_sha256': store.digest(state)}}


def _prepare(state, tutor_reply):
    state = deepcopy(state)
    if state['status'] == 'awaiting-tutor':
        state['episode'] = continuation.branch_episode(state['episode'],
            continuation.Continuation(decision='reply', text=state['message']), tutor_reply)
        state.update(status='ready', message=None)
    elif state['status'] != 'ready':
        raise ValueError('A terminal chat cannot continue.')
    elif tutor_reply is not None:
        raise ValueError('A tutor reply requires a pending student message.')
    return state


def _result(prepared, receipt):
    state = deepcopy(prepared)
    if receipt['status'] == 'complete':
        response = continuation.Continuation.model_validate(receipt['response'])
        state.update(status='awaiting-tutor' if response.decision == 'reply' else 'no-reply',
                     message=response.text if response.decision == 'reply' else None)
    elif receipt['status'] == 'error':
        error = receipt['error']
        if (not isinstance(error, dict) or set(error) != {'type', 'message'}
                or any(not isinstance(value, str) for value in error.values())):
            raise ValueError('Invalid saved error.')
        state.update(status='error', error=deepcopy(error))
    else:
        raise ValueError('An incomplete operation cannot resend; inspect its receipt.')
    return state


def _load(folder):
    manifest = store._read(folder / 'session.json')
    if (manifest.get('version') != 1 or manifest.get('engine') != _engine()
            or not isinstance(manifest.get('session_id'), str) or not manifest['session_id']
            or type(manifest.get('max_decisions')) is not int or not 1 <= manifest['max_decisions'] <= 100
            or not isinstance(manifest.get('model'), str) or not manifest['model'].strip()):
        raise ValueError('Session implementation/schema or settings changed; preserve its original environment.')
    state = _initial(manifest['query'])
    paths = sorted(folder.glob('step-*.json'))
    if len(paths) > manifest['max_decisions']:
        raise ValueError('Saved operations exceed the decision budget.')
    for index, path in enumerate(paths, 1):
        if path.name != f'step-{index:04}.json':
            raise ValueError('Session operation sequence is incomplete.')
        receipt = store._read(path)
        if receipt['status'] not in ('complete', 'error'):
            raise ValueError('An incomplete operation cannot resend; inspect its receipt.')
        request = receipt['request']
        if request['binding'] != _snapshot(manifest, state, index - 1)['binding']:
            raise ValueError('Saved operation does not match the session/state binding.')
        prepared = _prepare(state, request['tutor_reply'])
        if request['prompt'] != continuation.make_prompt(prepared['episode']):
            raise ValueError('Saved prompt does not reproduce.')
        state = _result(prepared, receipt)
        if receipt['result'] != state:
            raise ValueError('Saved result does not reproduce.')
    return manifest, state, len(paths)


def create(folder, *, query, model='gemini-2.5-pro', max_decisions=6):
    if type(max_decisions) is not int or not 1 <= max_decisions <= 100:
        raise ValueError('Set a decision budget between 1 and 100.')
    if not isinstance(model, str) or not model.strip():
        raise ValueError('Supply a model name.')
    query = retrieval_baseline.Query.model_validate(query).model_dump()
    state = _initial(query)
    manifest = {'version': 1, 'session_id': uuid4().hex, 'engine': _engine(), 'query': query,
                'model': model, 'max_decisions': max_decisions}
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    store._save(folder / 'session.json', manifest, exclusive=True)
    return _snapshot(manifest, state, 0)


def show(folder):
    """Reconstruct the saved conversation without a provider or execution call."""
    folder = Path(folder)
    with store._locked(folder):
        return _snapshot(*_load(folder))


def step(folder, *, binding, generate, tutor_reply=None):
    """One decision, bound to inspected state; interrupted calls never auto-resend."""
    folder = Path(folder)
    with store._locked(folder):
        manifest, state, decisions = _load(folder)
        if binding != _snapshot(manifest, state, decisions)['binding']:
            raise ValueError('Stale session/state binding: inspect the chat again.')
        if decisions >= manifest['max_decisions']:
            raise ValueError('Decision budget exhausted; this is not student silence.')
        prepared = _prepare(state, tutor_reply)
        prompt = continuation.make_prompt(prepared['episode'])
        receipt = {'status': 'pending', 'started_at': datetime.now(timezone.utc).isoformat(),
                   'request': {'binding': deepcopy(binding), 'tutor_reply': tutor_reply, 'prompt': prompt}}
        path = folder / f'step-{decisions + 1:04}.json'
        store._save(path, receipt, exclusive=True)
        try:
            response = continuation.Continuation.model_validate(
                generate(prompt, continuation.Continuation).model_dump())
            receipt.update(status='complete', response=response.model_dump())
        except Exception as error:
            receipt.update(status='error', error={'type': type(error).__name__, 'message': str(error)})
        state = _result(prepared, receipt)
        receipt.update(result=state, finished_at=datetime.now(timezone.utc).isoformat())
        store._save(path, receipt)
        return _snapshot(manifest, state, decisions + 1)


def main():
    import argparse
    import os
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create', 'show', 'step'])
    parser.add_argument('folder', type=Path)
    parser.add_argument('--query', type=Path, help='Strict historical prefix JSON; create only.')
    parser.add_argument('--max-decisions', type=int, help='Fixed session budget; create only, default 6.')
    parser.add_argument('--context-file', type=Path, help='Snapshot exported by show, required for step.')
    parser.add_argument('--tutor-file', type=Path, help='Supplied tutor reply after a student message.')
    parser.add_argument('--send', action='store_true', help='Allow one Gemini decision; no code execution.')
    args = parser.parse_args()
    if args.command == 'create':
        if not args.query or args.send or args.tutor_file or args.context_file:
            parser.error('create requires --query, without --send or tutor/context files.')
        result = create(args.folder, query=store._read(args.query),
                        max_decisions=args.max_decisions if args.max_decisions is not None else 6)
    elif args.command == 'show':
        if args.send or args.query or args.tutor_file or args.context_file or args.max_decisions is not None:
            parser.error('show is read-only and accepts only the session folder.')
        result = show(args.folder)
    else:
        if not args.send or not args.context_file or args.query or args.max_decisions is not None:
            parser.error('step requires --send and --context-file, without --query.')
        context = store._read(args.context_file)
        if (not isinstance(context.get('binding'), dict)
                or context['binding'].get('state_sha256') != store.digest(context.get('state'))):
            parser.error('The context state or binding changed; export show again.')

        def generate(prompt, schema):
            load_dotenv(Path.cwd() / '.env')
            load_dotenv(Path(__file__).resolve().parents[3] / 'main/.env')
            provider = llm.make_generate(os.environ['GEMINI_API_KEY'],
                                         model=store._read(args.folder / 'session.json')['model'])
            return provider(prompt, schema)

        result = step(args.folder, binding=context['binding'], generate=generate,
                      tutor_reply=args.tutor_file.read_text(encoding='utf-8') if args.tutor_file else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['state']['status'] == 'error':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
