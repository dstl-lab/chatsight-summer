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


def test_history_matches_preserve_locations_roles_and_literal_boundaries():
    from src.eval.student_repetition import history_matches

    row = {'id': 'authored', 'conversation_id': 'authored', 'prefix': [
        {'role': 'student', 'text': 'help with this'},
        {'role': 'tutor', 'text': 'help with this'},
        {'role': 'student', 'text': ' \nhelp with this\t'},
        {'role': 'student', 'text': 'a different request'},
        {'role': 'tutor', 'text': 'What have you tried?'}], 'response': 'help with this'}
    before = deepcopy(row)
    assert history_matches(row) == [
        {'prefix_index': 0, 'role': 'student', 'latest_student': False, 'exact': True},
        {'prefix_index': 1, 'role': 'tutor', 'latest_student': False, 'exact': True},
        {'prefix_index': 2, 'role': 'student', 'latest_student': False, 'exact': False}]
    assert row == before
    assert history_matches(row | {'response': 'a different request'}) == [
        {'prefix_index': 3, 'role': 'student', 'latest_student': True, 'exact': True}]
    assert history_matches(row | {'response': 'What have you tried?'}) == [
        {'prefix_index': 4, 'role': 'tutor', 'latest_student': False, 'exact': True}]
    for response in ('', ' \n', 'Help with this', 'help  with this', 'help with this!',
                     'help with', 'help with this plus a changed header'):
        assert history_matches(row | {'response': response}) == []
    assert len(history_matches(row | {'response': '\thelp with this\n'})) == 3
    assert 'help with this' not in json.dumps(history_matches(row))
    with pytest.raises(ValueError):
        history_matches(row | {'prefix': row['prefix'][:-1]})


def test_contained_replies_keep_roles_and_do_not_fuzz_internal_text():
    from src.eval import student_repetition
    assert hasattr(student_repetition, 'contained_matches'), 'Contained-reply matcher is missing'
    matches = student_repetition.contained_matches
    row = {'id': 'authored', 'conversation_id': 'authored', 'prefix': [
        {'role': 'student', 'text': 'Can you help? What changed?'},
        {'role': 'tutor', 'text': 'Inspect the variable. What changed?'},
        {'role': 'student', 'text': ' what changed?\n'},
        {'role': 'tutor', 'text': 'What  changed?'}], 'response': 'what changed?'}
    before = deepcopy(row)
    assert matches(row) == [
        {'prefix_index': 0, 'role': 'student', 'whole_turn': False, 'case_sensitive': False},
        {'prefix_index': 1, 'role': 'tutor', 'whole_turn': False, 'case_sensitive': False},
        {'prefix_index': 2, 'role': 'student', 'whole_turn': True, 'case_sensitive': True}]
    assert matches(row | {'response': '\twhat changed?\n'}) == matches(row)
    assert row == before and 'changed' not in json.dumps(matches(row))
    for response in ('', ' \n', 'what\nchanged?', 'what changed!', 'what changed? extra'):
        assert matches(row | {'response': response}) == []
    # Short common fragments are counted, not silently treated as role errors or removed.
    assert len(matches(row | {'response': 'changed'})) == 4
    unicode = row | {'prefix': [{'role':'student','text':'help'},
                               {'role':'tutor','text':'Straße'}], 'response':'STRASSE'}
    assert matches(unicode) == [
        {'prefix_index': 1, 'role': 'tutor', 'whole_turn': True, 'case_sensitive': False}]
    with pytest.raises(ValueError):
        matches(row | {'prefix': row['prefix'][:-1]})
