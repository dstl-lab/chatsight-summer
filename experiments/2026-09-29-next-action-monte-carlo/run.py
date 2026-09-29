"""One fixed 30-attempt diagnostic; private inputs/receipts stay outside Git."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
from itertools import count
import json
import math
import os
from pathlib import Path
from statistics import NormalDist
import tempfile

from src.agents import notebook_student as store
from src.eval.notebook_action import Action
from src.labeling import llm


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def input_data(plan):
    path = Path(plan['input_path'])
    if sha(path) != plan['input_sha256']:
        raise ValueError('Prepared input changed.')
    data = store._read(path)
    if (hashlib.sha256(data['prompt'].encode()).hexdigest() != data['prompt_sha256']
            or data['schema'] != Action.model_json_schema()):
        raise ValueError('Prompt or action schema changed.')
    return data


def prepare(path, expected, out):
    plan = {'input_path':str(path.resolve()), 'input_sha256':expected}
    data = input_data(plan)
    if data['model'] != 'gemini-2.5-pro':
        raise ValueError('This diagnostic is fixed to the original model.')
    plan.update(version=1, created_at=now(), attempts=30, workers=3,
        model=data['model'], prompt_sha256=data['prompt_sha256'],
        generation_config={'response_mime_type':'application/json', 'response_schema':data['schema']},
        sdk_version=version('google-genai'), timeout_ms=120000, sdk_attempts=1,
        code_pins={str(p):sha(p) for p in (Path(__file__).resolve(), Path(llm.__file__), Path(store.__file__),
            Path(__import__(Action.__module__, fromlist=['Action']).__file__))},
        authorization={'user_request':"Let's experiment and then report the results back to me - use monte carlo simulation.",
            'scope':'30 fresh Gemini requests with the unchanged saved reaction input. No tutor requests, code execution, retries or replacement draws.'},
        omitted_settings=['temperature','top_p','top_k','seed','thinking_config','max_output_tokens'])
    out.mkdir(parents=True, exist_ok=False)
    store._save(out/'plan.json', plan, exclusive=True)
    return {'status':'prepared', 'attempts':30, 'plan_sha256':sha(out/'plan.json'),
            'prompt_sha256':data['prompt_sha256'], 'prompt_characters':len(data['prompt'])}


def wilson(k, n):
    if n == 0:
        return None
    z = NormalDist().inv_cdf(.975)
    p, denominator = k/n, 1+z*z/n
    center = (p+z*z/(2*n))/denominator
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return [max(0., center-half), min(1., center+half)]


def parse_response(raw):
    candidates = raw.get('candidates') or []
    if len(candidates) != 1 or candidates[0].get('finish_reason') != 'STOP':
        raise ValueError('Exactly one completed STOP candidate required.')
    parts = candidates[0].get('content', {}).get('parts') or []
    text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
    return Action.model_validate_json(text).model_dump()


def execute(out, expected, generate):
    if sha(out/'plan.json') != expected:
        raise ValueError('Experiment plan changed.')
    plan = store._read(out/'plan.json')
    if plan['sdk_version'] != version('google-genai'):
        raise ValueError('Provider SDK changed.')
    for name, pin in plan['code_pins'].items():
        if sha(name) != pin:
            raise ValueError('Runner or dependency changed.')
    data = input_data(plan)
    if plan['generation_config'] != {'response_mime_type':'application/json', 'response_schema':data['schema']}:
        raise ValueError('Generation settings changed.')
    # A failed/interrupted launch also consumes this batch; there is no resume mode.
    store._save(out/'started.json', {'plan_sha256':expected,'started_at':now()}, exclusive=True)

    def draw(index):
        path = out/f'draw-{index:02d}.json'
        receipt = {'index':index, 'status':'pending', 'plan_sha256':expected,
                   'prompt_sha256':data['prompt_sha256'], 'started_at':now()}
        store._save(path, receipt, exclusive=True)
        try:
            raw = generate(plan, data['prompt'])
            receipt['raw_response'] = raw
            store._save(path, receipt)
            receipt.update(status='complete', response=parse_response(raw))
        except Exception as error:
            # Provider exception text may echo credentials/payloads; retain only safe fields.
            receipt.update(status='error', error={'type':type(error).__name__,
                'code':getattr(error,'code',None), 'status':getattr(error,'status',None)})
        receipt['finished_at'] = now()
        store._save(path, receipt)
        print(json.dumps({'draw':index, 'status':receipt['status'],
                         'decision':receipt.get('response',{}).get('decision')}), flush=True)

    with ThreadPoolExecutor(max_workers=plan['workers']) as pool:
        list(pool.map(draw, range(1, plan['attempts']+1)))
    result = analyse(out)
    store._save(out/'report.json', result, exclusive=True)
    return result


def analyse(out):
    plan = store._read(out/'plan.json')
    pin = sha(out/'plan.json')
    if store._read(out/'started.json')['plan_sha256'] != pin:
        raise ValueError('Plan differs from launch.')
    input_data(plan)
    records = [store._read(out/f'draw-{i:02d}.json') for i in range(1, plan['attempts']+1)]
    for i, r in enumerate(records, 1):
        if (r['index'] != i or r['plan_sha256'] != pin or r['prompt_sha256'] != plan['prompt_sha256']
                or r['status'] not in ('complete','error') or r['finished_at'] < r['started_at']):
            raise ValueError('Incomplete or mismatched draw.')
        if r['status'] == 'complete':
            if r['response'] != parse_response(r['raw_response']):
                raise ValueError('Accepted action differs from provider response.')
        elif 'response' in r:
            raise ValueError('Failed draws cannot contain an accepted action.')
    valid = [r for r in records if r['status'] == 'complete']
    counts = Counter(r['response']['decision'] for r in valid)
    usage = Counter()
    for r in records:
        usage.update({k:v for k,v in (r.get('raw_response',{}).get('usage_metadata') or {}).items()
                      if type(v) is int})
    return {'plan_sha256':pin,'model':plan['model'],'prompt_sha256':plan['prompt_sha256'],
        'attempts':len(records), 'valid':len(valid), 'failed':len(records)-len(valid),
        'actions':{key:{'count':counts[key], 'proportion':counts[key]/len(valid) if valid else None,
                       'wilson_95_marginal':wilson(counts[key],len(valid))}
                   for key in ('revise-work','reply','no-reply')},
        'unique_valid_outputs':len({store.digest(r['response']) for r in valid}),
        'responses_with_message':sum(bool(r['response']['text']) for r in valid),
        'model_versions':dict(Counter(r.get('raw_response',{}).get('model_version','unreported') for r in records)),
        'usage_totals':dict(usage), 'first_request':min(r['started_at'] for r in records),
        'last_completion':max(r['finished_at'] for r in records),
        'draw_sha256':{f'draw-{r["index"]:02d}.json':sha(out/f'draw-{r["index"]:02d}.json') for r in records},
        'interpretation':'Model sampling conditional on this one input and valid output; not real-student probabilities. Marginal intervals assume stationary independent draws.'}


def live_generate(plan, prompt):
    from google import genai
    with genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=genai.types.HttpOptions(
            timeout=plan['timeout_ms'], retry_options={'attempts':1})) as client:
        response = client.models.generate_content(model=plan['model'], contents=prompt,
                                                  config=llm.gen_config(Action))
        return response.model_dump(mode='json', exclude_none=True)


def self_test():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'input.json'
        store._save(source, {'model':'gemini-2.5-pro','prompt':'Authored fixed context.',
            'prompt_sha256':hashlib.sha256(b'Authored fixed context.').hexdigest(),
            'schema':Action.model_json_schema()})
        out = root/'run'
        prepared = prepare(source, sha(source), out)
        calls = []
        indices = count()
        def fake(plan, prompt):
            calls.append(prompt)
            index = next(indices)
            if index == 0:
                raise ValueError('Authored failure')
            if index == 1:
                return {'candidates':[{'finish_reason':'MAX_TOKENS'}]}
            if index == 2:
                return {'candidates':[{'finish_reason':'STOP','content':{'parts':[{'text':
                    '{"decision":"no-reply","text":"contradictory message","source":null}'}]}}]}
            return {'candidates':[{'finish_reason':'STOP','content':{'parts':[{'text':json.dumps(
                {'decision':'no-reply','text':'','source':None})}]}}]}
        report = execute(out, prepared['plan_sha256'], fake)
        assert len(calls) == 30 and set(calls) == {'Authored fixed context.'}
        assert (report['valid'],report['failed'],report['unique_valid_outputs']) == (27,3,1)
        assert report['actions']['no-reply']['count'] == 27
        assert report == analyse(out)
        try:
            execute(out, prepared['plan_sha256'], fake)
        except FileExistsError:
            pass
        else:
            raise AssertionError('Batch was resent.')
        assert len(calls) == 30
        saved = store._read(out/'draw-30.json')
        saved['response'] = {'decision':'reply','text':'Authored changed result.','source':None}
        store._save(out/'draw-30.json', saved)
        try:
            analyse(out)
        except ValueError:
            pass
        else:
            raise AssertionError('Provider/action disagreement accepted.')
        assert wilson(0,0) is None and abs(wilson(0,30)[1]-.1135133932) < 1e-8
        assert abs(wilson(30,30)[0]-.8864866068) < 1e-8
    print('Authored checks pass: fixed inputs, failure denominator, duplicates, intervals, replay, no resend.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare','run','report','self-test'))
    parser.add_argument('--input', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--sha256')
    args = parser.parse_args()
    if args.command == 'self-test':
        self_test()
    elif args.command == 'prepare':
        print(json.dumps(prepare(args.input, args.sha256, args.out)))
    elif args.command == 'run':
        from dotenv import load_dotenv
        load_dotenv(Path.cwd()/'.env')
        load_dotenv(Path.cwd().parent/'main/.env')
        if not os.environ.get('GEMINI_API_KEY'):
            raise SystemExit('GEMINI_API_KEY is not configured; no requests made.')
        print(json.dumps(execute(args.out, args.sha256, live_generate),indent=2))
    else:
        print(json.dumps(analyse(args.out),indent=2))
