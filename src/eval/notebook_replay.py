"""Export saved notebook encounters and their verified shared history to static HTML."""
from contextlib import ExitStack
from html import escape
import json
from pathlib import Path

from src.agents import notebook_next_task, notebook_student as student


def _text(value):
    return escape(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))


def _block(value):
    return '<pre>' + _text(value) + '</pre>'


def _feedback(observation):
    feedback = student.notebook_session._feedback(observation)
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
    elif decision == 'request-check' and event['observation'] is not None:
        feedback = event['observation']
        summary += ' · ' + ('pass' if feedback['success'] else 'fail') \
            if feedback['status'] == 'checked' else ' · ' + feedback['status']
    body = f'<p>Origin: {_text(event["origin"])}</p>'
    if action['text']:
        body += '<h4>Student message</h4>' + _block(action['text'])
    body += _work(event['work_after'])
    if decision == 'request-check':
        body += '<h4>Recorded check result</h4>' + _feedback(event['observation'])
    elif decision == 'revise-work':
        body += '<p>This edit cleared the current check feedback. No check was requested by this action.</p>'
    elif decision == 'no-reply':
        body += '<p>The student chose to stop this encounter without a reply.</p>'
    return (f'<li id="{prefix}-action-{number}"><details><summary>{_text(summary)}</summary>'
            + body + '</details></li>')


def _encounter(manifest, state, receipts, decisions, *, prefix, title):
    initial = manifest['initial']
    initialization = initial['initialization']
    if manifest.get('provenance', {}).get('previous_encounter') is not None:
        initialization = initialization.get('current_task', 'Earlier shared context is shown separately.')
    body = (f'<section id="{prefix}"><h2>{title}</h2><h3>{_text(initial["task"])}</h3>'
            '<details><summary>Supplied initial task context and dialogue</summary>'
            '<p>Origin: supplied initial context</p>' + _block(initialization))
    for turn in initial['dialogue']:
        body += (f'<h4>{_text(turn["role"])} · Origin: {_text(turn.get("origin", "supplied"))}</h4>'
                 + _block(turn['text']))
    body += '<h4>Initial selected cell</h4>' + _work(initial['work'])
    body += '<h4>Declared activity</h4>' + _block({
        key:value for key,value in initial['activity'].items() if key != 'image_id'}) + '</details>'
    body += '<h3>Recorded actions</h3><ol class="steps">'
    history_count = 0
    for recorded in [initial, *receipts]:
        if 'request' in recorded:
            reply = recorded['request']['tutor_reply']
            if reply is not None:
                body += ('<li><details open><summary>Supplied tutor turn</summary>'
                         '<p>Origin: supplied intervention, as recorded by the student session.</p>'
                         + _block(reply) + '</details></li>')
            recorded = recorded['result']['state']
        for event in recorded['history'][history_count:]:
            history_count += 1
            body += _action(event, history_count, prefix)
    body += '</ol>'
    if not history_count:
        body += '<p>No student action has been recorded.</p>'
    body += '<h3>Final saved state</h3><p>Status: <strong>' + _text(state['status']) + '</strong>. '
    body += f'Model decisions used: {decisions} / {_text(manifest["max_decisions"])}.</p>'
    if state['status'] == 'no-reply':
        body += '<p>Chosen no-reply is the recorded stop; it does not establish learning or abandonment.</p>'
    elif state['status'] == 'active':
        body += ('<p>Decision budget exhausted; this is a runner pause, not student silence.</p>'
                 if decisions >= manifest['max_decisions'] else '<p>The saved encounter remains active.</p>')
    elif state['status'] == 'awaiting-tutor':
        body += '<p>The student is awaiting a tutor reply.</p>'
    elif state['status'] == 'error':
        body += '<p>The runner stopped with an error; no additional student action is established.</p>'
    body += _work(state['work']) + '<h4>Current task feedback</h4>' + _feedback(state['observation'])
    return body + '</section>'


def export(folder, output, *, previous=None):
    """Create one escaped, self-contained page; verify ancestry and dispatch no calls."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    folder, output = Path(folder).resolve(), output.resolve()
    with ExitStack() as stack:
        entries = notebook_next_task.lineage(folder, stack, previous=previous)
        if any(output.is_relative_to(entry[0]) for entry in entries):
            raise ValueError('Replay output must be outside each input session.')
        body = '<header><p class="eyebrow">Saved notebook simulation</p><h1>Encounter replay</h1>'
        body += '<p>Read-only replay of saved evidence. No model calls or code execution.</p></header>'
        prefixes = [f'task-{i + 1}' for i in range(len(entries) - 1)] + ['current']
        if len(entries) > 1:
            body += ('<p class="notice">Verified linked continuation: each new task was supplied by a researcher. '
                     'The history actually delivered at each initialization is shown separately. '
                     'Continuation does not establish learning.</p><nav aria-label="Replay sections">')
            body += ''.join(f'<a href="#{prefix}">Task {i + 1}</a>' for i, prefix in enumerate(prefixes)) + '</nav>'
        for i, ((_, manifest, state, receipts, decisions), prefix) in enumerate(zip(entries, prefixes), 1):
            if i > 1:
                initialization = manifest['initial']['initialization']
                records = initialization.get('earlier_encounters', []) + [initialization['previous_encounter']]
                body += (f'<section id="{prefix}-history"><h2>Shared history supplied to Task {i}</h2>'
                         f'<p>Origin: {len(records)} saved observed encounter(s), supplied to both agents. '
                         'Each record’s work and feedback belong to its earlier task.</p>'
                         '<details><summary>Inspect the exact shared observed records</summary>'
                         + _block(records) + '</details></section>')
            body += _encounter(manifest, state, receipts, decisions, prefix=prefix,
                               title=f'Task {i}' if len(entries) > 1 else 'Saved encounter')
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
