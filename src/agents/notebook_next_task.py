"""Start a fresh task with shared observed history from one completed encounter."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from src.agents import notebook_student as student


def create(previous, folder, *, task, activity, evaluation=None, max_decisions=12):
    previous, folder = Path(previous), Path(folder)
    with student._locked(previous):
        manifest, state, _, _ = student._load(previous)
        if (state['status'] != 'no-reply' or not state['history']
                or state['history'][-1]['action']['decision'] != 'no-reply'
                or state['history'][-1]['origin'] != 'model'):
            raise ValueError('The previous encounter must end with a generated no-reply action.')
        shared = deepcopy({key:state[key] for key in ('task', 'dialogue', 'work', 'status')})
        shared.update(activity={k:v for k,v in state['activity'].items() if k != 'image_id'},
            observation=student.notebook_session._feedback(state['observation']),
            history=[deepcopy(event) | {'observation':student.notebook_session._feedback(event['observation'])}
                     for event in state['history']])
        # ponytail: one complete predecessor, at most 64 KB; select evidence explicitly if more context is needed.
        if len(json.dumps(shared, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 64000:
            raise ValueError('Previous encounter exceeds the 64000-byte shared-history limit.')
        provenance = {'path':str(previous.resolve()), 'session_sha256':student.digest(manifest),
                      'state_sha256':student.digest(state), 'history_sha256':student.digest(shared),
                      'source_sha256':student.digest(Path(__file__).read_text())}
        prepared = deepcopy(task)
        prepared['initialization'] = {
            'current_task':prepared['initialization'],
            'history_scope':'Shared observed record of one previous simulated encounter. Its work and feedback '
                'belong to that earlier task. The researcher supplied this new task; no learning or choice '
                'to continue is established by the earlier stop.',
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
                      'shared_previous_encounters':1}, indent=2))


if __name__ == '__main__':
    main()
