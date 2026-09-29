"""Execute distinct saved policy edits once, then one predetermined reaction per policy."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path

from src.agents import next_action_sampling as sampling, notebook_student as store
from src.eval import notebook_action as action

ROOT = Path(__file__).resolve().parents[2]
COMPARISON = ROOT/'experiments/2026-09-29-notebook-policy-sampling/run.py'
IMAGE = 'sha256:5a4faf5e0cfc5a8bd6603cddf7b5e428c6e74eee6111b90bab483f0d0a561be4'
MODEL = 'gemini-2.5-pro'
CONDITIONS = ('direct','hint')
OLD = 'A revision is only a source edit. No code is executed and no grader result is\navailable. Do not invent checks, outputs, unseen edits or outcomes.'
NEW = ('The displayed work was executed locally after the previous simulated edit.\n'
       'Its actual result is supplied as observation; no correctness grade is available.\n'
       'Any new revision is only a source edit and has not been executed. Do not invent\n'
       'checks, outputs, unseen edits or outcomes. Choose one next action after seeing\n'
       'this feedback; the earlier run was a researcher intervention, not a student choice.')


def now():
    return datetime.now(timezone.utc).isoformat()


def ordered(*values):
    times = [datetime.fromisoformat(value) for value in values]
    if any(value.tzinfo is None for value in times) or times != sorted(times):
        raise ValueError('Follow-up timestamps are missing timezones or out of order.')


def digest_source(source):
    return sha256(source.encode('utf-8')).hexdigest()


def module(path, name):
    sampling._no_symlinks(Path(path))
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def read(path):
    sampling._no_symlinks(path)
    if not path.is_file() or path.stat().st_size > 64*1024*1024:
        raise ValueError('Expected a bounded regular follow-up artifact.')
    return store._read(path)


def pins(paths):
    result = {}
    for path in paths:
        path = Path(path).absolute()
        sampling._no_symlinks(path)
        result[str(path)] = sha256(path.read_bytes()).hexdigest()
    return result


def code_pins():
    return sampling._pins() | pins([Path(__file__),COMPARISON])


def selection(report):
    if set(report['conditions']) != set(CONDITIONS):
        raise ValueError('Exactly the two saved policy conditions are required.')
    sources, selected = {}, {}
    for name in CONDITIONS:
        item = report['conditions'][name]
        records = item['records']
        if item['status'] != 'complete' or len(records) != 30:
            raise ValueError('Use the completed fixed 30-draw comparison.')
        valid = [record for record in records if record['status']=='complete']
        if not valid or valid[0]['response']['decision'] != 'revise-work':
            raise ValueError('The first valid sample must be an edit; do not choose a later outcome.')
        selected[name] = valid[0]['index']
        for record in valid:
            if record['response']['decision'] == 'revise-work':
                source = record['response']['source']
                key = digest_source(source)
                if key in sources and sources[key] != source:
                    raise ValueError('Distinct source strings share a checksum.')
                sources[key] = source
    return sources, selected


def request(source, dataset):
    return {'source':source,'source_sha256':digest_source(source),'result':'unique_uris','csv_sha256':dataset['sha256']}


def prepare(folder, comparison, probe):
    folder, comparison, probe = (Path(path).absolute() for path in (folder,comparison,probe))
    sampling._no_symlinks(folder)
    if folder.is_relative_to(comparison) or folder.is_relative_to(probe.parent):
        raise ValueError('Keep follow-up output separate from the frozen inputs.')
    report = module(COMPARISON,'policy_comparison').load(comparison)
    executor = module(probe,'policy_probe')
    if executor.verify(probe.parent)['status'] != 'verified':
        raise ValueError('Use the already verified archived-data probe.')
    sources, selected = selection(report)
    for source in sources.values():
        executor.validate_request(request(source,executor.DATASET))
    probe_files = [probe]+[probe.parent/name for name in ('probe_worker.py','preparation.json','run.json','results.json')
                         if (probe.parent/name).is_file()]
    plan = {'version':1,'kind':'notebook-policy-execution','created_at':now(),
        'comparison_folder':str(comparison),'comparison_sha256':store.digest(report),
        'probe':str(probe),'probe_pins':pins(probe_files),'code_pins':code_pins(),
        'dataset':deepcopy(executor.DATASET),'image_id':IMAGE,'sources':sources,'selected_samples':selected,
        'model':MODEL,'sdk_version':version('google-genai'),'sdk_attempts':1,'timeout_ms':120000,
        'schema':action.Action.model_json_schema(),'maximum_reactions':2,
        'authorization':'User approved each distinct saved policy edit once and one reaction per policy, first valid sample selected before results.',
        'scope':'Researcher-triggered executions and two new reactions; the original 60-draw comparison remains unchanged. No course grader or further execution.'}
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'checks').mkdir()
    store._save(folder/'plan.json',{'sha256':store.digest(plan),'plan':plan},exclusive=True)
    return deepcopy(plan)


def context(folder):
    folder = Path(folder).absolute()
    envelope = read(folder/'plan.json')
    plan = envelope['plan']
    if (envelope['sha256'] != store.digest(plan) or plan['version'] != 1
            or plan['kind'] != 'notebook-policy-execution' or plan['code_pins'] != code_pins()
            or plan['probe_pins'] != pins(plan['probe_pins']) or plan['image_id'] != IMAGE
            or plan['model'] != MODEL or plan['sdk_version'] != version('google-genai')
            or plan['sdk_attempts'] != 1 or plan['timeout_ms'] != 120000 or plan['maximum_reactions'] != 2
            or plan['schema'] != action.Action.model_json_schema()):
        raise ValueError('Frozen follow-up plan or implementation changed.')
    if str(Path(plan['probe']).absolute()) not in plan['probe_pins']:
        raise ValueError('The selected probe implementation is not pinned.')
    report = module(COMPARISON,'policy_comparison').load(plan['comparison_folder'])
    sources, selected = selection(report)
    if plan['comparison_sha256'] != store.digest(report) or plan['sources'] != sources or plan['selected_samples'] != selected:
        raise ValueError('Original comparison or predetermined selection changed.')
    probe = module(Path(plan['probe']),'policy_probe')
    if probe.verify(Path(plan['probe']).parent)['status'] != 'verified' or plan['dataset'] != probe.DATASET:
        raise ValueError('Pinned archive probe changed.')
    return plan, report, probe


def checks(folder, plan, probe):
    result = {}
    paths = list((folder/'checks').glob('*.json'))
    expected = [folder/'checks'/f'{key}.json' for key in plan['sources']]
    present = [path for path in expected if path.exists()]
    if set(paths) != set(present) or present != expected[:len(present)]:
        raise ValueError('Execution sequence contains unknown or missing sources.')
    started = read(folder/'execution.json') if (folder/'execution.json').exists() else None
    if started is None:
        if paths:
            raise ValueError('Checks have no execution launch receipt.')
        return result
    if started['plan_sha256'] != store.digest(plan) or started['status'] not in ('pending','complete','error'):
        raise ValueError('Execution launch changed.')
    ordered(plan['created_at'],started['started_at'])
    previous = started['started_at']
    if started['status']=='complete' and len(present)!=len(expected):
        raise ValueError('Completed execution is missing a distinct source.')
    for index,path in enumerate(present):
        receipt = read(path)
        key = path.stem
        if (receipt['plan_sha256'] != store.digest(plan) or receipt['request'] != request(plan['sources'][key],plan['dataset'])
                or receipt['status'] not in ('pending','complete','error')):
            raise ValueError('Execution receipt changed its bound source.')
        ordered(previous,receipt['started_at'])
        if receipt['status'] != 'pending':
            ordered(receipt['started_at'],receipt['finished_at'])
            previous = receipt['finished_at']
        if receipt['status']=='complete':
            observed = {'revision':1,'source_sha256':key, **probe.parse_result(
                receipt['exit_code'],bytes.fromhex(receipt['raw_output_hex']),receipt['problem'],plan['image_id'])}
            if observed != receipt['result']:
                raise ValueError('Execution result differs from its raw worker output.')
            result[key] = observed
        elif 'result' in receipt or index!=len(present)-1 or started['status']=='complete':
            raise ValueError('Incomplete execution cannot establish a result or be followed by another check.')
    if started['status'] != 'pending':
        ordered(previous,started['finished_at'])
    return result


def execute(folder):
    folder = Path(folder).absolute()
    plan, _, probe = context(folder)
    launch = {'status':'pending','plan_sha256':store.digest(plan),'started_at':now()}
    store._save(folder/'execution.json',launch,exclusive=True)
    try:
        command = probe.nr._local_docker(plan['image_id'])
        probe.verify_image_base(command,plan['image_id'])
        for key,source in plan['sources'].items():
            context(folder)
            payload = request(source,plan['dataset'])
            probe.validate_request(payload)
            path = folder/'checks'/f'{key}.json'
            receipt = {'status':'pending','plan_sha256':store.digest(plan),'request':payload,'started_at':now()}
            store._save(path,receipt,exclusive=True)
            try:
                code,output,problem = probe.nr._execute(command,plan['image_id'],payload,30)
                receipt.update(exit_code=code,raw_output_hex=output.hex(),problem=problem)
                store._save(path,receipt)
                receipt.update(status='complete',result={'revision':1,'source_sha256':key,
                    **probe.parse_result(code,output,problem,plan['image_id'])})
            except Exception as exc:
                receipt.update(status='error',error={'type':type(exc).__name__})
                raise
            finally:
                receipt['finished_at'] = now()
                store._save(path,receipt)
        launch['status'] = 'complete'
    except Exception as exc:
        launch.update(status='error',error={'type':type(exc).__name__})
        raise
    finally:
        launch['finished_at'] = now()
        store._save(folder/'execution.json',launch)
    return load(folder)


def reaction_inputs(plan, report, observed):
    prepared = {}
    if action.PROMPT.count(OLD) != 1:
        raise ValueError('The source-only prompt boundary changed.')
    for name in CONDITIONS:
        item = report['conditions'][name]
        index = plan['selected_samples'][name]
        response = item['records'][index-1]['response']
        task = deepcopy(item['task'])
        applied = action.apply_action(task,action.Action.model_validate(response))
        task['work'] = applied['work']
        if response['text']:
            task['dialogue'].append({'role':'student','text':response['text']})
        check = observed[digest_source(task['work']['source'])]
        if check['status'] not in ('ok','cell-error') or check['execution'] != 'completed':
            raise ValueError('Both selected edits require completed cell execution before reactions.')
        task['history'] = [{'origin':'model','sample_index':index,'action':deepcopy(response)}]
        task['observation'] = deepcopy(check) | {'dataset':deepcopy(plan['dataset']),
            'basis':'Researcher-triggered local execution of this saved edit on archived course data in a new declared environment; no course grader ran.'}
        task['omitted'] = 'Other cells, full table values and the historical kernel are not supplied. New edits remain unexecuted.'
        prompt = action.PROMPT.replace(OLD,NEW)+json.dumps(task,ensure_ascii=False,sort_keys=True)
        prepared[name] = {'sample_index':index,'model':MODEL,'task':task,'prompt':prompt,
                          'prompt_sha256':digest_source(prompt),'schema':action.Action.model_json_schema()}
    return prepared


def prepare_reactions(folder):
    folder = Path(folder).absolute()
    plan, report, probe = context(folder)
    observed = checks(folder,plan,probe)
    if read(folder/'execution.json')['status'] != 'complete' or len(observed)!=len(plan['sources']):
        raise ValueError('Complete the one-time execution batch before preparing reactions.')
    prepared = reaction_inputs(plan,report,observed)
    data = {'plan_sha256':store.digest(plan),'created_at':now(),'inputs':prepared}
    store._save(folder/'reaction-inputs.json',{'sha256':store.digest(data),'preparation':data},exclusive=True)
    return load(folder)


def load(folder):
    folder = Path(folder).absolute()
    plan, report, probe = context(folder)
    observed = checks(folder,plan,probe)
    result = {'comparison_sha256':plan['comparison_sha256'],'dataset':deepcopy(plan['dataset']),
              'image_id':plan['image_id'],'checks':observed,'reactions':{}}
    if not (folder/'reaction-inputs.json').exists():
        if list(folder.glob('reaction-*.json')) or (folder/'reactions-started.json').exists():
            raise ValueError('Reaction receipts lack their prepared input.')
        return result
    envelope = read(folder/'reaction-inputs.json')
    prepared = envelope['preparation']
    if (envelope['sha256'] != store.digest(prepared) or prepared['plan_sha256'] != store.digest(plan)
            or prepared['inputs'] != reaction_inputs(plan,report,observed)):
        raise ValueError('Prepared reaction input changed.')
    execution = read(folder/'execution.json')
    if execution['status'] != 'complete' or len(observed) != len(plan['sources']):
        raise ValueError('Reaction inputs require a completed execution batch.')
    ordered(execution['finished_at'],prepared['created_at'])
    launch = read(folder/'reactions-started.json') if (folder/'reactions-started.json').exists() else None
    if launch is not None and (launch['preparation_sha256'] != store.digest(prepared)
                              or launch['status'] not in ('pending','complete','error')):
        raise ValueError('Reaction launch differs from its prepared inputs.')
    previous = prepared['created_at']
    if launch is not None:
        ordered(previous,launch['started_at'])
        previous = launch['started_at']
    sampler = module(sampling.RUNNER,'policy_reaction_sampler')
    attempted, terminal = [], []
    for name in CONDITIONS:
        data = prepared['inputs'][name]
        view = {key:deepcopy(data[key]) for key in ('sample_index','model','task')} | {'status':'prepared'}
        path = folder/f'reaction-{name}.json'
        if path.exists():
            attempted.append(name)
            receipt = read(path)
            if (launch is None or receipt['input_sha256'] != store.digest(data)
                    or receipt['preparation_sha256'] != store.digest(prepared)
                    or receipt['status'] not in ('pending','complete','error')):
                raise ValueError('Reaction receipt differs from the frozen request.')
            ordered(previous,receipt['started_at'])
            if receipt['status'] != 'pending':
                ordered(receipt['started_at'],receipt['finished_at'])
                previous = receipt['finished_at']
                terminal.append(name)
            view['status'] = receipt['status']
            view.update({key:receipt[key] for key in ('started_at','finished_at') if key in receipt})
            if receipt['status']=='complete':
                response = sampler.parse_response(receipt['raw_response'])
                applied = action.apply_action(data['task'],action.Action.model_validate(response))
                if receipt.get('response') != response or receipt.get('applied') != applied:
                    raise ValueError('Reaction does not reproduce from the raw provider response.')
                view.update(response=response,applied=applied)
            elif 'response' in receipt or 'applied' in receipt:
                raise ValueError('Incomplete reactions cannot supply accepted actions.')
        result['reactions'][name] = view
    if attempted != list(CONDITIONS[:len(attempted)]) or terminal != attempted[:len(terminal)]:
        raise ValueError('Reaction sequence contains a gap or follows a pending request.')
    if launch is not None and launch['status']=='complete':
        if terminal != list(CONDITIONS):
            raise ValueError('Completed launch lacks two terminal reaction receipts.')
        ordered(previous,launch['finished_at'])
    elif terminal == list(CONDITIONS):
        raise ValueError('Terminal reactions lack their completed launch receipt.')
    return result


def send(folder,send=False,*,generate=None):
    if send is not True:
        raise ValueError('Explicit send=True is required.')
    folder = Path(folder).absolute()
    current = load(folder)
    if len(current['reactions']) != 2 or any(item['status']!='prepared' for item in current['reactions'].values()):
        raise FileExistsError('Prepare exactly two fresh reactions; existing attempts cannot resend.')
    plan, _, _ = context(folder)
    prepared = read(folder/'reaction-inputs.json')['preparation']
    sampler = module(sampling.RUNNER,'policy_reaction_sampler')
    if generate is None:
        from dotenv import load_dotenv
        load_dotenv(ROOT/'.env')
        load_dotenv(ROOT.parent/'main/.env')
        if not os.environ.get('GEMINI_API_KEY'):
            raise ValueError('Configure GEMINI_API_KEY before sending.')
    launch = {'status':'pending','preparation_sha256':store.digest(prepared),'started_at':now()}
    store._save(folder/'reactions-started.json',launch,exclusive=True)
    for name in CONDITIONS:
        load(folder)
        data = prepared['inputs'][name]
        path = folder/f'reaction-{name}.json'
        receipt = {'status':'pending','preparation_sha256':store.digest(prepared),
                   'input_sha256':store.digest(data),'started_at':now()}
        store._save(path,receipt,exclusive=True)
        try:
            receipt['raw_response'] = (generate or sampler.live_generate)(plan,data['prompt'])
            store._save(path,receipt)
            response = sampler.parse_response(receipt['raw_response'])
            receipt.update(status='complete',response=response,
                           applied=action.apply_action(data['task'],action.Action.model_validate(response)))
        except Exception as exc:
            receipt.update(status='error',error={'type':type(exc).__name__})
        receipt['finished_at'] = now()
        store._save(path,receipt)
    launch.update(status='complete',finished_at=now())
    store._save(folder/'reactions-started.json',launch)
    return load(folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','execute','prepare-reactions','send','show'))
    parser.add_argument('folder',type=Path)
    parser.add_argument('--comparison',type=Path)
    parser.add_argument('--probe',type=Path)
    parser.add_argument('--send',action='store_true')
    args = parser.parse_args()
    if args.command=='prepare':
        if args.comparison is None or args.probe is None:
            parser.error('prepare requires --comparison and --probe')
        prepare(args.folder,args.comparison,args.probe)
        result = load(args.folder)
    elif args.command=='execute':
        result = execute(args.folder)
    elif args.command=='prepare-reactions':
        result = prepare_reactions(args.folder)
    elif args.command=='send':
        result = send(args.folder,send=args.send)
    else:
        result = load(args.folder)
    print(json.dumps({'comparison_sha256':result['comparison_sha256'],'distinct_checks':len(result['checks']),
                     'reactions':{name:item['status'] for name,item in result['reactions'].items()}}))


if __name__=='__main__':
    main()
