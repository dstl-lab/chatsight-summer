import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Tutor policy cohort lab")


@app.cell
def _():
    import html
    from pathlib import Path
    import marimo as mo
    from src.agents import policy_cohort, policy_comparison_setup
    return Path, html, mo, policy_cohort, policy_comparison_setup


@app.cell
def _(Path, mo):
    _args = mo.cli_args()
    _sources = _args.get("sources")
    _workspace = _args.get("workspace")
    mo.stop(
        not isinstance(_sources, str) or not _sources.strip()
        or not isinstance(_workspace, str) or not _workspace.strip(),
        mo.callout("Open with --sources /path/to/sessions --workspace /path/to/cohorts.", kind="warn"),
    )
    source_root = Path(_sources).resolve()
    workspace_path = Path(_workspace).resolve()
    send_enabled = _args.get("send") is True
    return send_enabled, source_root, workspace_path


@app.cell
def _(mo, policy_cohort, policy_comparison_setup, source_root):
    try:
        _found = policy_comparison_setup.sources(source_root)
        source_error = ""
    except (OSError, ValueError) as _exc:
        _found, source_error = {}, str(_exc)
    available_sources = {
        f"Scenario {index}": path for index, path in enumerate(_found.values(), 1)
    }
    source_selector = (
        mo.ui.multiselect(
            available_sources,
            value=list(available_sources),
            label="Conversation scenarios",
            full_width=True,
            max_selections=policy_cohort.MAX_CASES,
        )
        if available_sources else None
    )
    return available_sources, source_error, source_selector


@app.cell
def _(mo, policy_comparison_setup):
    policy_inputs = mo.ui.dictionary({
        "current": mo.ui.text_area(
            label="Current tutor policy", full_width=True, debounce=False,
            value=policy_comparison_setup.DEFAULT_CURRENT_POLICY,
        ),
        "proposed": mo.ui.text_area(
            label="Proposed tutor policy", full_width=True, debounce=False,
            placeholder="Write the policy you want to screen across the fixed cohort.",
        ),
    })
    return (policy_inputs,)


@app.cell
def _(mo, policy_cohort, workspace_path):
    try:
        _runs = policy_cohort.runs(workspace_path)
        history_error = ""
    except (OSError, ValueError) as _exc:
        _runs, history_error = {}, str(_exc)
    history_picker = (
        mo.ui.dropdown(
            _runs, value=next(reversed(_runs)), allow_select_none=False,
            label="Previously saved cohort",
        ) if _runs else None
    )
    _latest_path = next(reversed(_runs.values())) if _runs else None
    _latest = policy_cohort.show(_latest_path) if _latest_path else None
    get_result, set_result = mo.state((_latest_path, _latest, ""), allow_self_loops=True)
    return get_result, history_error, history_picker, set_result


@app.cell
def _(available_sources, get_result, history_error, history_picker, html, mo,
      policy_cohort, policy_comparison_setup, policy_inputs, send_enabled, set_result,
      source_error, source_selector, workspace_path):
    _result_path, _state_saved, _error = get_result()
    if _result_path is not None:
        try:
            _saved = policy_cohort.show(_result_path)
        except (OSError, ValueError, KeyError, TypeError) as _exc:
            _saved = _state_saved
            _error = _error or str(_exc)
    else:
        _saved = _state_saved

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
        _card = (
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
        )
        return mo.Html(_card.format(
            **_colors,
            role=_role,
            origin=html.escape(origin),
            text=html.escape(text),
        ))

    def _freeze(_):
        try:
            if source_selector is None or not source_selector.value:
                raise ValueError("Choose at least one eligible conversation scenario.")
            with mo.status.spinner(
                title="Freezing fixed cohort",
                subtitle="Copying independent A/B starts without making provider requests.",
            ):
                _path, _created = policy_cohort.freeze_next(
                    workspace_path,
                    sources=source_selector.value,
                    current_policy=policy_inputs.value["current"],
                    proposed_policy=policy_inputs.value["proposed"],
                )
            set_result((_path, _created, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            set_result((_result_path, _saved, str(exc)))

    def _run(_):
        try:
            if _result_path is None:
                raise ValueError("Freeze a cohort plan before running it.")
            with mo.status.spinner(
                title="Running fixed cohort",
                subtitle="Running independent conversations concurrently; each result stays separate.",
            ):
                _updated = policy_cohort.run(
                    _result_path,
                    send=send_enabled,
                    workers=min(4, max(1, len(_saved["cases"]))),
                )
            set_result((_result_path, _updated, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            try:
                _preserved = policy_cohort.show(_result_path) if _result_path else _saved
            except (OSError, ValueError, KeyError, TypeError):
                _preserved = _saved
            set_result((_result_path, _preserved, str(exc)))

    def _open_saved(_):
        try:
            if history_picker is None:
                raise ValueError("No saved cohort is available.")
            _path = history_picker.value
            set_result((_path, policy_cohort.show(_path), ""))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            set_result((_result_path, _saved, str(exc)))

    _heading = mo.md("# Tutor policy cohort lab")
    _scope = mo.callout(
        "This development cohort uses eligible saved scenarios with a recorded prefix and a "
        "cached simulated starting question. It does not yet branch directly from a set of "
        "recorded student questions and cannot estimate a real-student policy effect.",
        kind="warn",
    )
    _error_text = _error or source_error or history_error
    _error_view = mo.callout(mo.plain_text(_error_text), kind="danger") if _error_text else mo.md("")
    _source_count = len(available_sources)
    _request_count = len(source_selector.value) * 4 if source_selector is not None else 0
    _controls = mo.vstack([
        mo.md(f"**{_source_count} eligible scenario{'s' if _source_count != 1 else ''} available.**"),
        source_selector if source_selector is not None else mo.md("No eligible scenarios found."),
        policy_inputs["current"],
        mo.callout(mo.md(
            "The current policy is prefilled from the packaged DSC 10 baseline at "
            f"[`{policy_comparison_setup.PACKAGED_POLICY_COMMIT[:12]}`]"
            f"({policy_comparison_setup.PACKAGED_POLICY_URL}). Confirm deployment overrides before research use."
        ), kind="warn"),
        policy_inputs["proposed"],
        mo.md(f"The current selection would freeze **{_request_count} total provider requests** "
              "but freezing the plan itself sends none."),
        mo.ui.button(
            label="Freeze cohort plan", on_change=_freeze, kind="success",
            disabled=source_selector is None or not source_selector.value,
        ),
    ], gap=1)
    _history = (mo.hstack([
        history_picker,
        mo.ui.button(label="Open saved cohort", on_change=_open_saved),
    ], align="end") if history_picker is not None else mo.md("No earlier cohorts in this workspace."))

    if _saved is None:
        _results = mo.callout("Freeze a cohort plan to create the overview.", kind="neutral")
    else:
        _summary = _saved["summary"]
        _comparison_labels = {
            "both-replied": "Both students replied",
            "both-no-follow-up": "Neither student followed up",
            "proposed-gained-follow-up": "Proposed policy gained a follow-up",
            "proposed-lost-follow-up": "Proposed policy lost a follow-up",
            "not-comparable": "Not comparable",
        }

        def _comparison_key(a, b):
            _terminal = {"student-replied", "no-follow-up"}
            if a not in _terminal or b not in _terminal:
                return "not-comparable"
            if a == b == "student-replied":
                return "both-replied"
            if a == b == "no-follow-up":
                return "both-no-follow-up"
            return ("proposed-gained-follow-up" if a == "no-follow-up"
                    else "proposed-lost-follow-up")

        _rows = []
        _comparison_counts = {key: 0 for key in _comparison_labels}
        for _case in _saved["cases"]:
            _a, _b = _case["outcomes"]["a"], _case["outcomes"]["b"]
            _comparison_outcome = _case.get("comparison_outcome", _comparison_key(_a, _b))
            _comparison_counts[_comparison_outcome] += 1
            _rows.append({
                "Case": _case["case_id"].replace("case-", "Question "),
                "Condition A": _a.replace("-", " ").title(),
                "Condition B": _b.replace("-", " ").title(),
                "A/B comparison": _comparison_labels[_comparison_outcome],
            })
        _summary_rows = []
        for _name, _title in (("a", "Condition A · Current"), ("b", "Condition B · Proposed")):
            _counts = _summary["conditions"][_name]
            _summary_rows.append({
                "Condition": _title,
                "Ready": _counts["ready"],
                "Student replied": _counts["student-replied"],
                "No follow-up": _counts["no-follow-up"],
                "Incomplete": _counts.get("incomplete", 0),
                "Failed": _counts["failed"],
            })
        _comparison_rows = [
            {"Saved A/B outcome": _comparison_labels[key], "Cases": count}
            for key, count in _comparison_counts.items()
        ]
        _ready_conditions = sum(
            _summary["conditions"][name]["ready"] for name in ("a", "b")
        )
        _run_control = (
            mo.ui.button(
                label=f"Run all remaining conversations ({_ready_conditions * 2} requests)",
                on_change=_run,
                kind="success",
                disabled=not send_enabled,
            ) if _ready_conditions else mo.callout(
                "Every condition is already complete or has a preserved failure.", kind="neutral"
            )
        )

        def _case_view(case):
            _comparison = case["comparison"]
            _base = _comparison["conditions"]["a"]["snapshot"]
            _recorded = []
            _starting_text = None
            if _base is not None:
                for _message in _base["dialogue"]:
                    if _message.get("origin") == "source":
                        _recorded.append(_turn(
                            _message["role"], _message["text"], "Recorded context"
                        ))
                    elif _message["role"] == "student" and _message.get("origin") == "generated":
                        _starting_text = _message["text"]
                if _starting_text is None and case["outcomes"]["a"] == "ready":
                    _starting_text = _base["pending_message"]
            _question = (_turn("student", _starting_text, "Shared simulated starting question")
                         if _starting_text else
                         mo.callout("No starting question was available.", kind="neutral"))
            _context = (mo.vstack(_recorded, gap=0) if _recorded else
                        mo.md("No earlier recorded context was saved."))

            def _condition(name, title):
                _item = _comparison["conditions"][name]
                _snapshot = _item["snapshot"]
                _outcome = case["outcomes"][name]
                if _item["error"]:
                    _body = mo.callout(mo.plain_text(_item["error"]), kind="danger")
                elif _outcome == "ready":
                    _body = mo.callout("Frozen and ready; this condition has not been generated.", kind="neutral")
                else:
                    _tutor = next((
                        message for message in reversed(_snapshot["dialogue"])
                        if message["role"] == "tutor"
                        and message.get("origin") in ("scripted", "supplied")
                    ), None)
                    _parts = [
                        _turn("tutor", _tutor["text"], "Generated under this policy")
                        if _tutor else mo.callout("No tutor response was saved.", kind="neutral")
                    ]
                    if _outcome == "student-replied":
                        _parts.append(_turn(
                            "student", _snapshot["pending_message"], "Simulated follow-up"
                        ))
                    elif _outcome == "no-follow-up":
                        _parts.append(mo.callout(
                            "The simulated student chose not to send a follow-up.", kind="neutral"
                        ))
                    _body = mo.vstack(_parts, gap=0)
                return mo.vstack([
                    mo.md(f"#### {title}"),
                    mo.accordion({"Policy used": _wrapped(_item["policy"])}),
                    _body,
                ], gap=0.75)

            return mo.vstack([
                mo.md("#### Student question"),
                _question,
                mo.accordion({f"Earlier recorded context ({len(_recorded)} messages)": _context}),
                mo.md("#### A/B simulated continuation"),
                mo.ui.tabs({
                    "Condition A · Current": _condition("a", "Current policy"),
                    "Condition B · Proposed": _condition("b", "Proposed policy"),
                }),
            ], gap=0.75)

        _case_views = {
            f'{case["case_id"].replace("case-", "Question ")} · '
            f'A: {case["outcomes"]["a"].replace("-", " ")} · '
            f'B: {case["outcomes"]["b"].replace("-", " ")}': _case_view(case)
            for case in _saved["cases"]
        }
        _results = mo.vstack([
            mo.md(f"## Cohort overview · `{_result_path.name}`"),
            mo.md(
                f'**{_summary["case_count"]} fixed cases** · '
                f'**{_summary["different_reply_status"]} different reply statuses** · '
                f'**{_summary["provider_requests_if_fully_run"]} requests in the complete plan**'
            ),
            mo.ui.table(
                _summary_rows, selection=None, pagination=False,
                show_data_types=False, show_download=False,
            ),
            _run_control,
            mo.md("### Saved A/B outcome categories"),
            mo.ui.table(
                _comparison_rows, selection=None, pagination=False,
                show_data_types=False, show_download=False,
            ),
            mo.md("### Question-by-question status"),
            mo.ui.table(
                _rows, selection=None, pagination=False,
                show_data_types=False, show_download=False,
                wrapped_columns=["Case"],
            ),
            mo.md("### Inspect individual comparisons"),
            mo.accordion(_case_views),
        ], gap=1)

    cohort_view = mo.vstack([
        _heading, _scope, _error_view,
        mo.md("## Cohort plan"), _controls,
        mo.md("## Saved cohorts"), _history,
        _results,
        mo.md("These outputs describe simulated continuations, not real-student or learning effects."),
    ], gap=1.5)
    cohort_view
    return (cohort_view,)


if __name__ == "__main__":
    app.run()
