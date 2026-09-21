"""Create an authored notebook exercise for the existing student and tutor runners."""
import argparse
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from src.agents import notebook_student as student


def create(folder, *, image_id):
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
    activity = student.notebook_runtime.Activity(image_id=image_id, library='babypandas', library_version='1.0.0',
        table='swatches', column='shade', result='fraction_blue', values=['blue', 'amber', 'blue', 'green'])
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.notebook-example-') as temporary:
        staged = Path(temporary) / 'example'
        student.create(staged / 'session', task=task, activity=activity.model_dump(),
            evaluation={'expected': 0.5}, branch_id='synthetic/' + uuid4().hex,
            model='gemini-2.5-pro', max_decisions=6)
        (staged / 'policy.txt').write_text('Give one concise next-step hint based on the supplied task, work '
            'and current feedback. Ask at most one focused question; do not give a complete solution.\n', encoding='utf-8')
        student.load(staged / 'session')
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return folder / 'session'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='New directory for the session and tutor policy.')
    parser.add_argument('--image-id', required=True, help='Immutable local notebook-runtime image ID (sha256:...).')
    args = parser.parse_args()
    child = create(args.folder, image_id=args.image_id)
    print(f'Authored notebook example saved to {child}. No model calls or code execution.')


if __name__ == '__main__':
    main()
