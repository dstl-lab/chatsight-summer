"""Create an authored notebook exercise for the existing student and tutor runners."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from src.agents import chat_student as chat, notebook_student as student


def create(folder, *, image_id, chat_source=None, exercise=None):
    """Publish explicit task inputs and a hint policy without generating or executing."""
    folder = Path(folder)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    task = {
        'initialization': 'Authored task, table, work and dialogue for a mechanism example; '
            'not a recovered student record or calibrated persona.',
        'task': 'Find the proportion of rows whose shade is blue. Assign the result as a float to fraction_blue.',
        'work': {'cell_index': 1, 'revision': 0,
                 'source': "fraction_blue = (swatches.get('shade') == 'blue').sum()"},
        'dialogue': [
            {'role': 'student', 'text': 'how do i get the share of blue', 'origin': 'authored'},
            {'role': 'tutor', 'text': 'Consider how the count of blue rows relates to the total number of rows.',
             'origin': 'authored'}],
    }
    activity = {'library': 'babypandas', 'library_version': '1.0.0', 'table': 'swatches',
                'column': 'shade', 'result': 'fraction_blue', 'values': ['blue', 'amber', 'blue', 'green']}
    evaluation = {'expected': 0.5}
    policy = ('Give one concise next-step hint based on the supplied task, work and current feedback. '
              'Ask at most one focused question; do not give a complete solution.\n')
    if exercise is not None:
        if not isinstance(exercise, dict) or set(exercise) != {'task', 'activity', 'evaluation', 'policy'}:
            raise ValueError('An exercise requires exactly task, activity, evaluation and policy.')
        task = deepcopy(exercise['task'])
        required = {'initialization', 'task', 'work', 'dialogue'}
        if (not isinstance(task, dict) or not required <= task.keys()
                or task.keys() - required - {'captured_at', 'omitted'}
                or not isinstance(task['task'], str) or not task['task'].strip()
                or not isinstance(task['initialization'], (str, dict)) or not task['initialization']
                or isinstance(task['initialization'], str) and not task['initialization'].strip()
                or not isinstance(task['dialogue'], list)
                or any(not isinstance(turn, dict) for turn in task['dialogue'])
                or not isinstance(task['work'], dict)
                or set(task['work']) != {'cell_index', 'revision', 'source'}
                or type(task['work']['cell_index']) is not int or task['work']['cell_index'] < 0):
            raise ValueError('Supply an initial task with initialization, task text, work and dialogue.')
        activity, policy = exercise['activity'], exercise['policy']
        if not isinstance(activity, dict) or 'image_id' in activity:
            raise ValueError('Supply activity fields without image_id; use the separate immutable image argument.')
        if not isinstance(policy, str) or not policy.strip():
            raise ValueError('Supply a nonblank tutor policy.')
        evaluation = student.notebook_runtime.Evaluation.model_validate(exercise['evaluation']).model_dump()
    activity = student.notebook_runtime.Activity.model_validate(activity | {'image_id': image_id})
    if chat_source is not None:
        chat_source = Path(chat_source)
        if folder.resolve().is_relative_to(chat_source.resolve()):
            raise ValueError('Keep the new example outside its chat source.')
        source = chat._load(chat_source)  # Read verified source without creating a lock or new progress.
        prefix = source[0]['query']['prefix']
        # ponytail: exact examples up to 64 KB; add explicit selection if longer context is needed.
        if len(json.dumps(prefix, ensure_ascii=False).encode('utf-8')) > 64000:
            raise ValueError('Conversation example exceeds the 64000-byte limit.')
        task['initialization'] = {
            'current_task': task['initialization'],
            'communication_scope': 'The conversation_example is the original supplied prefix from a separate '
                'chat scenario. It is a light example of communication, not current task/work/feedback '
                'or evidence that the same real student attempted this authored exercise. No stable '
                'personality, ability or emotion is established. Generated continuations are excluded. '
                'This initialization is visible to both student and tutor.',
            'conversation_example': prefix}
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.notebook-example-') as temporary:
        staged = Path(temporary) / 'example'
        student.create(staged / 'session', task=task, activity=activity.model_dump(),
            evaluation=evaluation, branch_id='synthetic/' + uuid4().hex,
            model='gemini-2.5-pro', max_decisions=6)
        if chat_source is not None:
            manifest = student._read(staged / 'session/session.json')
            manifest['provenance']['communication_source'] = {
                'path': str(chat_source.resolve()), 'session_sha256': student.digest(source[0]),
                'prefix_sha256': student.digest(prefix)}
            student._save(staged / 'session/session.json', manifest)
        (staged / 'policy.txt').write_text(policy, encoding='utf-8')
        student.load(staged / 'session')
        if chat_source is not None and chat._load(chat_source) != source:
            raise ValueError('The chat source changed during preparation.')
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return folder / 'session'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='New directory for the session and tutor policy.')
    parser.add_argument('--image-id', required=True, help='Immutable local notebook-runtime image ID (sha256:...).')
    parser.add_argument('--chat-source', type=Path,
                        help='Optional saved chat session; use only its original prefix as a communication example.')
    parser.add_argument('--exercise-file', type=Path,
                        help='Optional JSON object with task, activity (without image_id), evaluation and policy.')
    args = parser.parse_args()
    exercise = student._read(args.exercise_file) if args.exercise_file is not None else None
    if args.exercise_file is not None and not isinstance(exercise, dict):
        parser.error('The exercise file must contain an object, not null or a list.')
    child = create(args.folder, image_id=args.image_id, chat_source=args.chat_source, exercise=exercise)
    print(f'Notebook exercise saved to {child}. '
          + ('Includes a separate conversation example; no validated persona. ' if args.chat_source else '')
          + 'No model calls or code execution.')


if __name__ == '__main__':
    main()
