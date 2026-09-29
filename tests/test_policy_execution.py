"""Authored follow-up: deduplicate execution, freeze selection, retain raw reactions."""
import importlib.util
import json
from pathlib import Path

import pytest

from src.agents import notebook_branch as branch, notebook_student as store

ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def runner():
    path = ROOT/'experiments/2026-09-29-policy-execution/run.py'
    assert path.exists(), 'bounded policy follow-up is not implemented'
    return module(path, 'policy_execution_test')


def raw(action, finish='STOP'):
    return {'candidates':[{'finish_reason':finish,'content':{'parts':[{'text':json.dumps(action)}]}}],
            'usage_metadata':{'prompt_token_count':7,'candidates_token_count':3}}


def prepared_followup(tmp_path):
    """Reusable wholly authored comparison/probe fixture; never executes submitted code."""
    followup = runner()
    comparison = module(ROOT/'experiments/2026-09-29-notebook-policy-sampling/run.py', 'policy_original_test')
    source, original, destination = tmp_path/'source', tmp_path/'comparison', tmp_path/'followup'
    branch.create(source, recovered={'notebook':{'recorded_at':'2026-01-01T00:00:00Z','cells':[
        {'cell_type':'markdown','source':'Count the authored values.'},
        {'cell_type':'code','source':'unique_uris = 0'}]}, 'exchange':[
        {'role':'student','text':'RECORDED_STUDENT'}, {'role':'tutor','text':'ORIGINAL_TUTOR'}]},
        instruction_cells=[0], work_cell=1)
    comparison.prepare(original,source)
    counts = {'direct':0,'hint':0}
    def tutor(plan,prompt):
        return raw({'text':'DIRECT_TUTOR' if 'Answer the current student question directly' in prompt else 'HINT_TUTOR'})
    def student(plan,prompt):
        condition = 'direct' if 'DIRECT_TUTOR' in prompt else 'hint'
        counts[condition] += 1
        value = 1 if condition == 'direct' else (3 if counts[condition] in (6,7,8,9) else 2)
        return raw({'decision':'revise-work','source':f'unique_uris = {value}',
                    'text':'EDIT_MESSAGE' if condition == 'hint' else ''})
    comparison.execute(original,send=True,generate_tutor=tutor,generate_student=student)
    probe_dir = tmp_path/'probe'
    probe_dir.mkdir()
    probe_path = probe_dir/'run.py'
    probe_path.write_text('''import hashlib, json
from pathlib import Path
from types import SimpleNamespace
DATASET = {'sha256':'a'*64,'rows':3,'columns':1,'provenance':'authored fixture'}
def verify(folder): return {'status':'verified'}
def verify_image_base(command,image_id): pass
def validate_request(request):
    assert set(request)=={'source','source_sha256','result','csv_sha256'}
    assert hashlib.sha256(request['source'].encode()).hexdigest()==request['source_sha256']
    assert request['csv_sha256']==DATASET['sha256']
def parse_result(code,output,problem,image_id): return json.loads(output)
def execute(command,image_id,request,timeout):
    root=Path(__file__).parent.parent
    pending=json.loads((root/'followup'/'checks'/(request['source_sha256']+'.json')).read_text())
    assert pending['status']=='pending'
    with (root/'calls.txt').open('a') as stream: stream.write(request['source']+'\\n')
    failed=request['source']=='unique_uris = 1'
    result={'execution':'completed','status':'cell-error' if failed else 'ok','value':None if failed else 2,
            'error':{'type':'AttributeError','message':'authored missing method'} if failed else None,'output':'',
            'runtime':{'python':'3.13','libraries':{'babypandas':'1.0.0'},'image_id':image_id}}
    return 0,json.dumps(result).encode(),None
nr=SimpleNamespace(_local_docker=lambda image:['authored'],_execute=execute)
''')
    followup.prepare(destination,original,probe_path)
    return followup, original, destination, probe_path


def test_followup_executes_distinct_sources_once_and_reacts_to_first_samples(tmp_path):
    followup, original, folder, _ = prepared_followup(tmp_path)
    original_bytes = {path: path.read_bytes() for path in original.rglob('*.json')}
    plan = store._read(folder/'plan.json')['plan']
    assert plan['selected_samples'] == {'direct':1,'hint':1}
    assert len(plan['sources']) == 3
    assert followup.load(folder)['checks'] == {}
    followup.execute(folder)
    assert len((tmp_path/'calls.txt').read_text().splitlines()) == 3
    with pytest.raises(FileExistsError):
        followup.execute(folder)
    followup.prepare_reactions(folder)
    prepared = followup.load(folder)
    assert all(item['status']=='prepared' for item in prepared['reactions'].values())
    calls = []
    def generate(plan,prompt):
        name = 'direct' if 'DIRECT_TUTOR' in prompt else 'hint'
        assert store._read(folder/f'reaction-{name}.json')['status'] == 'pending'
        calls.append((plan,prompt))
        return raw({'decision':'reply','text':'What should I change?' if name=='direct' else 'Done.', 'source':None})
    with pytest.raises(ValueError,match='send'):
        followup.send(folder,generate=generate)
    result = followup.send(folder,send=True,generate=generate)
    assert len(calls) == 2
    for name,item in result['reactions'].items():
        assert item['status']=='complete' and item['sample_index']==1
        assert item['task']['work']['revision']==1 and item['applied']['work']['revision']==1
        assert item['task']['dialogue'][0]['text']=='RECORDED_STUDENT'
        assert item['task']['dialogue'][1]['text']==('DIRECT_TUTOR' if name=='direct' else 'HINT_TUTOR')
        assert item['task']['observation']['status']==('cell-error' if name=='direct' else 'ok')
        assert item['task']['history'][0]['action']['decision']=='revise-work'
        receipt = store._read(folder/f'reaction-{name}.json')
        assert receipt['raw_response']['usage_metadata']['prompt_token_count']==7
    assert result['reactions']['hint']['task']['dialogue'][-1]['text']=='EDIT_MESSAGE'
    assert all(plan['sdk_attempts']==1 and plan['model']=='gemini-2.5-pro' for plan,_ in calls)
    assert followup.load(folder)==result
    assert all(path.read_bytes()==data for path,data in original_bytes.items())
    with pytest.raises(FileExistsError):
        followup.send(folder,send=True,generate=generate)
    assert len(calls)==2 and len((tmp_path/'calls.txt').read_text().splitlines())==3
    launch = store._read(folder/'reactions-started.json')
    store._save(folder/'reactions-started.json',launch | {'status':'pending'})
    with pytest.raises(ValueError,match='completed launch'):
        followup.load(folder)
    store._save(folder/'reactions-started.json',launch)
    receipt = store._read(folder/'reaction-direct.json')
    store._save(folder/'reaction-direct.json',receipt | {'started_at':'2020-01-01T00:00:00+00:00'})
    with pytest.raises(ValueError,match='timestamps'):
        followup.load(folder)
    store._save(folder/'reaction-direct.json',receipt)
    changed = store._read(folder/'reaction-direct.json')
    changed['response']['text']='FORGED'
    store._save(folder/'reaction-direct.json',changed)
    with pytest.raises(ValueError):
        followup.load(folder)


def test_failed_provider_keeps_raw_response_and_changed_worker_result_is_rejected(tmp_path):
    followup, _, folder, _ = prepared_followup(tmp_path)
    followup.execute(folder)
    followup.prepare_reactions(folder)
    result = followup.send(folder,send=True,generate=lambda plan,prompt:raw(
        {'decision':'no-reply','text':'','source':None},finish='MAX_TOKENS'))
    assert all(item['status']=='error' for item in result['reactions'].values())
    assert all('raw_response' in store._read(folder/f'reaction-{name}.json') for name in ('direct','hint'))
    assert followup.load(folder)==result
    with pytest.raises(FileExistsError):
        followup.send(folder,send=True,generate=lambda *args:pytest.fail('resent'))
    check_path = next((folder/'checks').glob('*.json'))
    changed = store._read(check_path)
    changed['result']['value']='FORGED'
    store._save(check_path,changed)
    with pytest.raises(ValueError):
        followup.load(folder)


def test_pending_execution_cannot_resend_or_prepare_reactions(tmp_path):
    followup, _, folder, _ = prepared_followup(tmp_path)
    plan = store._read(folder/'plan.json')['plan']
    store._save(folder/'execution.json',{'status':'pending','plan_sha256':store.digest(plan),
                                       'started_at':followup.now()},exclusive=True)
    assert followup.load(folder)['checks']=={}
    with pytest.raises(FileExistsError):
        followup.execute(folder)
    with pytest.raises(ValueError):
        followup.prepare_reactions(folder)
    assert not (tmp_path/'calls.txt').exists()
