import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.ingest.episode_events import build_dataset, link_transcripts
from src.viewer.insights import sequence_context_at
from src.viewer.message_labels import (
    labels_from_dataset,
    purpose_for_event,
    request_categories,
)

BASE = datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc)


def event(seq: int, event_type: str, payload: dict, **overrides) -> dict:
    row = {
        "schema_version": "1.0.0",
        "event_id": f"label-event-{seq}",
        "event_type": event_type,
        "occurred_at": (BASE + timedelta(seconds=seq)).isoformat(),
        "client_sequence": seq,
        "analytics_session_id": "label-session",
        "user_id": "student-a",
        "notebook_path": "lab1.ipynb",
        "notebook_name": "lab1.ipynb",
        "cell_id": "cell-1",
        "cell_index": 5,
        "question_id": "2.1",
        "question_source": "grader_id",
        "conversation_id": f"conversation-{seq}",
        "turn_id": f"turn-{seq}",
        "response_id": None,
        "correlation_id": None,
        "payload": payload,
    }
    row.update(overrides)
    return row


def write_dataset(tmp_path: Path, rows: list[dict]):
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return build_dataset(path, source_kind="synthetic")


def test_message_labels_count_one_student_in_overlapping_categories(tmp_path: Path):
    data = write_dataset(
        tmp_path,
        [
            event(1, "cell_error", {"error_name": "NameError"}, conversation_id=None),
            event(
                2,
                "tutor_query",
                {
                    "message_length": 12,
                    "synthetic_message_act": "debugging-request",
                    "synthetic_ground_truth": True,
                },
                conversation_id="conversation-debug",
            ),
            event(
                3,
                "tutor_response",
                {"response_length": 20, "code_block_count": 0},
                conversation_id="conversation-debug",
            ),
            event(
                4,
                "autograder_completed",
                {"grader_id": "q2_1", "success": True},
                conversation_id=None,
            ),
            event(
                5,
                "tutor_query",
                {
                    "message_length": 18,
                    "synthetic_message_act": "direct-request",
                    "synthetic_ground_truth": True,
                },
                conversation_id="conversation-direct",
            ),
            event(
                6,
                "tutor_response",
                {"response_length": 20, "code_block_count": 0},
                conversation_id="conversation-direct",
            ),
        ],
    )

    artifact = labels_from_dataset(data)
    categories = {item["purpose"]: item for item in request_categories(artifact.labels, question_id="2.1")}

    assert [item.purpose for item in artifact.labels] == [
        "debugging",
        "direct-answer-request",
    ]
    assert artifact.labels[0].sequence_context == "after-problem"
    assert artifact.labels[1].sequence_context == "after-pass"
    assert categories["debugging"]["student_count"] == 1
    assert categories["direct-answer-request"]["student_count"] == 1
    assert categories["debugging"]["journey_ids"] == categories["direct-answer-request"]["journey_ids"]
    first_query = next(
        event
        for episode in data.episodes
        for event in episode.events
        if event.event_type == "tutor_query"
    )
    assert purpose_for_event(first_query) == "debugging"


def test_sequence_context_is_local_to_each_message(tmp_path: Path):
    data = write_dataset(
        tmp_path,
        [
            event(
                1,
                "tutor_query",
                {
                    "message_length": 10,
                    "synthetic_message_act": "validation",
                    "synthetic_ground_truth": True,
                },
            ),
            event(2, "tutor_response", {"response_length": 8, "code_block_count": 0}),
        ],
    )
    events = data.episodes[0].events
    assert sequence_context_at(events, 0) == "before-attempt"


def test_link_transcripts_prefers_event_id_and_refuses_ambiguous_order(tmp_path: Path):
    query = event(1, "tutor_query", {"message_length": 10}, conversation_id="shared")
    reply = event(
        2,
        "tutor_response",
        {"response_length": 8, "code_block_count": 0},
        conversation_id="shared",
        response_id="response-1",
        user_id="student-b",
    )
    data = write_dataset(
        tmp_path,
        [
            query,
            reply,
            {
                "record_kind": "legacy",
                "event_type": "tutor_query",
                "event_id": "label-event-1",
                "payload": {
                    "conversation_id": "shared",
                    "question": "linked by event id",
                },
            },
            {
                "record_kind": "legacy",
                "event_type": "tutor_response",
                "payload": {
                    "conversation_id": "shared",
                    "response": "ambiguous leftover reply",
                },
            },
            {
                "record_kind": "legacy",
                "event_type": "tutor_response",
                "payload": {
                    "conversation_id": "shared",
                    "response": "second leftover reply",
                },
            },
        ],
    )

    events = [event for episode in data.episodes for event in episode.events]
    linked = link_transcripts(events, data.transcripts)
    assert linked["label-event-1"] == "linked by event id"
    # Two leftover tutor turns and one leftover tutor event: refuse order linkage.
    assert linked["label-event-2"] is None
