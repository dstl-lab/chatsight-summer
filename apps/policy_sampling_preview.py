"""Inspect one frozen tutor-policy sampling study in the notebook/chat workspace."""
import argparse
from copy import deepcopy
from hashlib import sha256
import importlib.util
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from src.agents import browser_workspace as workspace, notebook_student as store, student_evidence
from src.eval import notebook_action as action, notebook_replay


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('notebook_policy_sampling',
    ROOT/'experiments/2026-09-29-notebook-policy-sampling/run.py')
CONTINUATION_SPEC = importlib.util.spec_from_file_location('policy_execution',
    ROOT/'experiments/2026-09-29-policy-execution/run.py')


def project(report, continuation=None):
    """Every sampled action branches directly from its own supplied tutor reply."""
    shared = report['shared_task']
    evidence = student_evidence.supplied_card(shared['dialogue'])
    pin = report['plan_sha256']
    if continuation is not None and continuation['comparison_sha256'] != store.digest(report):
        raise ValueError('The continuation belongs to a different saved comparison.')

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
        reaction = continuation['reactions'].get(name) if continuation else None
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
            saved_sample = {'index':record['index'], 'decision':choice.decision, 'frame':sample}
            if continuation and choice.decision == 'revise-work':
                check = continuation['checks'].get(sha256(applied['work']['source'].encode()).hexdigest())
                if check:
                    sample['external_execution'] = {**check, 'dataset':continuation['dataset'],
                                                    'image_id':continuation['image_id']}
            if reaction and reaction['sample_index'] == record['index'] and reaction['status'] == 'complete':
                observed = sample['external_execution']
                next_action, next_applied = reaction['response'], reaction['applied']
                after = deepcopy(sample)
                del after['external_execution']
                after.update(label='After execution', status='no-reply' if next_action['decision'] == 'no-reply'
                    else 'awaiting-tutor' if next_applied['message'] else 'active',
                    work=next_applied['work'], actions=[next_action],
                    binding={'session_sha256':pin, 'state_sha256':store.digest(next_applied)},
                    changes={'baseline_revision':sample['work']['revision'], 'baseline_kind':'previous-saved-step',
                             'unified_diff':notebook_replay._code_diff(sample['work'], next_applied['work'])},
                    reaction={key:reaction[key] for key in ('model', 'status', 'started_at', 'finished_at')} | {
                        'action':next_action, 'observed_revision':observed['revision'], 'observation':observed})
                if next_applied['message']:
                    after['dialogue'].append({'role':'student', 'origin':'generated', 'text':next_applied['message']})
                saved_sample['reaction_frame'] = after
            samples.append(saved_sample)
        encounters.append({'id':name, 'title':condition['label'], 'task':shared['task'],
            'evidence_card':evidence,
            'task_html':workspace._tutor_html('\n\n'.join(cell['source'] for cell in shared['task'])),
            'initialization':shared['initialization'], 'activity':None,
            'frames':[frame(shared, 'Captured work · Before tutor reply'), baseline],
            'saved_results_html':workspace._tutor_html(
                f'{condition["valid"]} valid of {condition["requested"]} planned student samples; '
                f'{condition["failed"]} failed.\n\nOriginal sampling study: '+str(report['scope'])+(
                    f'\n\nSeparate continuation: {len(continuation["checks"])} local source checks saved. '
                    'Results attach to matching edits. Reactions belong only '
                    'to their selected sample and do not change these counts. Any reaction edit is unexecuted; '
                    'no course grade or learning outcome is established.' if continuation else ''))})
        conditions.append({**{key:condition[key] for key in (
            'label', 'policy', 'valid', 'failed', 'requested', 'status', 'categories')},
            'id':name, 'samples':samples,
            **({'reaction':{key:reaction[key] for key in ('sample_index', 'status')}} if reaction else {})})
    packet = {'version':1, 'kind':'notebook', 'source_only':True, 'encounters':encounters,
        'controls':{'send_enabled':False, 'tutor_generation_enabled':False,
                    'blocked_reason':'Saved policy study. Viewing does not generate or execute.'},
        'operation':{'status':'idle', 'message':''}}
    return packet, {'model':report['model'], 'requested_per_condition':30,
                    'conditions':conditions, 'scope':report['scope'], 'continuation':continuation is not None,
                    'execution_count':len(continuation['checks']) if continuation else 0}


def student_loop(packet, sampling, condition_id):
    """Expose one verified saved sequence without treating local execution as a student action."""
    if condition_id == 'both':
        return {**packet, 'encounters': [student_loop(packet, sampling, name)['encounters'][0]
                                        for name in ('direct', 'hint')]}
    condition = next((c for c in sampling['conditions'] if c['id'] == condition_id), None)
    if condition is None or not sampling['continuation'] or not condition.get('reaction'):
        raise ValueError('A student loop requires a condition with a saved execution and reaction.')
    selected = condition['reaction']['sample_index']
    sample = next((s for s in condition['samples'] if s['index'] == selected), None)
    if (sample is None or sample['decision'] != 'revise-work' or
            not sample['frame'].get('external_execution') or not sample.get('reaction_frame')):
        raise ValueError('The predetermined sample has no complete execution and reaction.')
    encounter = deepcopy(next(c for c in packet['encounters'] if c['id'] == condition_id))
    captured, tutor = encounter['frames']
    edit = deepcopy(sample['frame'])
    execution = deepcopy(sample['frame'])
    reaction = deepcopy(sample['reaction_frame'])
    del edit['external_execution']
    execution['actions'] = []  # The researcher ran this revision; the model did not choose Run.
    execution['changes'] = {'baseline_revision': edit['work']['revision'],
                            'baseline_kind': 'previous-saved-step', 'unified_diff': ''}
    encounter['frames'] = [captured, tutor, edit, execution, reaction]
    for frame, stage, label in zip(encounter['frames'],
            ('captured', 'tutor', 'edit', 'execution', 'reaction'),
            ('Captured start', 'Tutor reply', 'Student edit', 'Local execution', 'Next action')):
        frame.update(loop_stage=stage, label=label, decisions_remaining=0)
    encounter.update(loop_example=True, loop_policy_label=condition['label'], loop_sample=selected,
        title='Student loop · '+condition['label'],
        saved_results_html=workspace._tutor_html(
            f'Saved {condition["label"]} sample {selected}. One tutor reply, one student edit, '
            'a researcher-triggered local execution, and one student decision after its result. '
            'The execution is not a student-selected Run action. This replays existing receipts; '
            'viewing makes no new model or execution requests. The source came from a historical '
            'capture; the continuation is simulated. Local results are not course grades or '
            'evidence of learning. Historical dataset bytes and kernel are not established. '
            'No evidence-card guidance was used in this earlier saved sequence. These paths do not '
            'establish a general policy advantage or real-student fidelity.'
            f'\n\nTutor instructions:\n\n{condition["policy"]}'))
    return {**packet, 'encounters': [encounter]}


def create_app(*, notebook_branch, comparison, authored_demo, continuation=None, loop_condition=None):
    if type(authored_demo) is not bool:
        raise ValueError('Explicitly identify authored test data or live results.')
    if loop_condition is not None and continuation is None:
        raise ValueError('The student loop requires --continuation.')
    experiment = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(experiment)
    folder = Path(comparison).absolute()
    initial = experiment.load(folder)
    if Path(experiment._plan(folder)['source_branch']).resolve() != Path(notebook_branch).resolve():
        raise ValueError('Use the notebook branch frozen in this comparison.')
    pin = store.digest(initial)
    if continuation is not None:
        continuation = Path(continuation).absolute()
        followup = importlib.util.module_from_spec(CONTINUATION_SPEC)
        CONTINUATION_SPEC.loader.exec_module(followup)
        attached = followup.load(continuation)
        project(initial, attached)
        continuation_pin = store.digest(attached)
    if loop_condition is not None:
        student_loop(*project(initial, attached), loop_condition)
    app = workspace.create_app(notebook_branch=notebook_branch)

    def snapshot(request):
        if request.query_params:
            raise HTTPException(400, 'This is one fixed saved comparison.')
        try:
            report = experiment.load(folder)
            if store.digest(report) != pin:
                raise ValueError('The saved comparison changed.')
            attached = followup.load(continuation) if continuation is not None else None
            if attached is not None and store.digest(attached) != continuation_pin:
                raise ValueError('The saved continuation changed.')
            return project(report, attached)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            raise HTTPException(409, 'The saved comparison could not be verified. Its contents are not displayed.') from exc

    app.router.routes[:] = [route for route in app.routes if route.path not in ('/', '/api/workspace')]

    @app.get('/api/workspace')
    def saved_workspace(request: Request):
        packet, sampling = snapshot(request)
        if loop_condition is not None:
            packet = student_loop(packet, sampling, loop_condition)
            for encounter in packet['encounters']:
                encounter['loop_authored_demo'] = authored_demo
        return packet

    @app.get('/api/policy-sampling')
    def saved_sampling(request: Request):
        return {**snapshot(request)[1], 'authored_demo':authored_demo}

    @app.get('/', response_class=HTMLResponse)
    def page():
        if loop_condition is not None:
            return workspace._page().replace('</head>', '<link rel="stylesheet" href="/student-loop.css"></head>').replace(
                '</body>', '<script src="/student-loop.js"></script></body>')
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

    @app.get('/student-loop.js')
    def loop_script():
        return Response((ROOT/'apps/student-loop.js').read_text(), media_type='text/javascript')

    @app.get('/student-loop.css')
    def loop_style():
        return Response((ROOT/'apps/student-loop.css').read_text(), media_type='text/css')

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
    parser.add_argument('--continuation', type=Path, help='Verified saved execution and reaction attachment; read only.')
    parser.add_argument('--student-loop', choices=('direct', 'hint', 'both'),
                        help='Replay predetermined samples as five-stage loops; both enables policy switching.')
    parser.add_argument('--port', type=int, default=8450)
    provenance = parser.add_mutually_exclusive_group(required=True)
    provenance.add_argument('--authored-demo', action='store_true', dest='authored_demo',
                            help='Clearly identify authored UI test data.')
    provenance.add_argument('--live-results', action='store_false', dest='authored_demo',
                            help='Explicitly identify a completed live provider study.')
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(notebook_branch=args.branch, comparison=args.comparison,
                          authored_demo=args.authored_demo, continuation=args.continuation,
                          loop_condition=args.student_loop),
                host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
