"""Observed-policy cohorts isolate recorded outcomes from counterfactual prompts."""
import json

import pytest

from src.agents import notebook_student as store
from src.agents.notebook_tutor import Reply
from src.eval.student_continuation import Continuation


def _conversation(number, *, followup=True):
    turns = [
        {
            "index": 0,
            "student_index": 0,
            "role": "student",
            "text": f"REQUEST_{number}",
            "at": "2026-01-01T00:00:00+00:00",
            "mode": "tutor",
        },
        {
            "index": 1,
            "student_index": None,
            "role": "tutor",
            "text": f"RECORDED_TUTOR_{number}",
            "at": "2026-01-01T00:01:00+00:00",
            "mode": "",
        },
    ]
    if followup:
        turns.append({
            "index": 2,
            "student_index": 1,
            "role": "student",
            "text": f"RECORDED_FOLLOWUP_{number}",
            "at": "2026-01-01T00:02:00+00:00",
            "mode": "tutor",
        })
    return {
        "chatlog_id": number,
        "conv_id": f"PRIVATE_CONVERSATION_{number}",
        "notebook": "PRIVATE_NOTEBOOK",
        "started_at": "2026-01-01T00:00:00+00:00",
        "turns": turns,
    }


def _snapshot(path, count=5):
    path.mkdir()
    rows = [_conversation(number, followup=number % 2 == 0)
            for number in range(1, count + 1)]
    (path / "conversations.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )


def _files(path):
    return {
        str(file.relative_to(path)): file.read_bytes()
        for file in path.rglob("*") if file.is_file() and file.name != ".lock"
    }


def test_prepare_uses_disjoint_conversation_holdout_and_hides_recorded_future(tmp_path):
    from src.eval import observed_policy_cohort as cohort

    snapshot, folder = tmp_path / "snapshot", tmp_path / "cohort"
    _snapshot(snapshot)
    saved = cohort.prepare(
        snapshot,
        folder,
        proposed_policy="Proposed policy.",
        development_conversations=2,
        case_count=3,
        seed=7,
    )

    manifest = saved["manifest"]
    assert manifest["selection"] == {
        "seed": 7,
        "development_conversations": 2,
        "holdout_conversations": 3,
        "unit": "conversation",
        "learner_identity_available": False,
    }
    assert manifest["logical_requests_if_fully_run"] == 6
    assert len({case["conversation_key"] for case in saved["cases"]}) == 3
    assert saved["summary"]["proposed"]["ready"] == 3
    for case in saved["cases"]:
        source = case["source"]
        prompt = cohort._tutor_prompt(source, manifest["proposed_policy"])
        assert source["request"][-1]["text"] in prompt
        assert all(turn["text"] not in prompt for turn in source["recorded_tutor"])
        assert all(turn["text"] not in prompt for turn in source["recorded_followup"])
    serialized_manifest = json.dumps(manifest)
    assert "PRIVATE_CONVERSATION" not in serialized_manifest
    assert "PRIVATE_NOTEBOOK" not in serialized_manifest


def test_run_compares_recorded_outcomes_with_only_proposed_simulation(tmp_path):
    from src.eval import observed_policy_cohort as cohort

    snapshot, folder = tmp_path / "snapshot", tmp_path / "cohort"
    _snapshot(snapshot, count=4)
    prepared = cohort.prepare(
        snapshot,
        folder,
        proposed_policy="Ask the student to explain their next step.",
        development_conversations=1,
        case_count=3,
        seed=3,
    )
    recorded_text = {
        turn["text"]
        for case in prepared["cases"]
        for key in ("recorded_tutor", "recorded_followup")
        for turn in case["source"][key]
    }
    calls = []

    def tutor(prompt, schema):
        assert schema is Reply
        assert all(text not in prompt for text in recorded_text)
        calls.append("tutor")
        return schema(text="PROPOSED_TUTOR_REPLY")

    def student(prompt, schema):
        assert schema is Continuation
        assert "PROPOSED_TUTOR_REPLY" in prompt
        assert all(text not in prompt for text in recorded_text)
        calls.append("student")
        return schema(decision="no-reply", text="")

    saved = cohort.run(
        folder,
        send=True,
        generate_tutor=tutor,
        generate_student=student,
        workers=2,
    )

    assert calls.count("tutor") == calls.count("student") == 3
    assert saved["summary"]["proposed"]["no-follow-up"] == 3
    assert saved["summary"]["statistics"]["comparable_cases"] == 3
    assert saved["summary"]["statistics"]["proposed_reply_rate"] == 0.0
    complete = _files(folder)
    assert cohort.run(
        folder,
        send=True,
        generate_tutor=lambda *_: pytest.fail("Tutor resent"),
        generate_student=lambda *_: pytest.fail("Student resent"),
        workers=2,
    ) == saved
    assert _files(folder) == complete


def test_failed_proposed_request_is_saved_and_never_called_again(tmp_path):
    from src.eval import observed_policy_cohort as cohort

    snapshot, folder = tmp_path / "snapshot", tmp_path / "cohort"
    _snapshot(snapshot, count=2)
    cohort.prepare(
        snapshot,
        folder,
        proposed_policy="Proposed policy.",
        development_conversations=1,
        case_count=1,
    )
    saved = cohort.run(
        folder,
        send=True,
        generate_tutor=lambda *_: (_ for _ in ()).throw(RuntimeError("Provider failed")),
        generate_student=lambda *_: pytest.fail("Student must not run"),
    )

    assert saved["summary"]["proposed"]["failed"] == 1
    assert saved["summary"]["comparisons"]["not-comparable"] == 1
    assert cohort.run(
        folder,
        send=True,
        generate_tutor=lambda *_: pytest.fail("Failed request resent"),
        generate_student=lambda *_: pytest.fail("Student resent"),
    ) == saved


def test_tampered_recorded_source_is_rejected(tmp_path):
    from src.eval import observed_policy_cohort as cohort

    snapshot, folder = tmp_path / "snapshot", tmp_path / "cohort"
    _snapshot(snapshot, count=2)
    cohort.prepare(
        snapshot,
        folder,
        proposed_policy="Proposed policy.",
        development_conversations=1,
        case_count=1,
    )
    source_path = folder / "cases" / "case-0001" / "source.json"
    source = store._read(source_path)
    source["source"]["recorded_tutor"][0]["text"] = "Changed history"
    store._save(source_path, source)

    with pytest.raises(ValueError, match="source changed"):
        cohort.show(folder)


def test_prepare_next_preserves_numbered_history(tmp_path):
    from src.eval import observed_policy_cohort as cohort

    snapshot, workspace = tmp_path / "snapshot", tmp_path / "workspace"
    _snapshot(snapshot, count=3)
    first, _ = cohort.prepare_next(
        workspace,
        snapshot,
        proposed_policy="First proposed policy.",
        development_conversations=1,
        case_count=1,
    )
    second, _ = cohort.prepare_next(
        workspace,
        snapshot,
        proposed_policy="Second proposed policy.",
        development_conversations=1,
        case_count=1,
    )

    assert first.name == "run-0001" and second.name == "run-0002"
    assert cohort.runs(workspace) == {
        "run-0001": first.resolve(),
        "run-0002": second.resolve(),
    }
