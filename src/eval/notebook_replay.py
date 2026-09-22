"""Export saved notebook encounters and their verified shared history to static HTML."""
from contextlib import ExitStack
from copy import deepcopy
import difflib
from html import escape
import json
from pathlib import Path

from src.agents import notebook_next_task, notebook_student as student


def _work_data(work):
    return {key:deepcopy(work[key]) for key in ('cell_index', 'source', 'revision')}


def _code_diff(before, after):
    lines = difflib.unified_diff(before['source'].splitlines(keepends=True),
        after['source'].splitlines(keepends=True),
        fromfile=f"revision {before['revision']}", tofile=f"revision {after['revision']}")
    return ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                   for line in lines)


def _feedback_data(observation):
    feedback = student.notebook_session._feedback(observation)
    if feedback is not None and feedback['status'] == 'environment-error':
        feedback['error'] = {'message':'Local execution was unavailable; this work is ungraded. '
                             'The operation receipt retains the diagnostic.'}
        feedback['output'] = ''
    return feedback


def _shared_record_data(record):
    dialogue = []
    for turn in record['dialogue']:
        saved = {'role':turn['role'], 'text':turn['text']}
        if 'origin' in turn:
            saved['origin'] = turn['origin']
        dialogue.append(saved)
    history = []
    for event in record['history']:
        action = event['action']
        history.append({'origin':event['origin'],
            'action':{key:deepcopy(action[key]) for key in ('decision', 'source', 'text')},
            'revision_before':event['revision_before'],
            'observation':_feedback_data(event['observation']),
            'work_after':_work_data(event['work_after'])})
    return {'task':record['task'], 'dialogue':dialogue, 'work':_work_data(record['work']),
        'status':record['status'],
        'activity':{key:deepcopy(value) for key,value in record['activity'].items() if key != 'image_id'},
        'observation':_feedback_data(record['observation']), 'history':history}


def _encounter_data(manifest, state, receipts, decisions, *, number, linked):
    initial = manifest['initial']
    initialization = initial['initialization']
    shared_history = []
    communication_scope = None
    conversation_example = None
    if manifest.get('provenance', {}).get('previous_encounter') is not None:
        records = initialization.get('earlier_encounters', []) + [initialization['previous_encounter']]
        shared_history = [_shared_record_data(record) for record in records]
        communication_scope = deepcopy(initialization.get('communication_scope'))
        conversation_example = deepcopy(initialization.get('conversation_example'))
        initialization = initialization.get('current_task', 'Earlier shared context is shown separately.')
    events, history_count, action_number = [], 0, 0
    work_before = _work_data(initial['work'])
    for recorded in [initial, *receipts]:
        if 'request' in recorded:
            reply = recorded['request']['tutor_reply']
            if reply is not None:
                events.append({'sequence':len(events) + 1, 'kind':'tutor-intervention',
                    'origin':'supplied', 'text':reply})
            recorded = recorded['result']['state']
        for saved_event in recorded['history'][history_count:]:
            history_count += 1
            action_number += 1
            work_after = _work_data(saved_event['work_after'])
            action = saved_event['action']
            events.append({'sequence':len(events) + 1, 'kind':'student-action',
                'number':action_number, 'origin':saved_event['origin'],
                'action':{key:deepcopy(action[key]) for key in ('decision', 'source', 'text')},
                'work_before':work_before, 'work_after':work_after,
                'code_diff':_code_diff(work_before, work_after),
                'feedback':_feedback_data(saved_event['observation'])})
            work_before = work_after
    dialogue = [{'role':turn['role'], 'text':turn['text'],
                 'origin':turn.get('origin', 'supplied')} for turn in initial['dialogue']]
    disposition = ('budget-exhausted' if state['status'] in ('active', 'awaiting-tutor')
                   and decisions >= manifest['max_decisions'] else state['status'])
    return {'number':number, 'title':f'Task {number}' if linked else 'Saved encounter',
        'task':initial['task'], 'initialization':deepcopy(initialization),
        'dialogue':dialogue, 'initial_work':_work_data(initial['work']),
        'activity':{key:deepcopy(value) for key,value in initial['activity'].items() if key != 'image_id'},
        'shared_history':deepcopy(shared_history), 'communication_scope':communication_scope,
        'conversation_example':conversation_example, 'events':events,
        'final':{'status':state['status'], 'disposition':disposition, 'decisions_used':decisions,
                 'max_decisions':manifest['max_decisions'], 'work':_work_data(state['work']),
                 'feedback':_feedback_data(state['observation'])}}


def _replay_data(entries):
    linked = len(entries) > 1
    return {'version':1, 'contains_private_content':True, 'linked':linked,
        'tasks':[_encounter_data(manifest, state, receipts, decisions,
            number=number, linked=linked)
            for number, (_, manifest, state, receipts, decisions) in enumerate(entries, 1)]}


def _read_replay(folder, *, previous=None):
    with ExitStack() as stack:
        entries = notebook_next_task.lineage(folder, stack, previous=previous)
        return _replay_data(entries), [entry[0] for entry in entries]


def load_replay(folder, *, previous=None):
    """Return display-oriented private evidence after offline replay and ancestry checks.

    The result contains saved dialogue and code. It is for local inspection and is
    not a de-identified or shareable artifact.
    """
    return _read_replay(Path(folder).resolve(), previous=previous)[0]


def _text(value):
    return escape(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))


def _block(value):
    return '<pre>' + _text(value) + '</pre>'


def _feedback(feedback):
    if feedback is None:
        return '<p>No check feedback for this revision.</p>'
    if feedback['status'] == 'environment-error':
        return '<p>Environment error: execution unavailable; this work is ungraded.</p>'
    label = ('Checked: ' + ('pass' if feedback['success'] else 'fail')
             if feedback['status'] == 'checked' else feedback['status'] + ' · ungraded')
    return '<p><strong>' + _text(label) + '</strong></p>' + _block(feedback)


def _work(work):
    return (f'<p>Selected cell {_text(work["cell_index"])} · revision {_text(work["revision"])}</p>'
            + _block(work['source']))


def _action(event, number, prefix):
    action = event['action']
    decision = action['decision']
    summary = f'Action {number} · {decision}'
    if decision == 'revise-work':
        summary += ' · ' + ('message with edit' if action['text'] else 'quiet edit')
    elif decision == 'request-check' and event['feedback'] is not None:
        feedback = event['feedback']
        summary += ' · ' + ('pass' if feedback['success'] else 'fail') \
            if feedback['status'] == 'checked' else ' · ' + feedback['status']
    body = f'<p>Origin: {_text(event["origin"])}</p>'
    if action['text']:
        body += '<h4>Student message</h4>' + _block(action['text'])
    body += _work(event['work_after'])
    if decision == 'request-check':
        body += '<h4>Recorded check result</h4>' + _feedback(event['feedback'])
    elif decision == 'revise-work':
        body += '<p>This edit cleared the current check feedback. No check was requested by this action.</p>'
    elif decision == 'no-reply':
        body += '<p>The student chose to stop this encounter without a reply.</p>'
    return (f'<li id="{prefix}-action-{number}"><details><summary>{_text(summary)}</summary>'
            + body + '</details></li>')


def _encounter(encounter, *, prefix):
    body = (f'<section id="{prefix}"><h2>{_text(encounter["title"])}</h2>'
            f'<h3>{_text(encounter["task"])}</h3>'
            '<details><summary>Supplied initial task context and dialogue</summary>'
            '<p>Origin: supplied initial context</p>' + _block(encounter['initialization']))
    for turn in encounter['dialogue']:
        body += (f'<h4>{_text(turn["role"])} · Origin: {_text(turn.get("origin", "supplied"))}</h4>'
                 + _block(turn['text']))
    body += '<h4>Initial selected cell</h4>' + _work(encounter['initial_work'])
    body += '<h4>Declared activity</h4>' + _block(encounter['activity']) + '</details>'
    body += '<h3>Recorded actions</h3><ol class="steps">'
    action_count = 0
    for event in encounter['events']:
        if event['kind'] == 'tutor-intervention':
            body += ('<li><details open><summary>Supplied tutor turn</summary>'
                     '<p>Origin: supplied intervention, as recorded by the student session.</p>'
                     + _block(event['text']) + '</details></li>')
        else:
            action_count += 1
            body += _action(event, action_count, prefix)
    body += '</ol>'
    if not action_count:
        body += '<p>No student action has been recorded.</p>'
    final = encounter['final']
    body += '<h3>Final saved state</h3><p>Status: <strong>' + _text(final['status']) + '</strong>. '
    body += f'Model decisions used: {final["decisions_used"]} / {_text(final["max_decisions"])}.</p>'
    if final['status'] == 'no-reply':
        body += '<p>Chosen no-reply is the recorded stop; it does not establish learning or abandonment.</p>'
    elif final['disposition'] == 'budget-exhausted':
        body += '<p>Decision budget exhausted; this is a runner pause, not student silence.</p>'
    elif final['status'] == 'active':
        body += '<p>The saved encounter remains active.</p>'
    elif final['status'] == 'awaiting-tutor':
        body += '<p>The student is awaiting a tutor reply.</p>'
    elif final['status'] == 'error':
        body += '<p>The runner stopped with an error; no additional student action is established.</p>'
    body += _work(final['work']) + '<h4>Current task feedback</h4>' + _feedback(final['feedback'])
    return body + '</section>'


def export(folder, output, *, previous=None):
    """Create one escaped, self-contained page; verify ancestry and dispatch no calls."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    folder, output = Path(folder).resolve(), output.resolve()
    replay, input_folders = _read_replay(folder, previous=previous)
    if any(output.is_relative_to(input_folder) for input_folder in input_folders):
        raise ValueError('Replay output must be outside each input session.')
    body = '<header><p class="eyebrow">Saved notebook simulation</p><h1>Encounter replay</h1>'
    body += '<p>Read-only replay of saved evidence. No model calls or code execution.</p></header>'
    prefixes = [f'task-{i + 1}' for i in range(len(replay['tasks']) - 1)] + ['current']
    if replay['linked']:
        body += ('<p class="notice">Verified linked continuation: each new task was supplied by a researcher. '
                 'The history actually delivered at each initialization is shown separately. '
                 'Continuation does not establish learning.</p><nav aria-label="Replay sections">')
        body += ''.join(f'<a href="#{prefix}">Task {i + 1}</a>' for i, prefix in enumerate(prefixes)) + '</nav>'
    for encounter, prefix in zip(replay['tasks'], prefixes):
        if encounter['shared_history']:
            body += (f'<section id="{prefix}-history"><h2>Shared history supplied to Task {encounter["number"]}</h2>'
                     f'<p>Origin: {len(encounter["shared_history"])} saved observed encounter(s), supplied to both agents. '
                     'Each record’s work and feedback belong to its earlier task. '
                     'Environment diagnostics are redacted from this display.</p>'
                     '<details><summary>Inspect shared observed records</summary>'
                     + _block(encounter['shared_history']) + '</details>')
            if encounter['conversation_example'] is not None:
                body += ('<details><summary>Recorded communication example supplied to this task</summary>'
                         + _block(encounter['communication_scope'])
                         + _block(encounter['conversation_example']) + '</details>')
            body += '</section>'
        body += _encounter(encounter, prefix=prefix)
    body += ('<footer>Only selected-cell work and recorded dialogue/actions are available. Checks apply to their '
             'recorded revision and supplied data; a pass is not a general correctness proof. '
             'No pacing, hidden attempts, learner traits or learning are inferred.</footer>')
    page = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Saved notebook encounter replay</title>
<style>
:root{font-family:system-ui,sans-serif;color:#23312b;background:#f6f5f0;line-height:1.55}
body{max-width:960px;margin:auto;padding:32px 24px}h1{font-size:2.5rem;line-height:1.15;margin:.25em 0}
h2{margin-top:0}h3{margin-top:1.5em}h4{margin-bottom:.4em}p{max-width:80ch}
.eyebrow{font-weight:700;color:#476151}section{background:#fff;border:1px solid #cad3cb;border-radius:10px;padding:24px;margin:24px 0;scroll-margin-top:16px}
.notice{border-left:4px solid #476151;padding:12px 16px;background:#eaf0e8}nav{display:flex;gap:20px;flex-wrap:wrap}
a{color:#245740;text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #bd6116;outline-offset:4px}
details{border:1px solid #d9ded7;border-radius:6px;padding:12px 16px;margin:12px 0}summary{cursor:pointer;font-weight:650}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f1;border:1px solid #d9ded7;padding:14px;border-radius:4px;font-size:.9rem;line-height:1.5}
.steps{padding-left:24px}.steps>li{padding-left:4px}footer{color:#4b5c51;font-size:.9rem;padding-bottom:24px}
@media(max-width:600px){body{padding:20px 12px}section{padding:16px}h1{font-size:2rem}details{padding:10px}}
</style><body>''' + body + '</body></html>\n'
    with output.open('x', encoding='utf-8') as stream:
        stream.write(page)
    return output


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--previous', type=Path, help='Explicit predecessor; recorded ancestry must match.')
    parser.add_argument('--output', type=Path, required=True, help='Create a new HTML file outside the sessions.')
    args = parser.parse_args()
    print(export(args.folder, args.output, previous=args.previous))


if __name__ == '__main__':
    main()
