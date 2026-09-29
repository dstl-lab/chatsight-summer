"""Two fixed tutor replies and 30 independent next actions per reply; private receipts only."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import time
from uuid import uuid4

from src.agents import notebook_branch as branch, notebook_student as store, notebook_tutor as tutor
from src.agents import next_action_sampling as sampling


MODEL = 'gemini-2.5-pro'
POLICIES = {
    'direct': {'label':'Direct answer', 'policy':
        'Answer the current student question directly and concisely. Supply the complete corrected '
        'code for the selected cell and briefly explain the relevant correction. Do not ask the '
        'student to discover or explain it before giving the answer.'},
    'hint': {'label':'Guided hint', 'policy':
        'Give one concise, actionable hint addressing the current student question. Explain the '
        'relevant concept and ask one focused question to help the student make the next edit. '
        'Do not supply the complete corrected cell or final answer.'}}
SCOPE = ('Exploratory model sensitivity at one captured checkpoint. Thirty draws per fixed generated '
         'tutor reply; these are not 30 students or 30 independently generated tutor replies. '
         'Source edits are unexecuted. No real-student fidelity, learning, or tutor effectiveness is established.')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read(path):
    path = Path(path).absolute()
    sampling._no_symlinks(path)
    if not path.is_file() or path.stat().st_size > 64*1024*1024:
        raise ValueError('Expected a bounded regular comparison file.')
    return store._read(path)


def _pins():
    return sampling._pins() | {str(Path(p).resolve()):sha256(Path(p).read_bytes()).hexdigest()
                              for p in (__file__, tutor.__file__)}


def _shared(manifest):
    task = deepcopy(manifest['task'])
    if (set(task) != {'initialization','captured_at','task','work','dialogue','observation','omitted'}
            or task['observation'] is not None or task['work']['revision'] != 0
            or set(task['work']) != {'cell_index','source','revision'}
            or [turn['role'] for turn in task['dialogue']] != ['student','tutor']):
        raise ValueError('Use captured revision zero with its first student/tutor exchange and no observation.')
    task['dialogue'] = task['dialogue'][:-1]
    return task


def prepare(folder, source_branch):
    folder, source = Path(folder).absolute(), Path(source_branch).absolute()
    sampling._no_symlinks(folder)
    if folder.is_relative_to(source):
        raise ValueError('Keep comparison output outside the source branch.')
    manifest, _ = branch.load(source)
    plan = {'version':1, 'kind':'notebook-policy-sampling', 'created_at':_now(), 'model':MODEL,
        'source_branch':str(source), 'checkpoint_sha256':store.digest(manifest),
        'shared_task':_shared(manifest), 'policies':deepcopy(POLICIES), 'runs_per_condition':30,
        'batch_ids':{name:str(uuid4()) for name in POLICIES}, 'max_provider_calls':62,
        'code_pins':_pins(), 'sdk_version':version('google-genai'),
        'authorization':'User approved three-sample live check followed by 30 samples each for direct answer versus guided hint.',
        'scope':SCOPE}
    folder.mkdir(parents=True, exist_ok=False)
    store._save(folder/'plan.json', {'sha256':store.digest(plan), 'plan':plan}, exclusive=True)
    return deepcopy(plan)


def _plan(folder):
    envelope = _read(Path(folder)/'plan.json')
    plan = envelope['plan']
    manifest, _ = branch.load(plan['source_branch'])
    if (envelope['sha256'] != store.digest(plan) or plan['version'] != 1
            or plan['kind'] != 'notebook-policy-sampling' or plan['model'] != MODEL
            or plan['policies'] != POLICIES or plan['runs_per_condition'] != 30
            or plan['max_provider_calls'] != 62 or plan['code_pins'] != _pins()
            or plan['sdk_version'] != version('google-genai')
            or plan['checkpoint_sha256'] != store.digest(manifest)
            or plan['shared_task'] != _shared(manifest) or set(plan['batch_ids']) != set(POLICIES)):
        raise ValueError('Frozen comparison plan, source or implementation changed.')
    for value in plan['batch_ids'].values():
        sampling._identifier(value)
    return plan


def _tutor_prompt(plan, name):
    task = plan['shared_task']
    context = {**task, 'pending_message':task['dialogue'][-1]['text'], 'feedback':None}
    return tutor.PROMPT + json.dumps({'policy':plan['policies'][name]['policy'], 'context':context},
                                    ensure_ascii=False, sort_keys=True)


def _reply(raw):
    candidates = raw.get('candidates') or []
    if len(candidates) != 1 or candidates[0].get('finish_reason') != 'STOP':
        raise ValueError('Exactly one complete tutor STOP candidate is required.')
    parts = candidates[0].get('content', {}).get('parts') or []
    return tutor.Reply.model_validate_json(''.join(p.get('text','') for p in parts if not p.get('thought'))).model_dump()


def _tutor_receipt(folder, plan, name):
    receipt = _read(Path(folder)/f'tutor-{name}.json')
    if (receipt['plan_sha256'] != store.digest(plan) or receipt['prompt'] != _tutor_prompt(plan,name)
            or receipt['schema'] != tutor.Reply.model_json_schema()
            or receipt['status'] not in ('complete','error','pending')):
        raise ValueError('Tutor receipt differs from the frozen request.')
    if receipt['status'] == 'complete':
        if receipt['response'] != _reply(receipt['raw_response']):
            raise ValueError('Tutor reply differs from the raw provider response.')
    elif 'response' in receipt:
        raise ValueError('An unfinished tutor cannot supply a reply.')
    return receipt


def _input(plan, reply):
    task = deepcopy(plan['shared_task'])
    task['dialogue'].append({'role':'tutor', 'text':reply})
    prompt = branch.action.make_prompt(task)
    return {'model':MODEL, 'task':task, 'prompt':prompt,
            'prompt_sha256':sha256(prompt.encode()).hexdigest(), 'schema':branch.action.Action.model_json_schema()}


def _live_tutor(plan, prompt):
    from google import genai
    with genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=genai.types.HttpOptions(
            timeout=120000, retry_options={'attempts':1})) as client:
        response = client.models.generate_content(model=MODEL, contents=prompt,
                                                   config=store.llm.gen_config(tutor.Reply))
        return response.model_dump(mode='json', exclude_none=True)


def execute(folder, send=False, *, generate_tutor=None, generate_student=None):
    if send is not True:
        raise ValueError('Explicit send=True is required.')
    folder = Path(folder).absolute()
    plan = _plan(folder)
    if generate_tutor is None or generate_student is None:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parents[2]
        load_dotenv(root/'.env')
        load_dotenv(root.parent/'main/.env')
        if not os.environ.get('GEMINI_API_KEY'):
            raise ValueError('Configure GEMINI_API_KEY before sending.')
    # An interrupted or failed launch also consumes this fixed experiment; never resume or replace draws.
    store._save(folder/'started.json', {'plan_sha256':store.digest(plan), 'started_at':_now()}, exclusive=True)
    for name in POLICIES:
        plan = _plan(folder)
        prompt, path = _tutor_prompt(plan,name), folder/f'tutor-{name}.json'
        receipt = {'status':'pending', 'plan_sha256':store.digest(plan), 'prompt':prompt,
                   'schema':tutor.Reply.model_json_schema(), 'started_at':_now()}
        store._save(path, receipt, exclusive=True)
        try:
            receipt['raw_response'] = (generate_tutor or _live_tutor)(plan,prompt)
            store._save(path,receipt)
            receipt.update(status='complete', response=_reply(receipt['raw_response']))
        except Exception as error:
            receipt.update(status='error', error={'type':type(error).__name__})
        receipt['finished_at'] = _now()
        store._save(path,receipt)
    managers = []
    try:
        for name in POLICIES:
            if _tutor_receipt(folder,plan,name)['status'] != 'complete':
                continue
            def get_input(condition=name):
                current = _plan(folder)
                return _input(current,_tutor_receipt(folder,current,condition)['response']['text'])
            jobs = sampling.SamplingJobs(folder/name,get_input,generate=generate_student)
            managers.append((jobs,plan['batch_ids'][name]))
            jobs.start(plan['batch_ids'][name],30,store.digest(get_input()))
        while any(jobs.snapshot(batch_id)['status'] == 'running' for jobs,batch_id in managers):
            time.sleep(.1)
    finally:
        for jobs,_ in managers:
            jobs.close()
    report = _report(folder,_plan(folder))
    store._save(folder/'report.json', {'sha256':store.digest(report), 'report':report}, exclusive=True)
    return load(folder)


def _report(folder, plan):
    spec = importlib.util.spec_from_file_location('policy_sampling_frozen',sampling.RUNNER)
    sampler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sampler)
    conditions = {}
    for name,policy in plan['policies'].items():
        receipt = _tutor_receipt(folder,plan,name)
        records, task, status, batch_id = [], None, 'tutor-'+receipt['status'], plan['batch_ids'][name]
        if receipt['status'] == 'complete':
            prepared = _input(plan,receipt['response']['text'])
            task = prepared['task']
            envelope = _read(Path(folder)/name/f'{batch_id}.json')
            batch = envelope['batch']
            if (envelope['sha256'] != store.digest(batch) or batch['id'] != batch_id
                    or batch['request_id'] != batch_id or batch['requested'] != 30
                    or batch['prepared'] != prepared or batch['input_sha256'] != store.digest(prepared)
                    or batch['plan']['code_pins'] != sampling._pins()
                    or batch['plan']['model'] != MODEL or batch['plan']['prompt_sha256'] != prepared['prompt_sha256']
                    or batch['plan']['generation_config'] != {'response_mime_type':'application/json','response_schema':prepared['schema']}
                    or batch['plan']['sdk_attempts'] != 1 or batch['plan']['timeout_ms'] != 120000
                    or batch['plan']['sdk_version'] != plan['sdk_version']
                    or batch['status'] not in ('complete','error','interrupted','cancelled')
                    or len(batch['records']) > 30
                    or batch['status'] == 'complete' and len(batch['records']) != 30):
                raise ValueError('Student batch differs from the frozen policy input.')
            records, status = batch['records'], batch['status']
            for index,record in enumerate(records,1):
                if (type(record['index']) is not int or record['index'] != index or record['prompt_sha256'] != prepared['prompt_sha256']
                        or record['status'] not in ('complete','error','pending')
                        or record['status'] == 'pending' and (index != len(records) or status in ('complete','cancelled'))
                        or record['status'] == 'complete' and record['response'] != sampler.parse_response(record['raw_response'])
                        or record['status'] != 'complete' and 'response' in record):
                    raise ValueError('Student sample differs from its raw provider receipt.')
        counts = Counter(record['response']['decision'] for record in records if record['status'] == 'complete')
        valid = sum(counts.values())
        conditions[name] = {**policy, 'model':MODEL, 'task':task, 'tutor_status':receipt['status'],
            'tutor_reply':receipt.get('response',{}).get('text'), 'status':status, 'batch_id':batch_id,
            'records':records, 'requested':30, 'valid':valid,
            'failed':sum(record['status'] == 'error' for record in records),
            'categories':[{'decision':decision,'count':counts[decision],
                'proportion':counts[decision]/valid if valid else None,'interval':sampler.wilson(counts[decision],valid)}
                for decision in sampling.DECISIONS]}
    return {'version':1,'kind':'notebook-policy-sampling','plan_sha256':store.digest(plan),'model':MODEL,
            'shared_task':plan['shared_task'],'conditions':conditions,'scope':SCOPE}


def load(folder):
    folder = Path(folder).absolute()
    plan = _plan(folder)
    if _read(folder/'started.json')['plan_sha256'] != store.digest(plan):
        raise ValueError('Launch receipt differs from the comparison plan.')
    envelope = _read(folder/'report.json')
    report = envelope['report']
    if envelope['sha256'] != store.digest(report) or report != _report(folder,plan):
        raise ValueError('Comparison report does not reproduce from its verified receipts.')
    return report


def aggregate(report):
    return {key:report[key] for key in ('version','kind','model','scope')} | {
        'conditions':{name:{key:item[key] for key in ('label','tutor_status','status','requested','valid','failed','categories')}
                      for name,item in report['conditions'].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','execute','show'))
    parser.add_argument('folder',type=Path)
    parser.add_argument('--source-branch',type=Path)
    parser.add_argument('--send',action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.source_branch is None:
            parser.error('prepare requires --source-branch')
        plan = prepare(args.folder,args.source_branch)
        result = {'status':'prepared','plan_sha256':store.digest(plan),'max_provider_calls':62}
    else:
        result = aggregate(execute(args.folder,send=args.send) if args.command == 'execute' else load(args.folder))
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
