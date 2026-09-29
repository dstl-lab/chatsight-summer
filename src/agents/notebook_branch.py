"""Save one source-only student choice from a recovered initial notebook capture."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
import json
from pathlib import Path

from src.agents import notebook_student as store
from src.eval import notebook_action as action


def _engine():
    from src.agents import student_workspace
    return {Path(path).name:store.digest(Path(path).read_text())
            for path in (__file__, action.__file__, store.__file__, action.sc.__file__,
                         store.llm.__file__, student_workspace.__file__)}


def _folder(folder):
    folder = Path(folder).absolute()
    if any(path.is_symlink() for path in (folder, *folder.parents,
            folder/'checkpoint.json', folder/'decision.json', folder/'.lock')):
        raise ValueError('Branch paths must not contain symlinks.')
    return folder


def _read(path):
    if path.stat().st_size > 4_000_000:
        raise ValueError('Branch file exceeds the supported size.')
    return store._read(path)


def create(folder, *, recovered, instruction_cells, work_cell, model='gemini-2.5-pro'):
    if not isinstance(model, str) or not model.strip():
        raise ValueError('Supply a nonblank model name.')
    task = action.initial_task(recovered, instruction_cells=instruction_cells, work_cell=work_cell)
    if (not all(isinstance(t['text'], str) and t['text'].strip() for t in task['dialogue'])
            or not isinstance(task['work']['source'], str)
            or not all(isinstance(cell['source'], str) for cell in task['task'])):
        raise ValueError('Captured instructions, source and dialogue must be text.')
    manifest = {'version':1, 'kind':'source-only-notebook-branch', 'model':model,
                'engine':_engine(), 'schema':action.Action.model_json_schema(),
                'source':{'recovered_sha256':store.digest(recovered),
                          'instruction_cells':list(instruction_cells), 'work_cell':work_cell},
                'task':task, 'prompt':action.make_prompt(task)}
    if len(json.dumps(manifest).encode()) > 4_000_000:
        raise ValueError('Checkpoint exceeds the supported size.')
    folder = _folder(folder)
    folder.mkdir(parents=True, exist_ok=False)
    store._save(folder/'checkpoint.json', manifest, exclusive=True)
    return deepcopy(manifest)


def _request(manifest):
    return {'checkpoint_sha256':store.digest(manifest), 'prompt':manifest['prompt'],
            'model':manifest['model'], 'single_attempt':True}


def load(folder):
    """Verify saved choices without dispatch, notebook execution or file mutation."""
    folder = _folder(folder)
    manifest = _read(folder/'checkpoint.json')
    if (manifest.get('version') != 1 or manifest.get('kind') != 'source-only-notebook-branch'
            or manifest.get('engine') != _engine() or manifest.get('schema') != action.Action.model_json_schema()
            or manifest.get('prompt') != action.make_prompt(manifest['task'])
            or not isinstance(manifest.get('model'), str) or not manifest['model'].strip()):
        raise ValueError('Checkpoint implementation, schema or prompt changed.')
    receipt = _read(folder/'decision.json') if (folder/'decision.json').exists() else None
    if receipt is not None:
        if receipt.get('request') != _request(manifest) or receipt.get('status') not in ('pending', 'complete', 'error'):
            raise ValueError('Saved request does not match the checkpoint.')
        if receipt['status'] == 'complete':
            response = action.Action.model_validate(receipt['response'])
            if receipt.get('applied') != action.apply_action(manifest['task'], response):
                raise ValueError('Saved action result does not reproduce.')
        elif 'response' in receipt or 'applied' in receipt:
            raise ValueError('An incomplete request cannot establish an action.')
    return manifest, receipt


def step(folder, *, checkpoint_sha256, send=False, generate=None):
    if send is not True:
        raise ValueError('Explicit --send is required.')
    folder = _folder(folder)
    with store._locked(folder):
        manifest, previous = load(folder)
        if store.digest(manifest) != checkpoint_sha256:
            raise ValueError('The inspected checkpoint changed.')
        if previous is not None:
            raise ValueError('A decision request already exists; it cannot be resent.')
        if generate is None:
            from src.agents.student_workspace import _generate_model
            generate = partial(_generate_model, manifest['model'], single_attempt=True)
        receipt = {'status':'pending', 'request':_request(manifest),
                   'started_at':datetime.now(timezone.utc).isoformat()}
        store._save(folder/'decision.json', receipt, exclusive=True)
        try:
            response = action.Action.model_validate(generate(manifest['prompt'], action.Action).model_dump())
            receipt.update(status='complete', response=response.model_dump(),
                           applied=action.apply_action(manifest['task'], response))
        except Exception as error:
            receipt.update(status='error', error={'type':type(error).__name__, 'message':str(error)})
        receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
        store._save(folder/'decision.json', receipt)
        return deepcopy(receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create_parser = commands.add_parser('create')
    create_parser.add_argument('folder', type=Path)
    create_parser.add_argument('--recovered', type=Path, required=True)
    create_parser.add_argument('--instruction-cells', type=int, nargs='+', required=True)
    create_parser.add_argument('--work-cell', type=int, required=True)
    create_parser.add_argument('--model', default='gemini-2.5-pro')
    step_parser = commands.add_parser('step')
    step_parser.add_argument('folder', type=Path)
    step_parser.add_argument('--checkpoint-sha256', required=True)
    step_parser.add_argument('--send', action='store_true')
    show_parser = commands.add_parser('show')
    show_parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'create':
            if args.recovered.is_symlink():
                raise ValueError('Recovered input must not be a symlink.')
            create(args.folder, recovered=_read(args.recovered), instruction_cells=args.instruction_cells,
                   work_cell=args.work_cell, model=args.model)
        elif args.command == 'step':
            step(args.folder, checkpoint_sha256=args.checkpoint_sha256, send=args.send)
        manifest, receipt = load(args.folder)
        print(json.dumps({'checkpoint_sha256':store.digest(manifest),
                          'status':receipt['status'] if receipt else 'ready',
                          'decision':receipt.get('response', {}).get('decision') if receipt else None,
                          'execution':'not-run'}))
        if receipt and receipt['status'] != 'complete':
            raise SystemExit(1)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
