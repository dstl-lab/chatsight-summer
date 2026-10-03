"""Inspect authored joint probabilities without selecting or rendering a reply."""
import argparse
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from src.agents import behavior_policy as policy


def predict_distribution(value):
    """Pure probability calculation; seed is validated but never consumed.

    Keep the source-pinned original selector untouched. This frozen arithmetic
    mirrors its pre-sampling stage; differential tests protect compatibility.
    """
    data = policy.Request.model_validate(value)
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
        key = policy._key(example.behavior)
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
    return {'version': 1, 'scope': policy.SCOPE,
        'status': 'available' if used else 'insufficient-evidence',
        'query': data.query.model_dump(),
        'matching': {'fields': fields, 'unknown_fields': [k for k in context if k not in fields],
                     'minimum_accounts': 2, 'exact_accounts': exact_accounts, 'pool': pool, 'reason': reason},
        'weighting': 'Uniform account, then uniform example within account; no smoothing.',
        'counts': {'library_examples': len(rows), 'eligible_examples': len(eligible),
                   'eligible_accounts': eligible_accounts, 'used_examples': len(used),
                   'used_accounts': len(grouped)},
        'examples': rows, 'distribution': distribution,
        'limits': ['The two-account floor is a mechanics rule, not a reliability threshold.',
                   'Source references and authored origin are supplied assertions, not verified lineage.',
                   'No natural student probabilities, semantic accuracy, silence or notebook actions measured.',
                   'An unavailable message is a renderer limitation, never an observed student non-response.']}


def report(value):
    """Bind the normalized request, context and implementations; read source only."""
    value = policy.Request.model_validate(value).model_dump()
    result = predict_distribution(value)
    return {'version': 1, 'kind': 'authored-behavior-distribution',
        'input_sha256': sha256(policy._json(value).encode()).hexdigest(),
        'context_sha256': sha256(policy._json(value['query']['context']).encode()).hexdigest(),
        'sources': {Path(path).name: sha256(Path(path).read_bytes()).hexdigest()
                    for path in (__file__, policy.__file__)},
        'result': result}


def markdown(saved):
    """Readable probability summary with the complete bound evidence below it."""
    result = saved['result']
    lines = ['# Behavior probabilities before sampling', '', policy.SCOPE, '',
             'No behavior selected and no message rendered.', '',
             f"Status: **{result['status']}**. Pool: **{result['matching']['pool']}**.",
             result['matching']['reason'], '', result['weighting'], '',
             '| Assistance | Material | Task | Probability | Exact weight | Examples | Accounts |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for row in result['distribution']:
        behavior = row['behavior']
        lines.append(f"| {', '.join(behavior['assistance']) or 'none'} | "
                     f"{', '.join(behavior['material']) or 'none'} | {behavior['task_relation']} | "
                     f"{row['probability']:.1%} | {row['fraction']} | {row['examples']} | {row['accounts']} |")
    lines += ['', '## Context, supporting examples and bindings', '',
              'Declared references are not verified lineage. Unknown is not absence. '
              'The input binding retains the seed, but these probabilities do not use it.', '',
              'The JSON includes every example, inclusion/exclusion, account weight and source binding.', '']
    # An input identifier may contain Markdown fence text; indent literal JSON.
    lines.extend('    ' + line for line in policy._json(saved).splitlines())
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Existing authored policy request JSON.')
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args()
    try:
        saved = report(json.loads(args.input.read_text(encoding='utf-8')))
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(markdown(saved) if args.format == 'markdown' else policy._json(saved), end='')


if __name__ == '__main__':
    main()
