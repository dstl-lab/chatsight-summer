"""Serve a verified saved notebook session in the browser; never continue the run."""
import argparse
from contextlib import ExitStack
import difflib
from pathlib import Path
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.agents import notebook_next_task, notebook_student as student

ROOT = Path(__file__).resolve().parents[2]


def _frame(manifest, state, previous, decisions, index):
    before = previous['work'] if previous is not None else state['work']
    lines = difflib.unified_diff(before['source'].splitlines(keepends=True),
        state['work']['source'].splitlines(keepends=True), fromfile='previous saved work', tofile='saved work')
    diff = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)
    feedback = student.notebook_session._feedback(state['observation'])
    if feedback is not None and feedback['status'] == 'environment-error':
        feedback['error'] = {'message':'Local execution was unavailable; this work is ungraded.'}
    history = state['history'][len(previous['history']):] if previous is not None else []
    return {'label':f'Saved step {index}' if index else 'Initial state',
        'binding':{'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state)},
        'status':state['status'], 'decisions_remaining':manifest['max_decisions'] - decisions,
        'work':{key:state['work'][key] for key in ('cell_index', 'revision', 'source')},
        'dialogue':[{'role':turn['role'], 'text':turn['text'], 'origin':turn.get('origin')}
                    for turn in state['dialogue']],
        'pending_message':state['message'] if state['status'] == 'awaiting-tutor' else None,
        'feedback':feedback,
        'changes':{'baseline_revision':before['revision'],
                   'baseline_kind':'previous-saved-step' if previous is not None else 'initial-work',
                   'unified_diff':diff},
        'actions':[{key:event['action'][key] for key in ('decision', 'text', 'source')} for event in history]}


def snapshot(folder):
    """Project only display evidence after verifying every saved predecessor and receipt."""
    encounters = []
    with ExitStack() as stack:
        for number, (_, manifest, _, receipts, _) in enumerate(notebook_next_task.lineage(folder, stack), 1):
            initial = manifest['initial']
            frames = [_frame(manifest, initial, None, 0, 0)]
            previous, decisions = initial, 0
            for index, receipt in enumerate(receipts, 1):
                state = receipt['result']['state']
                decisions += sum(call['kind'] == 'model' for call in receipt['calls'])
                frames.append(_frame(manifest, state, previous, decisions, index))
                previous = state
            encounters.append({'id':str(number), 'title':f'Task {number}', 'task':initial['task'],
                'initialization':initial['initialization'],
                'activity':{key:value for key,value in initial['activity'].items() if key != 'image_id'},
                'frames':frames})
    return {'version':1, 'encounters':encounters}


def _page():
    # ponytail: reuse the single preview shell; extract a template if the layouts diverge.
    page = (ROOT / 'docs/prototypes/student-workspace.html').read_text(encoding='utf-8')
    page, count = re.subn(r'<script>.*?</script>', '<script src="/workspace.js"></script>', page, flags=re.S)
    if count != 1:
        raise ValueError('The workspace shell must have exactly one replaceable script.')
    for before, after in (
        ('Student simulation workspace · Design prototype', 'Saved student workspace'),
        ('Authored demo · Backend disconnected', 'Saved session · Read only'),
        ('<div class="breadcrumb">DSC 10</div>', '<div class="breadcrumb">Notebook session</div>'),
        ('Reset all demo changes', 'Reload saved session'), ('Reset demo', 'Reload saved session'),
        ('Filter sample cases', 'Filter saved tasks'),
        ('class="body-grid"', 'class="body-grid no-inspector"'),
        ('<h1 id="case-title"></h1>', '<h1 id="case-title">Loading saved workspace…</h1>'),
        ('<div class="canvas" id="canvas"></div>',
         '<div class="canvas" id="canvas"><p>Loading saved evidence. No simulation will run.</p>'
         '<noscript>Enable JavaScript to inspect this saved session.</noscript></div>'),
        ('id="playback"', 'id="playback" hidden'),
    ):
        page = page.replace(before, after)
    return page


def create_app(folder):
    folder = Path(folder).resolve()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def local_requests(request: Request, call_next):
        origin = request.headers.get('origin')
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin is not None and origin != expected or request.headers.get('sec-fetch-site') == 'cross-site':
            response = JSONResponse({'detail':'Open this workspace directly on localhost.'}, status_code=403)
        else:
            response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        return response

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])

    @app.get('/', response_class=HTMLResponse)
    @app.get('/student-workspace.html', response_class=HTMLResponse)
    def page():
        return _page()

    @app.get('/workspace.js')
    def script():
        return Response((ROOT / 'apps/browser_workspace.js').read_text(encoding='utf-8'),
                        media_type='text/javascript')

    @app.get('/api/workspace')
    def workspace(request: Request):
        if request.query_params:
            raise HTTPException(400, 'This workspace uses only the session selected at launch.')
        try:
            return snapshot(folder)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(409, 'Saved evidence could not be verified. Check the configured session '
                                'and its original environment; no simulation was run.') from exc

    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='Saved notebook session to inspect read-only.')
    parser.add_argument('--port', type=int, default=8427)
    args = parser.parse_args()
    uvicorn.run(create_app(args.folder), host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
