import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Tutor policy simulation lab")


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
    _workspace = _args.get("workspace")
    mo.stop(
        not isinstance(_sources, str) or not _sources.strip()
        or not isinstance(_workspace, str) or not _workspace.strip(),
        mo.callout("Open with --sources /path/to/sessions --workspace /path/to/policy-runs.", kind="warn"),
    )
    source_root = Path(_sources).resolve()
    workspace_path = Path(_workspace).resolve()
    send_enabled = _args.get("send") is True
    return send_enabled, source_root, workspace_path


@app.cell
def _(mo, policy_comparison_setup, source_root):
    try:
        _sources = policy_comparison_setup.sources(source_root)
        source_error = ""
    except (OSError, ValueError) as _exc:
        _sources, source_error = {}, str(_exc)
    source_picker = (
        mo.ui.dropdown(_sources, value=next(iter(_sources)), allow_select_none=False,
                       label="Saved conversation scenario")
        if _sources else None
    )
    return source_error, source_picker


@app.cell
def _(mo, policy_comparison_setup):
    policy_inputs = mo.ui.dictionary({
        "current": mo.ui.text_area(
            label="Current tutor policy", full_width=True, debounce=False,
            value=policy_comparison_setup.DEFAULT_CURRENT_POLICY,
        ),
        "proposed": mo.ui.text_area(
            label="Proposed tutor policy", full_width=True, debounce=False,
            placeholder="Write the policy you want to simulate.",
        ),
    })
    return (policy_inputs,)


@app.cell
def _(mo, policy_comparison_setup, workspace_path):
    try:
        _runs = policy_comparison_setup.runs(workspace_path)
        history_error = ""
    except (OSError, ValueError) as _exc:
        _runs, history_error = {}, str(_exc)
    history_picker = (
        mo.ui.dropdown(_runs, value=next(reversed(_runs)), allow_select_none=False,
                       label="Previously saved simulation")
        if _runs else None
    )
    _latest_path = next(reversed(_runs.values())) if _runs else None
    _latest = policy_comparison_setup.reopen(_latest_path) if _latest_path else None
    get_result, set_result = mo.state((_latest_path, _latest, ""), allow_self_loops=True)
    return get_result, history_error, history_picker, set_result


@app.cell
def _(get_result, history_error, history_picker, html, mo, policy_comparison_setup,
      policy_inputs, send_enabled, set_result, source_error, source_picker, workspace_path):
    _result_path, _saved, _error = get_result()

    def _wrapped(value):
        return mo.Html(
            '<div style="white-space: pre-wrap; overflow-wrap: anywhere; '
            'word-break: break-word; max-width: 100%;">'
            + html.escape(value) + '</div>'
        )

    def _turn(role, text, origin):
        _role = "Student" if role == "student" else "Tutor"
        _colors = ({
            "background": "#ecfdf5", "border": "#6ee7b7",
            "accent": "#059669", "heading": "#047857",
        } if role == "student" else {
            "background": "#fff7ed", "border": "#fdba74",
            "accent": "#ea580c", "heading": "#c2410c",
        })
        return mo.Html(
            '<article style="border: 1px solid {border}; border-left: 5px solid {accent}; '
            'border-radius: 6px; box-sizing: border-box; background: {background}; '
            'color: #1f2937; margin: 0 0 12px; max-width: 100%; padding: 14px 16px;">'
            '<div style="align-items: baseline; display: flex; flex-wrap: wrap; '
            'gap: 6px 10px; margin-bottom: 8px;">'
            '<strong style="color: {heading}; font-size: 1rem; font-weight: 700;">{role}</strong>'
            '<span style="color: #4b5563; font-size: 0.8rem; font-weight: 600;">{origin}</span>'
            '</div>'
            '<div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, '
            'monospace; line-height: 1.55; overflow-wrap: anywhere; white-space: pre-wrap; '
            'word-break: break-word;">{text}</div>'
            '</article>'
        .format(
            **_colors,
            role=_role,
            origin=html.escape(origin),
            text=html.escape(text),
        )
        )

    def _run(_):
        try:
            if source_picker is None:
                raise ValueError("No eligible saved conversation scenario is available.")
            with mo.status.spinner(
                title="Running new policy simulation",
                subtitle="Saving a new run, then generating A and B once.",
            ):
                _path, _created = policy_comparison_setup.freeze_next(
                    workspace_path,
                    source=source_picker.value,
                    current_policy=policy_inputs.value["current"],
                    proposed_policy=policy_inputs.value["proposed"],
                )
                _created = policy_comparison_setup.run_both(_path, send=send_enabled)
            set_result((_path, _created, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            set_result((_result_path, _saved, str(exc)))

    def _open_saved(_):
        try:
            if history_picker is None:
                raise ValueError("No saved simulation is available.")
            _path = history_picker.value
            set_result((_path, policy_comparison_setup.reopen(_path), ""))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            set_result((_result_path, _saved, str(exc)))

    _heading = mo.md("# Tutor policy simulation lab")
    _notice = mo.callout(
        ("Each run saves a new immutable comparison and makes four logical Gemini requests."
         if send_enabled else "Viewing only. Relaunch with --send=true to run a new comparison."),
        kind="warn" if send_enabled else "neutral",
    )
    _source_notice = mo.callout(mo.md(
        "The current policy is prefilled from the packaged DSC 10 baseline at "
        f"[`{policy_comparison_setup.PACKAGED_POLICY_COMMIT[:12]}`]"
        f"({policy_comparison_setup.PACKAGED_POLICY_URL}). Confirm deployment overrides before research use."
    ), kind="warn")
    _error_text = _error or source_error or history_error
    _error_view = mo.callout(mo.plain_text(_error_text), kind="danger") if _error_text else mo.md("")
    _controls = mo.vstack([
        source_picker if source_picker is not None else mo.md("No eligible saved scenarios found."),
        policy_inputs["current"], _source_notice, policy_inputs["proposed"],
        mo.ui.button(label="Run new simulation", on_change=_run, kind="success",
                     disabled=not send_enabled or source_picker is None),
    ], gap=1)
    _history = (mo.hstack([
        history_picker,
        mo.ui.button(label="Open saved simulation", on_change=_open_saved),
    ], align="end") if history_picker is not None else mo.md("No earlier runs in this workspace."))

    if _saved is None:
        _results = mo.callout("No simulation selected yet.", kind="neutral")
    else:
        def _condition_view(name, title):
            _condition = _saved["conditions"][name]
            _snapshot = _condition["snapshot"]
            if _condition["error"]:
                _outcome = mo.callout(mo.plain_text(_condition["error"]), kind="danger")
            else:
                _recorded_context = []
                _starting_question = None
                _generated_tutor = None
                for _message in _snapshot["dialogue"]:
                    _origin = _message.get("origin")
                    if _origin == "source":
                        _recorded_context.append(_turn(
                            _message["role"], _message["text"], "Recorded context"
                        ))
                    elif _message["role"] == "student" and _origin == "generated":
                        _starting_question = _turn(
                            "student", _message["text"], "Shared simulated starting question"
                        )
                    elif (_message["role"] == "tutor"
                          and _origin in ("scripted", "supplied")):
                        _generated_tutor = _turn(
                            "tutor", _message["text"], "Generated under this policy"
                        )
                _question_view = (_starting_question if _starting_question is not None else
                                  mo.callout("No simulated starting question was saved.", kind="neutral"))
                _context_view = (mo.vstack(_recorded_context, gap=0) if _recorded_context else
                                 mo.md("No earlier recorded conversation was saved."))
                _continuation = [
                    _generated_tutor if _generated_tutor is not None else
                    mo.callout("No tutor response was saved.", kind="neutral")
                ]
                if _snapshot["pending_message"]:
                    _continuation.append(_turn(
                        "student", _snapshot["pending_message"], "Simulated follow-up"
                    ))
                else:
                    _continuation.append(mo.callout(
                        "The simulated student chose not to send a follow-up.",
                        kind="neutral",
                    ))
                _outcome = mo.vstack([
                    mo.md("#### Student question used by this simulation"),
                    _question_view,
                    mo.accordion({
                        f"Earlier recorded context ({len(_recorded_context)} messages)": _context_view,
                    }),
                    mo.md("#### Simulated continuation"),
                    mo.vstack(_continuation, gap=0),
                ], gap=0.75)
            return mo.vstack([
                mo.md(f"### {title}"),
                mo.accordion({"Policy used for this condition": _wrapped(_condition["policy"])}),
                _outcome,
            ], gap=0.75)

        _results = mo.vstack([
            mo.md(f"## Saved simulation · `{_result_path.name}`"),
            mo.callout(
                "Both conditions use the same recorded conversation and the same cached "
                "simulated starting question. The tutor policy, tutor reply, and simulated "
                "student follow-up are what you compare.",
                kind="neutral",
            ),
            mo.ui.tabs({
                "Condition A · Current": _condition_view("a", "Condition A · Current policy"),
                "Condition B · Proposed": _condition_view("b", "Condition B · Proposed policy"),
            }),
            mo.md("Edit either policy above and run again to create a new saved comparison. "
                  "The current result will not be overwritten."),
        ], gap=1)

    lab_view = mo.vstack([
        _heading, _notice, _error_view,
        mo.md("## Policy draft"), _controls,
        mo.md("## Run history"), _history,
        _results,
        mo.md("Simulated differences are not evidence of real-student or learning effects."),
    ], gap=1.5)
    lab_view
    return (lab_view,)


if __name__ == "__main__":
    app.run()
