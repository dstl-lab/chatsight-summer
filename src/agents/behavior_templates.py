"""Add deterministic wording to a saved authored choice; never select or dispatch."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from textwrap import indent

from src.agents import behavior_policy as policy


# Additive because the original policy and expression sources are pinned by saved runs.
EXTRA_TEMPLATES = {
    (('unspecified',), (), 'same'): ('help-current', (), 'can you help me with this?'),
    (('solution',), (), 'different'): (
        'solution-next', ('next_task',), '{next_task}\ncan you show me the solution?'),
    (('solution',), ('work',), 'different'): (
        'solution-next-with-work', ('work', 'next_task'),
        '{work}\n{next_task}\ncan you show me the solution?'),
}


def express(result):
    """Word an already-selected behavior. Caller must supply a verified policy result."""
    query = policy.Query.model_validate(result['query'])
    selection = result['selection']
    behavior = None if selection is None else policy.Behavior.model_validate(selection['behavior'])
    if behavior is not None and any(value is None for value in behavior.model_dump().values()):
        raise ValueError('A selected behavior must be resolved; never guess its wording.')
    template = None if behavior is None else EXTRA_TEMPLATES.get(policy._key(behavior))
    if template is None:
        return policy._render(behavior, query)
    name, slots, pattern = template
    missing = [slot for slot in slots if getattr(query, slot) is None]
    return {'origin': 'authored-template', 'status': 'missing-input' if missing else 'rendered',
        'template_id': name, 'missing': missing,
        'text': None if missing else pattern.format(**{slot: getattr(query, slot) for slot in slots})}


def _receipt(saved):
    return {'version': 1, 'renderer': 'deterministic-extension-v1',
        'source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'policy_sha256': sha256(policy._json(saved).encode()).hexdigest(),
        'rendering': express(saved['result']),
        'scope': 'Authored wording of the unchanged saved choice; no measured realism or new probabilities.'}


def _report(receipt):
    rendered = receipt['rendering']
    lines = ['# Deterministic student wording', '', receipt['scope'], '',
        f"Status: **{rendered['status']}**. Template: {rendered['template_id'] or 'none'}.", '',
        'Missing required inputs: ' + (', '.join(rendered['missing']) or 'none') + '.', '']
    if rendered['text'] is not None:
        lines += ['Rendered reply:', '', indent(rendered['text'], '    '), '']
    lines += ['The original choice, probabilities and input remain in `policy/`. '
              'No rendering means unavailable wording, never an observed student silence.', '']
    return '\n'.join(lines)


def run(source, folder):
    """Preserve the verified original files and write one separate rendering receipt."""
    source, folder = Path(source), Path(folder)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    if folder.resolve().is_relative_to(source.resolve()):
        raise ValueError('Keep new wording outside the source policy directory.')
    saved = policy.verify(source)
    receipt = _receipt(saved)
    folder.mkdir(parents=True, exist_ok=False)
    copied = folder / 'policy'
    copied.mkdir()
    for name in ('input.json', 'trace.json', 'report.md'):
        with (copied / name).open('xb') as stream:
            stream.write((source / name).read_bytes())
    if policy.verify(copied) != saved:
        raise ValueError('The source policy changed while it was being copied.')
    for name, text in (('rendering.json', policy._json(receipt)), ('report.md', _report(receipt))):
        with (folder / name).open('x', encoding='utf-8') as stream:
            stream.write(text)
    return receipt


def verify(folder):
    """Replay wording and source bindings without generating or changing the old choice."""
    folder = Path(folder)
    saved = policy.verify(folder / 'policy')
    expected = _receipt(saved)
    if (json.loads((folder / 'rendering.json').read_text(encoding='utf-8')) != expected
            or (folder / 'report.md').read_text(encoding='utf-8') != _report(expected)):
        raise ValueError('Saved deterministic wording or its source binding changed.')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('render')
    create.add_argument('source', type=Path, help='Verified saved behavior-policy directory.')
    create.add_argument('folder', type=Path, help='New deterministic rendering directory.')
    inspect = commands.add_parser('verify')
    inspect.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        receipt = run(args.source, args.folder) if args.command == 'render' else verify(args.folder)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(receipt['rendering'], ensure_ascii=False))


if __name__ == '__main__':
    main()
