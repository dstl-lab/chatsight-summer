"""The saved-study diagnostic must retain draw weights and unknown outcomes."""
import importlib.util
from pathlib import Path

import pytest


def test_source_disagreement_keeps_unknowns_and_original_draw_weights():
    path = Path(__file__).parents[1] / 'experiments/2026-09-30-evaluator-source-disagreement.py'
    assert path.exists(), 'The offline source-disagreement report is not implemented.'
    spec = importlib.util.spec_from_file_location('source_disagreement', path)
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)

    # (human, model) pairs; repeated slots stay repeated, cases get equal weight.
    cases = [
        {'recorded': ('no', 'yes'), 'generated': [('yes', 'yes')]},
        {'recorded': ('no', 'no'), 'generated': [('no', 'no'), ('no', 'no'), ('yes', 'unclear')]},
    ]
    result = run.compare(cases)
    assert result['recorded']['human_rate'] == 0
    assert result['recorded']['model_rate_range'] == [0.5, 0.5]
    assert result['generated']['human_rate'] == pytest.approx(2 / 3)
    assert result['generated']['model_rate_range'] == pytest.approx([0.5, 2 / 3])
    assert result['generated']['outcomes'] == {'yes': 1, 'no': 2, 'unclear': 1}
    assert result['model_gap_range'] == pytest.approx([0, 1 / 6])
    assert result['gap_shift_range'] == pytest.approx([-2 / 3, -0.5])
    for bad in ([], [{'recorded': ('no', 'no'), 'generated': []}],
                [{'recorded': ('conflict', 'no'), 'generated': [('no', 'no')]}],
                [{'recorded': ('no', None), 'generated': [('no', 'no')]}]):
        with pytest.raises(ValueError):
            run.compare(bad)

    mappings = [
        {'packet_id': 'p', 'cases': [{'id': 'c', 'reference_id': 'r',
                                    'draws': [{'id': 'd'}, {'id': 'd'}]}]},
        {'packet_id': 'q', 'occurrences': [{'case_id': 'c2', 'candidate_id': 'd2'}]},
    ]
    refs = {
        'one': {'occurrences': [{'source_index': 0, 'packet_id': 'p', 'case_id': 'c', 'candidate_id': 'r'}]},
        'two': {'occurrences': [
            {'source_index': 0, 'packet_id': 'p', 'case_id': 'c', 'candidate_id': 'd'},
            {'source_index': 1, 'packet_id': 'q', 'case_id': 'c2', 'candidate_id': 'd2'}]},
    }
    assert run.origins(refs, mappings) == {'one': 'recorded', 'two': 'generated'}
    mappings[1]['occurrences'][0]['candidate_id'] = 'unmatched'
    with pytest.raises(ValueError):
        run.origins(refs, mappings)
