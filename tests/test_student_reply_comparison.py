"""Invented saved outputs test joins, immutable evidence and exact text display."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from src.eval.student_training import messages


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def repin(folder):
    """Author new, internally consistent closures for semantic-tamper tests."""
    cohort, adapter = read(folder/'cohort-manifest.json'), read(folder/'adapter-manifest.json')
    first = cohort['cases'][0]['key']
    cohort['pins'] = read(folder/f'calls/{first}/base/result.json')['model_identity']['files']
    save(folder/'cohort-manifest.json', cohort)
    cohort_files = {'manifest.json': digest(folder/'cohort-manifest.json')}
    adapter_files = {}
    for case in cohort['cases']:
        key = case['key']
        for arm, prefix, files in [('base', f'calls/{key}/01-starting/01-student', cohort_files),
                                  ('full', f'calls/{key}/01-student', adapter_files)]:
            for name in ('request.json', 'result.json', 'invocation.json'):
                files[f'{prefix}/{name}'] = digest(folder/f'calls/{key}/{arm}/{name}')
        call = next(c for c in adapter['calls'] if c['case']==key)
        call['request_sha256'] = digest(folder/f'calls/{key}/full/request.json')
        call['cached_result_sha256'] = 'c'*64
        cohort_files[f'calls/{key}/02-trained/01-student/request.json'] = call['request_sha256']
        cohort_files[f'calls/{key}/02-trained/01-student/result.json'] = call['cached_result_sha256']
    save(folder/'cohort-completion.json', {'status':'closed', 'files':cohort_files})
    adapter['pins'] = {**read(folder/f'calls/{first}/full/result.json')['model_identity']['files'],
                      '/never/open/local-conversation-cohort-v1/manifest.json': digest(folder/'cohort-manifest.json'),
                      '/never/open/local-conversation-cohort-v1/completion.json': digest(folder/'cohort-completion.json')}
    save(folder/'adapter-manifest.json', adapter)
    adapter_files['manifest.json'] = digest(folder/'adapter-manifest.json')
    save(folder/'adapter-completion.json', {'status':'closed', 'files':adapter_files})
    names = ['cohort-manifest.json','cohort-completion.json','adapter-manifest.json','adapter-completion.json']
    names += [f'calls/{c["key"]}/{arm}/{name}' for c in cohort['cases'] for arm in ('base','full')
              for name in ('request.json','result.json','invocation.json')]
    save(folder/'closure.json', {'version':1, 'files':{name:digest(folder/name) for name in names}})


def write_bundle(tmp_path):
    """Browser tests may reuse this real-file fixture; no models or remote files."""
    folder = tmp_path/'student-comparison'
    cases, calls = [], []
    base_identity = {'base':{'repo_id':'authored/model','revision':'authored-revision'},
        'model_path':'/never/open/model', 'adapter':False, 'adapter_path':None,
        'files':{'/never/open/model/config.json':'a'*64, '/never/open/model/model.safetensors':'b'*64},
        'packages':{'mlx':'authored','transformers':'authored'},
        'training_preparation_sha256':'1'*64, 'training_receipt_sha256':'2'*64}
    for number in (1, 2):
        key = f'case-{number:02}'
        query = {'id':f'query-{number}', 'conversation_id':f'conversation-{number}', 'student_id':None,
            'prefix':[{'role':'student','text':'Earlier question.'}, {'role':'tutor','text':'Earlier hint.'},
                      {'role':'student','text':f'  α{number}\n\nwhy?'}, {'role':'tutor','text':'Try <script>inert</script>.'}]}
        cases.append({'key':key,'ordinal':number,'query':query,'prompt_tokens':3})
        calls.append({'key':f'{key}/01-student','case':key,'position':1,
            'source':f'/never/open/local-conversation-cohort-v1/calls/{key}/02-trained/01-student'})
        for arm in ('base','full'):
            path = folder/f'calls/{key}/{arm}'
            request = {'role':'student','adapter':arm=='full','seed':number,'max_tokens':256,
                       'prefix':query['prefix'],'messages':messages(query['prefix']),'harness_prompt':'legacy metadata'}
            save(path/'request.json', request)
            identity = deepcopy(base_identity)
            if arm=='full':
                identity.update(adapter=True,adapter_path='/never/open/full/run',
                    training_preparation_sha256='3'*64,training_receipt_sha256='4'*64,
                    training_closure_sha256='5'*64)
                identity['files'].update({'/never/open/full/run/adapters.safetensors':'d'*64,
                                          '/never/open/full/run/adapter_config.json':'e'*64})
            save(path/'result.json', {'status':'complete','role':'student','adapter':arm=='full',
                'seed':number,'max_tokens':256,'text':f'  {arm} {number}\n\n<literal>\n',
                'finish_reason':'stop','prompt_tokens':[1,2,3], 'generated_token_ids':[8,9],
                'generation_tokens':2,'eos_token_ids':[9], 'request_sha256':digest(path/'request.json'),
                'settings':{'temperature':.7,'top_p':.8,'top_k':20,'enable_thinking':False,
                    'context_limit':4096,'memory_limit_bytes':16*1024**3,'prefill_step_size':256},
                'model_identity':identity})
            save(path/'invocation.json', {'status':'returned','returncode':0,'timeout_seconds':120,'elapsed_seconds':1})
    save(folder/'cohort-manifest.json', {'cases':cases,'pins':{}})
    save(folder/'adapter-manifest.json', {'cases':cases,'calls':calls,'pins':{}})
    repin(folder)
    return folder


def test_saved_replies_share_exact_context_without_writes_or_source_path_access(tmp_path):
    from src.eval import student_reply_comparison as reader

    folder = write_bundle(tmp_path)
    before = {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in folder.rglob('*') if p.is_file()}
    packet = reader.load_comparison(folder, expected_files=reader.evidence_hashes(folder))
    assert packet['kind']=='saved-student-reply-comparison'
    assert packet['study']['cases']==2 and packet['study']['saved_replies']==4
    first = packet['cases'][0]
    assert first['prefix']=={'context':[{'role':'student','text':'Earlier question.'},{'role':'tutor','text':'Earlier hint.'}],
        'turns':[{'role':'student','text':'  α1\n\nwhy?'},{'role':'tutor','text':'Try <script>inert</script>.'}]}
    assert [(c['id'],c['status'],c['text']) for c in first['conditions']]==[
        ('base','reply','  base 1\n\n<literal>\n'),('full','reply','  full 1\n\n<literal>\n')]
    assert [c['model_details']['adapter'] for c in first['conditions']]==[False,True]
    assert '/never/open' not in json.dumps(packet)
    assert {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in folder.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('change', ['prefix','seed','prompt_tokens','base_identity','target','position'])
def test_rehashed_but_incomparable_evidence_is_rejected(tmp_path, change):
    from src.eval import student_reply_comparison as reader

    folder = write_bundle(tmp_path)
    path = folder/'calls/case-01/full'
    request, result = read(path/'request.json'), read(path/'result.json')
    if change=='prefix':
        request['prefix'][2]['text']='different recorded request'
        request['messages']=messages(request['prefix'])
    elif change=='seed':
        request['seed']=result['seed']=999
    elif change=='prompt_tokens':
        result['prompt_tokens']=[1,2,4]
    elif change=='base_identity':
        result['model_identity']['files']['/never/open/model/model.safetensors']='f'*64
    elif change=='target':
        for name in ('cohort-manifest.json','adapter-manifest.json'):
            value=read(folder/name);value['cases'][0]['query']['response']='must not be supplied'
            save(folder/name,value)
    else:
        value=read(folder/'adapter-manifest.json');value['calls'][0]['position']=2
        save(folder/'adapter-manifest.json',value)
    save(path/'request.json',request);result['request_sha256']=digest(path/'request.json')
    save(path/'result.json',result);repin(folder)
    with pytest.raises(ValueError):
        reader.load_comparison(folder)


def test_hash_changes_startup_rebinding_and_symlinks_fail_closed(tmp_path):
    from src.eval import student_reply_comparison as reader

    folder=write_bundle(tmp_path);pin=reader.evidence_hashes(folder)
    path=folder/'calls/case-01/base/result.json';value=read(path);value['text']='changed'
    save(path,value)
    with pytest.raises(ValueError):reader.load_comparison(folder)
    repin(folder)
    with pytest.raises(ValueError):reader.load_comparison(folder,expected_files=pin)
    outside=tmp_path/'outside.json';outside.write_bytes(path.read_bytes())
    path.unlink();path.symlink_to(outside)
    with pytest.raises(ValueError):reader.evidence_hashes(folder)


def test_source_closure_and_exact_local_inventory_are_required(tmp_path):
    from src.eval import student_reply_comparison as reader

    folder=write_bundle(tmp_path)
    closure=read(folder/'adapter-completion.json');closure['files']['manifest.json']='f'*64
    save(folder/'adapter-completion.json',closure)
    bundle=read(folder/'closure.json');bundle['files']['adapter-completion.json']=digest(folder/'adapter-completion.json')
    save(folder/'closure.json',bundle)
    with pytest.raises(ValueError):reader.load_comparison(folder)
    repin(folder);bundle=read(folder/'closure.json');bundle['files']['../outside.json']='a'*64
    save(folder/'closure.json',bundle)
    with pytest.raises(ValueError):reader.load_comparison(folder)


@pytest.mark.parametrize('change', ['adapter_weight', 'training_receipt'])
def test_one_model_label_cannot_mix_adapter_identities_across_cases(tmp_path, change):
    from src.eval import student_reply_comparison as reader

    folder = write_bundle(tmp_path)
    path = folder/'calls/case-02/full/result.json'
    result = read(path)
    if change == 'adapter_weight':
        result['model_identity']['files']['/never/open/full/run/adapters.safetensors'] = 'f'*64
    else:
        result['model_identity']['training_receipt_sha256'] = 'f'*64
    save(path, result)
    repin(folder)
    with pytest.raises(ValueError):
        reader.load_comparison(folder)
