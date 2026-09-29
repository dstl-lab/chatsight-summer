"""Authored recorded observations use native, prefix-only Marimo views."""
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

mo = pytest.importorskip("marimo")

from apps.notebook_replay import app
from src.eval import notebook_replay


def _text(html):
    parts = []
    parser = HTMLParser()
    parser.handle_data = parts.append
    parser.feed(html)
    return "".join(parts)


@pytest.fixture
def recorded(monkeypatch, tmp_path):
    from tests.test_notebook_replay import recorded_projection

    packet = recorded_projection()
    packet["events"][0].update(student_question='VISIBLE STUDENT <script>alert(1)</script>',
                               effective_question="VISIBLE EFFECTIVE")
    packet["events"][1]["tutor_reply"] = "VISIBLE TUTOR"
    packet["events"][4]["output"] = "VISIBLE OUTPUT"
    source = tmp_path / "recorded.json"
    source.write_text(json.dumps(packet))
    digest = sha256(source.read_bytes()).hexdigest()
    calls = []
    real_load = notebook_replay.load_recorded

    def load(path, *, expected_sha256):
        calls.append((path, expected_sha256))
        return real_load(path, expected_sha256)

    monkeypatch.setattr(notebook_replay, "load_recorded", load)
    monkeypatch.setattr(notebook_replay, "load_replay", lambda *_a, **_kw: pytest.fail("Synthetic loader called in recorded mode"))
    args = {"recorded-replay": str(source), "recorded-sha256": digest}
    monkeypatch.setattr(mo, "cli_args", lambda: args)
    return args, calls


def test_recorded_app_run_selects_difference_and_keeps_future_out(recorded):
    args, calls = recorded
    _, definitions = app.run()
    assert len(calls) == 1 and calls[0][1] == args["recorded-sha256"]
    assert "replay_view" not in definitions
    assert definitions["recorded_event_picker"].value == 3
    assert definitions["recorded_frame"]["event"]["sequence"] == 4
    html = definitions["recorded_view"].text
    text = _text(html)
    assert "VISIBLE STUDENT" in text and "VISIBLE TUTOR" in text and "VISIBLE EFFECTIVE" in text
    assert "FUTURE_" not in html and '<script>alert(1)</script>' not in html
    assert "Net difference" in html and "Historical notebook capture" in html
    assert "Submitted execution source" in html and "VISIBLE OUTPUT" not in html
    assert "Later evidence" in html and "Result not yet recorded" in html
    assert "marimo-code-editor" in html and 'disabled' in html
    assert "iframe" not in html

    _, completed = app.run(defs={"recorded_event_picker": SimpleNamespace(value=4)})
    result = completed["recorded_view"].text
    assert "VISIBLE OUTPUT" in result and "not an assignment grade" in result
    assert "FUTURE_" not in result
    _, earlier = app.run(defs={"recorded_event_picker": SimpleNamespace(value=2)})
    unknown = earlier["recorded_view"].text
    assert "Source unavailable for this change" in unknown
    assert "VISIBLE OUTPUT" not in unknown and "FUTURE_" not in unknown


def test_recorded_sequence_gap_remains_inspectable(recorded):
    args, _ = recorded
    source = Path(args['recorded-replay'])
    packet = json.loads(source.read_text())
    packet['events'] = [event for event in packet['events'] if event['sequence'] != 3]
    packet['summary'].update(event_count=6, gaps=[3])
    source.write_text(json.dumps(packet))
    args['recorded-sha256'] = sha256(source.read_bytes()).hexdigest()
    _, definitions = app.run()
    text = _text(definitions['recorded_view'].text)
    assert 'Missing client sequence: 3' in text
    assert 'VISIBLE STUDENT' in text and 'FUTURE_' not in text


@pytest.mark.parametrize("changes", [
    {"session": "also-synthetic"}, {"previous": "prior"}, {"send": True},
    {"recorded-sha256": None},
])
def test_recorded_cli_rejects_conflicting_or_unpinned_mode(recorded, changes):
    args, calls = recorded
    args.update(changes)
    _, definitions = app.run()
    assert calls == [] and "recorded_view" not in definitions


def test_existing_synthetic_app_still_runs(tmp_path, monkeypatch):
    from src.agents import notebook_student as student
    from tests.test_notebook_session import ACTIVITY, TASK

    folder = tmp_path / "synthetic"
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id="authored/marimo-replay")
    student.step(folder, generate=lambda *_: student.Action(decision="no-reply", text="", source=None),
                 check=None, max_actions=1)
    monkeypatch.setattr(mo, "cli_args", lambda: {"session": str(folder)})
    monkeypatch.setattr(notebook_replay, "load_recorded", lambda *_a, **_kw: pytest.fail("Recorded loader called in synthetic mode"), raising=False)
    monkeypatch.setattr(student.llm, "make_generate", lambda *_a, **_kw: pytest.fail("Replay called a model"))
    _, definitions = app.run()
    assert "replay_view" in definitions and "recorded_view" not in definitions
    assert "Notebook simulation replay" in definitions["replay_view"].text
