"""A student must retain work and evidence across a saved tutor exchange."""
from copy import deepcopy
import importlib.util
import json

import pytest

from src.eval.notebook_session import Action
from tests.test_notebook_session import TASK, ACTIVITY, observation


def api():
    assert importlib.util.find_spec('src.agents.notebook_student'), 'Continuing student is missing'
    from src.agents import notebook_student
    return notebook_student


def test_saved_student_continues_after_tutor_without_restarting_work(tmp_path):
    student = api()
    folder = tmp_path / 'learner'
    task = deepcopy(TASK)
    task['reference_future'] = 'HIDDEN_FUTURE'
    task.update(captured_at='authored timestamp', omitted='Other cells unavailable.')
    student.create(folder, task=task, activity=ACTIVITY, branch_id='synthetic/learner')
    assert json.loads((folder / 'session.json').read_text())['provenance'] == {
        'captured_at':'authored timestamp', 'omitted':'Other cells unavailable.'}
    choices = iter([
        Action(decision='revise-work', source='n_shades = 1', text='this?'),
        Action(decision='revise-work', source="n_shades = len(swatches.get('shade').unique())", text=''),
        Action(decision='request-check', source=None, text=''),
        Action(decision='reply', source=None, text='what about repeats'),
    ])
    packets = []

    def generate(prompt, model):
        assert 'HIDDEN_FUTURE' not in prompt
        packets.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return next(choices)

    first = student.step(folder, generate=generate, check=None, max_actions=3)
    assert first['stop_reason'] == 'awaiting-tutor'
    saved = student.load(folder)
    assert saved['work']['source'] == 'n_shades = 1' and saved['work']['revision'] == 1
    with pytest.raises(ValueError, match='tutor'):
        student.step(folder, generate=generate, check=None)
    second = student.step(folder, tutor_reply='Count each distinct shade once.', generate=generate,
                          check=lambda *a, **kw: observation(*a, **kw, status='checked'), max_actions=3)
    reopened = student.load(folder)
    assert second['stop_reason'] == 'awaiting-tutor' and reopened == second['state']
    assert reopened['work']['revision'] == 2 and reopened['observation']['success'] is True
    assert len(reopened['history']) == 4
    assert packets[1]['work']['source'] == 'n_shades = 1'
    assert packets[1]['dialogue'][-2:] == [
        {'role':'student', 'text':'this?', 'origin':'generated'},
        {'role':'tutor', 'text':'Count each distinct shade once.', 'origin':'supplied'},
    ]
    assert packets[2]['observation'] is None and packets[3]['observation']['success'] is True
    assert [p.name for p in folder.glob('step-*.json')] == ['step-0001.json', 'step-0002.json']
    assert student.load(folder)['message'] == 'what about repeats'


def test_budget_pause_resumes_but_chosen_stop_and_errors_do_not(tmp_path):
    student = api()
    folder = tmp_path / 'learner'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/learner')
    revise = lambda *_: Action(decision='revise-work', source='n_shades = 0', text='')
    one = student.step(folder, generate=revise, check=None, max_actions=1)
    assert one['stop_reason'] == 'action-limit' and one['state']['status'] == 'active'
    two = student.step(folder, generate=revise, check=None, max_actions=1)
    assert two['state']['work']['revision'] == 2
    stopped = student.step(folder, generate=lambda *_: Action(decision='no-reply', text='', source=None), check=None)
    assert stopped['stop_reason'] == 'no-reply' and student.load(folder)['status'] == 'no-reply'
    before = sorted(p.name for p in folder.iterdir())
    with pytest.raises(ValueError, match='terminal'):
        student.step(folder, tutor_reply='Try again.', generate=revise, check=None)
    assert sorted(p.name for p in folder.iterdir()) == before


def test_pending_error_and_changed_receipts_cannot_silently_resend(tmp_path):
    student = api()
    folder = tmp_path / 'learner'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/learner')

    def failed(prompt, model):
        receipt = json.loads((folder / 'step-0001.json').read_text())
        assert receipt['status'] == 'pending' and receipt['calls'][0]['status'] == 'pending'
        raise RuntimeError('Authored provider outage')

    result = student.step(folder, generate=failed, check=None)
    assert result['stop_reason'] == 'error' and student.load(folder) == result['state']
    path = folder / 'step-0001.json'
    receipt = json.loads(path.read_text())
    receipt['status'] = 'pending'
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='incomplete'):
        student.step(folder, generate=failed, check=None)
    receipt['status'] = 'complete'
    receipt['request']['state_sha256'] = 'changed'
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='state'):
        student.load(folder)


def test_invalid_tutor_and_budget_do_not_write_or_generate(tmp_path):
    student = api()
    folder = tmp_path / 'learner'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/learner')
    for options in ({'tutor_reply':'Unsolicited'}, {'max_actions':True}, {'max_actions':0}, {'max_actions':7}):
        with pytest.raises(ValueError):
            student.step(folder, generate=None, check=None, **options)
    assert not list(folder.glob('step-*.json'))


def test_interrupted_dispatch_stays_pending_and_session_budget_is_cumulative(tmp_path):
    student = api()
    folder = tmp_path / 'interrupted'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/interrupted')

    def interrupted(*_):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        student.step(folder, generate=interrupted, check=None)
    with pytest.raises(ValueError, match='incomplete'):
        student.load(folder)
    assert json.loads((folder / 'step-0001.json').read_text())['calls'][0]['status'] == 'pending'
    limited = tmp_path / 'limited'
    student.create(limited, task=TASK, activity=ACTIVITY, branch_id='synthetic/limited', max_decisions=1)
    result = student.step(limited, generate=lambda *_: Action(decision='revise-work', source='n_shades = 1', text=''),
                          check=None, max_actions=6)
    assert len(result['state']['history']) == 1 and result['stop_reason'] == 'action-limit'
    with pytest.raises(ValueError, match='budget exhausted'):
        student.step(limited, generate=None, check=None)
    with student._locked(limited), pytest.raises(ValueError, match='busy'):
        student.load(limited)


def test_cli_reload_carries_checked_work_and_never_sends_without_flag(tmp_path, monkeypatch, capsys):
    import sys
    from src.labeling import llm
    student = api()
    folder = tmp_path / 'cli'
    task, activity = tmp_path / 'task.json', tmp_path / 'activity.json'
    task.write_text(json.dumps(TASK))
    activity.write_text(json.dumps(ACTIVITY))
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'create', str(folder), '--task', str(task), '--activity', str(activity)])
    student.main()
    assert json.loads(capsys.readouterr().out)['stop_reason'] == 'initialized'
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'step', str(folder)])
    with pytest.raises(SystemExit) as missing_flag:
        student.main()
    assert missing_flag.value.code == 2 and not list(folder.glob('step-*.json'))
    capsys.readouterr()
    choices = iter([Action(decision='request-check', text='', source=None),
                    Action(decision='reply', text='what about repeats', source=None),
                    Action(decision='no-reply', text='', source=None)])
    prompts = []

    def generate(prompt, model):
        prompts.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return next(choices)

    monkeypatch.setenv('GEMINI_API_KEY', 'invented-test-key')
    monkeypatch.setattr(llm, 'make_generate', lambda *args, **kwargs: generate)
    monkeypatch.setattr(student.notebook_runtime, 'check_work', lambda *a, **kw: observation(*a, **kw, status='checked'))
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'step', str(folder), '--send'])
    student.main()
    first = json.loads(capsys.readouterr().out)
    assert first['status'] == 'awaiting-tutor' and first['observation']['success'] is True
    tutor = tmp_path / 'tutor.txt'
    tutor.write_text('The distinct values omit repeats.')
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'step', str(folder), '--send', '--tutor-file', str(tutor)])
    student.main()
    assert json.loads(capsys.readouterr().out)['status'] == 'no-reply'
    assert prompts[-1]['work'] == TASK['work'] and prompts[-1]['observation']['success'] is True
    assert prompts[-1]['dialogue'][-1]['text'] == tutor.read_text()
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'show', str(folder)])
    student.main()
    assert json.loads(capsys.readouterr().out)['status'] == 'no-reply' and len(prompts) == 3


@pytest.mark.parametrize('status', ['environment-error', 'execution-limit'])
def test_cli_reports_runtime_infrastructure_stops_as_failure(tmp_path, monkeypatch, status):
    import sys
    from src.labeling import llm
    student = api()
    folder = tmp_path / 'runtime-stop'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/runtime-stop')
    monkeypatch.setenv('GEMINI_API_KEY', 'invented-test-key')
    monkeypatch.setattr(llm, 'make_generate', lambda *a, **kw: lambda *_: Action(decision='request-check', text='', source=None))
    monkeypatch.setattr(student.notebook_runtime, 'check_work', lambda *a, **kw: observation(*a, **kw, status=status))
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'step', str(folder), '--send'])
    with pytest.raises(SystemExit) as stopped:
        student.main()
    assert stopped.value.code == 1 and student.load(folder)['status'] == status


def test_bound_reply_checks_state_inside_lock_before_any_write(tmp_path):
    student = api()
    folder = tmp_path / 'bound'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/bound')
    student.step(folder, generate=lambda *_: Action(decision='reply', text='this?', source=None), check=None)
    state = student.load(folder)
    manifest = json.loads((folder/'session.json').read_text())
    expected = {'expected_state_sha256':student.digest(state), 'expected_session_sha256':student.digest(manifest)}
    original = {p.name:p.read_bytes() for p in folder.iterdir()}
    for mismatch in ({'expected_state_sha256':'wrong'}, {'expected_session_sha256':'wrong'}):
        with pytest.raises(ValueError, match='[Ss]tale'):
            student.step(folder, tutor_reply='An outdated hint.', generate=None, check=None, **(expected | mismatch))
    assert {p.name:p.read_bytes() for p in folder.iterdir()} == original
    result = student.step(folder, tutor_reply='Try distinct values.',
                          generate=lambda *_: Action(decision='reply', text='where?', source=None), check=None, **expected)
    assert result['state']['dialogue'][-1]['text'] == 'Try distinct values.'
    with pytest.raises(ValueError, match='[Ss]tale'):
        student.step(folder, tutor_reply='An outdated hint.', generate=None, check=None, **expected)


@pytest.mark.parametrize('version', [1, 2])
def test_original_wrapper_can_replay_and_record_current_engine_without_rewriting_old_receipts(tmp_path, monkeypatch, version):
    student = api()
    folder = tmp_path/'v1'
    current = student._engine()
    old = student._legacy_engine(version)
    with monkeypatch.context() as patch:
        patch.setattr(student, '_engine', lambda:deepcopy(old))
        student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/v1', max_decisions=2)
        student.step(folder, generate=lambda *_: Action(decision='reply', text='check this', source=None), check=None)
    first = folder/'step-0001.json'
    receipt = json.loads(first.read_text())
    if version == 1:
        receipt.pop('engine', None)  # The original v1 receipt did not have this field.
        receipt.pop('version', None)
    else:
        receipt['version'] = 2
    first.write_text(json.dumps(receipt))
    frozen = {p.name:p.read_bytes() for p in (folder/'session.json', first)}
    assert student.load(folder)['message'] == 'check this'
    result = student.step(folder, tutor_reply='Use distinct values.',
                          generate=lambda *_: Action(decision='revise-work', text='', source='n_shades = 2'), check=None)
    assert student.load(folder) == result['state']
    assert result['state']['status'] == 'active' and result['stop_reason'] == 'action-limit'
    with pytest.raises(ValueError, match='budget exhausted'):
        student.step(folder, generate=None, check=None)
    assert json.loads((folder/'step-0002.json').read_text())['engine'] == current
    assert {p.name:p.read_bytes() for p in (folder/'session.json', first)} == frozen
    second = folder/'step-0002.json'
    accepted = json.loads(second.read_text())
    for corrupt in ({'engine':{}}, {'engine':None}, {'engine':old}, {'version':999}):
        second.write_text(json.dumps(accepted | corrupt))
        with pytest.raises(ValueError, match='engine'):
            student.load(folder)
    second.write_text(json.dumps(accepted))
    for altered in ('notebook_session.py', 'notebook_student.py'):
        changed = deepcopy(old)
        changed['sources'][altered] = 'unknown'
        assert not student._compatible_engine(changed)
