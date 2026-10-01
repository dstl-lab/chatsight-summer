"""Offline, authored-only communication policy; no LLM, notebook execution or inferred state."""
import argparse
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Text = Annotated[str, Field(min_length=1, pattern=r'\S')]
Assistance = Literal['hint', 'explanation', 'solution', 'checking', 'unspecified']
SCOPE = ('Authored mechanics prototype, conditional on another message. '
         'Probabilities describe supplied examples, not measured student behavior.')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


def _labels(value):
    if value is not None and len(value) != len(set(value)):
        raise ValueError('Behavior sets must not contain duplicate labels.')
    return sorted(value) if value is not None else None


class Context(Strict):
    last_assistance: list[Assistance] | None
    feedback: Literal['pass', 'fail', 'runtime-error', 'not-checked'] | None

    _canonical = field_validator('last_assistance')(_labels)


class Behavior(Strict):
    assistance: list[Assistance] | None
    material: list[Literal['work', 'diagnostic']] | None
    task_relation: Literal['same', 'different'] | None

    _canonical = field_validator('assistance', 'material')(_labels)


class Query(Strict):
    id: Text
    account_id: Text
    source_ref: Text
    context: Context
    work: Text | None = None
    diagnostic: Text | None = None
    next_task: Text | None = None


class Example(Strict):
    id: Text
    account_id: Text
    source_ref: Text
    origin: Literal['authored', 'recorded', 'generated', 'assistant-labeled']
    context: Context
    behavior: Behavior | None


class Request(Strict):
    basis: Literal['authored'] = 'authored'
    seed: int = Field(default=0, ge=0)
    query: Query
    examples: list[Example]


TEMPLATES = {
    (('hint',), (), 'same'): ('hint-current', (), 'can i get another hint?'),
    (('checking',), (), 'same'): ('check-current', (), 'is this right?'),
    (('solution',), (), 'same'): ('solution-current', (), 'can you show me how to do this?'),
    (('checking',), ('work',), 'same'): ('check-work', ('work',), '{work}\nis this right?'),
    (('checking',), ('diagnostic',), 'same'): (
        'check-diagnostic', ('diagnostic',), '{diagnostic}\ncan you check this error?'),
    (('hint',), (), 'different'): ('hint-next', ('next_task',), 'can i get a hint for {next_task}?'),
}


def _key(behavior):
    return tuple(behavior.assistance), tuple(behavior.material), behavior.task_relation


def _render(behavior, query):
    result = {'origin': 'authored-template', 'status': 'not-selected',
              'template_id': None, 'missing': [], 'text': None}
    if behavior is None:
        return result
    template = TEMPLATES.get(_key(behavior))
    if template is None:
        return result | {'status': 'unsupported'}
    name, slots, text = template
    missing = [slot for slot in slots if getattr(query, slot) is None]
    return result | {'status': 'missing-input' if missing else 'rendered',
        'template_id': name, 'missing': missing,
        'text': None if missing else text.format(**{slot: getattr(query, slot) for slot in slots})}


def select(value):
    """Sample a whole behavior bundle, retaining support and all exclusions."""
    data = Request.model_validate(value)
    for field in ('id', 'source_ref'):
        identifiers = [getattr(data.query, field), *(getattr(r, field) for r in data.examples)]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f'Query and examples require distinct {field} values.')
    context = data.query.context.model_dump()
    fields = [key for key, value in context.items() if value is not None]
    rows, eligible, exact = [], [], []
    for example in sorted(data.examples, key=lambda r: r.id):
        exclusion = None
        if example.origin != 'authored':
            exclusion = 'Only authored examples are admitted by this prototype.'
        elif example.account_id == data.query.account_id:
            exclusion = 'Query account excluded; personalization is not implemented.'
        elif example.behavior is None or any(v is None for v in example.behavior.model_dump().values()):
            exclusion = 'Unresolved behavior; unknown is not absence.'
        mismatches = [field for field in fields if getattr(example.context, field) != context[field]]
        matched = bool(fields) and not mismatches
        rows.append(example.model_dump() | {'exclusion': exclusion,
            'matched': matched, 'mismatched_fields': mismatches, 'included': False, 'weight': '0'})
        if exclusion is None:
            eligible.append(example)
            if matched:
                exact.append(example)

    exact_accounts = len({r.account_id for r in exact})
    eligible_accounts = len({r.account_id for r in eligible})
    # ponytail: a fixed two-account demo floor; a research threshold needs its own protocol.
    if exact_accounts >= 2:
        pool, used = 'matching-context', exact
        reason = 'All known query context fields match in at least two authored accounts.'
    elif eligible_accounts >= 2:
        pool, used = 'broader-fallback', eligible
        reason = ('Fewer than two accounts match known context. Use the broader authored pool; '
                  'it may disagree with the query context.')
    else:
        pool, used = 'none', []
        reason = 'Fewer than two eligible authored accounts; no behavior sampled.'

    grouped = defaultdict(list)
    for example in used:
        grouped[example.account_id].append(example)
    masses, bundles, members = defaultdict(Fraction), {}, defaultdict(list)
    weights = {}
    for example in used:
        key = _key(example.behavior)
        weight = Fraction(1, len(grouped) * len(grouped[example.account_id]))
        weights[example.id] = weight
        masses[key] += weight
        bundles[key] = example.behavior.model_dump()
        members[key].append(example)
    for row in rows:
        row.update(included=row['id'] in weights, weight=str(weights.get(row['id'], 0)))
    distribution = [{'behavior': bundles[key], 'examples': len(members[key]),
                     'accounts': len({r.account_id for r in members[key]}),
                     'fraction': str(masses[key]), 'probability': float(masses[key])}
                    for key in sorted(masses)]
    selection, chosen = None, None
    if used:
        rng = random.Random(data.seed)
        accounts = sorted(grouped)
        account_index = rng.randrange(len(accounts))
        account = accounts[account_index]
        example_index = rng.randrange(len(grouped[account]))
        chosen = grouped[account][example_index]
        selection = {'account_index': account_index, 'example_index': example_index,
            'account_id': account, 'example_id': chosen.id, 'behavior': chosen.behavior.model_dump()}
    return {'version': 1, 'scope': SCOPE, 'status': 'selected' if chosen else 'insufficient-evidence',
        'seed': data.seed, 'query': data.query.model_dump(),
        'matching': {'fields': fields, 'unknown_fields': [k for k in context if k not in fields],
                     'minimum_accounts': 2, 'exact_accounts': exact_accounts, 'pool': pool, 'reason': reason},
        'weighting': 'Uniform account, then uniform example within account; no smoothing.',
        'counts': {'library_examples': len(rows), 'eligible_examples': len(eligible),
                   'eligible_accounts': eligible_accounts, 'used_examples': len(used),
                   'used_accounts': len(grouped)},
        'examples': rows, 'distribution': distribution, 'selection': selection,
        'rendering': _render(chosen.behavior if chosen else None, data.query),
        'limits': ['The two-account floor is a mechanics rule, not a reliability threshold.',
                   'Source references and authored origin are supplied assertions, not verified lineage.',
                   'No natural student probabilities, semantic accuracy, silence or notebook actions measured.',
                   'An unavailable message is a renderer limitation, never an observed student non-response.']}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'


def _receipt(value):
    return {'version': 1, 'input_sha256': sha256(_json(value).encode()).hexdigest(),
            'source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
            'python_version': platform.python_version(), 'result': select(value)}


def _markdown(receipt):
    result = receipt['result']
    lines = ['# Offline behavior policy — authored demonstration', '', SCOPE, '',
             f"Pool: **{result['matching']['pool']}**. {result['matching']['reason']}", '',
             f"Using {result['counts']['used_examples']} examples from "
             f"{result['counts']['used_accounts']} authored accounts. {result['weighting']}", '',
             '| Assistance | Material | Task | Probability | Exact weight |',
             '| --- | --- | --- | ---: | ---: |']
    for row in result['distribution']:
        behavior = row['behavior']
        lines.append(f"| {', '.join(behavior['assistance']) or 'none'} | "
                     f"{', '.join(behavior['material']) or 'none'} | {behavior['task_relation']} | "
                     f"{row['probability']:.1%} | {row['fraction']} |")
    lines += ['', '## Selected behavior and authored message', '', '```json',
              _json({'selection': result['selection'], 'rendering': result['rendering']}).rstrip(),
              '```', '', '## Full decision trace', '',
              'Declared sources, exclusions, matching, weights, seed and reproducibility pins:', '',
              '```json', _json(receipt).rstrip(), '```', '']
    return '\n'.join(lines)


def run(value, folder):
    """Create a self-contained trace; existing directories are never overwritten."""
    value = Request.model_validate(value).model_dump()
    receipt = _receipt(value)
    documents = {'input.json': _json(value), 'trace.json': _json(receipt), 'report.md': _markdown(receipt)}
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for name, text in documents.items():
        with (folder / name).open('x', encoding='utf-8') as stream:
            stream.write(text)
    return receipt


def verify(folder):
    """Recompute a saved trace, including source/runtime pins; never dispatch."""
    folder = Path(folder)
    try:
        value = json.loads((folder / 'input.json').read_text(encoding='utf-8'))
        saved = json.loads((folder / 'trace.json').read_text(encoding='utf-8'))
        expected = _receipt(value)
        if saved != expected or (folder / 'report.md').read_text(encoding='utf-8') != _markdown(expected):
            raise ValueError('Saved policy trace or report does not reproduce.')
    except (OSError, ValueError) as error:
        raise ValueError('Saved policy trace does not reproduce; preserve its original files and runtime.') from error
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('run', help='Read authored JSON and save a new offline trace.')
    create.add_argument('input', type=Path)
    create.add_argument('folder', type=Path)
    inspect = sub.add_parser('verify', help='Verify a saved trace without modifying it.')
    inspect.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'run':
            receipt = run(json.loads(args.input.read_text(encoding='utf-8')), args.folder)
        else:
            receipt = verify(args.folder)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    result = receipt['result']
    print(SCOPE)
    print(f"{result['status']}; pool={result['matching']['pool']}; rendering={result['rendering']['status']}")
    print(args.folder / 'report.md')


if __name__ == '__main__':
    main()
