import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Recorded baseline policy lab")


@app.cell
def _():
    import html
    import os
    from pathlib import Path

    import marimo as mo
    from dotenv import load_dotenv

    from src.eval import observed_policy_cohort
    from src.labeling import llm
    return Path, html, llm, load_dotenv, mo, observed_policy_cohort, os


@app.cell
def _(Path, mo):
    _args = mo.cli_args()
    _snapshot = _args.get("snapshot")
    _workspace = _args.get("workspace")
    mo.stop(
        not isinstance(_snapshot, str) or not _snapshot.strip()
        or not isinstance(_workspace, str) or not _workspace.strip(),
        mo.callout(
            "Open with --snapshot /path/to/snapshot --workspace /path/to/results.",
            kind="warn",
        ),
    )
    snapshot_path = Path(_snapshot).resolve()
    workspace_path = Path(_workspace).resolve()
    send_enabled = _args.get("send") is True
    return send_enabled, snapshot_path, workspace_path


@app.cell
def _(mo):
    setup_inputs = mo.ui.dictionary({
        "proposed_policy": mo.ui.text_area(
            label="Proposed tutor policy",
            placeholder="Write the policy to simulate against recorded outcomes.",
            full_width=True,
            debounce=False,
        ),
        "case_count": mo.ui.dropdown(
            {"8 conversations": 8, "16 conversations": 16, "24 conversations": 24},
            value="24 conversations",
            allow_select_none=False,
            label="Holdout cohort size",
        ),
    })
    return (setup_inputs,)


@app.cell
def _(mo, observed_policy_cohort, workspace_path):
    try:
        _runs = observed_policy_cohort.runs(workspace_path)
        history_error = ""
    except (OSError, ValueError, KeyError, TypeError) as _exc:
        _runs, history_error = {}, str(_exc)
    history_picker = (
        mo.ui.dropdown(
            _runs,
            value=next(reversed(_runs)),
            allow_select_none=False,
            label="Previously saved run",
        )
        if _runs else None
    )
    _latest_path = next(reversed(_runs.values())) if _runs else None
    _latest = observed_policy_cohort.show(_latest_path) if _latest_path else None
    get_result, set_result = mo.state((_latest_path, _latest, ""), allow_self_loops=True)
    return get_result, history_error, history_picker, set_result


@app.cell
def _(get_result, history_error, history_picker, html, llm, load_dotenv, mo,
      observed_policy_cohort, os, send_enabled, set_result, setup_inputs,
      snapshot_path, workspace_path, individual_selector):
    _result_path, _state_saved, _error = get_result()
    if _result_path is not None:
        try:
            _saved = observed_policy_cohort.show(_result_path)
        except (OSError, ValueError, KeyError, TypeError) as _exc:
            _saved = _state_saved
            _error = _error or str(_exc)
    else:
        _saved = _state_saved

    def _turn(role, text, origin):
        _student = role == "student"
        _colors = ({
            "background": "#ecfdf5",
            "border": "#6ee7b7",
            "accent": "#059669",
            "heading": "#047857",
        } if _student else {
            "background": "#fff7ed",
            "border": "#fdba74",
            "accent": "#ea580c",
            "heading": "#c2410c",
        })
        return mo.Html((
            '<article style="border: 1px solid {border}; border-left: 5px solid {accent}; '
            'border-radius: 6px; box-sizing: border-box; background: {background}; '
            'color: #1f2937; margin: 0 0 12px; max-width: 100%; padding: 14px 16px;">'
            '<div style="display: flex; flex-wrap: wrap; gap: 6px 10px; margin-bottom: 8px;">'
            '<strong style="color: {heading};">{role}</strong>'
            '<span style="color: #4b5563; font-size: 0.8rem; font-weight: 600;">{origin}</span>'
            '</div><div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, '
            'Consolas, monospace; line-height: 1.55; overflow-wrap: anywhere; '
            'white-space: pre-wrap; word-break: break-word;">{text}</div></article>'
        ).format(
            **_colors,
            role="Student" if _student else "Tutor",
            origin=html.escape(origin),
            text=html.escape(text),
        ))

    def _prepare(_):
        try:
            _policy = setup_inputs.value["proposed_policy"]
            if not _policy.strip():
                raise ValueError("Enter a proposed tutor policy.")
            with mo.status.spinner(
                title="Freezing conversation holdout",
                subtitle="Separating recorded outcomes before any model request.",
            ):
                _path, _created = observed_policy_cohort.prepare_next(
                    workspace_path,
                    snapshot_path,
                    proposed_policy=_policy,
                    case_count=setup_inputs.value["case_count"],
                    development_conversations=(
                        observed_policy_cohort.DEFAULT_DEVELOPMENT_CONVERSATIONS
                    ),
                    seed=observed_policy_cohort.DEFAULT_SEED,
                )
            set_result((_path, _created, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            set_result((_result_path, _saved, str(exc)))

    def _run(_):
        try:
            if _result_path is None:
                raise ValueError("Freeze a holdout cohort before running it.")
            load_dotenv(Path.cwd() / ".env")
            load_dotenv(Path(__file__).resolve().parents[2] / "main" / ".env")
            load_dotenv()
            _api_key = os.environ["GEMINI_API_KEY"]

            def _generate(prompt, schema):
                return llm.make_generate(
                    _api_key,
                    model=observed_policy_cohort.MODEL,
                )(prompt, schema)

            with mo.status.spinner(
                title="Running proposed-policy branches",
                subtitle="Recorded outcomes stay fixed; only counterfactual branches are generated.",
            ):
                _updated = observed_policy_cohort.run(
                    _result_path,
                    send=send_enabled,
                    generate_tutor=_generate,
                    generate_student=_generate,
                    workers=4,
                )
            set_result((_result_path, _updated, ""))
        except (OSError, ValueError, FileExistsError, KeyError, TypeError) as exc:
            try:
                _preserved = observed_policy_cohort.show(_result_path)
            except (OSError, ValueError, KeyError, TypeError):
                _preserved = _saved
            set_result((_result_path, _preserved, str(exc)))

    def _open_saved(_):
        try:
            if history_picker is None:
                raise ValueError("No saved run is available.")
            _path = history_picker.value
            set_result((_path, observed_policy_cohort.show(_path), ""))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            set_result((_result_path, _saved, str(exc)))

    _heading = mo.md("# Recorded baseline policy lab")
    _scope = mo.callout(
        "The baseline uses the tutor response and next student contribution actually recorded "
        "in the snapshot. Only the proposed-policy tutor response and following student action "
        "are simulated. Conversations are held out from a reserved development partition, but "
        "that partition is not used to train Gemini. Learner identity is unavailable, so this "
        "is not a student-level holdout or a causal estimate.",
        kind="warn",
    )
    _error_text = _error or history_error
    _error_view = (
        mo.callout(mo.plain_text(_error_text), kind="danger")
        if _error_text else mo.md("")
    )
    _request_budget = setup_inputs.value["case_count"] * 2
    _controls = mo.vstack([
        setup_inputs["proposed_policy"],
        setup_inputs["case_count"],
        mo.md(
            f"The fixed plan reserves 12 development conversations and selects "
            f"**{setup_inputs.value['case_count']} held-out conversations**. Running the "
            f"complete plan allows up to **{_request_budget} logical Gemini requests**."
        ),
        mo.ui.button(
            label="Freeze recorded baseline plan",
            on_change=_prepare,
            kind="success",
            disabled=not setup_inputs.value["proposed_policy"].strip(),
        ),
    ], gap=1)
    _history = (
        mo.hstack([
            history_picker,
            mo.ui.button(label="Open saved run", on_change=_open_saved),
        ], align="end")
        if history_picker is not None
        else mo.md("No earlier recorded-baseline runs in this workspace.")
    )

    if _saved is None:
        _results = mo.callout(
            "Freeze a plan to select the conversation-level holdout.", kind="neutral"
        )
    else:
        _summary = _saved["summary"]
        _stats = _summary["statistics"]
        _labels = {
            "both-replied": "Both branches have a follow-up",
            "both-no-follow-up": "Neither branch has a follow-up",
            "proposed-gained-follow-up": "Proposed branch gained a follow-up",
            "proposed-lost-follow-up": "Proposed branch lost a follow-up",
            "not-comparable": "Proposed branch not complete",
        }

        def _percent(value):
            return "Not available" if value is None else f"{value:.1%}"

        _status_rows = [
            {
                "Branch": "Recorded historical outcome",
                "Student replied": _summary["recorded"]["student-replied"],
                "No follow-up": _summary["recorded"]["no-follow-up"],
                "Ready": 0,
                "Failed or incomplete": 0,
            },
            {
                "Branch": "Simulated proposed-policy outcome",
                "Student replied": _summary["proposed"]["student-replied"],
                "No follow-up": _summary["proposed"]["no-follow-up"],
                "Ready": _summary["proposed"]["ready"],
                "Failed or incomplete": (
                    _summary["proposed"]["failed"]
                    + _summary["proposed"]["incomplete"]
                ),
            },
        ]
        _statistics_rows = [
            {
                "Measure": "Comparable recorded/proposed scenarios",
                "Result": (
                    f'{_stats["comparable_cases"]} / {_summary["case_count"]} '
                    f'({_percent(_stats["coverage_rate"])})'
                ),
            },
            {"Measure": "Recorded student follow-up rate",
             "Result": _percent(_stats["recorded_reply_rate"])},
            {"Measure": "Simulated proposed follow-up rate",
             "Result": _percent(_stats["proposed_reply_rate"])},
            {
                "Measure": "Proposed minus recorded",
                "Result": (
                    "Not available" if _stats["reply_rate_difference"] is None
                    else f'{_stats["reply_rate_difference"]:+.1%}'
                ),
            },
            {
                "Measure": "Changed follow-up outcome",
                "Result": (
                    f'{_stats["changed_cases"]} / {_stats["comparable_cases"]} '
                    f'({_percent(_stats["changed_rate"])})'
                ),
            },
            {"Measure": "Net gained minus lost follow-ups",
             "Result": f'{_stats["net_follow_up_change"]:+d}'},
        ]
        _simulated_replies = _summary["proposed"]["student-replied"]
        _simulated_no_followup = _summary["proposed"]["no-follow-up"]
        _completed_decisions = _simulated_replies + _simulated_no_followup
        _model_rows = [
            {"Gemini run detail": "Model", "Result": _saved["manifest"]["model"]},
            {
                "Gemini run detail": "Completed student decisions",
                "Result": f'{_completed_decisions} / {_summary["case_count"]}',
            },
            {
                "Gemini run detail": "Selected reply",
                "Result": f'{_simulated_replies} / {_completed_decisions}'
                if _completed_decisions else "No completed decisions",
            },
            {
                "Gemini run detail": "Selected no follow-up",
                "Result": f'{_simulated_no_followup} / {_completed_decisions}'
                if _completed_decisions else "No completed decisions",
            },
            {
                "Gemini run detail": "Sampling design",
                "Result": "One generated student decision per completed scenario",
            },
            {
                "Gemini run detail": "Course-specific training",
                "Result": "None in this workflow",
            },
        ]
        if not _completed_decisions:
            _model_interpretation = mo.callout(
                "No Gemini student decisions are complete yet.", kind="neutral"
            )
        elif _simulated_replies == _completed_decisions:
            _model_interpretation = mo.callout(
                f"Gemini selected reply for all {_completed_decisions} completed branches. "
                "This is a concentrated one-draw model output, not a calibrated 100% "
                "probability that real students will reply and not a measured policy effect.",
                kind="warn",
            )
        elif _simulated_no_followup == _completed_decisions:
            _model_interpretation = mo.callout(
                f"Gemini selected no follow-up for all {_completed_decisions} completed "
                "branches. This is a concentrated one-draw model output, not a calibrated "
                "100% probability that real students will stop and not a measured policy effect.",
                kind="warn",
            )
        else:
            _model_interpretation = mo.callout(
                "These counts summarize one generated decision per completed branch. They "
                "are not calibrated probabilities or measured responses from real students.",
                kind="neutral",
            )
        _case_rows = [
            {
                "Scenario": case["case_id"].replace("case-", "Scenario "),
                "Recorded": case["recorded_outcome"].replace("-", " ").title(),
                "Proposed": case["proposed_outcome"].replace("-", " ").title(),
                "Comparison": _labels[case["comparison_outcome"]],
            }
            for case in _saved["cases"]
        ]
        _ready = _summary["proposed"]["ready"]
        _run_control = (
            mo.vstack([
                mo.md(
                    f"**{_ready} proposed branches remain**, allowing up to "
                    f"**{_ready * 2} logical requests**."
                ),
                mo.ui.button(
                    label="Run proposed branches",
                    on_change=_run,
                    kind="success",
                    disabled=not send_enabled,
                ),
            ], gap=0.5)
            if _ready else mo.callout(
                "Every proposed branch is complete or has a preserved failure.",
                kind="neutral",
            )
        )

        _selected_case = next((
            case for case in _saved["cases"]
            if individual_selector is not None
            and case["case_id"] == individual_selector.value
        ), _saved["cases"][0])
        _source = _selected_case["source"]
        _context = [
            _turn(turn["role"], turn["text"], "Recorded earlier context")
            for turn in _source["context"]
        ]
        _request = [
            _turn("student", turn["text"], "Actual recorded student request")
            for turn in _source["request"]
        ]
        _recorded = [
            *[_turn("tutor", turn["text"], "Actual recorded tutor response")
              for turn in _source["recorded_tutor"]],
            *[_turn("student", turn["text"], "Actual recorded student follow-up")
              for turn in _source["recorded_followup"]],
        ]
        if not _source["recorded_followup"]:
            _recorded.append(mo.callout(
                "No later student contribution was recorded in this conversation. "
                "This does not establish what happened outside the chat.",
                kind="neutral",
            ))
        _receipt = _selected_case["proposed"]
        if _receipt is None:
            _proposed = [mo.callout(
                "The proposed branch is frozen and has not been generated.", kind="neutral"
            )]
        elif _selected_case["proposed_outcome"] in {"failed", "incomplete"}:
            _error_record = (
                _receipt["tutor"].get("error")
                or _receipt["student"].get("error")
                or {"message": "The saved request did not complete."}
            )
            _proposed = [mo.callout(
                mo.plain_text(_error_record["message"]), kind="danger"
            )]
        else:
            _proposed_tutor = _receipt["tutor"]["response"]["text"]
            _student = _receipt["student"]["response"]
            _proposed = [
                _turn("tutor", _proposed_tutor, "Generated under proposed policy")
            ]
            if _student["decision"] == "reply":
                _proposed.append(_turn(
                    "student", _student["text"], "Simulated student follow-up"
                ))
            else:
                _proposed.append(mo.callout(
                    "The simulator chose not to send a follow-up.", kind="neutral"
                ))
        _individual = mo.vstack([
            individual_selector,
            mo.callout(
                "This scenario is a held-out conversation, not a verified unique student. "
                "The recorded branch is historical evidence; the proposed branch is a forecast.",
                kind="neutral",
            ),
            mo.accordion({
                f"Earlier recorded context ({len(_context)} messages)": (
                    mo.vstack(_context, gap=0) if _context
                    else mo.md("No earlier context was selected.")
                )
            }),
            mo.md("#### Shared actual student request"),
            mo.vstack(_request, gap=0),
            mo.ui.tabs({
                "Recorded historical branch": mo.vstack(_recorded, gap=0),
                "Simulated proposed-policy branch": mo.vstack(_proposed, gap=0),
            }),
        ], gap=1)
        _class_summary = mo.vstack([
            mo.md("### Recorded versus simulated outcomes"),
            mo.ui.table(
                _status_rows,
                selection=None,
                pagination=False,
                show_data_types=False,
                show_download=False,
                wrapped_columns=["Branch"],
            ),
            mo.md("### Paired descriptive comparison"),
            mo.ui.table(
                _statistics_rows,
                selection=None,
                pagination=False,
                show_data_types=False,
                show_download=False,
                wrapped_columns=["Measure"],
            ),
            mo.md("### Gemini behavior in this run"),
            mo.ui.table(
                _model_rows,
                selection=None,
                pagination=False,
                show_data_types=False,
                show_download=False,
                wrapped_columns=["Gemini run detail", "Result"],
            ),
            _model_interpretation,
            mo.md("### Scenario-by-scenario status"),
            mo.ui.table(
                _case_rows,
                selection=None,
                pagination=False,
                show_data_types=False,
                show_download=False,
                wrapped_columns=["Scenario", "Comparison"],
            ),
        ], gap=1)
        _results = mo.vstack([
            mo.md(f"## Recorded baseline run · `{_result_path.name}`"),
            mo.md(
                f'**{_summary["case_count"]} held-out conversations** · '
                f'**{_stats["comparable_cases"]} comparable outcomes** · '
                f'**up to {_saved["manifest"]["logical_requests_if_fully_run"]} '
                "logical requests in the complete plan**"
            ),
            _run_control,
            mo.ui.tabs({
                "Class summary": _class_summary,
                "Individual scenario": _individual,
            }),
        ], gap=1)

    observed_policy_view = mo.vstack([
        _heading,
        _scope,
        _error_view,
        mo.md("## New policy screen"),
        _controls,
        mo.md("## Saved runs"),
        _history,
        _results,
        mo.md(
            "Differences are model-based counterfactual forecasts, not measured policy effects."
        ),
    ], gap=1.5)
    observed_policy_view
    return (observed_policy_view,)


@app.cell
def _(get_result, mo, observed_policy_cohort):
    _path, _saved_state, _ = get_result()
    try:
        _saved_for_picker = (
            observed_policy_cohort.show(_path) if _path is not None else _saved_state
        )
    except (OSError, ValueError, KeyError, TypeError):
        _saved_for_picker = _saved_state
    _options = {}
    if _saved_for_picker is not None:
        for _case in _saved_for_picker["cases"]:
            _label = (
                f'{_case["case_id"].replace("case-", "Scenario ")} · '
                f'Recorded: {_case["recorded_outcome"].replace("-", " ")} · '
                f'Proposed: {_case["proposed_outcome"].replace("-", " ")}'
            )
            _options[_label] = _case["case_id"]
    individual_selector = (
        mo.ui.dropdown(
            _options,
            value=next(iter(_options)),
            allow_select_none=False,
            label="Individual held-out scenario",
            full_width=True,
        )
        if _options else None
    )
    return (individual_selector,)


if __name__ == "__main__":
    app.run()
