"""Standalone cleanup must leave the workspace's visible controls callable."""
import gc
import json
from pathlib import Path
import weakref
from types import SimpleNamespace

import pytest

mo = pytest.importorskip('marimo')

from apps.student_workspace import app
from marimo._ast.app import InternalApp
from marimo._ast.compiler import compile_cell
from marimo._messaging.types import NoopStream
from marimo._plugins.ui._impl.input import button
from marimo._runtime.context import get_context, teardown_context
from marimo._runtime.context.script_context import initialize_script_context
from marimo._runtime.control_flow import MarimoStopError
from marimo._runtime.executor import Evaluator, resolve_executor
from marimo._runtime.exceptions import MarimoRuntimeException, unwrap_user_exception
from marimo._runtime.runner.hooks_post_execution import (
    _delete_local_variables, _store_reference_to_output,
)
from src.agents import notebook_tutor, tutor_context


def _buttons(output):
    if isinstance(output, button):
        yield output
    for child in getattr(output, '_live_children', ()):
        yield from _buttons(child)


@pytest.mark.parametrize('missing_packet', [False, True], ids=['loaded', 'load-error'])
def test_visible_controls_survive_standalone_cleanup(tmp_path, missing_packet):
    app._maybe_initialize()
    internal = InternalApp(app)
    source = next(cell._cell.code for _, cell in internal.cell_manager.valid_cells()
                  if 'get_view' in cell._cell.refs)
    cell = compile_cell(source, cell_id='view')
    packet = {
        'status': 'awaiting-tutor', 'decisions_remaining': 3,
        'binding': {'session_sha256': 'a' * 64, 'state_sha256': 'b' * 64},
        'task': 'Authored task', 'initialization': 'Authored context',
        'dialogue': [], 'pending_message': 'Authored question',
        'work': None, 'feedback': None, 'changes': None,
    }
    calls = []

    def snapshot(folder):
        assert folder == tmp_path
        calls.append('reload')
        return packet

    def respond(folder, *, binding, policy, send):
        assert (folder, binding, policy, send) == (
            tmp_path, packet['binding'], 'Authored policy', True)
        calls.append('respond')
        return packet | {'decisions_remaining': 2}

    initialize_script_context(internal, NoopStream(), None)
    runtime = get_context()
    try:
        with runtime.with_cell_id('inputs'):
            inputs = mo.ui.dictionary({
                'mode': mo.ui.radio({'Policy': 'policy'}, value='Policy'),
                'policy': mo.ui.text_area(value='Authored policy'),
                'reply': mo.ui.text_area(),
            })
            get_view, set_view = mo.state(
                (None, 'Authored load error') if missing_packet else (packet, ''),
                allow_self_loops=True)
        globals_ = dict(
            mo=mo, chat_mode=True, folder=tmp_path, get_view=get_view, set_view=set_view,
            advance_session=lambda *a, **k: pytest.fail('Unexpected advance'),
            respond_session=respond, snapshot_session=snapshot, scenario_picker=mo.md('Authored case'),
            send_enabled=True, tutor_inputs=inputs, tutor_context=tutor_context, library_reference=None,
            workspace_history=SimpleNamespace(render=lambda _: 'Authored saved result'))
        with runtime.with_cell_id('view'):
            result = Evaluator(executor=resolve_executor(), lifecycles=[]).evaluate_sync(cell, globals_)
        exception = result.exception
        if isinstance(exception, MarimoRuntimeException):
            exception = unwrap_user_exception(exception)
        assert (isinstance(exception, MarimoStopError) if missing_packet else exception is None), exception
        output = exception.output if missing_packet else result.output
        controls = {'reload' if 'Reload saved session' in b.text else 'continue':
                    (b._id, weakref.ref(b)) for b in _buttons(output)}
        assert set(controls) == ({'reload'} if missing_packet else {'reload', 'continue'})
        assert calls == []

        # app.run()/embed retain outputs; the standalone server instead runs these hooks.
        context = SimpleNamespace(glbls=globals_)
        _store_reference_to_output(cell, context, result)
        _delete_local_variables(cell, context, result)
        del output, result, exception
        gc.collect()
        assert all(ref() is not None for _, ref in controls.values()), 'Visible controls were collected'
        with runtime.with_cell_id('view'):
            runtime.ui_element_registry.get_object(controls['reload'][0])._update(1)
            assert get_view() == (packet, '') and calls == ['reload']
            if not missing_packet:
                runtime.ui_element_registry.get_object(controls['continue'][0])._update(1)
                assert get_view() == (packet | {'decisions_remaining': 2}, '')
                assert calls == ['reload', 'respond']
    finally:
        teardown_context()


def test_damaged_receipt_keeps_saved_results_and_reload_available(tmp_path, monkeypatch):
    from src.agents import chat_student, chat_workspace, notebook_student, workspace_history
    from src.eval.student_continuation import Continuation
    from tests.test_chat_student import QUERY, files

    folder = tmp_path / 'authored'
    initial = chat_student.create(folder, query=QUERY)
    first = chat_student.step(folder, binding=initial['binding'],
        generate=lambda *_: Continuation(decision='reply', text='Readable saved reply'))
    chat_student.step(folder, binding=first['binding'], tutor_reply='Authored tutor reply',
        generate=lambda *_: Continuation(decision='reply', text='Second saved reply'))
    path = folder / 'step-0002.json'
    receipt = notebook_student._read(path)
    del receipt['result']
    notebook_student._save(path, receipt)
    before = files(folder)
    monkeypatch.setattr(notebook_student.llm, 'make_generate',
                        lambda *_a, **_k: pytest.fail('Inspection contacted provider'))

    app._maybe_initialize()
    internal = InternalApp(app)
    cells = [cell._cell for _, cell in internal.cell_manager.valid_cells()]
    initial_cell = compile_cell(next(cell.code for cell in cells if 'get_view' in cell.defs), cell_id='initial')
    view_cell = compile_cell(next(cell.code for cell in cells if 'get_view' in cell.refs), cell_id='view')
    initialize_script_context(internal, NoopStream(), None)
    runtime = get_context()
    try:
        globals_ = dict(mo=mo, folder=folder, snapshot_session=chat_workspace.snapshot,
                       chat_mode=True, scenario_picker=mo.md('Authored case'), send_enabled=True,
                       tutor_context=tutor_context, workspace_history=workspace_history)
        evaluator = Evaluator(executor=resolve_executor(), lifecycles=[])
        with runtime.with_cell_id('initial'):
            initial_result = evaluator.evaluate_sync(initial_cell, globals_)
        exception = initial_result.exception
        if isinstance(exception, MarimoRuntimeException):
            exception = unwrap_user_exception(exception)
        assert exception is None, exception
        assert globals_['get_view']() == (None, "'result'")

        with runtime.with_cell_id('view'):
            result = evaluator.evaluate_sync(view_cell, globals_)
        exception = result.exception
        if isinstance(exception, MarimoRuntimeException):
            exception = unwrap_user_exception(exception)
        assert isinstance(exception, MarimoStopError), exception
        assert 'Readable saved reply' in exception.output.text
        assert 'unreadable or inconsistent' in exception.output.text
        controls = list(_buttons(exception.output))
        assert len(controls) == 1 and 'Reload saved session' in controls[0].text
        reload_id = controls[0]._id
        context = SimpleNamespace(glbls=globals_)
        _store_reference_to_output(view_cell, context, result)
        _delete_local_variables(view_cell, context, result)
        del controls, result, exception
        gc.collect()
        with runtime.with_cell_id('view'):
            runtime.ui_element_registry.get_object(reload_id)._update(1)
        assert globals_['get_view']() == (None, "'result'")
        assert files(folder) == before
    finally:
        teardown_context()


@pytest.mark.parametrize('with_reference', [False, True])
def test_policy_file_draft_survives_reload_and_reaches_saved_request(tmp_path, monkeypatch, with_reference):
    from src.agents import notebook_student as student, student_workspace as workspace, workspace_history
    from tests.test_notebook_session import ACTIVITY, TASK

    folder = tmp_path / 'student'
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id='authored/policy-file')
    student.step(folder, max_actions=1, check=None,
                 generate=lambda _, schema: schema(decision='reply', text='this?', source=None))
    policy_file = tmp_path / 'policy.txt'
    policy_file.write_text('Loaded instructions.\nUse one short hint.\n')
    reference = {'library': ACTIVITY['library'], 'library_version': ACTIVITY['library_version'],
                 'text': 'Authored tutor-only reference marker.', 'source': 'Authored API example.'}
    reference_file = tmp_path / 'reference.json'
    reference_file.write_text(json.dumps(reference))
    args = {'session': str(folder), 'policy-file': str(policy_file), 'send': True}
    if with_reference:
        args['reference-file'] = str(reference_file)
    monkeypatch.setattr(mo, 'cli_args', lambda: args)
    monkeypatch.setattr(student.llm, 'make_generate', lambda *a, **kw: pytest.fail('Unexpected provider'))
    app._maybe_initialize()
    internal = InternalApp(app)
    cells = [cell._cell for _, cell in internal.cell_manager.valid_cells()]
    evaluator = Evaluator(executor=resolve_executor(), lifecycles=[])
    initialize_script_context(internal, NoopStream(), None)
    runtime = get_context()
    globals_ = dict(mo=mo, Path=Path, notebook_tutor=notebook_tutor, chat_mode=False, folder=folder)
    def evaluate(definition):
        cell = compile_cell(next(c.code for c in cells if definition in c.defs), cell_id=definition)
        with runtime.with_cell_id(definition):
            result = evaluator.evaluate_sync(cell, globals_)
        assert result.exception is None, result.exception
        return result.output
    calls = []
    edited = 'Edited instructions.\nAsk one focused question.'
    def tutor(prompt, schema):
        payload = json.loads(prompt.split('POLICY AND CONTEXT JSON:\n')[1])
        assert payload.get('library_reference') == (reference if with_reference else None)
        calls.append('tutor')
        return schema(text='Which values should match?')
    def learner(prompt, schema):
        assert reference['text'] not in prompt and 'library_reference' not in prompt
        calls.append('student')
        return schema(decision='no-reply', text='', source=None)
    try:
        evaluate('chat_root')
        evaluate('tutor_inputs')
        inputs = globals_['tutor_inputs']
        assert inputs.value['policy'] == policy_file.read_text()
        inputs._update({'mode': 'Tutor policy', 'reply': '', 'policy': edited})
        with runtime.with_cell_id('state'):
            get_view, set_view = mo.state((tutor_context.snapshot(folder), ''), allow_self_loops=True)
        globals_.update(get_view=get_view, set_view=set_view, scenario_picker=None,
            snapshot_session=tutor_context.snapshot, tutor_context=tutor_context,
            workspace_history=workspace_history,
            advance_session=lambda *a, **kw: pytest.fail('Unexpected quiet continuation'),
            respond_session=lambda *a, **kw: workspace.respond(*a, **kw,
                generate_tutor=tutor, generate_student=learner, check=None))
        output = evaluate('workspace_view')
        assert calls == [] and not (folder / 'tutor-exchanges').exists()
        policy_file.write_text('Later file content; restart to load it.')
        reference_file.write_text('Later invalid content; restart to load it.')
        reload = next(b for b in _buttons(output) if 'Reload saved session' in b.text)
        with runtime.with_cell_id('event'):
            reload._update(1)
        output = evaluate('workspace_view')
        assert inputs.value['policy'] == edited and calls == []
        submit = next(b for b in _buttons(output) if 'Generate tutor reply' in b.text)
        with runtime.with_cell_id('event'):
            submit._update(1)
        assert calls == ['tutor', 'student'] and get_view()[0]['status'] == 'no-reply'
        receipt = student._read(next((folder / 'tutor-exchanges').glob('*/receipt.json')))
        assert receipt['request']['policy'] == edited
        assert receipt['request'].get('library_reference') == (reference if with_reference else None)
        assert policy_file.read_text() == 'Later file content; restart to load it.'
        globals_.update(folder=tmp_path / 'another-scenario', chat_mode=True)
        evaluate('tutor_inputs')
        assert globals_['tutor_inputs'].value['policy'] == 'Loaded instructions.\nUse one short hint.\n'
        assert calls == ['tutor', 'student']
    finally:
        teardown_context()


@pytest.mark.parametrize('kind', ['missing', 'encoding', 'invalid-json', 'invalid-schema', 'flag', 'empty-path', 'chat'])
def test_reference_file_invalid_inputs_stop_without_fallback(tmp_path, monkeypatch, kind):
    path = tmp_path / 'reference.json'
    if kind == 'encoding':
        path.write_bytes(b'\xff')
    elif kind == 'invalid-json':
        path.write_text('not JSON')
    elif kind == 'invalid-schema':
        path.write_text('{"library": "babypandas"}')
    elif kind == 'chat':
        path.write_text(json.dumps({'library': 'babypandas', 'library_version': '1.0.0',
                                    'text': 'Authored API facts.', 'source': 'Authored example.'}))
    args = {'chat-sessions' if kind == 'chat' else 'session': str(tmp_path / 'session'),
            'reference-file': True if kind == 'flag' else ' ' if kind == 'empty-path' else str(path)}
    monkeypatch.setattr(mo, 'cli_args', lambda: args)
    app._maybe_initialize()
    internal = InternalApp(app)
    cell = compile_cell(next(c._cell.code for _, c in internal.cell_manager.valid_cells()
                             if 'chat_root' in c._cell.defs), cell_id='launch')
    initialize_script_context(internal, NoopStream(), None)
    try:
        with get_context().with_cell_id('launch'):
            result = Evaluator(executor=resolve_executor(), lifecycles=[]).evaluate_sync(
                cell, dict(mo=mo, Path=Path, notebook_tutor=notebook_tutor))
        error = result.exception
        if isinstance(error, MarimoRuntimeException):
            error = unwrap_user_exception(error)
        assert isinstance(error, MarimoStopError), error
        assert 'reference' in error.output.text.lower()
    finally:
        teardown_context()


@pytest.mark.parametrize('kind', ['missing', 'blank', 'encoding', 'directory', 'flag', 'empty-path', 'default'])
def test_policy_file_invalid_inputs_stop_without_fallback(tmp_path, monkeypatch, kind):
    path = tmp_path / 'policy.txt'
    if kind == 'blank':
        path.write_text(' \n\t')
    elif kind == 'encoding':
        path.write_bytes(b'\xff')
    elif kind == 'directory':
        path.mkdir()
    args = {'session': str(tmp_path / 'session')}
    if kind != 'default':
        args['policy-file'] = True if kind == 'flag' else ' ' if kind == 'empty-path' else str(path)
    monkeypatch.setattr(mo, 'cli_args', lambda: args)
    app._maybe_initialize()
    internal = InternalApp(app)
    cell = compile_cell(next(c._cell.code for _, c in internal.cell_manager.valid_cells()
                             if 'chat_root' in c._cell.defs), cell_id='launch')
    initialize_script_context(internal, NoopStream(), None)
    try:
        globals_ = dict(mo=mo, Path=Path)
        with get_context().with_cell_id('launch'):
            result = Evaluator(executor=resolve_executor(), lifecycles=[]).evaluate_sync(cell, globals_)
        error = result.exception
        if isinstance(error, MarimoRuntimeException):
            error = unwrap_user_exception(error)
        if kind == 'default':
            assert error is None and globals_['initial_policy'] is None
            inputs_cell = compile_cell(next(c._cell.code for _, c in internal.cell_manager.valid_cells()
                                            if 'tutor_inputs' in c._cell.defs), cell_id='inputs')
            for chat_mode, expected in ((True, 'visible conversation'), (False, 'visible work and check feedback')):
                globals_.update(chat_mode=chat_mode, folder=tmp_path)
                with get_context().with_cell_id('inputs'):
                    result = Evaluator(executor=resolve_executor(), lifecycles=[]).evaluate_sync(inputs_cell, globals_)
                assert result.exception is None, result.exception
                assert expected in globals_['tutor_inputs'].value['policy']
        else:
            assert isinstance(error, MarimoStopError), error
            assert 'policy' in error.output.text.lower()
    finally:
        teardown_context()
