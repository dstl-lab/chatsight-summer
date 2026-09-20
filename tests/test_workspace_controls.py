"""Standalone cleanup must leave the workspace's visible controls callable."""
import gc
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
from src.agents import tutor_context


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
            send_enabled=True, tutor_inputs=inputs, tutor_context=tutor_context,
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
