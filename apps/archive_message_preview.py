"""Inspect saved student runs and their earlier policy samples in one read-only workspace."""
import argparse
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from src.agents import archived_notebook as archive, archive_tutor_continuation as continuation_store
from src.agents import browser_workspace as workspace
from src.agents import notebook_student as store, student_evidence
from src.eval import notebook_replay
from apps import policy_sampling_preview


ROOT = Path(__file__).resolve().parents[1]


def project(result, continuation=None):
    """Show the closed message and an optional, separately verified tutor continuation."""
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
    if continuation is not None:
        _append_continuation(encounter, result, continuation)
    return {'version':1, 'kind':'notebook', 'source_only':True, 'encounters':[encounter],
        'controls':{'send_enabled':False, 'tutor_generation_enabled':False,
                    'blocked_reason':'This saved run is read only. No model or execution request is running.'},
        'operation':{'status':'idle', 'message':''}}


def _append_continuation(encounter, parent, saved):
    if saved['parent'] != parent or saved['status'] == 'prepared':
        raise ValueError('Use a completed continuation of this exact saved parent.')
    plan, state, reply = saved['plan'], saved['state'], saved['tutor_reply']
    if plan['authored_demo'] != parent['plan']['authored_demo']:
        raise ValueError('Continuation provenance differs from its parent.')
    frames = encounter['frames']
    previous = frames[-1]
    encounter.update(archive_continuation=True, terminal_status=saved['status'], execution_results=0)
    del encounter['execution_calls']  # Loaded results do not expose failed executor-call counts.
    binding = {'session_sha256':store.digest(plan), 'state_sha256':store.digest(saved)}
    next_frame = deepcopy(previous) | {'decisions_remaining':plan['max_decisions'], 'actions':[],
        'changes':{'baseline_revision':previous['work']['revision'],
                   'baseline_kind':'previous-saved-step', 'unified_diff':''}, 'binding':binding}
    if saved['status'] == 'tutor-error':
        if state is not None or reply is not None:
            raise ValueError('A failed tutor request cannot contain a reply or student result.')
        frames.append(next_frame | {'label':'Tutor reply failed', 'archive_stage':'tutor-error',
                                   'status':'tutor-error'})
    else:
        if state is None or reply is None or not state['history']:
            raise ValueError('A saved tutor continuation requires a reply and student result.')
        dialogue = deepcopy(previous['dialogue']) + [
            {'role':'student', 'text':parent['state']['message'], 'origin':'generated'},
            {'role':'tutor', 'text':reply['text'], 'origin':'generated',
             'display_html':workspace._tutor_html(reply['text'])}]
        if [{key:t[key] for key in ('role','text')} for t in dialogue] != [
                {key:t[key] for key in ('role','text')} for t in state['dialogue']]:
            raise ValueError('Continuation dialogue differs from its saved exchange.')
        frames.append(next_frame | {'label':'New tutor reply', 'archive_stage':'tutor',
            'status':'active', 'dialogue':dialogue, 'pending_message':None})
        observed = None
        for index, event in enumerate(state['history'], 1):
            before, work, choice = frames[-1]['work'], event['work_after'], event.get('action')
            decision = choice['decision'] if choice else 'error'
            final = index == len(state['history'])
            if decision == 'revise-work' and work['revision'] != before['revision']:
                observed = None
            if event.get('observation') is not None:
                observed = deepcopy(event['observation'])
                encounter['execution_results'] += 1
            label = {'revise-work':'Student edit' + (' + message' if choice and choice['text'] else ''),
                     'request-check':'Student requested local run', 'reply':'Student message',
                     'no-reply':'No further action', 'error':'Student decision failed'}[decision]
            if event.get('error') and choice:
                label = 'Student action failed'
            item = {'label':label, 'archive_stage':decision,
                'status':state['status'] if final else 'active',
                'decisions_remaining':plan['max_decisions']-index, 'work':deepcopy(work),
                'dialogue':deepcopy(dialogue), 'pending_message':state['message'] if final else None,
                'feedback':None, 'actions':[deepcopy(choice)] if choice else [],
                'changes':{'baseline_revision':before['revision'], 'baseline_kind':'previous-saved-step',
                           'unified_diff':notebook_replay._code_diff(before, work)},
                'binding':{**binding, 'state_sha256':store.digest(event)}}
            if event.get('error'):
                item['archive_action_failed'] = True
            if observed is not None:
                if (observed['revision'] != work['revision'] or
                        observed['source_sha256'] != sha256(work['source'].encode()).hexdigest()):
                    raise ValueError('The displayed execution result is not bound to the current source.')
                item['archive_observation'] = {**observed, 'dataset':deepcopy(plan['dataset']),
                                               'image_id':plan['image_id']}
                item['archive_observation_new'] = event.get('observation') is not None
            frames.append(item)
        encounter['model_decisions'] += len(state['history'])
    encounter['saved_results_html'] = workspace._tutor_html(
        ('Authored test data. ' if plan['authored_demo'] else 'Saved model continuation. ')+
        f'Final saved status: {saved["status"]}. {encounter["model_decisions"]} student decision attempts across '
        f'the original run and this continuation; {encounter["execution_results"]} saved local execution results. '
        'The original message is unchanged. The new segment allows one tutor reply, at most three student '
        'decisions, and at most two student-requested local executions. An edit clears current feedback; '
        'a saved result belongs only to its source revision. Local execution is ungraded and does not '
        'establish correctness or learning. Historical dataset bytes and kernel are unverified. '
        'This is simulated behavior, not a reconstruction of the real student’s future. '
        'Viewing or reloading sends no model or execution requests.')


def consolidate(parent, continuation=None):
    """Use the exact earlier study frozen in this parent, without borrowing its outputs."""
    latest = project(parent, continuation)
    folder = Path(parent['plan']['followup_folder'])
    followup = archive._followup()
    _, report, _ = followup.context(folder)
    attached = followup.load(folder)
    if store.digest(attached) != parent['plan']['followup_sha256']:
        raise ValueError('The earlier policy study differs from this parent.')
    packet, sampling = policy_sampling_preview.project(report, attached)
    for encounter, condition in zip(packet['encounters'], sampling['conditions']):
        for sample in condition['samples']:
            captured, tutor = deepcopy(encounter['frames'])
            captured.update(archive_stage='captured', label='Captured start')
            tutor.update(archive_stage='tutor', label='Tutor reply')
            edit = deepcopy(sample['frame'])
            observed = edit.pop('external_execution', None)
            decision = sample['decision']
            edit.update(archive_stage=decision, label={
                'revise-work':'Student edit', 'reply':'Student message', 'no-reply':'No further action'}[decision])
            timeline = [captured, tutor, edit]
            if observed is not None:
                if (observed['revision'] != edit['work']['revision'] or
                        observed['source_sha256'] != sha256(edit['work']['source'].encode()).hexdigest()):
                    raise ValueError('The saved check does not match this policy revision.')
                timeline.append(deepcopy(edit) | {
                    'archive_stage':'researcher-check', 'label':'Researcher check', 'actions':[],
                    'archive_observation':observed, 'archive_observation_actor':'researcher',
                    'archive_observation_new':True,
                    'changes':{'baseline_revision':edit['work']['revision'],
                               'baseline_kind':'previous-saved-step', 'unified_diff':''}})
            if sample.get('reaction_frame'):
                reaction = deepcopy(sample['reaction_frame'])
                reaction.pop('reaction')
                decision = reaction['actions'][0]['decision']
                reaction.update(archive_stage=decision, archive_reaction=True,
                    label={'revise-work':'Student edit after check', 'reply':'Student message after check',
                           'no-reply':'No further action'}[decision])
                if observed and reaction['work'] == edit['work']:
                    reaction.update(archive_observation=deepcopy(observed), archive_observation_new=False,
                                    archive_observation_actor='researcher')
                timeline.append(reaction)
            sample['timeline'] = timeline
        if not condition['samples']:
            raise ValueError('The earlier policy study has no valid samples.')
        selected = condition['samples'][0]
        encounter.update(archive_message=True, simulation_workspace=True, policy_sample=True,
            policy_label=condition['label'], sample_index=selected['index'],
            authored_demo=parent['plan']['authored_demo'], frames=deepcopy(selected['timeline']),
            execution_results=sum(bool(f.get('archive_observation_new')) for f in selected['timeline']))
        encounter['saved_results_html'] += workspace._tutor_html(
            'These are earlier policy samples, separate from the latest continuation. Checks were triggered '
            'by the researcher and shared across matching source edits, not independently run for every sample. '
            'Only the predetermined first sample of each policy has a saved reaction; other paths end at '
            'the shared check. A missing reaction does not mean the student chose silence.')
    for encounter in latest['encounters']:
        encounter['simulation_workspace'] = True
    packet['encounters'].extend(latest['encounters'])  # The shared workbench defaults to the final encounter.
    sampling.update(unified_workspace=True, authored_demo=parent['plan']['authored_demo'])
    return packet, sampling


def create_app(folder, *, notebook_branch, continuation=None, include_policy_samples=False):
    folder = Path(folder).absolute()
    initial = archive.load(folder)
    continuation = Path(continuation).absolute() if continuation is not None else None
    attached = continuation_store.load(continuation) if continuation is not None else None
    project(initial, attached)
    if include_policy_samples:
        consolidate(initial, attached)
    pin = store.digest(initial)
    continuation_pin = store.digest(attached) if attached is not None else None
    app = workspace.create_app(notebook_branch=notebook_branch)
    # Keep the existing localhost security middleware and shared assets, not another data source.
    app.router.routes[:] = [route for route in app.routes if route.path in ('/workspace.js', '/api/scenarios')]

    def snapshot(request):
        if request.query_params:
            raise HTTPException(400, 'This is one fixed saved run.')
        try:
            result = archive.load(folder)
            if store.digest(result) != pin:
                raise ValueError('Saved run changed.')
            attached = continuation_store.load(continuation) if continuation is not None else None
            if attached is not None and store.digest(attached) != continuation_pin:
                raise ValueError('Saved continuation changed.')
            return consolidate(result, attached) if include_policy_samples else (project(result, attached), None)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            raise HTTPException(409, 'This saved run could not be verified. Its contents are not displayed.') from exc

    @app.get('/api/workspace')
    def saved(request: Request):
        return snapshot(request)[0]

    if include_policy_samples:
        @app.get('/api/policy-sampling')
        def samples(request: Request):
            return snapshot(request)[1]

    @app.get('/', response_class=HTMLResponse)
    def page():
        styles = '<link rel="stylesheet" href="/student-loop.css">'
        scripts = '<script src="/archive-message.js"></script>'
        if include_policy_samples:
            styles += '<link rel="stylesheet" href="/next-actions.css"><link rel="stylesheet" href="/policy-sampling.css">'
            scripts += '<script src="/policy-sampling.js"></script>'
        return workspace._page().replace('</head>', styles+'</head>').replace('</body>', scripts+'</body>')

    @app.get('/student-loop.css')
    def style():
        return Response((ROOT/'apps/student-loop.css').read_text(), media_type='text/css')

    @app.get('/archive-message.js')
    def script():
        return Response((ROOT/'apps/archive-message.js').read_text(), media_type='text/javascript')

    if include_policy_samples:
        @app.get('/{asset}')
        def comparison_asset(asset: str):
            if asset not in ('next-actions.css', 'policy-sampling.css', 'policy-sampling.js'):
                raise HTTPException(404)
            return Response((ROOT/'apps'/asset).read_text(),
                            media_type='text/javascript' if asset.endswith('.js') else 'text/css')

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
    parser.add_argument('--continuation', type=Path)
    parser.add_argument('--include-policy-samples', action='store_true',
                        help='Include the verified earlier policy study frozen in this run.')
    parser.add_argument('--port', type=int, default=8453)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(args.folder, notebook_branch=args.branch, continuation=args.continuation,
                          include_policy_samples=args.include_policy_samples),
                host='127.0.0.1', port=args.port)
