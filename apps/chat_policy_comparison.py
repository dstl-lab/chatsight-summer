import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Tutor policy comparison")


@app.cell
def _():
    import html
    from pathlib import Path
    import marimo as mo
    from src.agents import chat_policy_pair
    return Path, chat_policy_pair, html, mo


@app.cell
def _(Path, mo):
    _args = mo.cli_args()
    _comparison = _args.get("comparison")
    mo.stop(not isinstance(_comparison, str) or not _comparison.strip(),
            mo.callout("Open an existing comparison with --comparison /path/to/comparison.", kind="warn"))
    folder = Path(_comparison).resolve()
    send_enabled = _args.get("send") is True
    return folder, send_enabled


@app.cell
def _(chat_policy_pair, folder, mo):
    try:
        _initial, _error = chat_policy_pair.show(folder), ""
    except (OSError, ValueError) as _exc:
        _initial, _error = None, str(_exc)
    get_view, set_view = mo.state((_initial, _error), allow_self_loops=True)
    return get_view, set_view


@app.cell
def _(chat_policy_pair, folder, get_view, html, mo, send_enabled, set_view):
    _packet, _error = get_view()

    def _wrapped_text(value):
        return mo.Html(
            '<div style="white-space: pre-wrap; overflow-wrap: anywhere; '
            'word-break: break-word; max-width: 100%;">'
            + html.escape(value) + '</div>'
        )

    def _refresh(_=None, selected_folder=folder, message=""):
        try:
            set_view((chat_policy_pair.show(selected_folder), message))
        except (OSError, ValueError) as exc:
            set_view((None, str(exc)))

    _reload = mo.ui.button(label="Reload saved comparison", on_change=_refresh)
    _heading = mo.md("# Tutor policy comparison\nBoth conditions start from the same cached simulated student reply.")
    _error_view = mo.callout(mo.plain_text(_error), kind="danger") if _error else mo.md("")
    # Keep a public reference in both paths: standalone Marimo clears private variables.
    comparison_view = mo.vstack([_heading, _error_view, _reload])
    mo.stop(_packet is None, comparison_view)

    _condition_views = {}
    for _key in ("a", "b"):
        _condition = _packet["conditions"][_key]
        _snapshot = _condition["snapshot"]
        _condition_error = _condition["error"]
        _ready = (_snapshot is not None and not _condition_error
                  and _snapshot["status"] == "awaiting-tutor"
                  and _snapshot["decisions_remaining"] > 0)
        if _condition_error:
            _status = "This condition needs inspection. Saved operations are not automatically retried."
        elif _snapshot is None:
            _status = "This condition could not be loaded."
        elif _snapshot["status"] == "error":
            _status = "Generation failed. Inspect the saved result; this condition cannot continue."
        elif _snapshot["status"] == "no-reply":
            _status = "The simulated student stopped without replying."
        elif _snapshot["decisions_remaining"] <= 0:
            _status = "The fixed decision budget is used up. This is a simulation pause."
        elif _ready:
            _status = "Ready for one tutor reply and one student decision."
        else:
            _status = "This condition cannot continue from its saved state."
        if _snapshot is not None:
            _status += f" {_snapshot['decisions_remaining']} decisions remaining."

        _conversation = []
        if _snapshot is not None:
            for _turn in _snapshot["dialogue"]:
                _origin = {"source": "Recorded", "generated": "Simulated",
                           "scripted": "Tutor intervention", "supplied": "Tutor intervention"}.get(
                               _turn.get("origin"), "Supplied context")
                _conversation.append(mo.vstack([
                    mo.md(f"**{_turn['role'].capitalize()} · {_origin}**"),
                    _wrapped_text(_turn["text"]),
                ], gap=0.5))
            if _snapshot["pending_message"]:
                _conversation.append(mo.vstack([
                    mo.md("**Simulated student · Awaiting a tutor reply**"),
                    _wrapped_text(_snapshot["pending_message"]),
                ], gap=0.5))
        else:
            _conversation.append(mo.md("The saved results remain available in the next tab."))

        _controls = mo.md("")
        if _ready and send_enabled:
            def _continue(_, condition=_key, binding=dict(_snapshot["binding"]), selected_folder=folder):
                try:
                    with mo.status.spinner(title=f"Continuing condition {condition.upper()}",
                                           subtitle="Generating one tutor reply and one student decision."):
                        updated = chat_policy_pair.respond(selected_folder, condition, binding=binding, send=send_enabled)
                    set_view((updated, ""))
                except Exception as exc:
                    # Reopen saved evidence after failure; never dispatch a retry here.
                    _refresh(selected_folder=selected_folder, message=str(exc))

            _controls = mo.ui.button(label=f"Continue condition {_key.upper()} one decision",
                                     on_change=_continue, kind="success")
        _condition_views[f"Condition {_key.upper()}"] = mo.vstack([
            mo.md("### Fixed tutor policy"),
            _wrapped_text(_condition["policy"]), mo.md(_status),
            mo.callout(mo.plain_text(_condition_error), kind="danger") if _condition_error else mo.md(""),
            _controls,
            mo.ui.tabs({"Conversation": mo.vstack(_conversation),
                        "Saved results": mo.md(_condition["history"])}),
        ], gap=1)

    comparison_view = mo.vstack([
        _heading, mo.plain_text("Comparison: " + _packet["comparison_id"]),
        mo.md(f"Each condition allows up to **{_packet['max_new_decisions']} new student decisions**. "
              "The cached first reply is a simulated starting point, not an observed student future."),
        mo.md("Open each condition tab to compare its fixed policy, tutor response, and simulated student response."),
        _error_view, mo.ui.tabs(_condition_views),
        mo.md("Continuing sends only the selected condition's fixed policy and visible conversation to Gemini."
              if send_enabled else "Viewing only. Sending is disabled for this comparison."),
        _reload,
        mo.md("Reloading reads saved results without generating a reply. Notebook activity is unknown. "
              "A single pair does not establish a policy effect, learning or student fidelity."),
    ], gap=1.5)
    comparison_view
    return (comparison_view,)


if __name__ == "__main__":
    app.run()
