import json
import sys
from pathlib import Path

from src.ingest.rawlog import Conversation, Turn
from src.labeling.profile_report import (default_output_path, main,
                                         profile_conversations)


def _conv(conv_id: str, chatlog_id: int, texts: list[str]) -> Conversation:
    turns = []
    for i, text in enumerate(texts):
        turns.append(Turn(index=2 * i, role="student", text=text,
                          student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"reply {i}"))
    return Conversation(conv_id=conv_id, chatlog_id=chatlog_id,
                        notebook="lab.ipynb", started_at=None, turns=turns)


CONVS = [
    _conv("a", 1, [
        "?",
        "stuck on question 1.6",
        "Traceback: NameError: x is not defined",
    ]),
    _conv("b", 2, [
        "for i in range(3):\n    print(i)",
        "hola se\u00f1or",
        "Please read this long pasted prompt. " * 20,
        "PA3 problem 2 and lab 4",
    ]),
]


def test_profile_report_counts_lengths_rates_and_references():
    report = profile_conversations(CONVS, seed=7, close_read_per_stratum=2)

    assert report["metadata"] == {
        "artifact_type": "course_profile_corpus_report",
        "seed": 7,
        "close_read_per_stratum": 2,
        "student_text_included": False,
    }
    assert report["counts"] == {"conversations": 2, "student_messages": 7}
    assert report["message_lengths"]["chars"]["min"] == 1
    assert report["message_lengths"]["chars"]["max"] > 300
    assert report["message_lengths"]["short_under_40_chars_rate"] == 6 / 7
    assert report["rates"]["traceback_or_error"] == 1 / 7
    assert report["rates"]["code_bearing"] == 1 / 7
    assert report["rates"]["question_reference"] == 1 / 7
    assert report["rates"]["paste_like"] == 3 / 7
    assert report["rates"]["short_ambiguous"] == 1 / 7
    assert report["rates"]["long_message"] == 1 / 7
    assert report["language_mix"]["contains_non_ascii_messages"] == 1

    patterns = report["reference_patterns"]["pattern_counts"]
    assert patterns["question_word"] == 1
    assert patterns["decimal_question"] == 1
    assert patterns["pa_reference"] == 1
    assert patterns["problem_reference"] == 1
    assert patterns["lab_reference"] == 1
    assert report["reference_patterns"]["normalized_question_refs"] == [
        {"ref": "q1_6", "count": 1}
    ]


def test_close_reading_sample_is_deterministic_and_text_free():
    r1 = profile_conversations(CONVS, seed=3, close_read_per_stratum=1)
    r2 = profile_conversations(CONVS, seed=3, close_read_per_stratum=1)

    assert r1["close_reading_sample"] == r2["close_reading_sample"]
    reasons = {item["reason"] for item in r1["close_reading_sample"]}
    assert {"traceback_or_error", "code_bearing", "question_reference"} <= reasons
    for item in r1["close_reading_sample"]:
        assert set(item) == {
            "conv_id", "chatlog_id", "message_index", "student_index",
            "reason",
        }

    rendered = json.dumps(r1)
    assert "Traceback: NameError" not in rendered
    assert "for i in range" not in rendered
    assert "Please read this long pasted prompt" not in rendered


def _snapshot(tmp_path: Path) -> Path:
    snap = tmp_path / "data" / "snapshots" / "snap1"
    snap.mkdir(parents=True)
    (snap / "conversations.jsonl").write_text(
        "".join(c.model_dump_json() + "\n" for c in CONVS))
    return snap


def test_default_output_path_sits_next_to_snapshots_dir(tmp_path):
    snap = tmp_path / "data" / "snapshots" / "snap1"

    assert default_output_path(snap) == \
        tmp_path / "data" / "profile-reports" / "snap1" / \
        "profile-report.json"


def test_cli_writes_requested_output(tmp_path, monkeypatch, capsys):
    snap = _snapshot(tmp_path)
    out = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "profile-corpus", str(snap), "--out", str(out), "--seed", "9",
        "--close-read-per-stratum", "1"])

    main()

    saved = json.loads(out.read_text())
    assert saved["metadata"]["artifact_type"] == \
        "course_profile_corpus_report"
    assert saved["metadata"]["seed"] == 9
    assert saved["counts"]["student_messages"] == 7
    assert "wrote" in capsys.readouterr().out
