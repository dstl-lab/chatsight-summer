"""Verify and display the closed matched student-continuation benchmark offline."""
from hashlib import sha256
import json
from pathlib import Path

from src.eval import communication_scoring as scoring, student_continuation as continuation
from src.eval.communication_review import _keys, _text


FILES = ('protocol.json', 'experiment.json', 'episodes.json', 'inputs.json',
         'results.json', 'execution-verification.json', 'completion-verification.json',
         'review-packet.json', 'private-mapping.json', 'received/review.json',
         'coding-result.json', 'coding-verification.json')
CONDITIONS = (('current-exchange', 'Current exchange only'),
              ('grounded', 'With earlier dialogue'))


def _read_files(folder):
    folder = Path(folder).absolute()
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('The benchmark folder must be a real directory.')
    raw = {}
    for name in FILES:
        path = folder / name
        if (any(part.is_symlink() for part in (path, *path.parents))
                or not path.is_file()):
            raise ValueError('Benchmark evidence must be regular files without symlinks.')
        raw[name] = path.read_bytes()
    return raw


def _hashes(raw):
    return {name: sha256(value).hexdigest() for name, value in raw.items()}


def evidence_hashes(folder):
    """Pin the fixed local evidence without following saved provenance paths."""
    return _hashes(_read_files(folder))


def _pin(files, suffix, expected):
    # Archived absolute paths are metadata; a relocated bundle remains readable.
    parts = Path(suffix).parts
    matches = [digest for name, digest in files.items()
               if Path(name).parts[-len(parts):] == parts]
    if matches != [expected]:
        raise ValueError('The benchmark evidence does not match its saved pins.')


def _prompt(episode, condition, context_status):
    visible = json.loads(continuation.make_prompt(episode)[len(continuation.PROMPT):])
    for group in ('context', 'turns'):
        for number, turn in enumerate(visible[group], 1):
            turn['id'] = f'{group}-{number}'
    if condition == 'current-exchange':
        visible['context'] = []
    visible.update(context_status=context_status, current_work=None, current_observation=None)
    return continuation.PROMPT + json.dumps(visible, ensure_ascii=False, sort_keys=True)


def load_comparison(folder, *, expected_files=None):
    """Return saved messages and measurements; never send, score new labels or write."""
    raw = _read_files(folder)
    hashes = _hashes(raw)
    if expected_files is not None and hashes != expected_files:
        raise ValueError('The benchmark changed after this workspace opened.')
    values = {name: json.loads(value) for name, value in raw.items()}
    protocol, experiment, episodes, inputs, results, execution, completion, packet, mapping, form, report, coding = (
        values[name] for name in FILES)
    for name in ('protocol.json', 'episodes.json', 'inputs.json'):
        _pin(experiment['files'], name, hashes[name])
    for name in ('experiment.json', 'results.json', 'execution-verification.json',
                 'review-packet.json', 'private-mapping.json'):
        _pin(completion['files'], name, hashes[name])
    for name in ('experiment.json', 'completion-verification.json',
                 'received/review.json', 'coding-result.json'):
        _pin(coding['files'], name, hashes[name])
    if (execution != {'results_sha256': hashes['results.json']}
            or results.get('experiment_sha256') != hashes['experiment.json']
            or packet['packet_id'] != continuation._digest(
                [hashes['experiment.json'], hashes['results.json']])):
        raise ValueError('The saved generation and review identities differ.')
    if (protocol.get('cases') != 8 or protocol.get('draws_per_condition') != 4
            or protocol.get('logical_requests') != 64
            or protocol.get('conditions') != list(scoring.CONDITIONS)
            or protocol.get('rubric_id') != packet['rubric_id']
            or protocol.get('definitions') != packet['definitions']
            or experiment.get('schema') != continuation.Continuation.model_json_schema()):
        raise ValueError('This reader requires the frozen eight-case, four-draw benchmark.')
    _text(protocol['model'])
    for module, suffix in ((continuation, 'src/eval/student_continuation.py'),
                           (scoring, 'src/eval/communication_scoring.py')):
        _pin(experiment['files'], suffix, sha256(Path(module.__file__).read_bytes()).hexdigest())
    provenance = {key + '_sha256': hashes[name] for key, name in (
        ('packet', 'review-packet.json'), ('mapping', 'private-mapping.json'),
        ('judgments', 'received/review.json'))}
    provenance['source_sha256'] = sha256(Path(scoring.__file__).read_bytes()).hexdigest()
    if report.get('provenance') != provenance:
        raise ValueError('The saved score provenance changed.')
    # Verification only: preserve the archived report, including exclusions and denominators.
    if {key: value for key, value in report.items() if key != 'provenance'} != scoring.score(packet, mapping, form):
        raise ValueError('The saved measurements do not reproduce from their reviews.')
    if (not isinstance(episodes, list) or len(episodes) != 8
            or len({episode['conversation_key'] for episode in episodes}) != 8
            or not isinstance(inputs, list) or len(inputs) != 64
            or not isinstance(results.get('calls'), list) or len(results['calls']) != 64):
        raise ValueError('Keep all eight conversations and 64 scheduled dispositions.')

    mapped = {case['id']: case for case in mapping['cases']}
    reported = {case['id']: case for case in report['cases']}
    reviewed = {judgment['id']: judgment for judgment in form['judgments']}
    calls, expected = {}, []
    for draw in range(1, 5):
        for number, (episode, case) in enumerate(zip(episodes, packet['cases'], strict=True), 1):
            order = scoring.CONDITIONS if (draw + number) % 2 == 0 else scoring.CONDITIONS[::-1]
            for condition in order:
                expected.append({'case': number, 'condition': condition, 'draw': draw,
                                 'prompt': _prompt(episode, condition, case['context_status'])})
    if (inputs != expected or any(type(job.get('case')) is not int or type(job.get('draw')) is not int
                                  for job in inputs)):
        raise ValueError('Saved requests must reproduce from visible history without references.')
    for call, job in zip(results['calls'], inputs, strict=True):
        if call.get('request') != job or call.get('status') not in ('complete', 'error'):
            raise ValueError('Every scheduled request requires its exact saved disposition.')
        if call['status'] == 'complete':
            response = continuation.Continuation.model_validate(call['response'])
            status, text = response.decision, response.text if response.decision == 'reply' else None
        else:
            _keys(call['error'], 'type message')
            for value in call['error'].values():
                _text(value, empty=True)
            status, text = 'error', None
        calls[job['case'], job['condition'], job['draw']] = {'status': status, 'text': text}

    displayed = []
    for number, (episode, case) in enumerate(zip(episodes, packet['cases'], strict=True), 1):
        visible = {'context': episode['context'], 'turns': [turn for turn in episode['turns']
                   if (turn['phase'], turn['role']) in (('request', 'student'), ('response', 'tutor'))]}
        prefix = {group: [{key: turn[key] for key in ('role', 'text')} for turn in turns]
                  for group, turns in visible.items()}
        if prefix != {group: [{key: turn[key] for key in ('role', 'text')} for turn in turns]
                      for group, turns in case['prefix'].items()}:
            raise ValueError('The reviewed prefix differs from the generation prefix.')
        reference = next((turn['text'] for turn in episode['turns']
                          if (turn['phase'], turn['role']) == ('followup', 'student')), None)
        entry = mapped[case['id']]
        candidates = {candidate['id']: candidate['text'] for candidate in case['candidates']}
        if reference is None or candidates[entry['reference_id']] != reference:
            raise ValueError('The reference must be the first subsequent recorded student message.')

        def judgment(identity):
            return {key: reviewed[identity][key] for key in ('help_request', 'work_present', 'note')}

        conditions = []
        for condition, title in CONDITIONS:
            draws = []
            for slot in sorted((slot for slot in entry['draws'] if slot['condition'] == condition),
                               key=lambda slot: slot['draw']):
                saved = calls[number, condition, slot['draw']]
                if (saved['status'] != slot['status'] or
                        saved['status'] == 'reply' and saved['text'] != candidates[slot['id']]):
                    raise ValueError('The reviewed draw differs from the saved model response.')
                draws.append({'draw': slot['draw'], **saved,
                              'review': judgment(slot['id']) if saved['status'] == 'reply' else None})
            conditions.append({'id': condition, 'title': title, 'draws': draws})
        question = next((turn['text'] for turn in reversed(prefix['turns']) if turn['role'] == 'student'), '')
        summary = ' '.join(question.split())
        displayed.append({'id': str(number), 'title': f'Fidelity case {number:02d}',
            'summary': summary[:160] + ('…' if len(summary) > 160 else ''),
            'context_status': case['context_status'], 'prefix': prefix,
            'reference': {'text': reference, 'review': judgment(entry['reference_id'])},
            'conditions': conditions, 'scores': reported[case['id']]['scores']})
    if _hashes(_read_files(folder)) != hashes:
        raise ValueError('The benchmark changed during inspection.')
    return {'version': 1, 'kind': 'saved-student-fidelity-comparison',
        'definitions': packet['definitions'], 'study': {
            'model': protocol['model'], 'counts': report['counts'], 'paired': report['paired'],
            'dispositions': report['dispositions'], 'metric': report['metric'],
            'reference_counts': {flag: {value: sum(case['reference']['review'][flag] == value for case in displayed)
                                       for value in ('yes', 'no', 'unclear')} for flag in scoring.FLAGS},
            'limits': ['Previously exposed development conversations; no pristine holdout or learner identities.',
                       'The same recorded tutor reply is used in both conditions; only earlier dialogue differs.',
                       'Communication flags do not establish notebook actions, learning or causal tutor effects.',
                       *report['limits']]}, 'cases': displayed}
