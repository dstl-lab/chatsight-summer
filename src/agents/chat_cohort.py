"""One fixed round over three conversation scenarios and two tutor policies."""
import json
import os
from pathlib import Path
import re
import tempfile

from src.agents import chat_policy_pair as pair, notebook_student as store


ORDER = [{'case': case, 'condition': condition} for case, condition in
         [(1, 'a'), (1, 'b'), (2, 'b'), (2, 'a'), (3, 'a'), (3, 'b')]]
SCOPE = ('Three conversation scenarios, not reconstructed individual students. One new student '
         'decision per policy and case; at most twelve logical model requests. '
         'Saved outcomes do not establish student fidelity, learning or policy effects.')


def create(folder, *, sources, policies):
    """Publish three independent policy pairs offline, without touching their sources."""
    if not isinstance(sources, (list, tuple)) or len(sources) != 3:
        raise ValueError('Supply exactly three frozen conversation sources.')
    folder, sources = Path(folder), [Path(source) for source in sources]
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    if any(folder.resolve().is_relative_to(source.resolve()) for source in sources):
        raise ValueError('Keep the cohort outside its frozen sources.')
    originals = [pair._source(source) for source in sources]
    if len({manifest['query']['conversation_id'] for manifest, _, _ in originals}) != 3:
        raise ValueError('Use three distinct source conversations.')
    models = {manifest['model'] for manifest, _, _ in originals}
    if len(models) != 1:
        raise ValueError('All three sources must use the same model.')
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.chat-cohort-') as temporary:
        staged = Path(temporary) / 'cohort'
        pins = {}
        for case, source in enumerate(sources, 1):
            child = staged / 'comparisons' / f'case-{case:02}'
            pair.create(child, source=source, policies=policies, max_new_decisions=1)
            pins[str(case)] = store.digest(store._read(child / 'comparison.json'))
        if [pair._source(source) for source in sources] != originals:
            raise ValueError('A frozen source changed during preparation.')
        plan = {'version': 1, 'policies': dict(policies), 'model': models.pop(),
                'order': ORDER, 'comparisons': pins}
        store._save(staged / 'cohort.json', {'plan': plan, 'plan_sha256': store.digest(plan)}, exclusive=True)
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return show(folder)


def _plan(folder):
    receipt = store._read(folder / 'cohort.json')
    try:
        plan = receipt['plan']
        valid = (set(receipt) == {'plan', 'plan_sha256'} and
                 receipt['plan_sha256'] == store.digest(plan) and
                 set(plan) == {'version', 'policies', 'model', 'order', 'comparisons'} and
                 type(plan['version']) is int and plan['version'] == 1 and
                 isinstance(plan['model'], str) and bool(plan['model'].strip()) and
                 set(plan['policies']) == {'a', 'b'} and
                 all(isinstance(value, str) and value.strip() for value in plan['policies'].values()) and
                 plan['order'] == ORDER and all(type(job['case']) is int for job in plan['order']) and
                 set(plan['comparisons']) == {'1', '2', '3'} and
                 all(isinstance(pin, str) and re.fullmatch('[0-9a-f]{64}', pin)
                     for pin in plan['comparisons'].values()))
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('The fixed cohort manifest is incomplete or invalid.') from exc
    if not valid:
        raise ValueError('The fixed cohort manifest changed or is invalid.')
    return plan


def _ready(condition):
    snapshot = condition['snapshot']
    return (not condition['error'] and snapshot is not None and
            snapshot['status'] == 'awaiting-tutor' and snapshot['decisions_remaining'] > 0)


def _case(folder, plan, case):
    item = {'case': case, 'status': 'needs-inspection', 'error': '', 'comparison': None}
    child = folder / 'comparisons' / f'case-{case:02}'
    try:
        if not child.resolve().is_relative_to(folder.resolve()):
            raise ValueError('A comparison points outside this cohort.')
        if child.is_symlink() or any(path.is_symlink() for path in child.rglob('*')):
            raise ValueError('Comparison files and directories must not be symbolic links.')
        receipt = store._read(child / 'comparison.json')
        if (store.digest(receipt) != plan['comparisons'][str(case)] or
                receipt['plan']['policies'] != plan['policies'] or receipt['plan']['model'] != plan['model'] or
                receipt['plan']['max_new_decisions'] != 1):
            raise ValueError('The fixed comparison startup changed.')
        item['comparison'] = pair.show(child)
        conditions = item['comparison']['conditions'].values()
        errors = [condition['error'] or 'Student generation failed.' for condition in conditions
                  if condition['error'] or (condition['snapshot'] is not None and
                                           condition['snapshot']['status'] == 'error')]
        item['error'] = '\n'.join(errors)
        item['status'] = 'ready' if any(_ready(condition) for condition in conditions) else (
            'needs-inspection' if errors else 'finished')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        item['error'] = str(exc)
    return item


def show(folder):
    """Reopen all three comparisons, retaining each failed or damaged case."""
    folder = Path(folder)
    plan = _plan(folder)
    return {'version': 1, 'policies': plan['policies'], 'model': plan['model'], 'order': plan['order'],
            'cases': [_case(folder, plan, case) for case in range(1, 4)], 'scope': SCOPE}


def run(folder, *, send=False, generate_tutor=None, generate_student=None):
    """Continue untouched ready arms once; never resend failed or interrupted arms."""
    if send is not True:
        raise ValueError('Explicit send=True is required to run the fixed cohort.')
    folder = Path(folder)
    plan = _plan(folder)
    for job in plan['order']:
        if _plan(folder) != plan:
            raise ValueError('The fixed cohort manifest changed during this run.')
        item = _case(folder, plan, job['case'])
        if item['comparison'] is None:
            continue
        condition = item['comparison']['conditions'][job['condition']]
        if _ready(condition):
            try:
                pair.respond(folder / 'comparisons' / f"case-{job['case']:02}", job['condition'],
                             binding=condition['snapshot']['binding'], send=True,
                             generate_tutor=generate_tutor, generate_student=generate_student)
            except Exception:
                # Continue only when existing records expose the failure; never hide an unwritten error.
                saved = _case(folder, plan, job['case'])['comparison']
                if saved is not None:
                    failed = saved['conditions'][job['condition']]
                    if not failed['error'] and (failed['snapshot'] is None or
                                               failed['snapshot']['status'] != 'error'):
                        raise
    if _plan(folder) != plan:
        raise ValueError('The fixed cohort manifest changed during this run.')
    return show(folder)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('create', help='Prepare exactly three policy pairs offline.')
    prepare.add_argument('folder', type=Path)
    prepare.add_argument('--source', action='append', type=Path, required=True)
    prepare.add_argument('--policy-a', type=Path, required=True)
    prepare.add_argument('--policy-b', type=Path, required=True)
    for command in ('show', 'run'):
        subparser = commands.add_parser(command)
        subparser.add_argument('folder', type=Path)
        if command == 'run':
            subparser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    if args.command == 'create':
        result = create(args.folder, sources=args.source, policies={
            name: getattr(args, 'policy_' + name).read_text(encoding='utf-8') for name in ('a', 'b')})
    else:
        result = run(args.folder, send=args.send) if args.command == 'run' else show(args.folder)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
