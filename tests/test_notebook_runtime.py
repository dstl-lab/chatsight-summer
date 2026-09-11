"""Authored controls; run the container checks with NOTEBOOK_RUNTIME_IMAGE set."""
from copy import deepcopy
import os
import subprocess
from unittest.mock import MagicMock

import pytest


def activity(library='pandas'):
    return {'image_id':os.environ.get('NOTEBOOK_RUNTIME_IMAGE','sha256:'+'a'*64),
            'library':library,'library_version':'2.3.3' if library=='pandas' else '1.0.0',
            'table':'swatches','column':'shade','result':'n_shades',
            'values':['amber','blue','amber','green']}


def test_invalid_activity_and_work_are_rejected_before_execution():
    from src.eval.notebook_runtime import check_work
    work={'source':'n_shades = 3','revision':0}
    for change in [{'image_id':'mutable:tag'},{'values':['blue',None]},
                   {'table':'__builtins__'},{'result':'swatches'}, {'library':'guessed'}]:
        with pytest.raises(ValueError):
            check_work(work,branch_id='authored',activity={**activity(),**change})
    for changed in [{**work,'revision':True},{**work,'source':None}]:
        with pytest.raises(ValueError):
            check_work(changed,branch_id='authored',activity=activity())


def test_protocol_errors_stay_ungraded_and_cleanup_survives_client_error(monkeypatch):
    import src.eval.notebook_runtime as runtime
    monkeypatch.setattr(runtime,'_local_docker',lambda image:['docker'])
    header=b'{"kind":"runtime","python":"3.13","library":"pandas","libraries":{"pandas":"2.3.3"}}\n'
    for payload in [b'[]\n',header+b'[]\n']:
        monkeypatch.setattr(runtime,'_execute',lambda *args:(0,payload,None))
        result=runtime.check_work({'source':'n_shades=3','revision':0},branch_id='authored',activity=activity())
        assert result['status']=='environment-error' and result['success'] is None
    monkeypatch.undo()

    process=MagicMock()
    process.poll.return_value=None
    process.wait.side_effect=[0,subprocess.TimeoutExpired('docker',5)]
    selector=MagicMock()
    selector.__enter__.return_value.select.return_value=[True]
    cleanup=MagicMock(return_value=subprocess.CompletedProcess([],0,b'',b''))
    monkeypatch.setattr(runtime.subprocess,'Popen',lambda *args,**kwargs:process)
    monkeypatch.setattr(runtime.selectors,'DefaultSelector',lambda:selector)
    monkeypatch.setattr(runtime.os,'read',lambda *args:b'')
    monkeypatch.setattr(runtime.subprocess,'run',cleanup)
    with pytest.raises(subprocess.TimeoutExpired):
        runtime._execute(['docker'],activity()['image_id'],{},1)
    assert cleanup.call_args.args[0][0:3]==['docker','rm','-f']


@pytest.mark.skipif(not os.environ.get('NOTEBOOK_RUNTIME_IMAGE'),reason='Explicit local container image required')
def test_declared_runtime_evaluates_source_and_preserves_error_boundaries(tmp_path):
    from src.eval.notebook_runtime import check_work, require_current
    base=activity()
    def check(source,**overrides):
        return check_work({'source':source,'revision':0},branch_id='authored',activity=overrides.pop('activity',base),**overrides)
    work={'source':"n_shades = swatches.get('shade').nunique()\nn_shades",'revision':0}
    passed=check(work['source'])
    assert passed['status']=='checked' and passed['success'] is True and passed['value']==3
    assert passed['runtime']['libraries']['pandas']=='2.3.3'
    alternate=check("values = swatches.get('shade').unique()\nn_shades = len(values)")
    assert alternate['success'] is True
    wrong=check("n_shades = len(swatches.get('shade'))")
    assert wrong['status']=='checked' and wrong['success'] is False and wrong['value']==4
    incompatible=check(work['source'],activity=activity('babypandas'))
    assert incompatible['status']=='runtime-error' and incompatible['success'] is None
    assert incompatible['error']['type']=='AttributeError'
    assert check("n_shades = len(swatches.get('shade').unique())",activity=activity('babypandas'))['success'] is True
    assert check('n_shades = (')['status']=='runtime-error'
    assert check('import sys\nsys.exit(0)')['success'] is None
    assert check('n_shades = 3',activity={**base,'library_version':'0.0.0'})['status']=='environment-error'
    limited=check('while True: pass',timeout=3)
    assert limited['status']=='execution-limit' and limited['success'] is None
    flood=check("import os\nos.write(1, b'x' * 1000000)")
    assert flood['status']=='execution-limit' and flood['success'] is None
    marker=tmp_path/'host-only'
    marker.write_text('authored marker')
    hidden=check(f"import os\nn_shades = int(os.path.exists({str(marker)!r}))")
    assert hidden['value']==0 and marker.read_text()=='authored marker'
    readonly=check("open('/host-write-test', 'w').write('x')")
    assert readonly['status']=='runtime-error'
    offline=check("import socket\ns = socket.socket()\ns.settimeout(0.2)\ns.connect(('192.0.2.1', 9))")
    assert offline['status']=='runtime-error' and offline['error']['type']=='OSError'
    require_current(passed,work,branch_id='authored',activity=base)
    with pytest.raises(ValueError,match='stale'):
        require_current(passed,work,branch_id='authored',activity=base,timeout=3)
    for branch,changed,env in [('other',work,base),('authored',{**work,'revision':1},base),
                             ('authored',{**work,'source':'n_shades=3'},base),
                             ('authored',work,{**base,'values':['amber','blue','green']}),
                             ('authored',work,{**base,'image_id':'sha256:'+'b'*64})]:
        with pytest.raises(ValueError,match='stale'):
            require_current(passed,changed,branch_id=branch,activity=env)
    changed=deepcopy(passed);changed['runtime']['python']='changed'
    with pytest.raises(ValueError):
        require_current(changed,work,branch_id='authored',activity=base)
