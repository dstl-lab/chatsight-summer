from copy import deepcopy
import importlib.util
import json

import pytest


def test_exact_pairs_weighting_and_boundaries():
    assert importlib.util.find_spec('src.eval.student_repetition'), 'Repetition helper is missing'
    from src.eval.student_repetition import summarize

    def row(identifier, conversation, previous, response):
        return {'id': identifier, 'conversation_id': conversation, 'prefix': [
            {'role': 'student', 'text': response},  # Earlier context is not another pair.
            {'role': 'tutor', 'text': 'An earlier answer'},
            {'role': 'student', 'text': 'Earlier message in the request block'},
            {'role': 'student', 'text': previous},
            {'role': 'tutor', 'text': 'First tutor message'},
            {'role': 'tutor', 'text': 'Second tutor message'}], 'response': response}

    rows = [row('one', 'small', 'h?', 'h?'),
            row('two', 'large', '    x=2\n', 'x=2'),
            row('three', 'large', 'b' * 41, 'b' * 41),
            row('four', 'large', 'x', 'y'), row('five', 'blank', ' \n', ' ')]
    before = deepcopy(rows)
    report = summarize(rows)
    assert rows == before
    assert report['counts'] == {'windows': 5, 'conversations': 3, 'blank_pairs_excluded': 1}
    all_pairs = report['all']
    assert all_pairs['pairs'] == 4 and all_pairs['conversations'] == 2
    assert all_pairs['exact'] == {'repeats': 2, 'pair_rate': .5,
        'conversation_mean_rate': pytest.approx(2 / 3), 'conversations_with_repeat': 2,
        'conversation_any_rate': 1.0}
    assert all_pairs['outer_whitespace_stripped']['repeats'] == 3
    assert all_pairs['outer_whitespace_stripped']['conversation_mean_rate'] == pytest.approx(5 / 6)
    assert report['by_previous_length']['at_most_40']['pairs'] == 3
    assert report['by_previous_length']['at_most_40']['exact']['pair_rate'] == pytest.approx(1 / 3)
    assert report['by_previous_length']['over_40']['exact']['pair_rate'] == 1
    assert summarize(list(reversed(rows))) == report
    assert 'Earlier message' not in json.dumps(report) and 'large' not in json.dumps(report)
    empty = summarize([rows[-1]])['all']
    assert empty['pairs'] == 0 and empty['exact']['pair_rate'] is None
    assert empty['exact']['conversation_mean_rate'] is None
    assert summarize([])['all']['exact']['conversation_any_rate'] is None

    case = row('case', 'case', 'Hello', 'hello')
    assert summarize([case])['all']['outer_whitespace_stripped']['repeats'] == 0
    newline = row('lines', 'lines', 'a\n\nb', 'a\nb')
    assert summarize([newline])['all']['outer_whitespace_stripped']['repeats'] == 0
    for invalid in [rows + [rows[0]], [rows[0] | {'prefix': rows[0]['prefix'][:-2]}]]:
        with pytest.raises(ValueError):
            summarize(invalid)
