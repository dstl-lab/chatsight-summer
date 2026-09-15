"""Start a fresh task with bounded shared observed history from completed encounters."""
from contextlib import ExitStack
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from src.agents import notebook_student as student


def _observed(state):
    shared = deepcopy({key:state[key] for key in ('task', 'dialogue', 'work', 'status')})
    shared.update(activity={k:v for k,v in state['activity'].items() if k != 'image_id'},
        observation=student.notebook_session._feedback(state['observation']),
        history=[deepcopy(event) | {'observation':student.notebook_session._feedback(event['observation'])}
                 for event in state['history']])
    return shared


def _ended(state):
    return (state['status'] == 'no-reply' and bool(state['history'])
            and state['history'][-1]['action']['decision'] == 'no-reply'
            and state['history'][-1]['origin'] == 'model')


def lineage(folder, stack, *, previous=None):
    """Read and verify the saved chain oldest first; hold read-only locks in stack."""
    entries, seen = [], set()
    folder = Path(folder).resolve()
    while True:
        if folder in seen:
            raise ValueError('Ancestry contains a cycle.')
        seen.add(folder)
        try:
            stream = stack.enter_context((folder / '.lock').open('rb'))
        except FileNotFoundError as exc:
            raise ValueError('Ancestry requires available saved sessions and their locks.') from exc
        try:
            fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('This student session is busy.') from exc
        manifest, state, paths, decisions = student._load(folder)
        entries.append((folder, manifest, state, [student._read(path) for path in paths], decisions))
        ancestry = manifest.get('provenance', {}).get('previous_encounter')
        if ancestry is None:
            if previous is not None:
                raise ValueError('Ancestry is missing for the supplied predecessor.')
            break
        if not isinstance(ancestry, dict) or not isinstance(ancestry.get('path'), str) or not ancestry['path']:
            raise ValueError('Ancestry requires a saved predecessor path.')
        folder = Path(previous if previous is not None else ancestry['path']).resolve()
        previous = None
    entries.reverse()
    observed = []
    for index, (_, manifest, state, _, _) in enumerate(entries):
        if index:
            ancestry = manifest['provenance']['previous_encounter']
            initialization = manifest['initial']['initialization']
            shared = initialization.get('previous_encounter') if isinstance(initialization, dict) else None
            old_manifest, old_state = entries[index - 1][1:3]
            if (ancestry.get('session_sha256') != student.digest(old_manifest)
                    or ancestry.get('state_sha256') != student.digest(old_state)
                    or ancestry.get('history_sha256') != student.digest(shared)
                    or shared != observed[-1] or not _ended(old_state)
                    or ('earlier_encounters' in initialization
                        and initialization['earlier_encounters'] != observed[:-1])):
                raise ValueError('Ancestry does not match the saved predecessor and shared history.')
        observed.append(_observed(state))
    return entries


def create(previous, folder, *, task, activity, evaluation=None, max_decisions=12):
    previous, folder = Path(previous), Path(folder)
    with ExitStack() as stack:
        entries = lineage(previous, stack)
        _, manifest, state, _, _ = entries[-1]
        if not _ended(state):
            raise ValueError('The previous encounter must end with a generated no-reply action.')
        records = [_observed(entry[2]) for entry in entries]
        shared = records[-1]
        # ponytail: exact history up to 64 KB; add explicit evidence selection only when this ceiling is reached.
        if len(json.dumps(records, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 64000:
            raise ValueError('Previous encounters exceed the 64000-byte shared-history limit.')
        provenance = {'path':str(previous.resolve()), 'session_sha256':student.digest(manifest),
                      'state_sha256':student.digest(state), 'history_sha256':student.digest(shared),
                      'source_sha256':student.digest(Path(__file__).read_text())}
        prepared = deepcopy(task)
        prepared['initialization'] = {
            'current_task':prepared['initialization'],
            'history_scope':'Shared observed records of earlier simulated encounters, oldest first in '
                'earlier_encounters, followed by previous_encounter. Each record\'s work and feedback belong '
                'to its own earlier task. The researcher supplied this new task; no learning or choice '
                'to continue is established by earlier stops.',
            'earlier_encounters':records[:-1],
            'previous_encounter':shared}
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.next-task-') as temporary:
        staged = Path(temporary) / 'session'
        initial = student.create(staged, task=prepared, activity=activity, evaluation=evaluation,
            branch_id='synthetic/' + uuid4().hex, model=manifest['model'], max_decisions=max_decisions)
        created = student._read(staged / 'session.json')
        created['provenance']['previous_encounter'] = provenance
        student._save(staged / 'session.json', created)
        folder.mkdir(exist_ok=False)
        with student._locked(folder):
            os.replace(staged / 'session.json', folder / 'session.json')
    return initial


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous', type=Path)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--activity', type=Path, required=True)
    parser.add_argument('--evaluation-file', type=Path)
    parser.add_argument('--max-decisions', type=int, default=12)
    args = parser.parse_args()
    evaluation = student.notebook_runtime.Evaluation.model_validate(student._read(args.evaluation_file)).model_dump() \
        if args.evaluation_file else None
    state = create(args.previous, args.folder, task=student._read(args.task), activity=student._read(args.activity),
                   evaluation=evaluation, max_decisions=args.max_decisions)
    print(json.dumps({'status':state['status'], 'work':state['work'], 'observation':state['observation'],
                      'shared_previous_encounters':1 + len(state['initialization']['earlier_encounters'])}, indent=2))


if __name__ == '__main__':
    main()
