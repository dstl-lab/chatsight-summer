"""Saved starts and generated continuations must remain distinct in the lab views."""
import html
from types import SimpleNamespace

import pytest

mo = pytest.importorskip("marimo")

from marimo._ast.app import InternalApp
from marimo._ast.compiler import compile_cell
from marimo._messaging.types import NoopStream
from marimo._runtime.context import get_context, teardown_context
from marimo._runtime.context.script_context import initialize_script_context
from marimo._runtime.executor import Evaluator, resolve_executor
from src.agents import policy_comparison_setup, policy_cohort
from tests.test_policy_comparison_setup import _eligible


def _render(app, folder, saved, **bindings):
    app._maybe_initialize()
    internal = InternalApp(app)
    source = next(cell._cell.code for _, cell in internal.cell_manager.valid_cells()
                  if "get_result" in cell._cell.refs)
    cell = compile_cell(source, cell_id="view")
    initialize_script_context(internal, NoopStream(), None)
    try:
        runtime = get_context()
        with runtime.with_cell_id("view"):
            result = Evaluator(executor=resolve_executor(), lifecycles=[]).evaluate_sync(cell, {
                "mo": mo, "html": html, "get_result": lambda: (folder, saved, ""),
                "set_result": lambda *_: pytest.fail("Rendering changed saved state"),
                "history_error": "", "history_picker": None, "source_error": "",
                "policy_comparison_setup": policy_comparison_setup,
                "policy_inputs": {"current": mo.md("Current policy"),
                                  "proposed": mo.md("Proposed policy")},
                "send_enabled": False, "workspace_path": folder.parent,
                **bindings,
            })
        assert result.exception is None, result.exception
        return result.output.text
    finally:
        teardown_context()


@pytest.mark.parametrize("decision", [None, "reply", "no-reply"])
def test_simulation_distinguishes_cached_start_from_generated_followup(tmp_path, decision):
    from apps.policy_simulation_lab import app

    source, folder = tmp_path / "source", tmp_path / "run-0001"
    _eligible(source)
    saved = policy_comparison_setup.freeze(
        folder, source=source, current_policy="Current", proposed_policy="Proposed")
    if decision is not None:
        saved = policy_comparison_setup.run_both(
            folder, send=True,
            generate_tutor=lambda _prompt, schema: schema(text="Authored tutor reply"),
            generate_student=lambda _prompt, schema: schema(
                decision=decision, text="Authored follow-up" if decision == "reply" else ""),
        )

    rendered = _render(app, folder, saved, source_picker=None)

    assert "Authored pending message" in rendered
    assert "Shared simulated starting question" in rendered
    if decision is None:
        assert "Frozen and ready; this condition has not been generated." in rendered
        assert "Simulated follow-up" not in rendered
        assert "chose not to send a follow-up" not in rendered
    else:
        assert "Authored tutor reply" in rendered
        assert "Frozen and ready" not in rendered
        if decision == "reply":
            assert "Simulated follow-up" in rendered and "Authored follow-up" in rendered
        else:
            assert "chose not to send a follow-up" in rendered
    assert "No simulated starting question was saved" not in rendered
    assert "Recorded context" not in rendered


def test_cohort_can_show_shared_start_from_valid_b_when_a_cannot_load(tmp_path):
    from apps.policy_cohort_lab import app

    source, folder = tmp_path / "source", tmp_path / "cohort-0001"
    _eligible(source)
    saved = policy_cohort.create(
        folder, sources=[source], current_policy="Current", proposed_policy="Proposed")
    case = saved["cases"][0]
    case["comparison"]["conditions"]["a"].update(
        snapshot=None, error="Saved A is damaged.", lifecycle="failed")
    case["outcomes"]["a"] = "failed"
    saved["summary"]["conditions"]["a"].update(ready=0, failed=1)

    rendered = _render(
        app, folder, saved, available_sources={}, source_selector=None,
        policy_cohort=SimpleNamespace(show=lambda _: saved),
    )

    assert "Saved A is damaged." in rendered
    assert "Authored pending message" in rendered
    assert "Shared simulated starting question" in rendered
    assert "No starting question was available" not in rendered
    assert "Recorded context" not in rendered
    assert "total provider requests" not in rendered
