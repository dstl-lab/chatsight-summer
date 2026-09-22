"""Read a closed communication review without generation, scoring or new labels."""
from hashlib import sha256
import json
from pathlib import Path

from src.eval.communication_review import _keys, _text, validate_packet


def load_comparison(folder, *, expected_closure=None):
    """Verify fixed files and project only the messages and their saved reviews."""
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError('The comparison folder must not be a symlink.')
    folder = folder.resolve(strict=True)
    received = folder / 'received'
    if received.is_symlink() or not received.is_dir():
        raise ValueError('The received review folder must be a real directory.')

    def read(name):
        path = folder / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(folder):
            raise ValueError('Comparison evidence must be regular files inside its folder.')
        return path.read_bytes()

    raw_closure = read('closure.json')
    if expected_closure is not None and sha256(raw_closure).hexdigest() != expected_closure:
        raise ValueError('The comparison closure changed after this workspace opened.')
    closure = json.loads(raw_closure)
    if not isinstance(closure, dict) or not isinstance(closure.get('files'), dict):
        raise ValueError('Expected saved comparison closure hashes.')
    names = ('preparation.json', 'review-packet.json', 'private-mapping.json',
             'received/review.json', 'result.json', 'report.py')
    raw = {name: read(name) for name in names}
    hashes = {name: sha256(value).hexdigest() for name, value in raw.items()}
    if any(closure['files'].get(name) != value for name, value in hashes.items()):
        raise ValueError('Saved comparison evidence does not match its closure.')
    preparation, packet, mapping, form, result = (json.loads(raw[name]) for name in names[:-1])
    validate_packet(packet)
    _keys(mapping, 'packet_id cases')
    _keys(form, 'packet_id rubric_id reviewer previously_seen_cases judgments')
    for value in (preparation, mapping, form, result):
        if not isinstance(value, dict) or value.get('packet_id') != packet['packet_id']:
            raise ValueError('Saved comparison files belong to different packets.')
    if type(preparation.get('conditions')) is not int or preparation['conditions'] != 1:
        raise ValueError('This comparison requires two draws of one historical configuration.')
    if any(value.get('rubric_id') != packet['rubric_id'] for value in (preparation, form, result)):
        raise ValueError('Saved comparison files belong to different rubrics.')
    provenance = result.get('provenance')
    _keys(provenance, 'packet mapping form report_code')
    for key, name in (('packet', 'review-packet.json'), ('mapping', 'private-mapping.json'),
                      ('form', 'received/review.json'), ('report_code', 'report.py')):
        _keys(provenance[key], 'path sha256')
        if provenance[key]['sha256'] != hashes[name]:
            raise ValueError('Saved report source hashes do not match the comparison evidence.')
    if not all(isinstance(value, list) for value in
               (mapping['cases'], form['judgments'], result.get('cases'))):
        raise ValueError('Expected saved comparison cases and judgments.')
    _text(form['reviewer'])
    if form['previously_seen_cases'] not in ('yes', 'no', 'unsure'):
        raise ValueError('Reviewer prior exposure must be explicit.')
    cases = {case['id']: case for case in packet['cases']}
    candidates = {candidate['id']: candidate for case in packet['cases'] for candidate in case['candidates']}
    reviewed = {}
    for judgment in form['judgments']:
        _keys(judgment, 'id help_request work_present note')
        _text(judgment['id'])
        if judgment['id'] in reviewed or judgment['id'] not in candidates:
            raise ValueError('Every candidate must have exactly one saved review.')
        if any(judgment[flag] not in ('yes', 'no', 'unclear', None)
               for flag in ('help_request', 'work_present')):
            raise ValueError('Review flags must be yes, no, unclear or unfinished null.')
        if judgment['note'] is not None:
            _text(judgment['note'], empty=True)
        if 'unclear' in (judgment['help_request'], judgment['work_present']):
            _text(judgment['note'])
        reviewed[judgment['id']] = judgment
    if reviewed.keys() != candidates.keys():
        raise ValueError('Every candidate must have a saved review, including unfinished flags.')
    status = 'incomplete-review' if any(j[flag] is None for j in reviewed.values()
                                       for flag in ('help_request', 'work_present')) else 'complete-review'
    if result.get('status') != status:
        raise ValueError('Saved report status differs from the saved reviews.')
    reported = {}
    for row in result['cases']:
        _keys(row, 'id reference draws flags')
        _text(row['id'])
        if row['id'] in reported or row['id'] not in cases:
            raise ValueError('Saved report must cover each comparison case exactly once.')
        reported[row['id']] = row
    if reported.keys() != cases.keys():
        raise ValueError('Saved report is missing comparison cases.')

    def message(identity):
        return {'text': candidates[identity]['text'],
                'review': {key: reviewed[identity][key] for key in ('help_request', 'work_present', 'note')}}

    displayed, seen = [], set()
    for number, entry in enumerate(mapping['cases'], 1):
        _keys(entry, 'id reference_id draws')
        _text(entry['id'])
        _text(entry['reference_id'])
        if entry['id'] not in cases or entry['id'] in seen:
            raise ValueError('The mapping must cover each comparison case exactly once.')
        seen.add(entry['id'])
        if not isinstance(entry['draws'], list) or len(entry['draws']) != 2:
            raise ValueError('Each case must retain two saved reply draws.')
        for draw in entry['draws']:
            _keys(draw, 'id draw status')
            _text(draw['id'])
            if type(draw['draw']) is not int or draw['status'] != 'reply':
                raise ValueError('Saved draws must be numbered reply occurrences.')
        draws = sorted(entry['draws'], key=lambda draw: draw['draw'])
        identities = [draw['id'] for draw in draws]
        if [draw['draw'] for draw in draws] != [1, 2] or entry['reference_id'] in identities:
            raise ValueError('Require two numbered draws and a separate recorded reference.')
        case = cases[entry['id']]
        if {entry['reference_id'], *identities} != {candidate['id'] for candidate in case['candidates']}:
            raise ValueError('Reference and draw identities must match their exact case candidates.')
        saved = reported[entry['id']]
        if (saved['reference'] != reviewed[entry['reference_id']] or saved['draws'] !=
                [draw | {'judgment': reviewed[draw['id']]} for draw in draws]):
            raise ValueError('Saved report references and draws differ from the mapped reviews.')
        displayed.append({'id': str(number), 'title': f'Reviewed case {number:02d}',
            'context_status': case['context_status'],
            'prefix': {group: [{key: turn[key] for key in ('role', 'text')} for turn in turns]
                       for group, turns in case['prefix'].items()},
            'reference': message(entry['reference_id']),
            'draws': [{'draw': draw['draw'], **message(draw['id']),
                       'shared_review_with': 3 - draw['draw'] if identities[0] == identities[1] else None}
                      for draw in draws]})
    if seen != cases.keys():
        raise ValueError('The mapping is missing comparison cases.')
    return {'version': 1, 'kind': 'saved-communication-comparison',
            'rubric_id': packet['rubric_id'], 'definitions': packet['definitions'],
            'status': status, 'cases': displayed}
