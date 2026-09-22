import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Set up tutor policy comparison")


@app.cell
def _():
    import html
    from pathlib import Path
    import marimo as mo
    from src.agents import policy_comparison_setup
    return Path, html, mo, policy_comparison_setup


@app.cell
def _(Path, mo):
    _args = mo.cli_args()
    _sources = _args.get("sources")
    _output = _args.get("output")
    mo.stop(
        not isinstance(_sources, str) or not _sources.strip()
        or not isinstance(_output, str) or not _output.strip(),
        mo.callout("Open with --sources /path/to/sessions --output /path/to/new/comparison.", kind="warn"),
    )
    source_root = Path(_sources).resolve()
    output_path = Path(_output).resolve()
    send_enabled = _args.get("send") is True
    return output_path, send_enabled, source_root


@app.cell
def _(mo, policy_comparison_setup, source_root):
    try:
        _sources = policy_comparison_setup.sources(source_root)
        source_error = ""
    except OSError as _exc:
        _sources, source_error = {}, str(_exc)
    source_picker = (
        mo.ui.dropdown(_sources, value=next(iter(_sources)), allow_select_none=False,
                       label="Saved conversation scenario")
        if _sources else None
    )
    return source_error, source_picker


@app.cell
def _(mo):
    from src.agents.policy_comparison_setup import (
        DEFAULT_CURRENT_POLICY,
        PACKAGED_POLICY_COMMIT,
        PACKAGED_POLICY_URL,
    )
    policy_inputs = mo.ui.dictionary({
        "current": mo.ui.text_area(
            label="Confirmed current tutor policy", full_width=True, debounce=False,
            value=DEFAULT_CURRENT_POLICY,
        ),
        "proposed": mo.ui.text_area(
            label="Proposed tutor policy", full_width=True, debounce=False,
            placeholder="Write the policy you want to compare.",
        ),
    })
    return PACKAGED_POLICY_COMMIT, PACKAGED_POLICY_URL, policy_inputs


@app.cell
def _(mo, output_path, policy_comparison_setup):
    try:
        _existing = policy_comparison_setup.reopen(output_path) if output_path.exists() else None
        _existing_error = ""
    except (OSError, ValueError, KeyError, TypeError) as _exc:
        _existing, _existing_error = None, str(_exc)
    get_result, set_result = mo.state((_existing, _existing_error), allow_self_loops=True)
    return get_result, set_result


@app.cell
def _(PACKAGED_POLICY_COMMIT, PACKAGED_POLICY_URL, get_result, html, mo, output_path,
      policy_comparison_setup, policy_inputs, send_enabled, set_result, source_error,
      source_picker):
    _saved, _error = get_result()

    def _wrapped(value):
        return mo.Html(
            '<div style="white-space: pre-wrap; overflow-wrap: anywhere; '
            'word-break: break-word; max-width: 100%;">'
            + html.escape(value) + '</div>'
        )

    def _freeze(_):
        try:
            if source_picker is None:
                raise ValueError("No eligible saved conversation scenario is available.")
            with mo.status.spinner(
                title="Freezing comparison" if not send_enabled else "Running both conditions",
                subtitle=("Saving the fixed policies without generation." if not send_enabled else
                          "Saving the plan, then generating one tutor and student response per condition."),
            ):
                _created = policy_comparison_setup.freeze(
                    output_path,
                    source=source_picker.value,
                    current_policy=policy_inputs.value["current"],
                    proposed_policy=policy_inputs.value["proposed"],
                )
                if send_enabled:
                    _created = policy_comparison_setup.run_both(output_path, send=True)
            set_result((_created, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            try:
                _preserved = policy_comparison_setup.reopen(output_path) if output_path.exists() else None
            except (OSError, ValueError, KeyError, TypeError):
                _preserved = None
            set_result((_preserved, str(exc)))

    def _run(_):
        try:
            with mo.status.spinner(
                title="Running both conditions",
                subtitle="Generating one tutor and student response per untouched condition.",
            ):
                _updated = policy_comparison_setup.run_both(output_path, send=send_enabled)
            set_result((_updated, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            try:
                _preserved = policy_comparison_setup.reopen(output_path)
            except (OSError, ValueError, KeyError, TypeError):
                _preserved = _saved
            set_result((_preserved, str(exc)))

    _heading = mo.md("# Set up tutor policy comparison")
    _scope = mo.callout(
        ("Freeze and run saves the fixed plan, then makes four logical Gemini requests: "
         "one tutor and one student response per condition." if send_enabled else
         "Preparation only: freezing saves two independent conditions and makes no Gemini request."),
        kind="warn" if send_enabled else "neutral",
    )
    _error_text = _error or source_error
    _error_view = mo.callout(mo.plain_text(_error_text), kind="danger") if _error_text else mo.md("")

    if _saved is None:
        _body = mo.vstack([
            source_picker if source_picker is not None else mo.md("No eligible saved scenarios found."),
            policy_inputs["current"],
            mo.callout(mo.md(
                "Prefilled from the packaged DSC 10 tutor policy at "
                f"[`{PACKAGED_POLICY_COMMIT[:12]}`]({PACKAGED_POLICY_URL}). "
                "A deployment can override this configuration, so confirm it before freezing."
            ), kind="warn"),
            policy_inputs["proposed"],
            mo.md("Each condition is fixed to **one new simulated student decision**."),
            mo.ui.button(label=("Freeze and run comparison" if send_enabled else "Freeze comparison"),
                         on_change=_freeze, kind="success",
                         disabled=source_picker is None),
        ], gap=1.25)
    else:
        _conditions = _saved["conditions"]
        _ready = [name for name, item in _conditions.items()
                  if not item["error"] and item["snapshot"] is not None
                  and item["snapshot"]["status"] == "awaiting-tutor"
                  and item["snapshot"]["decisions_remaining"] > 0]

        def _condition_view(name, title):
            _condition = _conditions[name]
            _snapshot = _condition["snapshot"]
            _tutor_turn = None
            if _snapshot is not None:
                _tutor_turn = next((turn for turn in reversed(_snapshot["dialogue"])
                                    if turn["role"] == "tutor"
                                    and turn.get("origin") in ("scripted", "supplied")), None)
            if _condition["error"]:
                _outcome = mo.callout(mo.plain_text(_condition["error"]), kind="danger")
            elif name in _ready:
                _outcome = mo.callout("Ready to generate this condition.", kind="neutral")
            else:
                _student = (_wrapped(_snapshot["pending_message"])
                            if _snapshot is not None and _snapshot["pending_message"] else
                            mo.md("The simulated student chose no reply."))
                _outcome = mo.vstack([
                    mo.md("#### Generated tutor response"),
                    _wrapped(_tutor_turn["text"]) if _tutor_turn else mo.md("No tutor response was saved."),
                    mo.md("#### Generated student response"),
                    _student,
                ], gap=0.75)
            return mo.vstack([
                mo.md(f"### {title}"),
                mo.md("#### Fixed tutor policy"),
                _wrapped(_condition["policy"]),
                _outcome,
            ], gap=0.75)

        _run_control = (
            mo.ui.button(label="Run both conditions", on_change=_run, kind="success")
            if _ready and send_enabled else
            mo.callout("This comparison is frozen but not run. Reopen with --send=true to generate both conditions.",
                       kind="warn") if _ready else
            mo.callout("Simulation saved. Reloading this page will not generate new responses.", kind="success")
        )
        _body = mo.vstack([
            mo.callout("Comparison frozen. The policies and starting sessions are now immutable.", kind="success"),
            mo.md(f'**Decision budget:** {_saved["max_new_decisions"]} new student decision per condition.'),
            _run_control,
            mo.ui.tabs({
                "Condition A · Current": _condition_view("a", "Condition A · Current policy"),
                "Condition B · Proposed": _condition_view("b", "Condition B · Proposed policy"),
            }),
            mo.md("This single simulated pair does not establish how real students would respond."),
        ], gap=1)

    setup_view = mo.vstack([_heading, _scope, _error_view, _body], gap=1.5)
    setup_view
    return (setup_view,)


if __name__ == "__main__":
    app.run()
