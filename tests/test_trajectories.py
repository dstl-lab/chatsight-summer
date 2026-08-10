import json
import sys
from pathlib import Path

import pytest

from src.ingest.rawlog import Conversation, Turn
from src.labeling.draft import MessageLabels
from src.labeling.schema import LabelDef, LabelSchema
from src.trajectories.extract import (build_trajectory_report,
                                      default_output_path,
                                      main)


def _conv(conv_id: str, chatlog_id: int, student_texts: list[str]
          ) -> Conversation:
    turns = []
    for i, text in enumerate(student_texts):
        turns.append(Turn(index=2 * i, role="student", text=text,
                          student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"a{i}"))
    return Conversation(conv_id=conv_id, chatlog_id=chatlog_id,
                        notebook="lab.ipynb", started_at=None, turns=turns)


def _schema() -> LabelSchema:
    return LabelSchema(instructor_intent="i", labels=[
        LabelDef(name="confused", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n"),
        LabelDef(name="asks-answer", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n"),
    ])


def _ml(chatlog_id: int, message_index: int, **labels: bool) -> MessageLabels:
    names = ["confused", "asks-answer"]
    full = {name: labels.get(name, False) for name in names}
    return MessageLabels(chatlog_id=chatlog_id, message_index=message_index,
                         labels=full,
                         rationales={name: "invented rationale"
                                     for name in full})


def _snapshot(tmp_path: Path, labels: list[MessageLabels] | None = None
              ) -> tuple[Path, LabelSchema]:
    schema = _schema()
    conversations = [
        _conv("a", 1, ["alpha q0", "alpha q1"]),
        _conv("b", 2, ["beta q0"]),
    ]
    if labels is None:
        second = _ml(1, 2, **{"asks-answer": True}).model_copy(update={
            "no_label_fits": True,
            "move": "follow-up",
            "latency_seconds": 120.0,
            "latency_bucket": "working",
            "forms": ["code"],
            "concepts": ["loop"],
        })
        labels = [
            _ml(1, 0, confused=True),
            second,
            _ml(2, 0),
        ]
    snap = tmp_path / "snap1"
    snap.mkdir()
    (snap / "conversations.jsonl").write_text(
        "".join(c.model_dump_json() + "\n" for c in conversations))
    (snap / "labels.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in labels))
    (snap / "schema.json").write_text(schema.model_dump_json())
    (snap / "manifest.json").write_text(json.dumps({
        "snapshot_id": snap.name,
        "schema_version": schema.version_id,
        "classifier_hash": "hash123",
        "repo_sha": "abc",
    }))
    return snap, schema


def test_build_trajectory_report_orders_steps_and_preserves_label_state(tmp_path):
    snap, schema = _snapshot(tmp_path)
    report = build_trajectory_report(snap)

    assert report["metadata"]["snapshot_id"] == snap.name
    assert report["metadata"]["schema_version"] == schema.version_id
    assert report["metadata"]["classifier_hash"] == "hash123"
    assert report["metadata"]["label_names"] == ["confused", "asks-answer"]
    assert report["metadata"]["row_counts"] == {
        "conversations": 2, "trajectories": 2, "steps": 3}

    first = report["trajectories"][0]
    assert first["conv_id"] == "a"
    assert [s["message_index"] for s in first["steps"]] == [0, 2]
    assert first["steps"][0]["active_labels"] == ["confused"]
    assert first["steps"][1] == {
        "message_index": 2,
        "student_index": 1,
        "active_labels": ["asks-answer"],
        "no_label_fits": True,
        "move": "follow-up",
        "latency_seconds": 120.0,
        "latency_bucket": "working",
        "forms": ["code"],
        "concepts": ["loop"],
    }
    assert report["trajectories"][1]["steps"][0]["active_labels"] == []


def test_trajectory_report_omits_student_text_and_rationales(tmp_path):
    snap, _ = _snapshot(tmp_path)
    rendered = json.dumps(build_trajectory_report(snap))
    assert "alpha q0" not in rendered
    assert "alpha q1" not in rendered
    assert "beta q0" not in rendered
    assert "invented rationale" not in rendered


def test_missing_label_row_raises(tmp_path):
    snap, _ = _snapshot(tmp_path, labels=[
        _ml(1, 0, confused=True),
        _ml(1, 2),
    ])
    with pytest.raises(ValueError, match="missing labels"):
        build_trajectory_report(snap)


def test_extra_label_row_raises(tmp_path):
    snap, _ = _snapshot(tmp_path, labels=[
        _ml(1, 0, confused=True),
        _ml(1, 2),
        _ml(2, 0),
        _ml(99, 0),
    ])
    with pytest.raises(ValueError, match="not found in conversations"):
        build_trajectory_report(snap)


def test_cli_writes_requested_output(tmp_path, monkeypatch, capsys):
    snap, _ = _snapshot(tmp_path)
    out = tmp_path / "trajectories.json"
    monkeypatch.setattr(sys, "argv", [
        "extract-trajectories", str(snap), "--out", str(out)])

    main()

    saved = json.loads(out.read_text())
    assert saved["metadata"]["snapshot_id"] == snap.name
    assert len(saved["trajectories"]) == 2
    assert "wrote" in capsys.readouterr().out


def test_default_output_path_sits_next_to_snapshots_dir(tmp_path):
    snap = tmp_path / "data" / "snapshots" / "snap1"
    assert default_output_path(snap) == \
        tmp_path / "data" / "trajectories" / "snap1" / "trajectories.json"
