"""Only authored data and invented code identifiers are used here."""
from copy import deepcopy
import json

import pytest

FIXTURE = {'table':'paint','column':'color','result':'n_colors',
           'values':['red','blue','red','green'],'expected':3}
TASK = {'initialization':'Invented branch', 'task':[{'source':'Count distinct paint colors.'}],
        'work':{'cell_index':1,'source':"n_colors = len(paint.get('color'))\nn_colors",'revision':0},
        'dialogue':[{'role':'student','text':'count?'},{'role':'tutor','text':'Repeated colors count once.'}]}


def test_requested_check_edit_and_chat_follow_current_work():
    from src.eval.notebook_check import run
    task=deepcopy(TASK); before=deepcopy(task)
    actions=[dict(decision='request-check',text='',source=None),
             dict(decision='revise-work',text='',source="n_colors = len(paint.get('color').unique())\nn_colors"),
             dict(decision='request-check',text='',source=None),
             dict(decision='reply',text='what about empty colors?',source=None)]
    packets=[]
    def generate(prompt,model):
        packets.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return model.model_validate(actions[len(packets)-1])
    result=run(task,fixture=FIXTURE,generate=generate)
    assert packets[0]['observation'] is None
    assert packets[1]['observation']['success'] is False
    assert packets[1]['observation']['actual']==4
    assert packets[2]['observation'] is None and packets[2]['work']['revision']==1
    assert packets[2]['history'][0]['observation']['binding']['revision']==0
    assert packets[3]['observation']['success'] is True and packets[3]['observation']['actual']==3
    assert result['status']=='awaiting-tutor' and result['message']=='what about empty colors?'
    assert result['work']['revision']==1 and task==before


def test_stale_feedback_and_unsupported_source_do_not_become_a_grade(tmp_path):
    from src.eval.notebook_check import check_work, require_current
    work=deepcopy(TASK['work'])
    observation=check_work(work,branch_id='invented',fixture=FIXTURE)
    for changed in [{**work,'revision':1},{**work,'source':'changed'}]:
        with pytest.raises(ValueError,match='stale'):
            require_current(observation,changed,branch_id='invented',fixture=FIXTURE)
    for branch,fixture in [('different',FIXTURE),('invented',{**FIXTURE,'values':['x','y','z']})]:
        with pytest.raises(ValueError,match='stale'):
            require_current(observation,work,branch_id=branch,fixture=fixture)
    marker=tmp_path/'must-not-exist'
    for source in [f"open({str(marker)!r}, 'w').write('bad')",'n_colors = __import__("os").system("true")','broken(']:
        result=check_work({**work,'source':source},branch_id='invented',fixture=FIXTURE)
        assert result['status']=='unavailable' and result['success'] is None and result['actual'] is None
    assert not marker.exists()


def test_unrequested_checks_and_invalid_actions_do_not_create_feedback():
    from src.eval.notebook_check import Action, run
    result=run(TASK,fixture=FIXTURE,generate=lambda _,model:model(decision='reply',text='passed',source=None))
    assert result['observation'] is None and result['work']==TASK['work']
    assert result['events'][0]['action']['text']=='passed'
    for action in [dict(decision='request-check',text='check it',source=None),
                   dict(decision='request-check',text='',source='new work')]:
        with pytest.raises(ValueError):Action.model_validate(action)


def test_reference_metadata_cannot_change_later_prompts():
    from src.eval.notebook_check import run
    def collect(task):
        prompts=[]
        def generate(prompt,model):
            prompts.append(prompt)
            return model(decision='request-check' if len(prompts)==1 else 'no-reply',text='',source=None)
        run(task,fixture=FIXTURE,generate=generate)
        return prompts
    changed=deepcopy(TASK)
    changed['reference']={'future':'HIDDEN_FUTURE'}
    assert collect(changed)==collect(TASK)


def test_edit_can_end_silently_or_with_accompanying_chat():
    from src.eval.notebook_check import run
    for text in ('','check this?'):
        calls=[]
        def generate(prompt,model):
            calls.append(prompt)
            return model(decision='revise-work',text=text,source='') if len(calls)==1 else model(decision='no-reply',text='',source=None)
        result=run(TASK,fixture=FIXTURE,generate=generate)
        assert result['work']['source']=='' and result['work']['revision']==1
        assert result['message']==(text or None) and result['observation'] is None
        assert result['status']==('awaiting-tutor' if text else 'no-reply')
        assert len(calls)==(1 if text else 2)
