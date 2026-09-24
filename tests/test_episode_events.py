import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.episodes.models import EpisodeEvent
from src.episodes.reconstruct import reconstruct_episodes
from src.ingest.episode_events import build_dataset, load_event_log

BASE = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)


def event(
    seq: int,
    event_type: str,
    *,
    user_id: str = "student@example.edu",
    question_id: str = "1.1.1",
    question_source: str = "grader_id",
    minutes: int = 0,
    payload: dict | None = None,
    conversation_id: str | None = None,
) -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": f"event-{seq}",
        "event_type": event_type,
        "occurred_at": (BASE + timedelta(minutes=minutes, seconds=seq)).isoformat(),
        "client_sequence": seq,
        "analytics_session_id": "session-1",
        "user_id": user_id,
        "notebook_path": "lab1.ipynb",
        "notebook_name": "lab1.ipynb",
        "cell_id": "cell-1",
        "cell_index": 4,
        "question_id": question_id,
        "question_source": question_source,
        "conversation_id": conversation_id,
        "turn_id": f"turn-{seq}" if conversation_id else None,
        "response_id": f"response-{seq}" if event_type == "tutor_response" else None,
        "correlation_id": f"run-{seq}" if "execution" in event_type else None,
        "payload": payload or {},
    }


def write_rows(path: Path, rows: list[object]) -> None:
    path.write_text(
        "\n".join(
            row if isinstance(row, str) else json.dumps(row) for row in rows
        )
        + "\n",
        encoding="utf-8",
    )


def test_loader_validates_deduplicates_and_indexes_legacy_transcript(
    tmp_path: Path,
):
    valid = event(
        1,
        "tutor_query",
        payload={"message_length": 12},
        conversation_id="conversation-1",
    )
    forbidden = event(2, "cell_edit", payload={"source": "secret code"})
    legacy = {
        "record_kind": "legacy",
        "event_type": "tutor_query",
        "payload": {
            "conversation_id": "conversation-1",
            "question": "How should I start?",
        },
    }
    path = tmp_path / "events.jsonl"
    write_rows(path, [valid, valid, forbidden, "{bad json", legacy])

    events, transcripts, quality = load_event_log(path)

    assert [item.event_id for item in events] == ["event-1"]
    assert transcripts["conversation-1"][0].text == "How should I start?"
    assert quality.total_rows == 5
    assert quality.accepted_events == 1
    assert quality.duplicate_events == 1
    assert quality.rejected_rows == 2
    assert quality.legacy_rows == 1
    assert quality.rejection_reasons == {
        "forbidden_payload_key": 1,
        "malformed_json": 1,
    }


def test_reconstruction_uses_episode_identity_and_observed_patterns():
    rows = [
        event(1, "cell_execution_started", payload={"source_hash": "a"}),
        event(2, "cell_error", payload={"error_name": "NameError"}),
        event(
            3,
            "tutor_query",
            payload={"message_length": 20},
            conversation_id="legacy-conversation",
        ),
        event(
            4,
            "tutor_response",
            payload={"response_length": 40, "code_block_count": 0},
            conversation_id="legacy-conversation",
        ),
        event(
            5,
            "cell_edit",
            payload={
                "source_hash": "b",
                "previous_source_hash": "a",
                "characters_inserted": 4,
                "characters_deleted": 1,
            },
        ),
        event(
            6,
            "autograder_completed",
            payload={"grader_id": "q1_1_1", "success": True},
        ),
    ]
    episodes = reconstruct_episodes([EpisodeEvent.model_validate(row) for row in rows])

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.episode_id.startswith("ep_")
    assert "student@example.edu" not in episode.episode_id
    assert episode.student_key.startswith("stu_")
    assert episode.conversation_ids == ["legacy-conversation"]
    assert episode.measures.attempted_before_asking is True
    assert episode.measures.errors_before_asking == 1
    assert episode.measures.edited_after_response is True
    assert episode.end_reason == "autograder_success"
    assert episode.patterns == [
        "struggle-then-ask",
        "revised-after-response",
        "tested-after-tutor",
    ]


def test_question_summary_counts_students_not_repeat_episodes(tmp_path: Path):
    rows = [
        event(
            1,
            "tutor_query",
            user_id="ask-first@example.edu",
            payload={"message_length": 8},
        ),
        event(
            2,
            "tutor_code_inserted",
            user_id="ask-first@example.edu",
            payload={"provenance": "inserted_from_tutor"},
        ),
        event(
            3,
            "autograder_completed",
            user_id="ask-first@example.edu",
            payload={"grader_id": "q1_1_1", "success": True},
        ),
        event(
            4,
            "cell_execution_started",
            user_id="independent@example.edu",
            payload={"source_hash": "x"},
        ),
        event(
            5,
            "autograder_completed",
            user_id="independent@example.edu",
            payload={"grader_id": "q1_1_1", "success": False},
        ),
        event(
            6,
            "cell_execution_started",
            user_id="independent@example.edu",
            payload={"source_hash": "y"},
        ),
        event(
            7,
            "autograder_completed",
            user_id="independent@example.edu",
            payload={"grader_id": "q1_1_1", "success": True},
        ),
    ]
    path = tmp_path / "events.jsonl"
    write_rows(path, rows)

    dataset = build_dataset(path, source_kind="synthetic")

    assert dataset.meta.source_kind == "synthetic"
    assert dataset.meta.episode_count == 2
    assert dataset.meta.question_count == 1
    summary = dataset.questions[0]
    assert summary.student_count == 2
    assert summary.pct_asked_before_attempting.model_dump() == {
        "numerator": 1,
        "denominator": 2,
        "value": 0.5,
    }
    assert summary.pct_used_tutor_code.value == 0.5


def test_inactivity_closes_episode_with_honest_end_reason():
    rows = [
        event(1, "cell_edit", payload={"source_hash": "a"}),
        event(2, "cell_edit", minutes=31, payload={"source_hash": "b"}),
    ]
    episodes = reconstruct_episodes([EpisodeEvent.model_validate(row) for row in rows])

    assert len(episodes) == 2
    assert episodes[0].end_reason == "inactivity"
    assert episodes[1].end_reason == "end_of_data"


def test_unknown_question_is_preserved_but_not_aggregated(tmp_path: Path):
    row = event(
        1,
        "cell_edit",
        question_id="unknown",
        question_source="unknown",
        payload={"source_hash": "a"},
    )
    path = tmp_path / "events.jsonl"
    write_rows(path, [row])

    dataset = build_dataset(path)

    assert len(dataset.episodes) == 1
    assert dataset.questions == []
    assert dataset.meta.quality.unknown_question_events == 1


def test_tutor_episode_after_recorded_pass_is_explicitly_marked():
    rows = [
        event(
            1,
            "autograder_completed",
            payload={"grader_id": "q1_1_1", "success": True},
        ),
        event(
            2,
            "tutor_query",
            payload={"message_length": 22},
            conversation_id="post-pass-conversation",
        ),
        event(
            3,
            "tutor_response",
            payload={"response_length": 41, "code_block_count": 0},
            conversation_id="post-pass-conversation",
        ),
    ]

    episodes = reconstruct_episodes([EpisodeEvent.model_validate(row) for row in rows])

    assert len(episodes) == 2
    assert episodes[1].measures.prior_pass_recorded is True
    assert episodes[1].patterns[0] == "post-pass-ask"
