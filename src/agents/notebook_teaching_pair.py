"""Prepare two initial tutor alternatives with identical student work and budgets."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from src.agents import notebook_student as student


def create(folder, *, task, activity, tutor_replies, evaluation=None,
           model='gemini-2.5-pro', max_decisions=6, timeout=10):
    """Create fresh A/B sessions without generating, executing, or reopening a learner."""
    if (not isinstance(tutor_replies, (list, tuple)) or len(tutor_replies) != 2
            or any(not isinstance(reply, str) or not reply.strip() for reply in tutor_replies)):
        raise ValueError('Supply exactly two nonblank tutor replies.')
    required = {'initialization', 'task', 'work', 'dialogue'}
    if (not isinstance(task, dict) or not required <= task.keys()
            or task.keys() - required - {'captured_at', 'omitted'}):
        raise ValueError('Supply an initial task, not a saved student state or manifest.')
    dialogue = task['dialogue']
    if (not isinstance(task['task'], str) or not task['task'].strip()
            or not isinstance(dialogue, list) or len(dialogue) < 2
            or any(not isinstance(t, dict) or t.get('role') not in ('student', 'tutor')
                   or not isinstance(t.get('text'), str) or not t['text'].strip() for t in dialogue)
            or [t['role'] for t in dialogue[-2:]] != ['student', 'tutor']):
        raise ValueError('An initial task must end with a student request followed by a tutor reply.')
    folder = Path(folder)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    comparison_id = uuid4().hex
    common = {'task_template': task, 'activity': activity, 'evaluation': evaluation,
              'model': model, 'max_decisions': max_decisions, 'timeout': timeout}
    input_sha = student.digest(common)
    receipt = {'version': 1, 'status': 'prepared', 'comparison_id': comparison_id,
        'source_sha256': student.digest(Path(__file__).read_text()),
        'common_input_sha256': input_sha, 'max_student_decisions_total': 2 * max_decisions,
        'model_calls': 0, 'sessions': {},
        'scope': 'Alternative initial tutor replies, not forks of a progressed learner. '
                 'Both sessions start with no feedback/history and independent budgets. '
                 'This setup does not establish tutor effects or student fidelity.'}
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.teaching-pair-') as temporary:
        staged = Path(temporary) / 'sessions'
        for condition, reply in zip(('a', 'b'), tutor_replies):
            prepared = deepcopy(task)
            prepared['dialogue'][-1] = {'role': 'tutor', 'text': reply, 'origin': 'supplied'}
            child = staged / condition
            student.create(child, task=prepared, activity=activity, evaluation=evaluation,
                model=model, max_decisions=max_decisions, timeout=timeout,
                branch_id='synthetic/' + uuid4().hex)
            with student._locked(child):
                manifest = student._read(child / 'session.json')
                manifest['provenance']['teaching_pair'] = {
                    'comparison_id': comparison_id, 'condition': condition, 'common_input_sha256': input_sha}
                student._save(child / 'session.json', manifest)
                student._load(child)
            receipt['sessions'][condition] = {'manifest_sha256': student.digest(manifest),
                'tutor_reply_sha256': student.digest(reply)}
        student._save(staged / 'comparison.json', receipt, exclusive=True)
        # One reserved parent lets both complete children publish together without replacing existing work.
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder / 'sessions')
    return folder / 'sessions'


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--activity', type=Path, required=True)
    parser.add_argument('--first-tutor-file', type=Path, required=True)
    parser.add_argument('--second-tutor-file', type=Path, required=True)
    parser.add_argument('--evaluation-file', type=Path)
    parser.add_argument('--model', default='gemini-2.5-pro')
    parser.add_argument('--max-decisions', type=int, default=6)
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args()
    evaluation = student.notebook_runtime.Evaluation.model_validate(student._read(args.evaluation_file)).model_dump() \
        if args.evaluation_file else None
    root = create(args.folder, task=student._read(args.task), activity=student._read(args.activity),
        tutor_replies=[p.read_text(encoding='utf-8') for p in (args.first_tutor_file, args.second_tutor_file)],
        evaluation=evaluation, model=args.model, max_decisions=args.max_decisions, timeout=args.timeout)
    print(json.dumps({'status': 'prepared', 'sessions': [str(root / name) for name in ('a', 'b')],
                      'model_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
