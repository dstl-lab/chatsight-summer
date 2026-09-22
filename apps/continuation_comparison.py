import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Recorded vs simulated continuation")


@app.cell
def _():
    from pathlib import Path
    import marimo as mo
    from src.agents import tutor_context
    from src.eval import heldout_continuation
    return Path, heldout_continuation, mo, tutor_context


@app.cell
def _(Path, mo):
    _folder = mo.cli_args().get("comparison")
    mo.stop(not isinstance(_folder, str) or not _folder.strip(),
            mo.callout("Open with --comparison /path/to/saved/case.", kind="warn"))
    comparison_path = Path(_folder).resolve()
    return (comparison_path,)


@app.cell
def _(comparison_path, heldout_continuation):
    try:
        comparison = heldout_continuation.load(comparison_path)
        comparison_error = ""
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as _exc:
        comparison, comparison_error = None, str(_exc)
    return comparison, comparison_error


@app.cell
def _(comparison, comparison_error, mo):
    mo.stop(comparison is None,
            mo.vstack([
                mo.md("# Recorded vs simulated continuation"),
                mo.callout(mo.plain_text(comparison_error), kind="danger"),
            ]))
    return


@app.cell
def _(comparison, mo, tutor_context):
    _block = tutor_context._block
    _review = comparison["review"]
    _prefix = _review["prefix"]
    _prefix_turns = _prefix["context"] + _prefix["turns"]

    _history = []
    for _turn in _prefix_turns:
        _text = "\n".join(_line["text"] for _line in _turn["lines"])
        _history.append(mo.md(
            f'**{_turn["role"].capitalize()} | Recorded history**\n\n'
            + _block(_text)
        ))
    _history_view = mo.vstack(_history, gap=1) if _history else mo.md("No visible history was saved.")

    _candidate_views = {}
    for _candidate in _review["candidates"]:
        _origin = _candidate["origin"]
        _title = "Recorded next message" if _origin == "recorded" else "Simulated next message"
        if _candidate["turns"]:
            _body = mo.vstack([
                mo.md(f'**Student | {_title}**'),
                mo.md(_block(_candidate["turns"][0]["text"])),
            ])
        elif _origin == "generated" and _candidate["status"] == "no-reply":
            _body = mo.callout("The simulation chose not to send another student message.", kind="neutral")
        else:
            _body = mo.callout("No next student message was recorded.", kind="neutral")
        _candidate_views[_title] = _body

    _provenance = comparison["provenance"]
    _provenance_view = mo.vstack([
        mo.md("### Saved provenance"),
        mo.md(
            f'**Model:** `{_provenance["model"]}`  \n'
            f'**Logical requests:** {_provenance.get("logical_requests", _provenance.get("provider_requests"))}  \n'
            '**Provider attempts (including retries):** Unmeasured  \n'
            f'**Source snapshot:** `{_provenance["source_snapshot"]}`  \n'
            f'**Prompt SHA-256:** `{_provenance["prompt_sha256"]}`  \n'
            f'**Comparison SHA-256:** `{comparison["sha256"]}`'
        ),
        mo.md("### Limits\n\n" + "\n".join(f"- {item}" for item in comparison["limits"])),
    ], gap=1)
    _candidate_views["Provenance and limits"] = _provenance_view

    comparison_view = mo.vstack([
        mo.md("# Recorded vs simulated continuation"),
        mo.callout("This page contains real student conversation text. Keep it local.", kind="warn"),
        mo.md("## Shared recorded history"),
        _history_view,
        mo.md("## What happened next"),
        mo.ui.tabs(_candidate_views),
        mo.md("This single case demonstrates the workflow. It does not measure simulation accuracy."),
    ], gap=1.5)
    comparison_view
    return (comparison_view,)


if __name__ == "__main__":
    app.run()
