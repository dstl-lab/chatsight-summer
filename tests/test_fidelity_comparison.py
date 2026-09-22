"""An authored frozen benchmark checks offline evidence joins and target isolation."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from src.eval import communication_scoring as scoring, student_continuation as continuation
from src.eval.fidelity_comparison import evidence_hashes, load_comparison, _prompt


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def _read(path):
    return json.loads(path.read_bytes())


def _hash(path):
    return sha256(path.read_bytes()).hexdigest()


def _repin(folder, *, score_report=True):
    experiment = _read(folder / 'experiment.json')
    experiment['files'] = {'/archived/private/' + name: _hash(folder / name)
                           for name in ('protocol.json', 'episodes.json', 'inputs.json')}
    for module in (continuation, scoring):
        experiment['files']['/never/open/src/eval/' + Path(module.__file__).name] = _hash(Path(module.__file__))
    _save(folder / 'experiment.json', experiment)
    result = _read(folder / 'results.json')
    result['experiment_sha256'] = _hash(folder / 'experiment.json')
    _save(folder / 'results.json', result)
    _save(folder / 'execution-verification.json', {'results_sha256': _hash(folder / 'results.json')})
    packet_id = continuation._digest([_hash(folder / name) for name in ('experiment.json', 'results.json')])
    packet, mapping, form = [_read(folder / name) for name in
                             ('review-packet.json', 'private-mapping.json', 'received/review.json')]
    for name, value in zip(('review-packet.json', 'private-mapping.json', 'received/review.json'),
                           (packet, mapping, form), strict=True):
        value['packet_id'] = packet_id
        _save(folder / name, value)
    report = scoring.score(packet, mapping, form) if score_report else _read(folder / 'coding-result.json')
    report['packet_id'] = packet_id
    report['provenance'] = {key + '_sha256': _hash(folder / name) for key, name in (
        ('packet', 'review-packet.json'), ('mapping', 'private-mapping.json'), ('judgments', 'received/review.json'))}
    report['provenance']['source_sha256'] = _hash(Path(scoring.__file__))
    _save(folder / 'coding-result.json', report)
    _save(folder / 'completion-verification.json', {'files': {name: _hash(folder / name) for name in (
        'experiment.json', 'results.json', 'execution-verification.json', 'review-packet.json', 'private-mapping.json')}})
    _save(folder / 'coding-verification.json', {'files': {'/private/archive/' + name: _hash(folder / name)
        for name in ('experiment.json', 'completion-verification.json', 'received/review.json', 'coding-result.json')}})


def write_bundle(tmp_path, *, dispositions=None):
    """Shared browser fixture: eight invented cases; returns the benchmark directory."""
    folder = tmp_path / 'fidelity'
    dispositions = dispositions or {}
    definitions = {'help_request': 'An observable help request.', 'work_present': 'Substantive submitted work.'}
    packet = {'packet_id': 'prepared', 'rubric_id': 'help-work-v1', 'definitions': definitions, 'cases': []}
    mapping = {'packet_id': 'prepared', 'cases': []}
    form = {'packet_id': 'prepared', 'rubric_id': 'help-work-v1', 'reviewer': 'PRIVATE REVIEWER',
            'previously_seen_cases': 'unsure', 'judgments': []}
    episodes, jobs, calls = [], [], []
    for number in range(1, 9):
        episode = {'id': f'private-episode-{number}', 'conversation_key': f'private-conversation-{number}',
            'context': [{'id': f'earlier-{number}', 'role': 'student', 'text': 'Earlier authored help request.'}],
            'turns': [
                {'id': f'question-{number}', 'phase': 'request', 'role': 'student', 'text': f'How does example {number} work?'},
                {'id': f'tutor-{number}', 'phase': 'response', 'role': 'tutor', 'text': 'Check the final item. <script>inert</script>'},
                {'id': f'future-{number}', 'phase': 'followup', 'role': 'student', 'text': f'Hidden reference {number}.'}]}
        episodes.append(episode)
        ref_id, case_id = f'private-reference-{number}', f'private-case-{number}'
        prefix = {group: [{key: turn[key] for key in ('id', 'role', 'text')} for turn in turns]
                  for group, turns in (('context', episode['context']), ('turns', episode['turns'][:2]))}
        packet['cases'].append({'id': case_id, 'context_status': 'Authored dialogue; notebook work is unknown.',
            'prefix': prefix, 'candidates': [{'id': ref_id, 'text': episode['turns'][-1]['text']}]})
        mapping['cases'].append({'id': case_id, 'reference_id': ref_id, 'draws': []})
        form['judgments'].append({'id': ref_id, 'help_request': 'yes', 'work_present': 'no', 'note': None})
    for draw in range(1, 5):
        for number, episode in enumerate(episodes, 1):
            order = scoring.CONDITIONS if (draw + number) % 2 == 0 else scoring.CONDITIONS[::-1]
            for condition in order:
                case = packet['cases'][number - 1]
                job = {'case': number, 'condition': condition, 'draw': draw,
                       'prompt': _prompt(episode, condition, case['context_status'])}
                jobs.append(job)
                status = dispositions.get((number, condition, draw), 'reply')
                identity = f'private-{number}-{condition}-{draw}'
                text = f'Authored draw {draw} for case {number}.'
                mapping['cases'][number - 1]['draws'].append(
                    {'id': identity, 'condition': condition, 'draw': draw, 'status': status})
                call = {'request': job, 'status': 'error' if status == 'error' else 'complete'}
                if status == 'error':
                    call['error'] = {'type': 'RuntimeError', 'message': 'Private provider diagnostic.'}
                else:
                    call['response'] = {'decision': status, 'text': text if status == 'reply' else ''}
                calls.append(call)
                if status == 'reply':
                    case['candidates'].append({'id': identity, 'text': text})
                    form['judgments'].append({'id': identity, 'help_request': 'yes',
                                              'work_present': 'yes' if draw % 2 else 'no', 'note': None})
    for name, value in (
        ('protocol.json', {'cases': 8, 'draws_per_condition': 4, 'logical_requests': 64,
            'conditions': list(scoring.CONDITIONS), 'model': 'authored-model',
            'rubric_id': 'help-work-v1', 'definitions': definitions}),
        ('experiment.json', {'schema': continuation.Continuation.model_json_schema()}),
        ('episodes.json', episodes), ('inputs.json', jobs), ('results.json', {'calls': calls}),
        ('review-packet.json', packet), ('private-mapping.json', mapping), ('received/review.json', form)):
        _save(folder / name, value)
    _repin(folder)
    return folder


def test_closed_view_matches_evidence_is_read_only_and_hides_private_metadata(tmp_path):
    folder = write_bundle(tmp_path)
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in folder.rglob('*') if path.is_file()}
    pin = evidence_hashes(folder)
    view = load_comparison(folder, expected_files=pin)
    assert view['kind'] == 'saved-student-fidelity-comparison'
    assert len(view['cases']) == 8
    assert view['study']['counts']['scheduled_draws'] == 64
    assert view['study']['paired']['grounded']['mean_brier'] == .125
    assert view['study']['paired']['grounded_minus_current_exchange'] == 0
    assert view['study']['reference_counts']['work_present'] == {'yes': 0, 'no': 8, 'unclear': 0}
    case = view['cases'][0]
    assert case['summary'] == 'How does example 1 work?'
    assert case['reference']['text'] == 'Hidden reference 1.'
    assert [arm['id'] for arm in case['conditions']] == ['current-exchange', 'grounded']
    assert [draw['draw'] for draw in case['conditions'][0]['draws']] == [1, 2, 3, 4]
    assert '<script>inert</script>' in case['prefix']['turns'][1]['text']  # Render layer owns HTML escaping.
    rendered = json.dumps(view)
    assert all(secret not in rendered for secret in ('private-', 'PRIVATE REVIEWER', '/private/archive/'))
    assert all((path.read_bytes(), path.stat().st_mtime_ns) == value for path, value in before.items())


def test_errors_and_no_reply_are_counted_and_never_relabelled(tmp_path):
    folder = write_bundle(tmp_path, dispositions={(1, 'grounded', 1): 'error', (2, 'current-exchange', 4): 'no-reply'})
    view = load_comparison(folder)
    assert view['study']['counts']['complete_cases'] == 6
    assert view['study']['dispositions']['grounded']['error'] == 1
    assert view['study']['dispositions']['current-exchange']['no-reply'] == 1
    assert view['cases'][0]['scores'] is None and view['cases'][1]['scores'] is None
    slot = view['cases'][0]['conditions'][1]['draws'][0]
    assert slot == {'draw': 1, 'status': 'error', 'text': None, 'review': None}
    assert 'Private provider diagnostic.' not in json.dumps(view)


def test_moved_bundle_does_not_follow_archived_paths(tmp_path):
    folder = write_bundle(tmp_path)
    moved = tmp_path / 'relocated'
    shutil.copytree(folder, moved)
    shutil.rmtree(folder)
    assert len(load_comparison(moved)['cases']) == 8


def test_changed_file_and_startup_pin_fail_closed(tmp_path):
    folder = write_bundle(tmp_path)
    pin = evidence_hashes(folder)
    path = folder / 'inputs.json'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        load_comparison(folder)
    _repin(folder)
    with pytest.raises(ValueError):
        load_comparison(folder, expected_files=pin)


@pytest.mark.parametrize('mutation', ['future-in-prompt', 'prefix', 'reference', 'response', 'duplicate-conversation', 'score'])
def test_even_repinned_mismatches_cannot_be_displayed(tmp_path, mutation):
    folder = write_bundle(tmp_path)
    if mutation == 'future-in-prompt':
        inputs, results = _read(folder / 'inputs.json'), _read(folder / 'results.json')
        inputs[0]['prompt'] += '\nHidden reference 1.'
        results['calls'][0]['request'] = deepcopy(inputs[0])
        _save(folder / 'inputs.json', inputs)
        _save(folder / 'results.json', results)
    elif mutation in ('prefix', 'reference'):
        packet = _read(folder / 'review-packet.json')
        if mutation == 'prefix':
            packet['cases'][0]['prefix']['turns'][0]['text'] = 'Different visible question.'
        else:
            packet['cases'][0]['candidates'][0]['text'] = 'Different recorded reference.'
        _save(folder / 'review-packet.json', packet)
    elif mutation == 'response':
        results = _read(folder / 'results.json')
        results['calls'][0]['response']['text'] = 'Different generated reply.'
        _save(folder / 'results.json', results)
    elif mutation == 'duplicate-conversation':
        episodes = _read(folder / 'episodes.json')
        episodes[1]['conversation_key'] = episodes[0]['conversation_key']
        _save(folder / 'episodes.json', episodes)
    else:
        report = _read(folder / 'coding-result.json')
        report['paired']['grounded']['mean_brier'] = 0
        _save(folder / 'coding-result.json', report)
    _repin(folder, score_report=mutation != 'score')
    with pytest.raises(ValueError):
        load_comparison(folder)


@pytest.mark.parametrize('name', ['inputs.json', 'received/review.json', 'received'])
def test_symlinks_are_rejected(tmp_path, name):
    folder = write_bundle(tmp_path)
    original = folder / name
    outside = tmp_path / 'outside'
    original.rename(outside)
    original.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(ValueError):
        load_comparison(folder)
