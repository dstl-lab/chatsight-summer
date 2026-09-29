"""Local, read-only design preview of a completed next-action sampling batch."""
import argparse
from copy import deepcopy
from hashlib import sha256
import importlib.util
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from src.agents import browser_workspace as workspace
from src.agents import notebook_branch as branch
from src.agents import notebook_student as store
from src.eval import notebook_replay
from src.labeling import llm


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT/'experiments/2026-09-29-next-action-monte-carlo/run.py'


def _batch(folder, report_pin, preparation_path, preparation_pin, prepared):
    """Reuse the frozen experiment's STOP parser and report calculation, never its runner."""
    report = workspace._branch_artifact(folder/'report.json', report_pin)
    plan = workspace._branch_artifact(folder/'plan.json', report['plan_sha256'])
    if (plan['input_path'] != str(preparation_path.resolve())
            or plan['input_sha256'] != preparation_pin
            or plan['model'] != prepared['model']
            or plan['prompt_sha256'] != prepared['prompt_sha256']
            or plan['generation_config'] != {'response_mime_type':'application/json',
                                             'response_schema':prepared['schema']}):
        raise ValueError('The batch input differs from the verified pre-reaction input.')
    if type(plan['attempts']) is not int or not 1 <= plan['attempts'] <= 1000:
        raise ValueError('Unsupported saved batch size.')
    code = (RUNNER, Path(llm.__file__), Path(store.__file__), Path(branch.action.__file__))
    if plan['code_pins'] != {str(p):sha256(p.read_bytes()).hexdigest() for p in code}:
        raise ValueError('The saved report implementation changed.')
    names = [f'draw-{i:02d}.json' for i in range(1, plan['attempts']+1)]
    if set(report['draw_sha256']) != set(names):
        raise ValueError('The report must pin every attempted draw.')
    records = [workspace._branch_artifact(folder/name, report['draw_sha256'][name]) for name in names]
    started = folder/'started.json'
    if any(p.is_symlink() for p in (started, *started.parents)) or not started.is_file() or started.stat().st_size > 1024*1024:
        raise ValueError('The saved launch must be a regular bounded file.')
    workspace._branch_artifact(started, sha256(started.read_bytes()).hexdigest())
    # Import only this fixed public module after its code pin is checked. No saved
    # script path is imported, and neither execute() nor live_generate() is called.
    spec = importlib.util.spec_from_file_location('next_actions_saved_report', RUNNER)
    sampler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sampler)
    if store.digest(sampler.analyse(folder)) != store.digest(report):
        raise ValueError('The saved report does not reproduce from its raw responses.')
    return report, records


def create_app(*, notebook_branch, notebook_execution, notebook_execution_sha256,
               notebook_reaction, notebook_reaction_sha256, batch, report_sha256):
    options = dict(notebook_branch=notebook_branch, notebook_execution=notebook_execution,
        notebook_execution_sha256=notebook_execution_sha256, notebook_reaction=notebook_reaction,
        notebook_reaction_sha256=notebook_reaction_sha256)
    app = workspace.create_app(**options)
    checkpoint_pin = store.digest(branch.load(notebook_branch)[0])
    folder = Path(batch).absolute()
    preparation = Path(notebook_reaction).with_name('reaction-preparation.json')

    def snapshot():
        packet = workspace._source_branch_snapshot(notebook_branch, checkpoint_pin,
            notebook_execution, notebook_execution_sha256, notebook_reaction, notebook_reaction_sha256)
        saved = workspace._branch_artifact(notebook_reaction, notebook_reaction_sha256)
        prepared = workspace._branch_artifact(preparation, saved['preparation_sha256'])
        report, records = _batch(folder, report_sha256, preparation, saved['preparation_sha256'], prepared)
        before, original = packet['encounters'][0]['frames'][1:]
        samples = []
        for record in records:
            if record['status'] != 'complete':
                continue
            choice = branch.action.Action.model_validate(record['response'])
            applied = branch.action.apply_action(prepared['task'], choice)
            frame = deepcopy(original)
            frame.pop('external_execution', None)
            frame.update(label=f'Saved sample {record["index"]}',
                status='no-reply' if choice.decision == 'no-reply' else 'awaiting-tutor' if applied['message'] else 'active',
                work=applied['work'], dialogue=deepcopy(before['dialogue']) + ([{
                    'role':'student', 'text':applied['message'], 'origin':'generated'}] if applied['message'] else []),
                actions=[choice.model_dump()], feedback=None,
                binding={'session_sha256':checkpoint_pin, 'state_sha256':store.digest(applied)},
                changes={'baseline_revision':before['work']['revision'], 'baseline_kind':'previous-saved-step',
                         'unified_diff':notebook_replay._code_diff(before['work'], applied['work'])})
            frame['reaction'].update(action=choice.model_dump(), started_at=record['started_at'],
                                     finished_at=record['finished_at'])
            samples.append({'index':record['index'], 'decision':choice.decision, 'frame':frame})
        return {'model':report['model'],
            'input_label':f'Executed revision {before["work"]["revision"]}, before the saved reaction',
            'attempts':report['attempts'], 'valid':report['valid'], 'failed':report['failed'],
            'categories':[{'decision':key, 'count':value['count'], 'proportion':value['proportion'],
                           'interval':value['wilson_95_marginal']} for key,value in report['actions'].items()],
            'samples':samples}

    snapshot()  # Fail closed at startup as well as on every saved-data reload.

    @app.get('/api/next-actions')
    def next_actions(request: Request):
        if request.query_params:
            raise HTTPException(400, 'This preview uses only the saved batch selected at launch.')
        try:
            return snapshot()
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(409, 'The saved samples could not be verified. Their contents are not displayed.') from exc

    # Leave the normal workspace and its legacy page unchanged outside this app.
    app.router.routes[:] = [route for route in app.router.routes if route.path != '/']

    @app.get('/', response_class=HTMLResponse)
    def page():
        return workspace._page().replace('</head>', '<link rel="stylesheet" href="/next-actions.css"></head>').replace(
            '</body>', '<script src="/next-actions.js"></script></body>')

    @app.get('/next-actions.css')
    def style():
        return Response((ROOT/'apps/next-actions.css').read_text(), media_type='text/css')

    @app.get('/next-actions.js')
    def script():
        return Response((ROOT/'apps/next-actions.js').read_text(), media_type='text/javascript')

    @app.middleware('http')
    async def preview_style(request: Request, call_next):
        response = await call_next(request)
        policy = response.headers.get('Content-Security-Policy', '')
        response.headers['Content-Security-Policy'] = policy.replace(
            "style-src 'unsafe-inline'", "style-src 'self' 'unsafe-inline'")
        return response

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', type=Path, required=True)
    parser.add_argument('--execution', type=Path, required=True)
    parser.add_argument('--execution-sha256', required=True)
    parser.add_argument('--reaction', type=Path, required=True)
    parser.add_argument('--reaction-sha256', required=True)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--report-sha256', required=True)
    parser.add_argument('--port', type=int, default=8449)
    args = parser.parse_args()
    app = create_app(notebook_branch=args.branch, notebook_execution=args.execution,
        notebook_execution_sha256=args.execution_sha256, notebook_reaction=args.reaction,
        notebook_reaction_sha256=args.reaction_sha256, batch=args.batch, report_sha256=args.report_sha256)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
