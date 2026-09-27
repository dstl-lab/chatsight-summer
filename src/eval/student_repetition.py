"""Literal text repetition across a tutor reply; no semantic or plausibility labels."""
from collections import defaultdict
from fractions import Fraction

from src.eval.retrieval_baseline import Example


def _rates(groups):
    groups = [pairs for pairs in groups if pairs]
    count = sum(len(pairs) for pairs in groups)
    result = {'pairs': count, 'conversations': len(groups)}
    for name, predicate in [('exact', lambda a, b: a == b),
                            ('outer_whitespace_stripped', lambda a, b: a.strip() == b.strip())]:
        hits = [sum(predicate(a, b) for a, b in pairs) for pairs in groups]
        result[name] = {
            'repeats': sum(hits), 'pair_rate': sum(hits) / count if count else None,
            'conversation_mean_rate': float(sum(Fraction(hit, len(pairs))
                for hit, pairs in zip(hits, groups)) / len(groups)) if groups else None,
            'conversations_with_repeat': sum(hit > 0 for hit in hits),
            'conversation_any_rate': sum(hit > 0 for hit in hits) / len(groups) if groups else None,
        }
    return result


def summarize(examples):
    """One pair per unique Example: last student in prefix -> recorded/generated reply.

    Caller verifies source-window uniqueness and distinguishes recorded from simulated
    populations. Earlier context is never counted as additional observations.
    """
    groups, ids, conversations = defaultdict(list), set(), set()
    blanks = 0
    for value in examples:
        row = Example.model_validate(value)
        if row.id in ids:
            raise ValueError('Duplicate response-window ID.')
        ids.add(row.id)
        conversations.add(row.conversation_id)
        previous = next(turn.text for turn in reversed(row.prefix) if turn.role == 'student')
        if not previous.strip() or not row.response.strip():
            blanks += 1
            continue
        groups[row.conversation_id].append((previous, row.response))
    return {
        'counts': {'windows': len(ids), 'conversations': len(conversations), 'blank_pairs_excluded': blanks},
        'all': _rates(groups.values()),
        'by_previous_length': {
            name: _rates([[(a, b) for a, b in pairs if predicate(len(a))]
                          for pairs in groups.values()])
            for name, predicate in [('at_most_40', lambda n: n <= 40), ('over_40', lambda n: n > 40)]
        },
    }
