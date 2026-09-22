"""Inspect a saved notebook or chat session; continue only through explicit submissions."""
import argparse
from contextlib import ExitStack
import difflib
import fcntl
from hashlib import sha256
from pathlib import Path
import re
from threading import Lock
from typing import Literal

from markdown import Markdown
from markdown.extensions.fenced_code import FencedBlockPreprocessor
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.agents import chat_student, chat_workspace, notebook_next_task, notebook_student as student, notebook_tutor, student_workspace
from src.eval.saved_comparison import load_comparison

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = "Respond concisely to the student's current request using the visible work and check feedback."


class _PlainFences(FencedBlockPreprocessor):
    def handle_attrs(self, attrs):
        # Saved text must not assign app IDs, classes or other HTML attributes.
        return '', [], {}


def _tutor_html(text):
    """Display-only Markdown: raw HTML, links, images and fence attributes stay inert."""
    md = Markdown(extensions=['fenced_code', 'sane_lists'])
    md.preprocessors.deregister('html_block')
    md.parser.blockprocessors.deregister('reference')
    for name in ('html', 'reference', 'link', 'image_link', 'image_reference',
                 'short_reference', 'short_image_ref', 'autolink', 'automail'):
        md.inlinePatterns.deregister(name)
    md.preprocessors.register(_PlainFences(md, md.preprocessors['fenced_code_block'].config),
                              'fenced_code_block', 25)
    return md.convert(text)


class Binding(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    session_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')
    state_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    binding: Binding
    mode: Literal['advance', 'reply', 'policy']
    text: str | None = Field(default=None, max_length=64000)

    @model_validator(mode='after')
    def mode_text(self):
        if self.mode == 'advance' and 'text' in self.model_fields_set:
            raise ValueError('Quiet continuation does not accept tutor text.')
        if self.mode != 'advance' and (self.text is None or not self.text.strip()):
            raise ValueError('Supply nonblank tutor instructions or a reply.')
        return self


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


def _chat_snapshot(folder):
    with (Path(folder) / '.lock').open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        manifest, _, _ = chat_student._load(Path(folder))
        receipts = [student._read(path) for path in sorted(Path(folder).glob('step-*.json'))]
        states = [chat_student._initial(manifest['query']), *(receipt['result'] for receipt in receipts)]
        frames = []
        for index, state in enumerate(states):
            episode = state['episode']
            receipt = receipts[index - 1] if index else None
            frames.append({'label':f'Saved step {index}' if index else 'Initial state',
                'binding':{'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state)},
                'status':state['status'], 'decisions_remaining':manifest['max_decisions'] - index,
                'dialogue':[{key:turn[key] for key in ('role', 'text', 'origin')}
                            for turn in [*episode['context'], *episode['turns']]],
                'pending_message':state['message'] if state['status'] == 'awaiting-tutor' else None,
                'work':None, 'feedback':None, 'changes':None,
                'actions':[{key:receipt['response'][key] for key in ('decision', 'text')} | {'source':None}]
                    if receipt is not None and receipt['status'] == 'complete' else []})
    return {'version':1, 'kind':'chat', 'encounters':[{
        'id':'1', 'title':'Conversation', 'task':'Conversation scenario',
        'initialization':'Supplied conversation prefix followed by saved simulated continuation. '
            'The prefix may be recorded or authored; its saved origin alone does not establish this. '
            'Notebook activity and outcomes are unknown. Code in a message is text only.',
        'activity':None, 'frames':frames}]}


def snapshot(folder, *, chat_mode=False):
    """Project only display evidence after verifying every saved predecessor and receipt."""
    if chat_mode:
        return _chat_snapshot(folder)
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
    return {'version':1, 'kind':'notebook', 'encounters':encounters}


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


def create_app(folder, *, chat_sessions=False, chat_mode=False, comparison=None, send=False, policy=None, reference=None, generate=None, generate_tutor=None, check=None):
    folder = Path(folder).resolve()
    if comparison is not None and Path(comparison).is_symlink():
        raise ValueError('The comparison folder must not be a symlink.')
    comparison = Path(comparison).resolve() if comparison is not None else None
    comparison_pin = sha256((comparison / 'closure.json').read_bytes()).hexdigest() if comparison else None
    if chat_sessions and chat_mode:
        raise ValueError('Choose one chat session or a chat collection, not both.')
    scenarios = {}
    if chat_sessions:
        scenarios = {student.digest(path.name):path for path in sorted(folder.iterdir())
            if path.is_dir() and not path.is_symlink()
            and (path / 'session.json').is_file() and not (path / 'session.json').is_symlink()}
        if not scenarios:
            raise ValueError('No saved conversation scenarios were found.')
        chat_mode = True
    titles = {key:f'Scenario {index:02d}' for index, key in enumerate(scenarios, 1)}
    if policy is not None and (not isinstance(policy, str) or not policy.strip()):
        raise ValueError('The tutor policy must contain nonblank text.')
    if chat_mode and reference is not None:
        raise ValueError('A library reference is only available for notebook sessions.')
    policy = ("Respond concisely to the student's current request using the visible conversation."
              if chat_mode else DEFAULT_POLICY) if policy is None else policy
    reference = notebook_tutor.LibraryReference.model_validate(reference).model_dump() if reference is not None else None
    runner = chat_workspace if chat_mode else student_workspace
    # ponytail: one serving process; use a shared job store if multiple writers are needed.
    running = Lock()
    operations = {key:{'status':'idle', 'message':''} for key in [None, *scenarios]}
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def selection(request):
        params = list(request.query_params.multi_items())
        if not chat_sessions:
            if params:
                raise HTTPException(400, 'This workspace uses only the session selected at launch.')
            return None, folder
        if len(params) != 1 or params[0][0] != 'scenario' or params[0][1] not in scenarios:
            raise HTTPException(400, 'Choose one scenario from the workspace catalog.')
        scenario_id = params[0][1]
        selected = scenarios[scenario_id]
        try:
            if (selected.is_symlink() or not selected.is_dir() or selected.resolve().parent != folder
                    or any(path.is_symlink() for path in
                           [selected / 'session.json', selected / '.lock', selected / 'tutor-exchanges',
                            *selected.glob('step-*.json')])):
                raise ValueError('The saved scenario path changed.')
        except (OSError, ValueError) as exc:
            raise HTTPException(409, 'The selected scenario could not be verified; continuation is disabled.') from exc
        return scenario_id, selected

    def blocked(selected, frame):
        if (selected / 'tutor-exchanges' / frame['binding']['state_sha256']).exists():
            return ('A tutor exchange already exists for this saved state. It will not be resent; '
                    'inspect its saved receipt before continuing.')
        return None

    def packet(scenario_id, selected):
        result = snapshot(selected, chat_mode=chat_mode)
        for encounter in result['encounters']:
            for saved_frame in encounter['frames']:
                for turn in saved_frame['dialogue']:
                    if turn['role'] == 'tutor':
                        turn['display_html'] = _tutor_html(turn['text'])
        if scenario_id is not None:
            result['encounters'][0]['title'] = titles[scenario_id]
        frame = result['encounters'][-1]['frames'][-1]
        return result | {'scenario_id':scenario_id, 'controls':{'send_enabled':send is True, 'policy':policy,
            'reference':{key:reference[key] for key in ('library', 'library_version', 'source')}
                        if reference is not None else None,
            'blocked_reason':blocked(selected, frame)}, 'operation':dict(operations[scenario_id])}

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

    @app.get('/api/scenarios')
    def catalog(request: Request):
        if request.query_params:
            raise HTTPException(400, 'The scenario catalog does not accept query parameters.')
        return {'version':1, 'scenarios':[{'id':key, 'title':titles[key]} for key in scenarios],
                **({'comparison_available':True} if comparison is not None else {})}

    @app.get('/api/comparison')
    def comparison_view(request: Request):
        if request.query_params:
            raise HTTPException(400, 'The comparison uses only the review selected at launch.')
        if comparison is None:
            raise HTTPException(404, 'No saved comparison is configured.')
        try:
            return load_comparison(comparison, expected_closure=comparison_pin)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(409, 'The saved comparison could not be verified. Its evidence is not displayed.') from exc

    @app.get('/api/workspace')
    def workspace(request: Request):
        scenario_id, selected = selection(request)
        if not running.acquire(blocking=False):
            return JSONResponse({'version':1, 'scenario_id':scenario_id, 'operation':{'status':'running',
                'message':'The workspace is handling a request. Reloading checks progress without resending.'}}, status_code=202)
        try:
            return packet(scenario_id, selected)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(409, 'Saved evidence could not be verified. Check the configured session '
                                'and its original environment; continuation is disabled.') from exc
        finally:
            running.release()

    @app.post('/api/continue')
    def continue_session(body: Submission, request: Request):
        scenario_id, selected = selection(request)
        if send is not True:
            raise HTTPException(403, 'This workspace was opened without sending enabled.')
        if not running.acquire(blocking=False):
            raise HTTPException(409, 'The workspace is busy. Reload to inspect its current state; do not resend.')
        operation = operations[scenario_id]
        try:
            current = snapshot(selected, chat_mode=chat_mode)['encounters'][-1]['frames'][-1]
            binding = body.binding.model_dump()
            if binding != current['binding']:
                raise HTTPException(409, 'The displayed state is stale. Reload before continuing.')
            if reason := blocked(selected, current):
                raise HTTPException(409, reason)
            ready = 'ready' if chat_mode else 'active'
            if current['status'] not in (ready, 'awaiting-tutor') or current['decisions_remaining'] <= 0:
                raise HTTPException(409, 'This encounter has stopped or used its decision budget.')
            if (body.mode == 'advance') != (current['status'] == ready):
                raise HTTPException(409, 'Tutor guidance requires a pending student message; continuation does not accept it.')
            if body.mode == 'policy':
                runner.respond(selected, binding=binding, policy=body.text, send=True,
                    generate_tutor=generate_tutor, generate_student=generate,
                    **({} if chat_mode else {'check':check, 'reference':reference}))
            else:
                runner.advance(selected, binding=binding,
                    tutor_reply=body.text if body.mode == 'reply' else None,
                    send=True, generate=generate, **({} if chat_mode else {'check':check}))
            result = packet(scenario_id, selected)
            failed = result['encounters'][-1]['frames'][-1]['status'] in ('error', 'environment-error', 'execution-limit')
            operation.update(status='error' if failed else 'complete', message=(
                ('The simulation stopped after a generation error. Inspect the saved result.' if chat_mode else
                 'The simulation stopped after an error or unavailable local check. Inspect the saved result.')
                if failed else 'One student decision was saved.'))
            result['operation'] = dict(operation)
            return result
        except HTTPException:
            raise
        except Exception as exc:
            operation.update(status='error', message=(
                'The request could not complete. Reload to inspect saved evidence; it will not be automatically resent.'))
            raise HTTPException(409, operation['message']) from exc
        finally:
            running.release()

    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='Saved session or direct-child conversation collection to inspect.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--chat', action='store_true', help='Open a chat-only session; notebook state remains unknown.')
    mode.add_argument('--chat-sessions', action='store_true', help='Choose among saved chat sessions directly inside the folder.')
    parser.add_argument('--port', type=int, default=8427)
    parser.add_argument('--comparison', type=Path, help='Completed cached communication review folder for read-only Compare.')
    parser.add_argument('--send', action='store_true', help='Enable explicit tutor/student generation and requested local checks.')
    parser.add_argument('--policy-file', type=Path, help='UTF-8 starting tutor instructions, loaded once.')
    parser.add_argument('--reference-file', type=Path, help='Tutor-only library reference JSON, loaded once.')
    args = parser.parse_args()
    try:
        if (args.chat or args.chat_sessions) and args.reference_file:
            raise ValueError('A library reference is only available for notebook sessions.')
        policy = args.policy_file.read_text(encoding='utf-8') if args.policy_file else None
        reference = notebook_tutor.LibraryReference.model_validate_json(
            args.reference_file.read_text(encoding='utf-8')).model_dump() if args.reference_file else None
        app = create_app(args.folder, chat_sessions=args.chat_sessions, chat_mode=args.chat, comparison=args.comparison,
                         send=args.send, policy=policy, reference=reference)
    except (OSError, ValueError) as exc:
        parser.error(f'Workspace configuration could not be loaded: {exc}')
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
