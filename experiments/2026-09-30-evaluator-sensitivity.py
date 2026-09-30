"""Offline sensitivity of historical human labels; no new scores or model calls."""
import argparse
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path

from src.agents.notebook_student import _save
from src.eval import fidelity_comparison, saved_comparison

LEVELS = tuple(map(F, ('0', '.025', '.05', '.10', '.15', '.20', '.25', '.30')))
DELTA = F(1, 5)


def bounds(recorded, generated, error_recorded, error_generated):
    r, g, er, eg = map(lambda v: F(str(v)), (recorded, generated, error_recorded, error_generated))
    if any(not 0 <= value <= 1 for value in (r, g, er, eg)):
        raise ValueError('Rates and assumed error masses must lie in [0,1].')
    return max(0, g-eg) - min(1, r+er), min(1, g+eg) - max(0, r-er)


def decision(lower, upper):
    if lower > DELTA:
        return 'large_excess'
    if upper < -DELTA:
        return 'large_deficit'
    if lower >= -DELTA and upper <= DELTA:
        return 'within_margin'
    return 'inconclusive'


def rates(cases):
    if not cases or any(not draws or reference not in ('yes', 'no') or
                        any(value not in ('yes', 'no') for value in draws) for reference, draws in cases):
        raise ValueError('Keep all planned cases with complete binary reference and draw labels.')
    return (sum(F(reference == 'yes') for reference, _ in cases) / len(cases),
            sum(F(draws.count('yes'), len(draws)) for _, draws in cases) / len(cases))


def summarize(name, cases):
    r, g = rates(cases)
    grid = []
    for er in LEVELS:
        for eg in LEVELS:
            lo, hi = bounds(r, g, er, eg)
            grid.append({'error_recorded': float(er), 'error_generated': float(eg),
                         'lower': float(lo), 'upper': float(hi), 'decision': decision(lo, hi)})
    omitted = [rates(cases[:i] + cases[i+1:]) for i in range(len(cases))]
    return {'name': name, 'cases': len(cases), 'generated_draws': sum(len(draws) for _, draws in cases),
        'recorded_yes': sum(reference == 'yes' for reference, _ in cases),
        'generated_yes': sum(draws.count('yes') for _, draws in cases),
        'recorded_rate': float(r), 'generated_rate': float(g), 'gap': float(g-r),
        'leave_one_case_out_gap': [float(min(g-r for r,g in omitted)), float(max(g-r for r,g in omitted))],
        'grid': grid}


def execute(fixed_folder, cached_folder, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Sensitivity output already exists.')
    fixed_folder, cached_folder = Path(fixed_folder), Path(cached_folder)
    fixed_pins = fidelity_comparison.evidence_hashes(fixed_folder)
    cached_names = ('closure.json', 'preparation.json', 'review-packet.json', 'private-mapping.json',
                    'received/review.json', 'result.json', 'report.py')
    def cached_pins():
        return {name: sha256((cached_folder/name).read_bytes()).hexdigest() for name in cached_names}
    pins = cached_pins()
    fixed = fidelity_comparison.load_comparison(fixed_folder, expected_files=fixed_pins)
    cached = saved_comparison.load_comparison(cached_folder, expected_closure=pins['closure.json'])
    if cached['rubric_id'] != 'help-work-v1' or fixed['definitions'] != cached['definitions']:
        raise ValueError('The two historical rubrics must agree exactly.')
    observations = []
    for condition, title in fidelity_comparison.CONDITIONS:
        cases = []
        for case in fixed['cases']:
            draws = next(arm['draws'] for arm in case['conditions'] if arm['id'] == condition)
            if any(draw['status'] != 'reply' for draw in draws):
                raise ValueError('This fixed-output analysis requires every scheduled reply.')
            cases.append((case['reference']['review']['work_present'],
                          [draw['review']['work_present'] for draw in draws]))
        observations.append(summarize('September 15: ' + title, cases))
    observations.append(summarize('September 22: Cached replies', [
        (case['reference']['review']['work_present'], [draw['review']['work_present'] for draw in case['draws']])
        for case in cached['cases']]))
    if fidelity_comparison.evidence_hashes(fixed_folder) != fixed_pins or cached_pins() != pins:
        raise ValueError('Source evidence changed during reading.')
    report = {'kind': 'retrospective-assumed-label-error-sensitivity', 'rubric_id': 'help-work-v1',
        'flag': 'work_present', 'threshold': float(DELTA), 'error_levels': list(map(float, LEVELS)),
        'scope': 'Fixed saved outputs; equal conversation weights; no population or finite-draw confidence claim.',
        'limit': 'Error levels are assumptions, not validated error bounds. Continuous envelopes can be wider '
                 'than attainable discrete flips. Studies stay separate; no new-rubric or simulator validation.',
        'sources': [{'path': str(fixed_folder.resolve()), 'files': fixed_pins},
                    {'path': str(cached_folder.resolve()), 'files': pins}],
        'code_pins': {str(Path(path).resolve()): sha256(Path(path).read_bytes()).hexdigest()
                      for path in (__file__, fidelity_comparison.__file__, saved_comparison.__file__)},
        'comparisons': observations}
    _save(output, report, exclusive=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixed_folder', type=Path)
    parser.add_argument('cached_folder', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = execute(args.fixed_folder, args.cached_folder, args.output)
    for row in result['comparisons']:
        print(row['name'], 'recorded:', row['recorded_rate'], 'generated:', row['generated_rate'])
