import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Student workspace")


@app.cell
def _():
    from pathlib import Path
    import marimo as mo
    from src.agents import chat_workspace, notebook_tutor, tutor_context, workspace_history
    from src.agents.student_workspace import advance, respond
    return Path, advance, chat_workspace, mo, notebook_tutor, respond, tutor_context, workspace_history


@app.cell
def _(chat_mode, folder, initial_policy, mo):
    # Keep drafts through refresh, but reset them when selecting another scenario.
    _selected_folder = folder
    tutor_inputs = mo.ui.dictionary({
        "mode": mo.ui.radio({"Tutor policy": "policy", "Write a reply": "reply"},
                            value="Tutor policy", inline=True),
        "reply": mo.ui.text_area(label="Your tutor reply", full_width=True, debounce=False),
        "policy": mo.ui.text_area(label="Tutor policy", full_width=True, debounce=False,
            value=initial_policy if initial_policy is not None else (
                "Respond concisely to the student's current request using the visible conversation." if chat_mode else
                "Respond concisely to the student's current request using the visible work and check feedback.")),
    })
    return (tutor_inputs,)


@app.cell
def _(Path, mo, notebook_tutor):
    _args = mo.cli_args()
    _session = _args.get("session")
    _chats = _args.get("chat-sessions")
    _selected = _session if _session is not None else _chats
    mo.stop((_session is None) == (_chats is None) or
            not isinstance(_selected, str) or not _selected.strip(),
            mo.callout("Open with either --session or --chat-sessions. See the workspace setup guide.", kind="warn"))
    session_folder = Path(_session).resolve() if _session is not None else None
    chat_root = Path(_chats).resolve() if _chats is not None else None
    send_enabled = _args.get("send") is True
    initial_policy = None
    _policy_file = _args.get("policy-file")
    if _policy_file is not None:
        mo.stop(not isinstance(_policy_file, str) or not _policy_file.strip(),
                mo.callout("Supply a file path with --policy-file.", kind="danger"))
        try:
            initial_policy = Path(_policy_file).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as _exc:
            mo.stop(True, mo.callout(mo.plain_text("Tutor policy could not be read: " + str(_exc)), kind="danger"))
        mo.stop(not initial_policy.strip(), mo.callout("The tutor policy file is blank.", kind="danger"))
    library_reference = None
    _reference_file = _args.get("reference-file")
    if _reference_file is not None:
        mo.stop(chat_root is not None, mo.callout("--reference-file is only available for notebook sessions.", kind="danger"))
        mo.stop(not isinstance(_reference_file, str) or not _reference_file.strip(),
                mo.callout("Supply a file path with --reference-file.", kind="danger"))
        try:
            library_reference = notebook_tutor.LibraryReference.model_validate_json(
                Path(_reference_file).read_text(encoding="utf-8")).model_dump()
        except (OSError, ValueError) as _exc:
            mo.stop(True, mo.callout(mo.plain_text("Library reference could not be loaded: " + str(_exc)), kind="danger"))
    return chat_root, initial_policy, library_reference, send_enabled, session_folder


@app.cell
def _(chat_root, mo):
    scenario_picker = None
    if chat_root is not None:
        try:
            _scenarios = {path.name: path for path in sorted(chat_root.iterdir())
                          if path.is_dir() and not path.is_symlink() and (path / "session.json").is_file()}
        except OSError as _exc:
            mo.stop(True, mo.callout(mo.plain_text(str(_exc)), kind="danger"))
        mo.stop(not _scenarios, mo.callout("No saved conversation scenarios were found in this folder.", kind="warn"))
        scenario_picker = mo.ui.dropdown(_scenarios, value=next(iter(_scenarios)),
                                        allow_select_none=False, label="Conversation scenario")
    return (scenario_picker,)


@app.cell
def _(advance, chat_root, chat_workspace, respond, scenario_picker, session_folder, tutor_context):
    chat_mode = chat_root is not None
    folder = scenario_picker.value if chat_mode else session_folder
    snapshot_session = chat_workspace.snapshot if chat_mode else tutor_context.snapshot
    advance_session = chat_workspace.advance if chat_mode else advance
    respond_session = chat_workspace.respond if chat_mode else respond
    return advance_session, chat_mode, folder, respond_session, snapshot_session


@app.cell
def _(folder, mo, snapshot_session):
    try:
        _initial = snapshot_session(folder)
        _error = ""
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as _exc:
        _initial, _error = None, str(_exc)
    # Callbacks only: rerendering these controls never dispatches a student action.
    get_view, set_view = mo.state((_initial, _error), allow_self_loops=True)
    return get_view, set_view


@app.cell
def _(advance_session, chat_mode, folder, get_view, library_reference, mo, respond_session, scenario_picker,
      send_enabled, set_view, snapshot_session, tutor_context, tutor_inputs, workspace_history):
    _packet, _error = get_view()

    def _refresh(_=None, selected_folder=folder):
        try:
            set_view((snapshot_session(selected_folder), ""))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            set_view((None, str(exc)))

    _reload = mo.ui.button(label="Reload saved session", on_change=_refresh)
    _heading = mo.md("# Student workspace\nInspect the saved student and continue one decision at a time.")
    _selector = mo.vstack([scenario_picker, mo.md("Tutor drafts reset when you choose another scenario.")]) if chat_mode else mo.md("")
    _error_view = mo.callout(mo.plain_text(_error), kind="danger") if _error else mo.md("")
    try:
        _saved_results = mo.md(workspace_history.render(folder))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as _exc:
        _saved_results = mo.callout(mo.plain_text("Saved results could not be read: " + str(_exc)), kind="danger")
    # Standalone Marimo clears private variables; retain the rendered controls.
    workspace_view = mo.vstack([
        _heading, _selector, _error_view, mo.ui.tabs({"Saved results": _saved_results}),
        mo.md("Continuation is unavailable while the saved session cannot be loaded."), _reload,
    ])
    mo.stop(_packet is None, workspace_view)

    _waiting = _packet["status"] == "awaiting-tutor"
    _can_step = _packet["status"] in ("ready", "active", "awaiting-tutor") and _packet["decisions_remaining"] > 0
    _mode = tutor_inputs.value["mode"]

    def _submit(_, binding=dict(_packet["binding"]), waiting=_waiting, mode=_mode,
                selected_folder=folder):
        try:
            if waiting and mode == "policy":
                _updated = respond_session(selected_folder, binding=binding, policy=tutor_inputs.value["policy"], send=send_enabled,
                    **({"reference": library_reference} if library_reference is not None else {}))
            else:
                _updated = advance_session(selected_folder, binding=binding,
                    tutor_reply=tutor_inputs.value["reply"] if waiting else None, send=send_enabled)
            set_view((_updated, ""))
        except Exception as exc:
            # Tutor errors retain their saved receipt; this callback never retries them.
            set_view((_packet, str(exc)))

    _status = {
        "ready": "Ready to generate the first simulated student reply from this recorded conversation.",
        "active": "The student can continue working. There is no message awaiting a tutor reply.",
        "awaiting-tutor": "The student is waiting for a tutor reply.",
        "no-reply": "The student chose to stop without replying.",
        "error": "The simulation stopped after an error. Inspect the saved operation before starting another session.",
        "environment-error": "The local check could not run. This work is ungraded.",
        "execution-limit": "The local check reached its execution limit. This work is ungraded.",
    }.get(_packet["status"], "This encounter has stopped.")
    if _packet["decisions_remaining"] <= 0 and _packet["status"] in ("ready", "active", "awaiting-tutor"):
        _status = "The decision budget is used up. This is a simulation pause, not student silence."

    _block = tutor_context._block
    _work = (mo.md("### Notebook work unavailable\nThis scenario contains conversation records. "
                   "Notebook state, edits and execution are unknown; code inside messages is conversation text.")
             if chat_mode else mo.md("### Current work\n" + _block(_packet["work"]["source"], "python")))
    _feedback = (mo.md("### Latest check\n" + _block(_packet["feedback"], "json"))
                 if _packet["feedback"] else mo.md("No check feedback for this revision."))
    _changes = mo.md("Notebook changes are unavailable for this conversation scenario.") if chat_mode else mo.md("Net changes since the initial work or last supplied tutor exchange.\n\n" +
                     (_block(_packet["changes"]["unified_diff"], "diff")
                      if _packet["changes"]["unified_diff"] else "No source changes yet."))
    _conversation = [mo.md("Recorded messages provide the starting context. Simulated replies and tutor interventions follow.")
                     if chat_mode else mo.md("Saved student and tutor conversation.")]
    if chat_mode:
        _conversation.append(mo.md("Notebook state and execution are unknown for this scenario."))
    for _turn in _packet["dialogue"]:
        _origin = {"source": "Recorded", "generated": "Simulated", "scripted": "Intervention",
                   "supplied": "Intervention"}.get(_turn.get("origin"), "Supplied context")
        _conversation.append(mo.md(f"**{_turn['role'].capitalize()} · {_origin}**\n\n" + _block(_turn["text"])))
    if _waiting:
        _conversation.append(mo.md("**Simulated student · Awaiting a reply**\n\n" + _block(_packet["pending_message"])))
    _tabs = mo.ui.tabs({"Conversation": mo.vstack(_conversation), "Notebook": _work,
                        "Saved results": _saved_results} if chat_mode else {
        "Work": mo.vstack([_work, _feedback]),
        "Changes": _changes,
        "Conversation": mo.vstack(_conversation),
        "Saved results": _saved_results,
    })
    if _can_step:
        _controls = mo.vstack([
            mo.md("### Pending simulated student message\n" + _block(_packet["pending_message"])) if _waiting else mo.md(""),
            tutor_inputs["mode"], tutor_inputs[_mode],
            mo.md("This setup is used when the student asks for help.") if not _waiting else mo.md(""),
            mo.ui.button(label=("Generate tutor reply and continue one decision" if _mode == "policy" else
                                "Send guidance and continue one decision") if _waiting else "Continue one student decision",
                         disabled=not send_enabled, on_change=_submit, kind="success"),
        ])
    else:
        _controls = mo.md("This saved encounter cannot continue. Its work and history remain available above.")
    _send_notice = (("Continuing sends this scenario's visible conversation to Gemini. " if chat_mode else
                    "Continuing sends the visible task, work and conversation to Gemini. ") +
             "Tutor-policy mode replies to a pending student message before the next decision. "
             + ("" if chat_mode else "A local container runs a check only if the student requests one.")
             if send_enabled else "Viewing only. Sending is disabled for this workspace.")
    _reference_notice = (mo.plain_text(
        "Configured tutor reference: " + library_reference["library"] + " " + library_reference["library_version"] +
        ". Sent only when generating a tutor reply; library and version must match the task.")
        if library_reference is not None else mo.md(""))
    workspace_view = mo.vstack([
        _heading, _selector, mo.md("## Scenario" if chat_mode else "## Task"), mo.plain_text(_packet["task"]),
        mo.md(_status + f" **{_packet['decisions_remaining']} decisions remaining.**"),
        _error_view, _tabs, _controls, mo.md(_send_notice), _reference_notice, _reload,
        mo.accordion({"Supplied context and scope": mo.vstack([
            mo.md(_block(_packet["initialization"])),
            mo.md("Only the recorded conversation prefix and subsequent simulated replies/interventions are available. "
                  "No notebook work or learner traits are reconstructed. Reloading generates no reply." if chat_mode else
                  "Only the selected cell and recorded feedback are available. "
                  "A successful check does not establish learning or fidelity to real students. "
                  "Reloading reads saved evidence without generating another action."),
        ])}),
    ], gap=1.5)
    workspace_view
    return (workspace_view,)


if __name__ == "__main__":
    app.run()
