"""One authored review bundle exercises saved comparison joins and file boundaries."""
from copy import deepcopy
from hashlib import sha256
import json
import shutil

import pytest

from src.eval.saved_comparison import load_comparison


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def _read(path):
    return json.loads(path.read_bytes())


def _hash(path):
    return sha256(path.read_bytes()).hexdigest()


def _repin(folder):
    result = _read(folder / 'result.json')
    for key, name in (('packet', 'review-packet.json'), ('mapping', 'private-mapping.json'),
                      ('form', 'received/review.json'), ('report_code', 'report.py')):
        result['provenance'][key]['sha256'] = _hash(folder / name)
    _save(folder / 'result.json', result)
    preparation = _read(folder / 'preparation.json')
    preparation['files'] = {str(folder / name): _hash(folder / name)
                            for name in ('review-packet.json', 'private-mapping.json', 'report.py')}
    _save(folder / 'preparation.json', preparation)
    _save(folder / 'closure.json', {'files': {name: _hash(folder / name) for name in (
        'preparation.json', 'review-packet.json', 'private-mapping.json',
        'received/review.json', 'result.json', 'report.py')}})


def write_bundle(tmp_path):
    """Write only invented evidence; shared with browser endpoint tests."""
    folder = tmp_path / 'comparison'
    packet = {'packet_id': 'private-packet', 'rubric_id': 'help-work-v1',
              'definitions': {'help_request': 'Asks for help.', 'work_present': 'Shows work.'},
              'cases': []}
    mapping = {'packet_id': packet['packet_id'], 'cases': []}
    form = {'packet_id': packet['packet_id'], 'rubric_id': packet['rubric_id'],
            'reviewer': 'PRIVATE REVIEWER', 'previously_seen_cases': 'unsure', 'judgments': []}
    result = {'packet_id': packet['packet_id'], 'rubric_id': packet['rubric_id'],
              'status': 'complete-review', 'cases': [], 'provenance': {
                  key: {'path': '/untrusted/path/never/read', 'sha256': ''}
                  for key in ('packet', 'mapping', 'form', 'report_code')}}
    for number, draw_ids in ((1, ['private-draw-1', 'private-draw-2']),
                             (2, ['private-shared', 'private-shared'])):
        case_id, reference_id = f'private-case-{number}', f'private-reference-{number}'
        ids = [reference_id, *dict.fromkeys(draw_ids)]
        packet['cases'].append({'id': case_id, 'context_status': 'Notebook evidence unavailable.',
            'prefix': {'context': [{'id': f'private-context-{number}', 'role': 'student',
                                    'text': 'Earlier authored question.'}],
                       'turns': [{'id': f'private-turn-{number}', 'role': 'tutor',
                                  'text': 'Try the next step.'}]},
            'candidates': [{'id': identity, 'text': f'Authored answer {index}.'}
                           for index, identity in enumerate(ids)]})
        draws = [{'id': identity, 'draw': index, 'status': 'reply'}
                 for index, identity in enumerate(draw_ids, 1)]
        mapping['cases'].append({'id': case_id, 'reference_id': reference_id, 'draws': draws})
        judgments = {identity: {'id': identity, 'help_request': 'yes',
                                'work_present': 'no', 'note': None} for identity in ids}
        form['judgments'].extend(judgments.values())
        result['cases'].append({'id': case_id, 'reference': judgments[reference_id],
            'draws': [draw | {'judgment': judgments[draw['id']]} for draw in draws], 'flags': {}})
    for name, value in (('review-packet.json', packet), ('private-mapping.json', mapping),
                         ('received/review.json', form), ('result.json', result),
                         ('preparation.json', {'packet_id': packet['packet_id'],
                                               'rubric_id': packet['rubric_id'], 'conditions': 1, 'files': {}})):
        _save(folder / name, value)
    (folder / 'report.py').write_text('raise RuntimeError("Must never execute saved code")\n')
    _repin(folder)
    return folder


def test_verified_projection_preserves_text_and_both_draws_without_private_metadata(tmp_path):
    folder = write_bundle(tmp_path)
    before = {path: path.read_bytes() for path in folder.rglob('*') if path.is_file()}
    view = load_comparison(folder, expected_closure=_hash(folder / 'closure.json'))
    assert view['version'] == 1 and view['kind'] == 'saved-communication-comparison'
    assert view['status'] == 'complete-review'
    assert [case['id'] for case in view['cases']] == ['1', '2']
    assert view['cases'][0]['title'] == 'Reviewed case 01'
    assert view['cases'][0]['prefix']['context'] == [
        {'role': 'student', 'text': 'Earlier authored question.'}]
    assert view['cases'][0]['reference']['review'] == {
        'help_request': 'yes', 'work_present': 'no', 'note': None}
    assert [draw['shared_review_with'] for draw in view['cases'][0]['draws']] == [None, None]
    assert [draw['shared_review_with'] for draw in view['cases'][1]['draws']] == [2, 1]
    assert view['cases'][1]['draws'][0]['text'] == view['cases'][1]['draws'][1]['text']
    assert 'private-' not in json.dumps(view) and 'PRIVATE REVIEWER' not in json.dumps(view)
    assert '/untrusted/' not in json.dumps(view) and str(folder) not in json.dumps(view)
    assert all(path.read_bytes() == value for path, value in before.items())


def test_partial_and_unclear_reviews_remain_explicit(tmp_path):
    folder = write_bundle(tmp_path)
    form, result = _read(folder / 'received/review.json'), _read(folder / 'result.json')
    form['judgments'][-1].update(help_request=None, work_present='unclear', note='Work is ambiguous.')
    for draw in result['cases'][-1]['draws']:
        draw['judgment'] = deepcopy(form['judgments'][-1])
    result['status'] = 'incomplete-review'
    _save(folder / 'received/review.json', form)
    _save(folder / 'result.json', result)
    _repin(folder)
    view = load_comparison(folder)
    assert view['status'] == 'incomplete-review'
    assert all(draw['review'] == {'help_request': None, 'work_present': 'unclear',
                                'note': 'Work is ambiguous.'} for draw in view['cases'][-1]['draws'])


def test_copied_bundle_keeps_recorded_paths_as_metadata(tmp_path):
    folder = write_bundle(tmp_path)
    copied = tmp_path / 'relocated-review'
    shutil.copytree(folder, copied)
    shutil.rmtree(folder)
    assert load_comparison(copied)['cases'][0]['id'] == '1'


def test_tampering_and_changed_closure_are_rejected(tmp_path):
    folder = write_bundle(tmp_path)
    closure_hash = _hash(folder / 'closure.json')
    packet = folder / 'review-packet.json'
    packet.write_bytes(packet.read_bytes() + b' ')
    with pytest.raises(ValueError):
        load_comparison(folder)
    _repin(folder)
    with pytest.raises(ValueError):
        load_comparison(folder, expected_closure=closure_hash)


@pytest.mark.parametrize('filename,change', [
    ('preparation.json', lambda x: x.update(conditions=2)),
    ('private-mapping.json', lambda x: x.update(packet_id='other')),
    ('private-mapping.json', lambda x: x['cases'].append(deepcopy(x['cases'][0]))),
    ('private-mapping.json', lambda x: x['cases'][0].update(reference_id='private-shared')),
    ('private-mapping.json', lambda x: x['cases'][0]['draws'][0].update(draw=True)),
    ('private-mapping.json', lambda x: x['cases'][0]['draws'][0].update(id='private-reference-1')),
    ('private-mapping.json', lambda x: x['cases'][0]['draws'][0].update(status='no-reply')),
    ('received/review.json', lambda x: x['judgments'].pop()),
    ('received/review.json', lambda x: x['judgments'].append(deepcopy(x['judgments'][0]))),
    ('received/review.json', lambda x: x['judgments'][0].update(work_present=True)),
    ('received/review.json', lambda x: x['judgments'][0].update(work_present='unclear', note=' ')),
    ('result.json', lambda x: x['cases'][0]['reference'].update(help_request='no')),
    ('result.json', lambda x: x['cases'][0]['draws'][0].update(id='private-draw-2')),
    ('result.json', lambda x: x['cases'].pop()),
    ('result.json', lambda x: x.update(status='incomplete-review')),
])
def test_repinned_invalid_joins_and_reviews_are_rejected(tmp_path, filename, change):
    folder = write_bundle(tmp_path)
    value = _read(folder / filename)
    change(value)
    _save(folder / filename, value)
    _repin(folder)
    with pytest.raises(ValueError):
        load_comparison(folder)


def test_source_hash_mismatch_is_rejected_even_with_current_closure(tmp_path):
    folder = write_bundle(tmp_path)
    name = 'result.json'
    value = _read(folder / name)
    value['provenance']['report_code']['sha256'] = '0' * 64
    _save(folder / name, value)
    closure = _read(folder / 'closure.json')
    closure['files'][name] = _hash(folder / name)
    _save(folder / 'closure.json', closure)
    with pytest.raises(ValueError):
        load_comparison(folder)


@pytest.mark.parametrize('name', ['review-packet.json', 'received/review.json', 'received'])
def test_symlinked_required_files_and_received_folder_are_rejected(tmp_path, name):
    folder = write_bundle(tmp_path)
    target = folder / name
    outside = tmp_path / 'outside'
    target.rename(outside)
    target.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(ValueError):
        load_comparison(folder)
