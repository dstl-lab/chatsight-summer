"""Two fixed tutor policies over independent copies of one cached chat start."""
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from src.agents import chat_student as chat, chat_workspace, notebook_student as store, workspace_history


def _source(folder):
    if sorted(p.name for p in folder.glob('step-*.json')) != ['step-0001.json'] or (folder / 'tutor-exchanges').exists():
        raise ValueError('Use a frozen source with exactly one cached reply and no tutor interventions.')
    # Read frozen evidence without creating or touching its lock file.
    manifest, state, decisions = chat._load(folder)
    first = store._read(folder / 'step-0001.json')
    if decisions != 1 or state['status'] != 'awaiting-tutor' or first['status'] != 'complete':
        raise ValueError('The source needs one completed cached student reply.')
    return manifest, state, first


def create(folder, *, source, policies, max_new_decisions=1):
    """Import the same cached reply twice; never generate or fork later progress."""
    if (not isinstance(policies, dict) or set(policies) != {'a', 'b'} or
            any(not isinstance(p, str) or not p.strip() for p in policies.values())):
        raise ValueError('Supply two nonblank policies, named a and b.')
    if type(max_new_decisions) is not int or not 1 <= max_new_decisions <= 99:
        raise ValueError('Set between 1 and 99 new student decisions per condition.')
    folder, source = Path(folder), Path(source)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    if folder.resolve().is_relative_to(source.resolve()):
        raise ValueError('Keep the comparison outside its frozen source.')
    manifest, state, first = _source(source)
    plan = {
        'version': 1, 'comparison_id': uuid4().hex, 'policies': dict(policies),
        'model': manifest['model'], 'max_new_decisions': max_new_decisions,
        'source': {'session_sha256': store.digest(manifest), 'first_step_sha256': store.digest(first),
                   'state_sha256': store.digest(state), 'saved_started_at': first['started_at'],
                   'saved_finished_at': first['finished_at'],
                   'scope': 'One reused simulated reply. Source timestamps may describe an earlier cache import.'},
    }
    receipt = {'plan': plan, 'plan_sha256': store.digest(plan), 'sessions': {}}
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.chat-policy-pair-') as temporary:
        staged = Path(temporary) / 'pair'
        for name in ('a', 'b'):
            child = staged / 'sessions' / name
            initial = chat.create(child, query=manifest['query'], model=manifest['model'],
                                  max_decisions=max_new_decisions + 1)

            def cached(prompt, schema):
                if prompt != first['request']['prompt'] or schema.model_json_schema() != manifest['engine']['schema']:
                    raise ValueError('Cached import prompt or response schema changed.')
                return schema.model_validate(first['response'])

            imported = chat.step(child, binding=initial['binding'], generate=cached)
            if imported['state'] != state or imported['binding']['session_sha256'] == store.digest(manifest):
                raise ValueError('The imported start must match with a new session identity.')
            receipt['sessions'][name] = {
                'manifest_sha256': store.digest(store._read(child / 'session.json')),
                'first_step_sha256': store.digest(store._read(child / 'step-0001.json')),
            }
        if _source(source) != (manifest, state, first):
            raise ValueError('The frozen source changed during preparation.')
        store._save(staged / 'comparison.json', receipt, exclusive=True)
        # Reserve the destination before publishing; never replace an existing comparison.
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return show(folder)


def _comparison(folder):
    receipt = store._read(folder / 'comparison.json')
    try:
        plan = receipt['plan']
        valid = (set(plan) == {'version', 'comparison_id', 'policies', 'model', 'max_new_decisions', 'source'} and
                 receipt['plan_sha256'] == store.digest(plan) and plan['version'] == 1 and
                 isinstance(plan['comparison_id'], str) and bool(plan['comparison_id']) and
                 isinstance(plan['model'], str) and bool(plan['model'].strip()) and
                 isinstance(plan['source'], dict) and
                 set(plan['policies']) == {'a', 'b'} and set(receipt['sessions']) == {'a', 'b'} and
                 type(plan['max_new_decisions']) is int and 1 <= plan['max_new_decisions'] <= 99 and
                 all(isinstance(p, str) and p.strip() for p in plan['policies'].values()))
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('The comparison plan is incomplete or invalid.') from exc
    if not valid:
        raise ValueError('The fixed comparison plan changed or is invalid.')
    return receipt


def _condition(folder, receipt, name):
    if name not in ('a', 'b'):
        raise ValueError('Choose condition a or b.')
    child = folder / 'sessions' / name
    pins, plan = receipt['sessions'][name], receipt['plan']
    manifest = store._read(child / 'session.json')
    first = store._read(child / 'step-0001.json')
    if (store.digest(manifest) != pins['manifest_sha256'] or store.digest(first) != pins['first_step_sha256'] or
            manifest['max_decisions'] != plan['max_new_decisions'] + 1 or manifest['model'] != plan['model'] or
            store.digest(first['result']) != plan['source']['state_sha256']):
        raise ValueError('The comparison startup files changed.')
    for directory in (child / 'tutor-exchanges').glob('*'):
        tutor = store._read(directory / 'receipt.json')
        if tutor['request']['policy'] != plan['policies'][name]:
            raise ValueError('A saved tutor exchange used a different policy.')
        if tutor['status'] != 'complete' or tutor['continuation']['status'] != 'complete':
            raise ValueError('A tutor exchange failed or is incomplete. Inspect saved results; it will not be resent.')
    for path in sorted(child.glob('step-*.json'))[1:]:
        step = store._read(path)
        binding = step['request']['binding']
        tutor = store._read(child / 'tutor-exchanges' / binding['state_sha256'] / 'receipt.json')
        if (tutor['request']['binding'] != binding or tutor['request']['policy'] != plan['policies'][name] or
                tutor['response']['text'] != step['request']['tutor_reply'] or
                tutor['continuation']['result']['state'] != step['result']):
            raise ValueError('A student step is not linked to the fixed tutor policy.')
    return child


def show(folder):
    """Reopen both saved outcomes independently, including failed/incomplete records."""
    folder = Path(folder)
    receipt = _comparison(folder)
    plan = receipt['plan']
    result = {key: plan[key] for key in ('comparison_id', 'max_new_decisions', 'source')}
    result['conditions'] = {}
    for name in ('a', 'b'):
        item = {'policy': plan['policies'][name], 'snapshot': None, 'error': '', 'history': ''}
        try:
            child = _condition(folder, receipt, name)
            item['snapshot'] = chat_workspace.snapshot(child)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            item['error'] = str(exc)
        try:
            item['history'] = workspace_history.render(folder / 'sessions' / name)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            item['error'] = item['error'] or str(exc)
        result['conditions'][name] = item
    return result


def respond(folder, condition, *, binding, send=False, generate_tutor=None, generate_student=None):
    """Apply only the frozen policy to one explicitly selected, bound condition."""
    chat_workspace._require_binding(binding, send)
    folder = Path(folder)
    receipt = _comparison(folder)
    child = _condition(folder, receipt, condition)
    chat_workspace.respond(child, binding=binding, policy=receipt['plan']['policies'][condition], send=send,
                           generate_tutor=generate_tutor, generate_student=generate_student)
    return show(folder)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('create', help='Prepare a pair offline; never generate.')
    prepare.add_argument('folder', type=Path)
    prepare.add_argument('--source', type=Path, required=True)
    prepare.add_argument('--policy-a', type=Path, required=True)
    prepare.add_argument('--policy-b', type=Path, required=True)
    prepare.add_argument('--max-new-decisions', type=int, default=1)
    inspect = commands.add_parser('show', help='Read both saved results without sending.')
    inspect.add_argument('folder', type=Path)
    args = parser.parse_args()
    result = create(args.folder, source=args.source,
                    policies={name: getattr(args, 'policy_' + name).read_text(encoding='utf-8') for name in ('a', 'b')},
                    max_new_decisions=args.max_new_decisions) if args.command == 'create' else show(args.folder)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
