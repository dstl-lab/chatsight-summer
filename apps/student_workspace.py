import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Student workspace")


@app.cell
def _():
    from pathlib import Path
    import marimo as mo
    from src.agents import tutor_context
    from src.agents.student_workspace import advance
    return Path, advance, mo, tutor_context


@app.cell
def _(Path, mo):
    _args = mo.cli_args()
    _session = _args.get("session")
    mo.stop(not isinstance(_session, str) or not _session.strip(),
            mo.callout("Open this app with a saved student session. See the workspace setup guide.", kind="warn"))
    folder = Path(_session).resolve()
    send_enabled = _args.get("send") is True
    return folder, send_enabled


@app.cell
def _(folder, mo, tutor_context):
    try:
        _initial = tutor_context.snapshot(folder)
        _error = ""
    except (OSError, ValueError) as _exc:
        _initial, _error = None, str(_exc)
    # Callbacks only: rerendering these controls never dispatches a student action.
    get_view, set_view = mo.state((_initial, _error, ""), allow_self_loops=True)
    return get_view, set_view


@app.cell
def _(advance, folder, get_view, mo, send_enabled, set_view, tutor_context):
    _packet, _error, _draft = get_view()

    def _refresh(_=None):
        try:
            set_view((tutor_context.snapshot(folder), "", _draft))
        except (OSError, ValueError) as exc:
            set_view((None, str(exc), _draft))

    _reload = mo.ui.button(label="Reload saved session", on_change=_refresh)
    _heading = mo.md("# Student workspace\nInspect the saved student and continue one decision at a time.")
    _error_view = mo.callout(mo.plain_text(_error), kind="danger") if _error else mo.md("")
    mo.stop(_packet is None, mo.vstack([_heading, _error_view, _reload]))

    _waiting = _packet["status"] == "awaiting-tutor"
    _can_step = _packet["status"] in ("active", "awaiting-tutor") and _packet["decisions_remaining"] > 0

    def _submit(value, binding=dict(_packet["binding"]), waiting=_waiting):
        if waiting and value is None:
            return
        try:
            _updated = advance(folder, binding=binding, tutor_reply=value if waiting else None,
                               send=send_enabled)
            set_view((_updated, "", ""))
        except (OSError, ValueError) as exc:
            # Keep the displayed binding and any typed guidance until the researcher reloads.
            set_view((_packet, str(exc), value if waiting else ""))

    _status = {
        "active": "The student can continue working. There is no message awaiting a tutor reply.",
        "awaiting-tutor": "The student is waiting for your tutor reply.",
        "no-reply": "The student chose to stop without replying.",
        "error": "The simulation stopped after an error. Inspect the saved operation before starting another session.",
        "environment-error": "The local check could not run. This work is ungraded.",
        "execution-limit": "The local check reached its execution limit. This work is ungraded.",
    }.get(_packet["status"], "This encounter has stopped.")
    if _packet["decisions_remaining"] <= 0 and _packet["status"] in ("active", "awaiting-tutor"):
        _status = "The decision budget is used up. This is a simulation pause, not student silence."

    _block = tutor_context._block
    _work = mo.md("### Current work\n" + _block(_packet["work"]["source"], "python"))
    _feedback = (mo.md("### Latest check\n" + _block(_packet["feedback"], "json"))
                 if _packet["feedback"] else mo.md("No check feedback for this revision."))
    _changes = mo.md("Net changes since the initial work or last supplied tutor exchange.\n\n" +
                     (_block(_packet["changes"]["unified_diff"], "diff")
                      if _packet["changes"]["unified_diff"] else "No source changes yet."))
    _conversation = [mo.md("Earlier dialogue and your supplied tutor interventions.")]
    for _turn in _packet["dialogue"]:
        _conversation.append(mo.md(f"**{_turn['role'].capitalize()}**\n\n" + _block(_turn["text"])))
    if _waiting:
        _conversation.append(mo.md("**Student awaiting a reply**\n\n" + _block(_packet["pending_message"])))
    _tabs = mo.ui.tabs({
        "Work": mo.vstack([_work, _feedback]),
        "Changes": _changes,
        "Conversation": mo.vstack(_conversation),
    })
    if _waiting and _can_step:
        _controls = mo.vstack([
            mo.md("### Student message\n" + _block(_packet["pending_message"])),
            mo.ui.text_area(value=_draft, label="Your tutor reply", full_width=True).form(
                submit_button_label="Send guidance and continue one decision",
                submit_button_disabled=not send_enabled, show_clear_button=False,
                validate=lambda value: None if value and value.strip() else "Write a tutor reply first.",
                on_change=_submit),
        ])
    elif _can_step:
        _controls = mo.ui.button(label="Continue one student decision", disabled=not send_enabled,
                                 on_change=_submit, kind="success")
    else:
        _controls = mo.md("This saved encounter cannot continue. Its work and history remain available above.")
    _mode = ("Each continuation sends the visible task, work and conversation to Gemini. "
             "A local container runs a check only if the student requests one."
             if send_enabled else "Viewing only. Sending is disabled for this workspace.")
    mo.vstack([
        _heading, mo.md("## Task"), mo.plain_text(_packet["task"]),
        mo.md(_status + f" **{_packet['decisions_remaining']} decisions remaining.**"),
        _error_view, _tabs, _controls, mo.md(_mode), _reload,
        mo.accordion({"Supplied context and scope": mo.vstack([
            mo.md(_block(_packet["initialization"])),
            mo.md("Only the selected cell and recorded feedback are available. "
                  "A successful check does not establish learning or fidelity to real students. "
                  "Reloading reads saved evidence without generating another action."),
        ])}),
    ], gap=1.5)
    return


if __name__ == "__main__":
    app.run()
