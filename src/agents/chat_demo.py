"""Create an authored, offline example for the existing saved-chat workspaces."""
import argparse
from pathlib import Path

from src.agents import chat_policy_pair as pair, chat_student as chat


def create(folder):
    """Save scripted outcomes through the real runner; never overwrite a demo."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    source = folder / 'source'
    initial = chat.create(source, model='authored-offline-demo', max_decisions=1, query={
        'id': 'authored-count-query', 'conversation_id': 'authored-count-conversation',
        'prefix': [
            {'role': 'tutor', 'text': 'Authored offline demo: all dialogue and outcomes are '
                'invented and scripted. No student data or model calls are used.'},
            {'role': 'student', 'text': "colors = ['teal', 'gold', 'teal']\nhow many teal"},
            {'role': 'tutor', 'text': "Count the values equal to 'teal'."},
        ],
    })
    chat.step(source, binding=initial['binding'],
              generate=lambda _, schema: schema(decision='reply', text='how do i count that'))
    comparison = folder / 'comparison'
    saved = pair.create(comparison, source=source, max_new_decisions=1, policies={
        'a': 'Authored offline demo: give one concise hint.',
        'b': 'Authored offline demo: give the answer directly.',
    })
    for name, tutor_text, decision, student_text in [
        ('a', 'A list has a count method. Give it the color you want to count.',
         'reply', "colors.count('teal')?"),
        ('b', 'There are 2 teal values.', 'no-reply', ''),
    ]:
        saved = pair.respond(comparison, name,
            binding=saved['conditions'][name]['snapshot']['binding'], send=True,
            generate_tutor=lambda _, schema: schema(text=tutor_text),
            generate_student=lambda _, schema: schema(decision=decision, text=student_text))
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='New directory, usually data/teammate-demo.')
    args = parser.parse_args()
    create(args.folder)
    print(f'Authored offline demo saved to {args.folder / "comparison"}.')
    print('A reaches its decision budget; B has a scripted no-reply. Neither is research evidence.')
    print('Open without --send=true. See docs/teammate-quickstart.md.')


if __name__ == '__main__':
    main()
