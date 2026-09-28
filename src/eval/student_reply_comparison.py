"""Verify saved base/adapter first replies without models, labels or source-path reads."""
from hashlib import sha256
import json
from pathlib import Path
import re

from src.eval.retrieval_baseline import Query
from src.eval.student_training import messages


ROOT_FILES = ('cohort-manifest.json', 'cohort-completion.json',
              'adapter-manifest.json', 'adapter-completion.json')
CALL_FILES = ('request.json', 'result.json', 'invocation.json')


def _require(condition):
    if not condition:
        raise ValueError('Saved student replies do not share verified first-reply evidence.')


def _read_files(folder):
    folder = Path(folder).absolute()
    raw = {}

    def read(name):
        path = folder / name
        if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Comparison evidence must be regular local files without symlinks.')
        raw[name] = path.read_bytes()
        return json.loads(raw[name])

    closure = read('closure.json')
    cohort = read('cohort-manifest.json')
    cases = cohort.get('cases')
    _require(isinstance(cases, list) and bool(cases))
    keys = [case.get('key') for case in cases]
    _require(all(isinstance(k, str) and re.fullmatch(r'case-[0-9]{2}', k) for k in keys)
             and len(set(keys)) == len(keys))
    names = [*ROOT_FILES, *[f'calls/{key}/{arm}/{name}' for key in keys
                          for arm in ('base', 'full') for name in CALL_FILES]]
    _require(closure.get('version') == 1 and isinstance(closure.get('files'), dict)
             and set(closure['files']) == set(names))
    for name in names:
        if name not in raw:
            read(name)
        _require(sha256(raw[name]).hexdigest() == closure['files'][name])
    return raw


def evidence_hashes(folder):
    """Pin only known local evidence; archived absolute paths remain metadata."""
    return {name: sha256(value).hexdigest() for name, value in _read_files(folder).items()}


def _pin_suffix(pins, suffix, expected):
    parts = Path(suffix).parts
    _require([value for name, value in pins.items() if Path(name).parts[-len(parts):] == parts] == [expected])


def _base_identity(identity):
    adapter = identity['adapter_path']
    return {key: identity[key] for key in ('base', 'model_path', 'packages')} | {
        'files': {path: value for path, value in identity['files'].items()
                  if adapter is None or not Path(path).is_relative_to(adapter)}}


def load_comparison(folder, *, expected_files=None):
    raw = _read_files(folder)
    hashes = {name: sha256(value).hexdigest() for name, value in raw.items()}
    _require(expected_files is None or hashes == expected_files)
    values = {name: json.loads(value) for name, value in raw.items()}
    cohort, closed, adapter, adapted = (values[name] for name in ROOT_FILES)
    _require(closed.get('status') == adapted.get('status') == 'closed')
    _require(closed['files']['manifest.json'] == hashes['cohort-manifest.json']
             and adapted['files']['manifest.json'] == hashes['adapter-manifest.json'])
    _pin_suffix(adapter['pins'], 'local-conversation-cohort-v1/manifest.json', hashes['cohort-manifest.json'])
    _pin_suffix(adapter['pins'], 'local-conversation-cohort-v1/completion.json', hashes['cohort-completion.json'])
    _require(adapter['cases'] == cohort['cases'])
    first = [call for call in adapter['calls'] if call['position'] == 1]
    _require(len(first) == len(cohort['cases']) and len({call['case'] for call in first}) == len(first))
    first = {call['case']: call for call in first}
    _require(set(first) == {case['key'] for case in cohort['cases']})
    displayed, query_ids, conversations, model = [], set(), set(), None
    identities = {}
    for number, case in enumerate(cohort['cases'], 1):
        key = case['key']
        query = Query.model_validate(case['query']).model_dump()
        _require(query['id'] not in query_ids and query['conversation_id'] not in conversations)
        query_ids.add(query['id']); conversations.add(query['conversation_id'])
        call = first[key]
        _require(call['key'] == f'{key}/01-student')
        _require(Path(call['source']).parts[-4:] == ('calls', key, '02-trained', '01-student'))
        _require(call['request_sha256'] == closed['files'][f'calls/{key}/02-trained/01-student/request.json']
                 and call['cached_result_sha256'] == closed['files'][f'calls/{key}/02-trained/01-student/result.json'])
        conditions, saved = [], {}
        for arm, title, original, closure in (
                ('base', 'Base model', f'calls/{key}/01-starting/01-student', closed),
                ('full', 'Full-pass adapter (experimental)', f'calls/{key}/01-student', adapted)):
            local = f'calls/{key}/{arm}'
            for name in CALL_FILES:
                _require(hashes[f'{local}/{name}'] == closure['files'][f'{original}/{name}'])
            request, result, invocation = (values[f'{local}/{name}'] for name in CALL_FILES)
            identity = result['model_identity']
            _require(identities.setdefault(arm, identity) == identity)
            pins = (adapter if arm == 'full' else cohort)['pins']
            _require(bool(identity['files']) and all(pins.get(path) == value
                     for path, value in identity['files'].items()))
            trained = arm == 'full'
            _require(request['role'] == result['role'] == 'student'
                     and request['adapter'] is trained and result['adapter'] is trained
                     and identity['adapter'] is trained
                     and (isinstance(identity['adapter_path'], str) and bool(identity['adapter_path']) if trained else identity['adapter_path'] is None))
            _require(request['prefix'] == query['prefix'] and request['messages'] == messages(query['prefix']))
            _require(result['request_sha256'] == hashes[f'{local}/request.json']
                     and result['status'] == 'complete' and result['finish_reason'] == 'stop'
                     and isinstance(result['text'], str) and bool(result['text'].strip())
                     and invocation['status'] == 'returned' and invocation['returncode'] == 0)
            ids = result['generated_token_ids']
            _require(isinstance(ids, list) and bool(ids) and len(ids) == result['generation_tokens'] <= 256
                     and ids[-1] in result['eos_token_ids']
                     and not any(token in result['eos_token_ids'] for token in ids[:-1]))
            _require(request['max_tokens'] == result['max_tokens'] == 256
                     and type(request['seed']) is int and request['seed'] == result['seed']
                     and isinstance(result['prompt_tokens'], list) and bool(result['prompt_tokens']))
            if trained:
                _require(call['request_sha256'] == hashes[f'{local}/request.json'])
            saved[arm] = (request, result)
            conditions.append({'id': arm, 'title': title, 'status': 'reply', 'text': result['text'],
                'model_details': {name: identity[name] for name in ('base', 'adapter', 'packages',
                    'training_preparation_sha256', 'training_receipt_sha256')}})
        base_request, base_result = saved['base']; full_request, full_result = saved['full']
        _require(base_request['seed'] == full_request['seed']
                 and base_result['settings'] == full_result['settings']
                 and base_result['prompt_tokens'] == full_result['prompt_tokens']
                 and _base_identity(base_result['model_identity']) == _base_identity(full_result['model_identity']))
        identity = _base_identity(base_result['model_identity'])
        _require(model is None or model == identity)
        model = identity
        prefix = query['prefix']; boundary = len(prefix)
        while boundary and prefix[boundary - 1]['role'] == 'tutor':
            boundary -= 1
        question = prefix[boundary - 1]['text']
        while boundary and prefix[boundary - 1]['role'] == 'student':
            boundary -= 1
        summary = ' '.join(question.split())
        displayed.append({'id': key, 'title': f'Conversation {number:02d}',
            'summary': summary[:160] + ('…' if len(summary) > 160 else ''),
            'context_status': 'Same recorded conversation supplied to both models; notebook behavior is unknown.',
            'prefix': {'context': prefix[:boundary], 'turns': prefix[boundary:]}, 'conditions': conditions})
    _require(evidence_hashes(folder) == hashes)
    return {'version': 1, 'kind': 'saved-student-reply-comparison', 'cases': displayed,
        'study': {'cases': len(displayed), 'saved_replies': 2 * len(displayed), 'model': model['base'],
            'limits': ['One saved first reply per model on the same exposed development prefixes.',
                       'The full-pass adapter is experimental; these examples do not establish improved student fidelity.',
                       'Conversation IDs do not identify individual learners; notebook behavior and policy effects are unmeasured.',
                       'Viewing does not generate messages, collect labels or adopt a model.']}}
