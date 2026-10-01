"""One authored, local communication step; no model calls or learned probabilities."""
import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

from src.agents import behavior_policy as policy, chat_student as chat, notebook_student as store

CONFIG = 'authored-policy.json'
REPLY = 'authored-policy-reply.json'
SCOPE = 'Authored scenario mechanics. Weights describe invented examples, not measured student probabilities.'
CODE = 'items = []\nfirst = items[0]\nprint(first)\n'


def _paths(folder):
    folder = Path(folder).absolute()
    if any(p.is_symlink() for p in (folder, *folder.parents, folder / CONFIG, folder / REPLY)):
        raise ValueError('Authored policy paths must not be symlinks.')
    return folder / CONFIG, folder / REPLY


def _sources():
    return {Path(p).name: store.digest(Path(p).read_text()) for p in (__file__, policy.__file__)}


def create(folder, *, seed=4):
    """Execute only this module's fixed example, then prepare a fresh one-step session."""
    folder = Path(folder)
    config_path, _ = _paths(folder)
    if folder.exists():
        raise FileExistsError(folder)
    if type(seed) is not int or seed < 0:
        raise ValueError('Use a nonnegative integer seed.')
    # No uploaded source, shell, dependencies, credentials or network in this fixed example.
    execution = subprocess.run([sys.executable, '-I', '-c', CODE], capture_output=True,
                               text=True, timeout=5, check=False)
    if execution.returncode != 1 or not execution.stderr.endswith('IndexError: list index out of range\n'):
        raise ValueError('The fixed authored checkpoint did not produce its expected error.')
    context = {'last_assistance': ['checking'], 'feedback': 'runtime-error'}
    request = {'basis': 'authored', 'seed': seed,
        'query': {'id': 'empty-list-query', 'account_id': 'authored-query',
                  'source_ref': 'authored:empty-list-checkpoint', 'context': context,
                  'diagnostic': execution.stderr.strip().splitlines()[-1]},
        'examples': [
            {'id': ident, 'account_id': account, 'source_ref': 'authored:' + ident,
             'origin': 'authored', 'context': context,
             'behavior': {'assistance': ['checking'], 'material': material, 'task_relation': 'same'}}
            for ident, account, material in (
                ('example-a1', 'authored-a', []), ('example-a2', 'authored-a', ['diagnostic']),
                ('example-b1', 'authored-b', ['diagnostic']))]}
    request = policy.Request.model_validate(request).model_dump()
    query = {'id': 'authored-empty-list', 'conversation_id': 'authored-empty-list',
             'student_id': 'authored-query', 'prefix': [
                 {'role': 'student', 'text': 'how do i get the first item'},
                 {'role': 'tutor', 'text': 'You can access the first item at index 0. What happens when you try it?'}]}
    saved = chat.create(folder, query=query, model='authored-policy-v1', max_decisions=1)
    store._save(config_path, {'version': 1, 'scope': SCOPE, 'binding': saved['binding'],
        'source_sha256': _sources(), 'prefix': query['prefix'], 'request': request,
        'checkpoint': {'source': CODE, 'stdout': execution.stdout, 'stderr': execution.stderr,
                       'returncode': execution.returncode}}, exclusive=True)
    chat.show(folder)  # Initialize the existing session lock for read-only browser access.
    return folder


def checked(folder, manifest, receipts):
    """Read and bind policy evidence to the verified chat; never execute or generate."""
    config_path, reply_path = _paths(folder)
    if not config_path.exists():
        if reply_path.exists() or manifest['model'] == 'authored-policy-v1':
            raise ValueError('The authored policy configuration is missing.')
        return None, None
    config = store._read(config_path)
    initial = chat._initial(manifest['query'])
    binding = {'session_sha256': store.digest(manifest), 'state_sha256': store.digest(initial)}
    if (set(config) != {'version', 'scope', 'binding', 'source_sha256', 'prefix', 'request', 'checkpoint'}
            or config['version'] != 1 or config['scope'] != SCOPE or config['source_sha256'] != _sources()
            or config['binding'] != binding or config['prefix'] != manifest['query']['prefix']
            or manifest['model'] != 'authored-policy-v1' or manifest['max_decisions'] != 1):
        raise ValueError('Authored configuration no longer matches this session and implementation.')
    checkpoint = config['checkpoint']
    if (set(checkpoint) != {'source', 'stdout', 'stderr', 'returncode'}
            or checkpoint['source'] != CODE or checkpoint['returncode'] != 1
            or checkpoint['stdout'] != '' or not isinstance(checkpoint['stderr'], str)
            or not checkpoint['stderr'].endswith('IndexError: list index out of range\n')):
        raise ValueError('The fixed execution checkpoint is invalid.')
    trace = policy._receipt(config['request'])
    diagnostic = trace['result']['query']['diagnostic']
    if diagnostic is not None and diagnostic != checkpoint['stderr'].strip().splitlines()[-1]:
        raise ValueError('The supplied diagnostic differs from the saved execution.')
    expected = {'version': 1, 'binding': binding, 'config_sha256': store.digest(config),
                'prefix_sha256': store.digest(config['prefix']), 'policy': trace}
    if receipts:
        step, = receipts
        if (not reply_path.exists() or store._read(reply_path) != expected
                or trace['result']['rendering']['status'] != 'rendered'
                or step['request']['binding'] != binding or step['request']['tutor_reply'] is not None
                or step['status'] != 'complete'
                or step['response'] != {'decision': 'reply', 'text': trace['result']['rendering']['text']}):
            raise ValueError('The policy selection does not bind to the saved chat reply.')
    elif reply_path.exists():
        raise ValueError('An incomplete policy reply exists; do not resend.')
    return config, expected


def make_reply(folder):
    """Preflight before chat.step; the callback checks the exact delivered prefix."""
    folder = Path(folder)
    with store._locked(folder):
        manifest, state, decisions = chat._load(folder)
        receipts = [store._read(p) for p in sorted(folder.glob('step-*.json'))]
        config, expected = checked(folder, manifest, receipts)
        if config is None or decisions or state['status'] != 'ready':
            raise ValueError('This authored checkpoint has no remaining local step.')
        rendered = expected['policy']['result']['rendering']
        if rendered['status'] != 'rendered':
            raise ValueError('The authored template is unavailable or missing input; no decision was consumed.')
    def reply(prefix):
        if prefix != config['prefix']:
            raise ValueError('The delivered prefix differs from the prepared policy checkpoint.')
        config_path, reply_path = _paths(folder)
        if store._read(config_path) != config or _sources() != config['source_sha256']:
            raise ValueError('The authored policy changed after preparation.')
        store._save(reply_path, expected, exclusive=True)
        return rendered['text']
    return reply


def project(folder, manifest, receipts, encounter):
    config, expected = checked(folder, manifest, receipts)
    if config is None:
        return
    result = expected['policy']['result']
    encounter.update(title='Local behavior example', task='Respond after an empty-list error',
        initialization=SCOPE, evidence_card=None,
        authored_policy={'scope': SCOPE, 'checkpoint': config['checkpoint'], 'preview': result})
    for index, frame in enumerate(encounter['frames']):
        frame['behavior_policy'] = deepcopy(result) if index else None
        for turn in frame['dialogue']:
            turn['origin'] = 'authored'


def verify(folder):
    folder = Path(folder)
    with store._locked(folder):
        manifest, _, _ = chat._load(folder)
        receipts = [store._read(p) for p in sorted(folder.glob('step-*.json'))]
        _, expected = checked(folder, manifest, receipts)
        if expected is None:
            raise ValueError('No authored policy is attached.')
        return expected['policy']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create', 'verify'])
    parser.add_argument('folder', type=Path)
    parser.add_argument('--seed', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'create':
        create(args.folder, seed=args.seed)
    else:
        verify(args.folder)
    print('Authored policy ' + ('prepared' if args.command == 'create' else 'verified') + '. No model requests.')


if __name__ == '__main__':
    main()
