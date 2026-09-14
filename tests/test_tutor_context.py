"""Tutor handoffs expose saved evidence and reject stale replies before dispatch."""
from copy import deepcopy
import importlib.util
import json
import sys

import pytest

from src.agents import notebook_student as student
from src.eval.notebook_session import Action
from tests.test_notebook_session import TASK, ACTIVITY, observation


def api():
    assert importlib.util.find_spec('src.agents.tutor_context'), 'Tutor context adapter is missing'
    from src.agents import tutor_context
    return tutor_context


def choose(folder, decision, *, text='', source=None, tutor_reply=None, check=None):
    return student.step(folder, generate=lambda *_: Action(decision=decision, text=text, source=source),
                        check=check, tutor_reply=tutor_reply, max_actions=1)


def files(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()}


def test_snapshot_has_current_work_valid_feedback_and_one_pending_message(tmp_path):
    context = api()
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/context')
    choose(folder, 'revise-work', source='n_shades = 2')
    first = context.snapshot(folder)
    assert first['work']['revision'] == 1 and first['feedback'] is None
    assert first['changes']['baseline_kind'] == 'initial-work'
    assert first['changes']['baseline_revision'] == 0 and first['changes']['baseline_source'] == TASK['work']['source']
    assert first['pending_message'] is None
    choose(folder, 'request-check', check=lambda *a, **kw: observation(*a, **kw, status='checked'))
    checked = context.snapshot(folder)
    assert checked['feedback'] == {'status':'checked', 'success':True, 'value':2, 'error':None, 'output':''}
    assert 'image_id' not in checked['activity'] and checked['activity']['library'] == ACTIVITY['library']
    pending = 'PENDING ``` question'
    source = '# ```` literal fence\nn_shades = 3'
    choose(folder, 'revise-work', source=source, text=pending)
    before = files(folder)
    packet = context.snapshot(folder)
    assert files(folder) == before
    assert packet['status'] == 'awaiting-tutor' and packet['decisions_remaining'] == 9
    assert packet['task'] == TASK['task'] and packet['work'] == {'cell_index':1, 'source':source, 'revision':2}
    assert packet['feedback'] is None and packet['pending_message'] == pending
    assert packet['dialogue'] == TASK['dialogue'] and pending not in json.dumps(packet['dialogue'])
    assert packet['version'] == 1 and packet['sha256'] == student.digest({key:value for key,value in packet.items() if key != 'sha256'})
    assert packet['binding'] == {'session_sha256':student.digest(json.loads((folder/'session.json').read_text())),
                                 'state_sha256':student.digest(student.load(folder))}
    rendered = context.render(packet)
    assert rendered.count(pending) == 1 and source in rendered and '`````' in rendered
    choose(folder, 'request-check', tutor_reply='Run the current revision.', check=lambda *a, **kw:
           observation(*a, **kw, status='environment-error') | {
               'error':{'type':'CalledProcessError', 'message':'PRIVATE_DOCKER_COMMAND'}})
    terminal = context.snapshot(folder)
    assert terminal['feedback']['success'] is None and terminal['feedback']['status'] == 'environment-error'
    assert 'PRIVATE_DOCKER_COMMAND' not in context.render(terminal)
    assert 'PRIVATE_DOCKER_COMMAND' in json.dumps(student.load(folder)['observation'])


def test_diff_uses_work_before_last_tutor_even_across_budget_pauses(tmp_path):
    context = api()
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/diff')
    baseline = 'n_shades = 1'
    choose(folder, 'revise-work', source=baseline)
    choose(folder, 'reply', text='What next?')
    tutor = 'Use the distinct values.\nKeep this exact newline.\n'
    choose(folder, 'revise-work', source='n_shades = 2', tutor_reply=tutor)
    choose(folder, 'revise-work', source='n_shades = 3', text='CURRENT question')
    packet = context.snapshot(folder)
    assert packet['changes']['baseline_kind'] == 'before-most-recent-supplied-tutor'
    assert packet['changes']['baseline_revision'] == 1 and packet['changes']['baseline_source'] == baseline
    assert packet['work']['revision'] == 3 and packet['decisions_remaining'] == 8
    diff = packet['changes']['unified_diff']
    assert '-n_shades = 1' in diff and '+n_shades = 3' in diff and 'n_shades = 2' not in diff
    assert packet['dialogue'][-2:] == [
        {'role':'student', 'text':'What next?', 'origin':'generated'},
        {'role':'tutor', 'text':tutor, 'origin':'supplied'}]
    assert context.render(packet).count('CURRENT question') == 1


def test_export_is_create_only_and_handoff_hash_and_binding_are_verified(tmp_path, monkeypatch, capsys):
    context = api()
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/export')
    choose(folder, 'reply', text='Exported question')
    packet = context.snapshot(folder)
    before = files(folder)
    destination = tmp_path / 'handoff.json'
    monkeypatch.setattr(sys, 'argv', ['tutor_context', str(folder), '--output', str(destination)])
    context.main()
    assert context.read_handoff(destination) == packet
    assert capsys.readouterr().out.strip() == context.render(packet).strip()
    assert files(folder) == before
    original = destination.read_bytes()
    for change in ({'pending_message':'Changed question'}, {'version':2}):
        destination.write_text(json.dumps(packet | change))
        with pytest.raises(ValueError):
            context.read_handoff(destination)
    for binding in ({'session_sha256':packet['binding']['session_sha256']},
                    {'session_sha256':'short', 'state_sha256':packet['binding']['state_sha256']}):
        changed = deepcopy(packet)
        changed['binding'] = binding
        changed['sha256'] = student.digest({key:value for key,value in changed.items() if key != 'sha256'})
        destination.write_text(json.dumps(changed))
        with pytest.raises(ValueError):
            context.read_handoff(destination)
    destination.write_bytes(original)
    assert context.read_handoff(destination) == packet
    destination.write_text('Human edit: do not replace.')
    with pytest.raises((FileExistsError, ValueError)):
        context.main()
    assert destination.read_text() == 'Human edit: do not replace.' and files(folder) == before


@pytest.mark.parametrize('mismatch', ['stale-state', 'other-session'])
def test_bound_cli_rejects_stale_or_other_session_without_write_or_dispatch(tmp_path, monkeypatch, mismatch):
    context = api()
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/bound')
    choose(folder, 'reply', text='Same pending question')
    packet = context.snapshot(folder)
    handoff = tmp_path / 'handoff.json'
    handoff.write_text(json.dumps(packet))
    if mismatch == 'stale-state':
        choose(folder, 'reply', text='A newer pending question', tutor_reply='An already accepted tutor reply.')
    else:
        other = tmp_path / 'other'
        # Identical current state but a different manifest isolates the session binding.
        student.create(other, task=TASK, activity=ACTIVITY, branch_id='synthetic/bound', max_decisions=11)
        choose(other, 'reply', text='Same pending question')
        assert student.load(other) == student.load(folder)
        folder = other
    tutor = tmp_path / 'tutor.txt'
    tutor.write_text('This reply belongs to the exported context.\n')
    before = files(folder)
    dispatched = []

    def forbidden(*args, **kwargs):
        dispatched.append(True)
        raise AssertionError('Stale context must be rejected before dispatch.')

    monkeypatch.setattr(student.llm, 'make_generate', forbidden)
    monkeypatch.setattr(student.notebook_runtime, 'check_work', forbidden)
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'step', str(folder), '--send',
                                    '--context-file', str(handoff), '--tutor-file', str(tutor)])
    with pytest.raises(ValueError, match='[Ss]tale'):
        student.main()
    assert dispatched == [] and files(folder) == before


def test_exported_context_accepts_exact_tutor_reply_and_keeps_work_across_cli_step(tmp_path, monkeypatch, capsys):
    context = api()
    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='synthetic/cli')
    choose(folder, 'revise-work', source='n_shades = 1', text='this?')
    packet = context.snapshot(folder)
    handoff = tmp_path / 'handoff.json'
    student._save(handoff, packet, exclusive=True)
    tutor = tmp_path / 'tutor.txt'
    tutor.write_text('Count each shade once.\nUse unique values.\n', encoding='utf-8')
    prompts = []

    def generate(prompt, schema):
        prompts.append(json.loads(prompt.split('\nSTATE JSON:\n')[1]))
        return Action(decision='revise-work', source='n_shades = 2', text='')

    monkeypatch.setenv('GEMINI_API_KEY', 'invented-test-key')
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw:generate)
    monkeypatch.setattr(sys, 'argv', ['notebook_student', 'step', str(folder), '--send', '--max-actions', '1',
                                    '--context-file', str(handoff), '--tutor-file', str(tutor)])
    student.main()
    assert json.loads(capsys.readouterr().out)['stop_reason'] == 'action-limit'
    assert len(prompts) == 1 and prompts[0]['work'] == packet['work']
    assert prompts[0]['dialogue'][-2:] == [
        {'role':'student', 'text':'this?', 'origin':'generated'},
        {'role':'tutor', 'text':tutor.read_text(), 'origin':'supplied'}]
    saved = student.load(folder)
    assert saved['work']['revision'] == 2 and saved['observation'] is None
    assert saved['dialogue'] == prompts[0]['dialogue']
    receipt = student._read(folder / 'step-0002.json')
    assert all(receipt['request'][key] == value for key,value in packet['binding'].items())
    for args in (['show', str(folder)], ['step', str(folder), '--send']):
        monkeypatch.setattr(sys, 'argv', ['notebook_student', *args, '--context-file', str(handoff)])
        with pytest.raises(SystemExit) as invalid:
            student.main()
        assert invalid.value.code == 2 and len(prompts) == 1
