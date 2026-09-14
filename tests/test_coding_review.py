"""The portable review must preserve frozen text and keep reviewers independent."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import re

import pytest


def test_portable_review_preserves_sources_and_rejects_contaminated_inputs(tmp_path):
    assert importlib.util.find_spec('src.eval.coding_review'), 'Portable coding review builder is missing'
    from src.eval.coding_review import build

    packet = tmp_path / 'packet'
    packet.mkdir()
    attack = '</script><script>alert("invented")</script>\n  student text\u2028'
    cases = [{
        'case': number, 'episode_id': 'PRIVATE_SOURCE_ID',
        'legacy_labels': ['PRIVATE_PRIOR_LABEL'],
        'prefix': {
            'context_status': 'Notebook work and later outcomes are unknown.',
            'context': [{'id': 'c1', 'role': 'student', 'lines': [
                {'line': 1, 'text': 'before = 1  '}, {'line': 3, 'text': 'before'}]}],
            'turns': [{'id': 't1', 'role': 'tutor', 'lines': [
                {'line': 1, 'text': 'Try another expression.'}]}],
        },
        'recorded_message': attack,
    } for number in range(1, 9)]
    form = {'reviewer': None, 'previously_seen_these_cases_or_labels': None,
            'cases': [{'case': n, 'followup': None, 'note': None} for n in range(1, 9)]}
    options = {name: 'Invented description for ' + name for name in (
        'revised-code', 'submitted-code', 'submitted-work', 'asked-for-help',
        'acknowledgment', 'other', 'insufficient-evidence')}
    manifest = {'cases': 8, 'options': options, 'artifacts': {}}

    def write(name, value):
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        (packet / name).write_bytes(raw)
        manifest['artifacts'][name] = sha256(raw).hexdigest()

    def pin():
        (packet / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

    write('source-records.json', cases)
    write('reviewer-1.json', form)
    write('reviewer-2.json', form)
    pin()
    originals = {p.name: p.read_bytes() for p in packet.iterdir()}
    output = tmp_path / 'ui'
    build(packet, output)
    pages = {}
    for reviewer in ('reviewer-1', 'reviewer-2'):
        html = (output / f'{reviewer}.html').read_text(encoding='utf-8')
        assert attack not in html
        embedded = re.search(r'<script\b[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                             html, re.S).group(1)
        pages[reviewer] = json.loads(embedded)
        assert pages[reviewer]['reviewer_id'] == reviewer
        assert pages[reviewer]['form'] == form
        assert pages[reviewer]['options'] == options
        assert pages[reviewer]['cases'][0] == {
            'case': 1, 'context_status': 'Notebook work and later outcomes are unknown.',
            'context': [{'id': 'c1', 'role': 'student', 'text': 'before = 1  \n\nbefore'}],
            'turns': [{'id': 't1', 'role': 'tutor', 'text': 'Try another expression.'}],
            'recorded_message': attack,
        }
        assert 'PRIVATE_PRIOR_LABEL' not in html and 'PRIVATE_SOURCE_ID' not in html
    assert pages['reviewer-1']['packet_id'] == pages['reviewer-2']['packet_id']
    assert re.fullmatch('[0-9a-f]{64}', pages['reviewer-1']['packet_id'])
    index = (output / 'index.html').read_text(encoding='utf-8')
    assert 'reviewer-1.html' in index and 'reviewer-2.html' in index
    assert attack not in index and 'before = 1' not in index
    assert {p.name: p.read_bytes() for p in packet.iterdir()} == originals
    built = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(FileExistsError):
        build(packet, output)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == built

    (packet / 'source-records.json').write_text('[]', encoding='utf-8')
    with pytest.raises(ValueError, match='hash|digest|pin'):
        build(packet, tmp_path / 'bad-pin')
    assert not (tmp_path / 'bad-pin').exists()
    write('source-records.json', cases)
    for name, change in (
        ('source-records.json', lambda value: value[0]['prefix']['context'][0]['lines'].reverse()),
        ('source-records.json', lambda value: value[0]['prefix']['context'][0].update(role='system')),
        ('source-records.json', lambda value: value[0].update(case=2)),
        ('reviewer-1.json', lambda value: value['cases'][0].update(followup='asked-for-help')),
        ('reviewer-2.json', lambda value: value.update(reviewer='Another reviewer')),
    ):
        value = deepcopy(cases if name == 'source-records.json' else form)
        change(value)
        write(name, value)
        pin()
        with pytest.raises(ValueError):
            build(packet, tmp_path / 'invalid')
        assert not (tmp_path / 'invalid').exists()
        write(name, cases if name == 'source-records.json' else form)
    manifest['options']['unrequested-new-label'] = 'A changed coding task'
    pin()
    with pytest.raises(ValueError):
        build(packet, tmp_path / 'changed-task')
    assert not (tmp_path / 'changed-task').exists()
