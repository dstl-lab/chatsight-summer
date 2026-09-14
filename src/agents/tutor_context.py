"""Inspect a saved student's selected cell and export the context for a tutor reply."""
import difflib
import json
from pathlib import Path
import re

from src.agents import notebook_student as student


def snapshot(folder):
    folder = Path(folder)
    with student._locked(folder):
        manifest, state, paths, decisions = student._load(folder)
        before = manifest['initial']
        baseline, kind = before['work'], 'initial-work'
        for path in paths:
            receipt = student._read(path)
            if receipt['request']['tutor_reply'] is not None:
                baseline, kind = before['work'], 'before-most-recent-supplied-tutor'
            before = receipt['result']['state']
        if state['observation'] is not None:
            student.notebook_runtime.require_current(state['observation'], state['work'],
                branch_id=state['branch_id'], activity=state['activity'], timeout=state['timeout'])
        lines = difflib.unified_diff(baseline['source'].splitlines(keepends=True),
            state['work']['source'].splitlines(keepends=True), fromfile='previous work', tofile='current work')
        diff = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                       for line in lines)
        feedback = student.notebook_session._feedback(state['observation'])
        if feedback is not None and feedback['status'] == 'environment-error':
            feedback['error'] = {'message': 'Local execution was unavailable; this work is ungraded. '
                                 'The operation receipt retains the diagnostic.'}
        packet = {'version': 1,
            'binding': {'session_sha256': student.digest(manifest), 'state_sha256': student.digest(state)},
            'status': state['status'], 'decisions_remaining': manifest['max_decisions'] - decisions,
            'initialization': state['initialization'], 'task': state['task'],
            'activity': {key:value for key,value in state['activity'].items() if key != 'image_id'},
            'dialogue': state['dialogue'],
            'pending_message': state['message'] if state['status'] == 'awaiting-tutor' else None,
            'work': state['work'], 'feedback': feedback,
            'changes': {'baseline_revision': baseline['revision'], 'baseline_source': baseline['source'],
                        'baseline_kind': kind, 'unified_diff': diff}}
        return packet | {'sha256': student.digest(packet)}


def _block(value, language=''):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    fence = '`' * max(3, 1 + max((len(run) for run in re.findall(r'`+', text)), default=0))
    return f'{fence}{language}\n{text}\n{fence}'


def render(packet):
    work, changes = packet['work'], packet['changes']
    if packet['status'] not in ('active', 'awaiting-tutor'):
        next_step = 'This encounter has stopped and cannot accept another tutor reply.'
    elif packet['decisions_remaining'] <= 0:
        next_step = 'Decision budget exhausted; this is not student silence.'
    elif packet['status'] == 'awaiting-tutor':
        next_step = 'A tutor reply can continue this student using the exported context.'
    elif packet['status'] == 'active':
        next_step = 'The student can continue quiet work; there is no message awaiting a tutor reply.'
    previous = ('the initial work' if changes['baseline_kind'] == 'initial-work'
                else 'the work before the most recent supplied tutor exchange')
    sections = ['# Student context',
        f"Status: {packet['status']}. Decisions remaining: {packet['decisions_remaining']}. {next_step}",
        'Scope: the selected cell and its recorded current feedback. Other notebook cells and '
        'unobserved student activity are unavailable.',
        '## Initialization\n\n' + _block(packet['initialization']),
        '## Task\n\n' + _block(packet['task']),
        '## Local activity\n\n' + _block(packet['activity'], 'json'),
        '## Preceding dialogue']
    for turn in packet['dialogue']:
        sections.append(f"{turn['role']} ({turn.get('origin', 'initial context')}):\n\n" + _block(turn['text']))
    sections.extend([
        '## Pending student message\n\n' + (_block(packet['pending_message'])
            if packet['pending_message'] is not None else 'No pending message.'),
        f"## Current work — cell index {work['cell_index']}, revision {work['revision']}\n\n"
            + _block(work['source'], 'python'),
        '## Current check feedback\n\n' + (_block(packet['feedback'], 'json')
            if packet['feedback'] is not None else 'No check feedback for this revision.'),
        f"## Changes from revision {changes['baseline_revision']}\n\nCompared with {previous}. "
            'This is the net source change between two saved endpoints.\n\n'
            + (_block(changes['unified_diff'], 'diff') if changes['unified_diff'] else 'No source change.')])
    return '\n\n'.join(sections) + '\n'


def read_handoff(path):
    packet = student._read(Path(path))
    if (not isinstance(packet, dict) or type(packet.get('version')) is not int or packet['version'] != 1
            or packet.get('sha256') != student.digest({k:v for k,v in packet.items() if k != 'sha256'})):
        raise ValueError('Tutor context is unsupported or its content hash changed.')
    binding = packet.get('binding')
    if (not isinstance(binding, dict) or set(binding) != {'session_sha256', 'state_sha256'}
            or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in binding.values())):
        raise ValueError('Tutor context requires valid session and state bindings.')
    return packet


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', type=Path, help='Create a JSON handoff without replacing an existing file.')
    args = parser.parse_args()
    packet = snapshot(args.folder)
    if args.output:
        student._save(args.output, packet, exclusive=True)
    print(render(packet), end='')


if __name__ == '__main__':
    main()
