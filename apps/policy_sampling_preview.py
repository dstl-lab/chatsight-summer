"""Inspect one frozen tutor-policy sampling study in the notebook/chat workspace."""
import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from src.agents import browser_workspace as workspace, notebook_student as store
from src.eval import notebook_action as action, notebook_replay


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('notebook_policy_sampling',
    ROOT/'experiments/2026-09-29-notebook-policy-sampling/run.py')


def project(report):
    """Every sampled action branches directly from its own supplied tutor reply."""
    shared = report['shared_task']
    pin = report['plan_sha256']

    def frame(task, label):
        return {'label':label, 'status':'active', 'decisions_remaining':1,
            'work':deepcopy(task['work']), 'pending_message':None, 'feedback':None, 'actions':[],
            'dialogue':[{**turn, 'origin':'generated' if turn['role'] == 'tutor' else 'source',
                **({'display_html':workspace._tutor_html(turn['text'])} if turn['role'] == 'tutor' else {})}
                for turn in task['dialogue']],
            'binding':{'session_sha256':pin, 'state_sha256':store.digest(task)},
            'changes':{'baseline_revision':0, 'baseline_kind':'initial-work', 'unified_diff':''}}

    encounters, conditions = [], []
    for name, condition in report['conditions'].items():
        task = condition['task']
        # A failed tutor request has no replacement reply and no sampled continuation.
        baseline = frame(task or shared, condition['label']+' · Tutor reply')
        samples = []
        for record in condition['records']:
            if record['status'] != 'complete':
                continue
            choice = action.Action.model_validate(record['response'])
            applied = action.apply_action(task, choice)
            sample = deepcopy(baseline)
            sample.update(label=f'{condition["label"]} · Sample {record["index"]}',
                status='no-reply' if choice.decision == 'no-reply' else 'awaiting-tutor' if applied['message'] else 'active',
                decisions_remaining=0, work=applied['work'], actions=[choice.model_dump()],
                binding={'session_sha256':pin, 'state_sha256':store.digest(applied)},
                changes={'baseline_revision':0, 'baseline_kind':'previous-saved-step',
                         'unified_diff':notebook_replay._code_diff(shared['work'], applied['work'])})
            if applied['message']:
                sample['dialogue'].append({'role':'student', 'origin':'generated', 'text':applied['message']})
            samples.append({'index':record['index'], 'decision':choice.decision, 'frame':sample})
        encounters.append({'id':name, 'title':condition['label'], 'task':shared['task'],
            'task_html':workspace._tutor_html('\n\n'.join(cell['source'] for cell in shared['task'])),
            'initialization':shared['initialization'], 'activity':None,
            'frames':[frame(shared, 'Captured work · Before tutor reply'), baseline],
            'saved_results_html':workspace._tutor_html(
                f'{condition["valid"]} valid of {condition["requested"]} planned student samples; '
                f'{condition["failed"]} failed.\n\n'+str(report['scope']))})
        conditions.append({**{key:condition[key] for key in (
            'label', 'policy', 'valid', 'failed', 'requested', 'status', 'categories')},
            'id':name, 'samples':samples})
    packet = {'version':1, 'kind':'notebook', 'source_only':True, 'encounters':encounters,
        'controls':{'send_enabled':False, 'tutor_generation_enabled':False,
                    'blocked_reason':'Saved policy study. Viewing does not generate or execute.'},
        'operation':{'status':'idle', 'message':''}}
    return packet, {'model':report['model'], 'requested_per_condition':30,
                    'conditions':conditions, 'scope':report['scope']}


def create_app(*, notebook_branch, comparison, authored_demo):
    if type(authored_demo) is not bool:
        raise ValueError('Explicitly identify authored test data or live results.')
    experiment = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(experiment)
    folder = Path(comparison).absolute()
    initial = experiment.load(folder)
    if Path(experiment._plan(folder)['source_branch']).resolve() != Path(notebook_branch).resolve():
        raise ValueError('Use the notebook branch frozen in this comparison.')
    pin = store.digest(initial)
    app = workspace.create_app(notebook_branch=notebook_branch)

    def snapshot(request):
        if request.query_params:
            raise HTTPException(400, 'This is one fixed saved comparison.')
        try:
            report = experiment.load(folder)
            if store.digest(report) != pin:
                raise ValueError('The saved comparison changed.')
            return project(report)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            raise HTTPException(409, 'The saved comparison could not be verified. Its contents are not displayed.') from exc

    app.router.routes[:] = [route for route in app.routes if route.path not in ('/', '/api/workspace')]

    @app.get('/api/workspace')
    def saved_workspace(request: Request):
        return snapshot(request)[0]

    @app.get('/api/policy-sampling')
    def saved_sampling(request: Request):
        return {**snapshot(request)[1], 'authored_demo':authored_demo}

    @app.get('/', response_class=HTMLResponse)
    def page():
        return workspace._page().replace('</head>',
            '<link rel="stylesheet" href="/next-actions.css"><link rel="stylesheet" href="/policy-sampling.css"></head>').replace(
            '</body>', '<script src="/policy-sampling.js"></script></body>')

    @app.get('/next-actions.css')
    def base_style():
        return Response((ROOT/'apps/next-actions.css').read_text(), media_type='text/css')

    @app.get('/policy-sampling.css')
    def style():
        return Response((ROOT/'apps/policy-sampling.css').read_text(), media_type='text/css')

    @app.get('/policy-sampling.js')
    def script():
        return Response((ROOT/'apps/policy-sampling.js').read_text(), media_type='text/javascript')

    @app.middleware('http')
    async def local_style(request: Request, call_next):
        response = await call_next(request)
        policy = response.headers.get('Content-Security-Policy', '')
        response.headers['Content-Security-Policy'] = policy.replace(
            "style-src 'unsafe-inline'", "style-src 'self' 'unsafe-inline'")
        return response

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', type=Path, required=True)
    parser.add_argument('--comparison', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8450)
    provenance = parser.add_mutually_exclusive_group(required=True)
    provenance.add_argument('--authored-demo', action='store_true', dest='authored_demo',
                            help='Clearly identify authored UI test data.')
    provenance.add_argument('--live-results', action='store_false', dest='authored_demo',
                            help='Explicitly identify a completed live provider study.')
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(notebook_branch=args.branch, comparison=args.comparison, authored_demo=args.authored_demo),
                host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
