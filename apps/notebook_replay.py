import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Notebook simulation replay")


@app.cell
def _():
    from pathlib import Path
    import marimo as mo
    from src.agents import tutor_context
    from src.eval import notebook_replay
    return Path, mo, notebook_replay, tutor_context


@app.cell
def _(Path, mo):
    _args = mo.cli_args()
    _session = _args.get("session")
    _previous = _args.get("previous")
    mo.stop(not isinstance(_session, str) or not _session.strip(),
            mo.callout("Open with --session /path/to/saved/session.", kind="warn"))
    mo.stop(_previous is not None and (not isinstance(_previous, str) or not _previous.strip()),
            mo.callout("When supplied, --previous must name the saved predecessor session.", kind="warn"))
    session_path = Path(_session).resolve()
    previous_path = Path(_previous).resolve() if _previous is not None else None
    return previous_path, session_path


@app.cell
def _(notebook_replay, previous_path, session_path):
    try:
        replay = notebook_replay.load_replay(session_path, previous=previous_path)
        replay_error = ""
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as _exc:
        replay, replay_error = None, str(_exc)
    return replay, replay_error


@app.cell
def _(mo, replay, replay_error):
    mo.stop(replay is None,
            mo.vstack([
                mo.md("# Notebook simulation replay"),
                mo.callout(mo.plain_text(replay_error), kind="danger"),
            ]))
    task_options = {task["title"]:task["number"] - 1 for task in replay["tasks"]}
    task_picker = mo.ui.dropdown(task_options, value=next(iter(task_options)),
                                 allow_select_none=False, label="Task")
    return (task_picker,)


@app.cell
def _(replay, task_picker):
    selected_task = replay["tasks"][task_picker.value]
    return (selected_task,)


@app.cell
def _(mo, selected_task):
    def _event_label(event):
        if event["kind"] == "tutor-intervention":
            return f'{event["sequence"]}. Tutor intervention'
        action = event["action"]
        decision = action["decision"]
        detail = {
            "reply":"Student message",
            "revise-work":"Student edited work" + (" and sent a message" if action["text"] else " quietly"),
            "request-check":"Student requested a check",
            "no-reply":"Student chose no reply",
        }.get(decision, "Student action")
        feedback = event["feedback"]
        if decision == "request-check" and feedback is not None:
            if feedback["status"] == "checked":
                detail += " (pass)" if feedback["success"] else " (fail)"
            else:
                detail += f' ({feedback["status"]})'
        return f'{event["sequence"]}. {detail}'

    event_options = {_event_label(event):index for index,event in enumerate(selected_task["events"])}
    event_picker = (mo.ui.dropdown(event_options, value=next(iter(event_options)),
                    allow_select_none=False, label="Recorded event") if event_options else None)
    timeline_labels = list(event_options)
    return event_picker, timeline_labels


@app.cell
def _(event_picker, selected_task):
    selected_event = selected_task["events"][event_picker.value] if event_picker is not None else None
    return (selected_event,)


@app.cell
def _(mo, replay, selected_event, selected_task, task_picker, timeline_labels, tutor_context):
    _block = tutor_context._block
    _final = selected_task["final"]
    _disposition = {
        "no-reply":"The student chose to stop without replying.",
        "budget-exhausted":"The decision budget is exhausted. This is a runner pause, not student silence.",
        "awaiting-tutor":"The student is waiting for a tutor reply.",
        "active":"The saved encounter remains active.",
        "error":"The runner stopped with an error.",
        "environment-error":"Local execution was unavailable; this work is ungraded.",
        "execution-limit":"The local check reached its execution limit; this work is ungraded.",
    }.get(_final["disposition"], "The saved encounter has stopped.")

    _conversation = []
    for _turn in selected_task["dialogue"]:
        _origin = {"model":"Simulated", "generated":"Simulated", "scripted":"Intervention",
                   "supplied":"Supplied context"}.get(_turn.get("origin"), "Supplied context")
        _conversation.append(mo.md(f'**{_turn["role"].capitalize()} | {_origin}**\n\n' + _block(_turn["text"])))
    for _event in selected_task["events"]:
        if _event["kind"] == "tutor-intervention":
            _conversation.append(mo.md("**Tutor | Supplied intervention**\n\n" + _block(_event["text"])))
        elif _event["action"]["text"]:
            _conversation.append(mo.md("**Student | Simulated**\n\n" + _block(_event["action"]["text"])))
    _conversation_view = (mo.vstack(_conversation, gap=1) if _conversation
                          else mo.md("No dialogue was recorded for this task."))

    if selected_event is None:
        _overview = mo.md("No student action has been recorded.")
        _code = mo.md("No recorded action is available for code comparison.")
        _check = mo.md("No recorded check is available.")
    elif selected_event["kind"] == "tutor-intervention":
        _overview = mo.vstack([
            mo.md("### Tutor intervention"),
            mo.md("**Origin:** Supplied intervention"),
            mo.md(_block(selected_event["text"])),
        ])
        _code = mo.md("This tutor intervention did not record a notebook revision.")
        _check = mo.md("This tutor intervention did not request a check.")
    else:
        _action = selected_event["action"]
        _decision_text = {
            "reply":"Student sent a message",
            "revise-work":"Student edited the selected cell",
            "request-check":"Student requested a local check",
            "no-reply":"Student chose no reply",
        }.get(_action["decision"], _action["decision"])
        _overview_parts = [
            mo.md(f"### Action {selected_event['number']}: {_decision_text}"),
            mo.md(f'**Origin:** {selected_event["origin"]}'),
        ]
        if _action["text"]:
            _overview_parts.extend([mo.md("**Student message**"), mo.md(_block(_action["text"]))])
        elif _action["decision"] == "revise-work":
            _overview_parts.append(mo.md("This was a quiet edit with no student message."))
        _overview = mo.vstack(_overview_parts)

        _before = selected_event["work_before"]
        _after = selected_event["work_after"]
        _diff = selected_event["code_diff"]
        _code = mo.vstack([
            mo.md(f'**Selected cell {_after["cell_index"]}: revision {_before["revision"]} to {_after["revision"]}**'),
            mo.md("### Code change\n\n" + (_block(_diff, "diff") if _diff else "No source change in this action.")),
            mo.accordion({"Work after this action": mo.md(_block(_after["source"], "python"))}),
        ])

        _feedback = selected_event["feedback"]
        if _feedback is None:
            _check = mo.md("This action did not record a check result.")
        else:
            _status = _feedback["status"]
            if _status == "checked":
                _check_heading = "Recorded check passed" if _feedback["success"] else "Recorded check failed"
                _check_kind = "success" if _feedback["success"] else "danger"
            elif _status == "runtime-error":
                _check_heading, _check_kind = "Recorded runtime error; ungraded", "warn"
            else:
                _check_heading, _check_kind = f"Recorded {_status}; ungraded", "warn"
            _check = mo.vstack([
                mo.callout(_check_heading, kind=_check_kind),
                mo.md(_block(_feedback, "json")),
            ])

    _timeline = ("\n".join(f"- {'**' if selected_event is not None and index == selected_event['sequence'] else ''}"
                            f"Event {label.replace('. ', ': ', 1)}"
                            f"{'**' if selected_event is not None and index == selected_event['sequence'] else ''}"
                            for index,label in enumerate(timeline_labels, 1))
                 if timeline_labels else "No recorded actions.")
    _shared = (mo.md(_block(selected_task["shared_history"], "json"))
               if selected_task["shared_history"] else mo.md("No earlier task history was supplied."))
    _context_sections = {
        "Initial task context": mo.md(_block(selected_task["initialization"])),
        "Initial selected-cell work": mo.md(_block(selected_task["initial_work"]["source"], "python")),
        "Declared activity": mo.md(_block(selected_task["activity"], "json")),
        "Shared earlier-task records": _shared,
    }
    if selected_task["conversation_example"] is not None:
        _context_sections["Recorded communication example"] = mo.md(
            _block({"scope": selected_task["communication_scope"],
                    "conversation": selected_task["conversation_example"]}, "json"))
    _context = mo.accordion(_context_sections)
    _tabs = mo.ui.tabs({
        "Event": _overview,
        "Code": _code,
        "Check": _check,
        "Conversation": _conversation_view,
    })
    _task_control = task_picker if replay["linked"] else mo.md("")
    _event_control = event_picker if event_picker is not None else mo.md("")
    replay_view = mo.vstack([
        mo.md("# Notebook simulation replay"),
        mo.callout("This view contains saved conversation text and code. Keep it local.", kind="warn"),
        _task_control,
        mo.md("## Task"),
        mo.plain_text(selected_task["task"]),
        mo.md(f'**{_disposition}** Decisions used: {_final["decisions_used"]} / {_final["max_decisions"]}.'),
        mo.md("## Recorded timeline\n\n" + _timeline),
        _event_control,
        _tabs,
        _context,
        mo.md("Checks apply only to their recorded revision and supplied data. A pass is not a general correctness proof."),
    ], gap=1.5)
    replay_view
    return (replay_view,)


if __name__ == "__main__":
    app.run()
