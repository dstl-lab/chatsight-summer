"""Alternative tutor replies must not change the shared work or cross session boundaries."""
from copy import deepcopy
import importlib.util
import json
import sys

import pytest

from src.agents import notebook_student as student, tutor_context
from src.eval import notebook_session as session
from tests.test_notebook_lesson import files
from tests.test_notebook_session import ACTIVITY, TASK, observation


def test_two_initial_interventions_share_only_the_start_and_preserve_inputs(tmp_path, monkeypatch, capsys):
    assert importlib.util.find_spec('src.agents.notebook_teaching_pair'), 'Teaching-pair setup is missing'
    from src.agents import notebook_teaching_pair as pair

    task = deepcopy(TASK)
    task['captured_at'] = 'PRIVATE_CAPTURE_SENTINEL'
    original = deepcopy(task)
    replies = ['Consider the distinct-value operation.', 'Use len(swatches.get("shade").unique()).']
    folder = tmp_path / 'pair'
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw: pytest.fail('Setup dispatched a model'))
    root = pair.create(folder, task=task, activity=ACTIVITY, tutor_replies=replies,
                       model='authored-model', max_decisions=3, evaluation={'expected':'PRIVATE_EXPECTED'})
    a, b = root / 'a', root / 'b'
    states = [student.load(child) for child in (a, b)]
    manifests = [student._read(child / 'session.json') for child in (a, b)]
    assert root == folder / 'sessions' and task == original
    assert states[0]['branch_id'] != states[1]['branch_id']
    assert all(m['model'] == 'authored-model' and m['max_decisions'] == 3 for m in manifests)
    for index, state in enumerate(states):
        assert state['work'] == TASK['work'] and state['activity'] == ACTIVITY
        assert state['status'] == 'active' and state['observation'] is None and state['history'] == []
        assert state['dialogue'][-1] == {'role':'tutor', 'text':replies[index], 'origin':'supplied'}
        assert state['evaluation'] == {'expected':'PRIVATE_EXPECTED'}
    prompts = [json.loads(session.make_prompt(state).split('\nSTATE JSON:\n')[1]) for state in states]
    assert prompts[0]['dialogue'][-1]['text'] != prompts[1]['dialogue'][-1]['text']
    prompts[0]['dialogue'][-1]['text'] = prompts[1]['dialogue'][-1]['text']
    assert prompts[0] == prompts[1]
    for prompt in prompts:
        encoded = json.dumps(prompt)
        assert 'PRIVATE_EXPECTED' not in encoded and 'PRIVATE_CAPTURE_SENTINEL' not in encoded
        assert 'comparison_id' not in encoded and 'condition' not in encoded
    receipt = student._read(root / 'comparison.json')
    assert receipt['status'] == 'prepared' and receipt['model_calls'] == 0
    assert receipt['max_student_decisions_total'] == 6
    for name, manifest in zip(('a','b'), manifests):
        assert receipt['sessions'][name]['manifest_sha256'] == student.digest(manifest)
        assert manifest['provenance']['teaching_pair']['condition'] == name
    before = files(root)
    with pytest.raises(FileExistsError):
        pair.create(folder, task=task, activity=ACTIVITY, tutor_replies=replies)
    assert files(root) == before
    # A check bound to A must not be accepted in B, even though initial work is equal.
    inherited = observation(states[0]['work'], **{k:states[0][k] for k in ('branch_id','activity','timeout')})
    inherited['binding'] = student.notebook_runtime._binding(states[0]['work'], states[0]['branch_id'],
        student.notebook_runtime.Activity.model_validate(ACTIVITY), states[0]['timeout'], states[0]['evaluation'])
    student.notebook_runtime.require_current(inherited, states[0]['work'], **session._check_args(states[0]))
    with pytest.raises(ValueError, match='stale'):
        session.advance(states[1], session.Action(decision='request-check', text='', source=None),
                        check=lambda *a, **kw: inherited, origin='scripted')
    # Existing saved-student and tutor-context APIs operate independently on the pair.
    student.step(a, generate=lambda *_:session.Action(decision='reply', text='what does unique do', source=None),
                 check=None, max_actions=1)
    assert tutor_context.snapshot(a)['pending_message'] == 'what does unique do'
    assert student.load(b) == states[1]
    student.step(a, tutor_reply='It keeps each distinct value once.', check=None, max_actions=1,
                 generate=lambda *_:session.Action(decision='no-reply', text='', source=None))
    student.step(b, check=None, max_actions=1,
                 generate=lambda *_:session.Action(decision='revise-work', text='', source='n_shades = 2'))
    assert student.load(a)['status'] == 'no-reply'
    assert student.load(b)['work']['source'] == 'n_shades = 2' and states[0]['work'] == TASK['work']

    for n, invalid in enumerate(([], ['one'], ['one',' '], ['one',None], ['a','b','c'])):
        bad = tmp_path / f'bad-{n}'
        with pytest.raises(ValueError):
            pair.create(bad, task=task, activity=ACTIVITY, tutor_replies=invalid)
        assert not bad.exists()
    for bad_task in (task | {'history':[]}, task | {'dialogue':[TASK['dialogue'][-1]]},
                     task | {'dialogue':list(reversed(TASK['dialogue']))}):
        with pytest.raises(ValueError):
            pair.create(tmp_path/'bad-task', task=bad_task, activity=ACTIVITY, tutor_replies=replies)
        assert not (tmp_path/'bad-task').exists()

    save = student._save
    def interrupt_second(path, value, **kwargs):
        if path.name == 'session.json' and path.parent.name == 'b':
            raise KeyboardInterrupt('Interrupted preparation of second condition')
        return save(path, value, **kwargs)
    with monkeypatch.context() as patched:
        patched.setattr(student, '_save', interrupt_second)
        with pytest.raises(KeyboardInterrupt):
            pair.create(tmp_path/'interrupted', task=task, activity=ACTIVITY, tutor_replies=replies)
    assert not (tmp_path/'interrupted').exists()

    # CLI takes authored files, creates both conditions, and has no send option.
    for name, value in (('task.json',task), ('activity.json',ACTIVITY)):
        (tmp_path/name).write_text(json.dumps(value))
    for name, value in zip(('first.txt','second.txt'), replies):
        (tmp_path/name).write_text(value)
    monkeypatch.setattr(sys, 'argv', ['notebook_teaching_pair', str(tmp_path/'cli'),
        '--task', str(tmp_path/'task.json'), '--activity', str(tmp_path/'activity.json'),
        '--first-tutor-file', str(tmp_path/'first.txt'), '--second-tutor-file', str(tmp_path/'second.txt'),
        '--max-decisions', '2'])
    pair.main()
    capsys.readouterr()
    assert student._read(tmp_path/'cli/sessions/a/session.json')['max_decisions'] == 2
