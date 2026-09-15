"""Authored lifecycle controls; the actual container has its own integration check."""
from copy import deepcopy
import json

import pytest
from src.eval import notebook_runtime as nr
from src.eval.student_continuation import _digest

ACTIVITY = {'image_id':'sha256:'+'a'*64,'library':'babypandas','library_version':'1.0.0',
            'table':'swatches','column':'shade','result':'n_shades','values':['red','red','blue']}
TASK = {'initialization':'Invented work and dialogue.', 'task':'Count distinct shades.',
        'work':{'cell_index':1,'source':"n_shades=swatches.get('shade').nunique()",'revision':0},
        'dialogue':[{'role':'student','text':'why wont this run'},
                    {'role':'tutor','text':'Check the distinct-value operation in this library.'}]}


def observation(work, *, branch_id, activity, timeout, status='runtime-error'):
    runtime={'image_id':activity['image_id'],'python':'test','library':activity['library'],
             'libraries':{activity['library']:activity['library_version']}}
    return {'binding':nr._binding(work,branch_id,nr.Activity.model_validate(activity),timeout),
            'status':status,'basis':'container','execution':'completed','runtime':runtime,
            'runtime_sha256':_digest(runtime),'success':True if status=='checked' else None,
            'value':2 if status=='checked' else None, 'output':'',
            'error':{'type':'AttributeError','message':'Authored test error.'} if status=='runtime-error' else None}


def test_runtime_feedback_follows_requested_checks_and_revisions():
    from src.eval.notebook_session import Action, initial_state, make_prompt, advance
    state=initial_state(TASK,activity=ACTIVITY,branch_id='authored/draw-1')
    before=deepcopy(state)
    request=Action(decision='request-check',text='',source=None)
    state=advance(state,request,origin='scripted',check=observation)
    packet=json.loads(make_prompt(state).split('\nSTATE JSON:\n')[1])
    assert packet['activity']['library']=='babypandas' and packet['observation']['status']=='runtime-error'
    assert packet['observation']['success'] is None and 'image_id' not in json.dumps(packet)
    assert state['history'][0]['origin']=='scripted' and before['observation'] is None
    source="n_shades=len(swatches.get('shade').unique())"
    state=advance(state,Action(decision='revise-work',text='',source=source),origin='model',check=None)
    assert state['work']['revision']==1 and state['observation'] is None and state['status']=='active'
    assert state['history'][0]['observation']['binding']['revision']==0
    state=advance(state,request,origin='model',check=lambda *a,**kw:observation(*a,**kw,status='checked'))
    assert state['observation']['success'] is True
    state=advance(state,Action(decision='no-reply',text='',source=None),origin='model',check=None)
    assert state['status']=='no-reply' and state['message'] is None
    with pytest.raises(ValueError,match='terminal'):
        make_prompt(state)
    with pytest.raises(ValueError,match='terminal'):
        advance(state,request,origin='model',check=observation)
    assert initial_state({**TASK,'reference':'HIDDEN_FUTURE'},activity=ACTIVITY,branch_id='authored/draw-1')==before


def test_bad_checks_stop_or_reject_without_inventing_student_outcomes():
    from src.eval.notebook_session import Action, initial_state, advance, make_prompt
    start=initial_state(TASK,activity=ACTIVITY,branch_id='authored/draw-2')
    request=Action(decision='request-check',text='',source=None)
    for status in ('environment-error','execution-limit'):
        result=advance(start,request,origin='model',check=lambda *a,**kw:observation(*a,**kw,status=status))
        assert result['status']==status and result['message'] is None and result['observation']['success'] is None
    for change in ({'success':True},{'status':'unknown'}):
        with pytest.raises(ValueError):
            advance(start,request,origin='model',check=lambda *a,**kw:{**observation(*a,**kw),**change})
    for change in ({'basis':'scenario'}, {'execution':'not-started'}, {'runtime':None,'runtime_sha256':None}):
        with pytest.raises(ValueError):
            advance(start,request,origin='model',check=lambda *a,**kw:{**observation(*a,**kw,status='checked'),**change})
    stale=observation(TASK['work'],branch_id='other',activity=ACTIVITY,timeout=10)
    with pytest.raises(ValueError,match='stale'):
        advance(start,request,origin='model',check=lambda *a,**kw:stale)
    checked=advance(start,request,origin='model',check=observation)
    checked['work']['revision']+=1
    with pytest.raises(ValueError,match='stale'):
        make_prompt(checked)
    reply=advance(start,Action(decision='reply',text='passed',source=None),origin='model',check=None)
    assert reply['observation'] is None and reply['work']==start['work'] and reply['status']=='awaiting-tutor'
    edit=advance(start,Action(decision='revise-work',text='check this?',source=''),origin='model',check=None)
    assert edit['work']['source']=='' and edit['work']['revision']==1 and edit['status']=='awaiting-tutor'
    assert start['observation'] is None and start['history']==[]
