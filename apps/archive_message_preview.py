"""Inspect the saved archive-loop edit/message that stopped for a tutor reply."""
import argparse
from copy import deepcopy
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from src.agents import archived_notebook as archive, browser_workspace as workspace
from src.agents import notebook_student as store, student_evidence
from src.eval import notebook_replay


ROOT = Path(__file__).resolve().parents[1]


def project(result):
    """This view deliberately supports only a completed, one-message stop without execution."""
    plan, state = result['plan'], result['state']
    if (result['status'] != 'awaiting-tutor' or state is None or len(state['history']) != 1
            or state['observation'] is not None):
        raise ValueError('This view requires one saved student action stopping for a tutor, without execution.')
    event = state['history'][0]
    choice = event.get('action', {})
    if (choice.get('decision') not in ('revise-work', 'reply') or not state['message']
            or event.get('observation') is not None or event.get('error')):
        raise ValueError('A completed edit/message with no execution or failure is required.')
    task = plan['initial']
    dialogue = [{**turn, 'origin':'generated' if turn['role'] == 'tutor' else 'source',
                 **({'display_html':workspace._tutor_html(turn['text'])} if turn['role'] == 'tutor' else {})}
                for turn in task['dialogue']]
    base = {'label':'Captured start', 'archive_stage':'captured', 'status':'active',
        'decisions_remaining':plan['max_decisions'], 'work':deepcopy(task['work']),
        'dialogue':dialogue[:-1], 'pending_message':None, 'feedback':None, 'actions':[],
        'changes':{'baseline_revision':0, 'baseline_kind':'initial-work', 'unified_diff':''},
        'binding':{'session_sha256':store.digest(plan), 'state_sha256':store.digest(task)}}
    tutor = deepcopy(base) | {'label':'Saved tutor reply', 'archive_stage':'tutor', 'dialogue':dialogue}
    final = deepcopy(tutor) | {'label':'Student edit + message' if choice['decision'] == 'revise-work' else 'Student message',
        'archive_stage':'message', 'status':'awaiting-tutor', 'decisions_remaining':plan['max_decisions']-1,
        'work':deepcopy(state['work']), 'pending_message':state['message'], 'actions':[deepcopy(choice)],
        'changes':{'baseline_revision':task['work']['revision'], 'baseline_kind':'previous-saved-step',
                   'unified_diff':notebook_replay._code_diff(task['work'], state['work'])},
        'binding':{'session_sha256':store.digest(plan), 'state_sha256':store.digest(state)}}
    encounter = {'id':'archive-message', 'title':'Student-controlled continuation',
        'archive_message':True, 'authored_demo':plan['authored_demo'], 'model_decisions':1, 'execution_calls':0,
        'task':deepcopy(task['task']), 'task_html':workspace._tutor_html('\n\n'.join(cell['source'] for cell in task['task'])),
        'initialization':task['initialization'], 'activity':None,
        'evidence_card':student_evidence.supplied_card(task['dialogue']), 'frames':[base, tutor, final],
        'saved_results_html':workspace._tutor_html(
            ('Authored test data. ' if plan['authored_demo'] else 'One saved Gemini student decision. ')+
            'The student sent a message and the run stopped awaiting a tutor. No local execution '
            'was requested; no output or grade is established. The tutor reply was already saved '
            'before this run. The new revision remains unexecuted in this run, even if identical '
            'code was checked in another study. This is a simulated continuation from captured '
            'work, not recorded future student behavior or evidence of learning. '
            'Viewing or reloading makes no model or execution requests.')}
    return {'version':1, 'kind':'notebook', 'source_only':True, 'encounters':[encounter],
        'controls':{'send_enabled':False, 'tutor_generation_enabled':False,
                    'blocked_reason':'Saved run ended awaiting a tutor. No reply is running; this view is read only.'},
        'operation':{'status':'idle', 'message':''}}


def create_app(folder, *, notebook_branch):
    folder = Path(folder).absolute()
    initial = archive.load(folder)
    project(initial)
    pin = store.digest(initial)
    app = workspace.create_app(notebook_branch=notebook_branch)
    # Keep the existing localhost security middleware and shared assets, not another data source.
    app.router.routes[:] = [route for route in app.routes if route.path in ('/workspace.js', '/api/scenarios')]

    @app.get('/api/workspace')
    def saved(request: Request):
        if request.query_params:
            raise HTTPException(400, 'This is one fixed saved run.')
        try:
            result = archive.load(folder)
            if store.digest(result) != pin:
                raise ValueError('Saved run changed.')
            return project(result)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            raise HTTPException(409, 'This saved run could not be verified. Its contents are not displayed.') from exc

    @app.get('/', response_class=HTMLResponse)
    def page():
        return workspace._page().replace('</head>', '<link rel="stylesheet" href="/student-loop.css"></head>').replace(
            '</body>', '<script src="/archive-message.js"></script></body>')

    @app.get('/student-loop.css')
    def style():
        return Response((ROOT/'apps/student-loop.css').read_text(), media_type='text/css')

    @app.get('/archive-message.js')
    def script():
        return Response((ROOT/'apps/archive-message.js').read_text(), media_type='text/javascript')

    @app.middleware('http')
    async def local_style(request: Request, call_next):
        response = await call_next(request)
        policy = response.headers.get('Content-Security-Policy', '')
        response.headers['Content-Security-Policy'] = policy.replace(
            "style-src 'unsafe-inline'", "style-src 'self' 'unsafe-inline'")
        return response

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--branch', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8453)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(args.folder, notebook_branch=args.branch), host='127.0.0.1', port=args.port)
