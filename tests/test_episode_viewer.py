import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from src.ingest.episode_events import build_dataset
from src.synthetic.cohort import generate_cohort
from src.synthetic.config import CohortConfig
from src.viewer.webapp import create_app

BASE = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)


def event(seq: int, event_type: str, payload: dict, **overrides) -> dict:
    row = {
        "schema_version": "1.0.0",
        "event_id": f"viewer-event-{seq}",
        "event_type": event_type,
        "occurred_at": (BASE + timedelta(seconds=seq)).isoformat(),
        "client_sequence": seq,
        "analytics_session_id": "viewer-session",
        "user_id": "private-student@example.edu",
        "notebook_path": "lab1.ipynb",
        "notebook_name": "lab1.ipynb",
        "cell_id": "cell-1",
        "cell_index": 5,
        "question_id": "2.1",
        "question_source": "grader_id",
        "conversation_id": "conversation-1",
        "turn_id": "turn-1",
        "response_id": None,
        "correlation_id": None,
        "payload": payload,
    }
    row.update(overrides)
    return row


def dataset(tmp_path: Path):
    rows = [
        event(1, "tutor_query", {"message_length": 18}),
        event(
            2,
            "tutor_response",
            {"response_length": 50, "code_block_count": 1},
            response_id="response-1",
        ),
        event(
            3,
            "notebook_paste",
            {
                "pasted_hash": "hash",
                "provenance": "copied_then_pasted",
                "matched_response_id": "response-1",
            },
            response_id="response-1",
        ),
        event(
            4,
            "cell_execution_started",
            {"source_hash": "hash", "is_autograder": False},
        ),
        event(
            5,
            "autograder_completed",
            {"grader_id": "q2_1", "success": True},
        ),
        {
            "record_kind": "legacy",
            "event_type": "tutor_query",
            "payload": {
                "conversation_id": "conversation-1",
                "question": "Can you explain question 2.1?",
            },
        },
        {
            "record_kind": "legacy",
            "event_type": "tutor_response",
            "payload": {
                "conversation_id": "conversation-1",
                "response": "Start by inspecting the column names.",
            },
        },
    ]
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return build_dataset(path, source_kind="synthetic")


def pathway_dataset(tmp_path: Path):
    rows = [
        event(1, "tutor_query", {"message_length": 10}, user_id="student-a"),
        event(
            2,
            "tutor_response",
            {"response_length": 20, "code_block_count": 0},
            user_id="student-a",
        ),
        event(
            3,
            "cell_edit",
            {
                "previous_source_hash": "a",
                "source_hash": "b",
                "characters_inserted": 1,
                "characters_deleted": 0,
            },
            user_id="student-b",
        ),
        event(4, "tutor_query", {"message_length": 10}, user_id="student-b"),
        event(
            5,
            "tutor_response",
            {"response_length": 20, "code_block_count": 0},
            user_id="student-b",
        ),
        event(
            6,
            "cell_edit",
            {
                "previous_source_hash": "b",
                "source_hash": "c",
                "characters_inserted": 1,
                "characters_deleted": 0,
            },
            user_id="student-b",
        ),
        event(
            7,
            "autograder_completed",
            {"grader_id": "q2_1", "success": False},
            user_id="student-c",
        ),
        event(8, "tutor_query", {"message_length": 10}, user_id="student-c"),
        event(
            9,
            "tutor_response",
            {"response_length": 20, "code_block_count": 1},
            user_id="student-c",
            response_id="response-c",
        ),
        event(
            10,
            "notebook_paste",
            {
                "pasted_hash": "hash-c",
                "provenance": "copied_then_pasted",
                "matched_response_id": "response-c",
            },
            user_id="student-c",
            response_id="response-c",
        ),
        event(
            11,
            "autograder_completed",
            {"grader_id": "q2_1", "success": True},
            user_id="student-d",
        ),
        event(12, "tutor_query", {"message_length": 10}, user_id="student-d"),
        event(
            13,
            "tutor_response",
            {"response_length": 20, "code_block_count": 1},
            user_id="student-d",
            response_id="response-d",
        ),
        event(
            14,
            "tutor_code_inserted",
            {
                "code_block_id": "block-d",
                "destination_cell_id": "cell-1",
                "source_hash": "hash-d",
                "provenance": "inserted_from_tutor",
            },
            user_id="student-d",
            response_id="response-d",
        ),
        event(
            15,
            "cell_edit",
            {
                "previous_source_hash": "hash-d",
                "source_hash": "hash-d2",
                "characters_inserted": 1,
                "characters_deleted": 0,
            },
            user_id="student-d",
        ),
    ]
    path = tmp_path / "pathway-events.jsonl"
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return build_dataset(path, source_kind="synthetic")


def test_api_exposes_question_summary_without_raw_student_identity(tmp_path: Path):
    app = create_app(dataset(tmp_path))
    client = TestClient(app)

    meta = client.get("/api/meta")
    questions = client.get("/api/questions")
    insights = client.get("/api/insights")
    briefing = client.get("/api/briefing")
    lab_overview = client.get("/api/overview")
    episodes = client.get(
        "/api/episodes",
        params={"notebook_id": "lab1.ipynb", "question_id": "2.1"},
    )

    assert meta.status_code == 200
    assert meta.json()["source_kind"] == "synthetic"
    assert meta.json()["transcripts_enabled"] is False
    assert questions.status_code == 200
    assert questions.json()[0]["pct_used_tutor_code"]["value"] == 1.0
    assert questions.json()[0]["pct_used_tutor"]["value"] == 1.0
    assert questions.json()[0]["pct_unresolved"]["value"] == 0.0
    assert insights.status_code == 200
    overview = insights.json()["class_overview"]
    assert overview["population"]["student_question_journeys"] == 1
    assert overview["population"]["tutor_using_journeys"] == 1
    matching_cell = next(
        cell
        for cell in overview["cells"]
        if cell["entry_context"] == "before-attempt"
        and cell["response_use"] == "exact-transfer-no-edit"
    )
    assert matching_cell["count"] == 1
    assert matching_cell["tested_after_response"]["value"] == 1.0
    assert "risk_score" not in json.dumps(insights.json())
    assert briefing.status_code == 200
    assert briefing.json()["generation_mode"] == "deterministic-fallback"
    assert len(briefing.json()["findings"]) == 3
    assert lab_overview.status_code == 200
    assert lab_overview.json()["lab_label"] == "Lab 1"
    assert lab_overview.json()["questions"]
    assert episodes.status_code == 200
    assert episodes.json()["total"] == 1
    serialized = json.dumps(episodes.json())
    assert "private-student@example.edu" not in serialized
    assert episodes.json()["episodes"][0]["student_key"].startswith("stu_")


def test_crossed_pathways_use_before_and_after_context(tmp_path: Path):
    client = TestClient(create_app(pathway_dataset(tmp_path)))

    overview = client.get("/api/insights").json()["class_overview"]
    counts = {
        (cell["entry_context"], cell["response_use"]): cell["count"]
        for cell in overview["cells"]
    }

    assert counts[("before-attempt", "no-code-change")] == 1
    assert counts[("after-attempt", "edited-no-transfer")] == 1
    assert counts[("after-problem", "exact-transfer-no-edit")] == 1
    assert counts[("after-pass", "exact-transfer-then-edit")] == 1
    assert sum(counts.values()) == 4


def test_episode_detail_is_traceable_and_transcript_is_opt_in(tmp_path: Path):
    data = dataset(tmp_path)
    episode_id = data.episodes[0].episode_id

    hidden = TestClient(create_app(data)).get(f"/api/episodes/{episode_id}")
    shown = TestClient(
        create_app(data, show_transcripts=True)
    ).get(f"/api/episodes/{episode_id}")

    assert hidden.status_code == 200
    assert hidden.json()["transcript"] == []
    assert hidden.json()["transcript_available"] is True
    assert [row["event_type"] for row in hidden.json()["events"]] == [
        "tutor_query",
        "tutor_response",
        "notebook_paste",
        "cell_execution_started",
        "autograder_completed",
    ]
    assert shown.status_code == 200
    assert [turn["role"] for turn in shown.json()["transcript"]] == [
        "student",
        "tutor",
    ]
    assert shown.json()["transcript"][0]["text"] == (
        "Can you explain question 2.1?"
    )
    assert "asked the tutor before attempting" in shown.json()["journey_summary"]
    assert "passed" in shown.json()["journey_summary"]
    assert [phase["name"] for phase in shown.json()["phases"]] == [
        "Attempt",
        "Difficulty",
        "Tutor",
        "Student action",
        "Outcome",
    ]
    assert shown.json()["journey"]["session_count"] == 1
    assert "private-student@example.edu" not in json.dumps(shown.json())


def test_question_journeys_show_complete_ordered_student_sequences(tmp_path: Path):
    data = dataset(tmp_path)
    hidden = TestClient(create_app(data)).get(
        "/api/question-journeys", params={"question_id": "2.1"}
    )
    shown = TestClient(create_app(data, show_transcripts=True)).get(
        "/api/question-journeys", params={"question_id": "2.1"}
    )

    assert hidden.status_code == 200
    assert hidden.json()["student_count"] == 1
    student = hidden.json()["students"][0]
    assert student["student_name"] == "Student 001"
    assert "student_key" not in json.dumps(hidden.json())
    assert "private-student@example.edu" not in json.dumps(hidden.json())
    assert [row["event_type"] for row in student["events"]] == [
        "tutor_query",
        "tutor_response",
        "notebook_paste",
        "cell_execution_started",
        "autograder_completed",
    ]
    assert all(row["transcript_text"] is None for row in student["events"])
    shown_events = shown.json()["students"][0]["events"]
    assert shown_events[0]["transcript_text"] == "Can you explain question 2.1?"
    assert shown_events[1]["transcript_text"] == (
        "Start by inspecting the column names."
    )
    assert shown.json()["students"][0]["entry_context"] == "before-attempt"


def test_episode_filters_and_not_found(tmp_path: Path):
    data = dataset(tmp_path)
    client = TestClient(create_app(data))

    matching = client.get(
        "/api/episodes", params={"pattern": "tutor-code-transfer"}
    )
    missing = client.get("/api/episodes", params={"pattern": "struggle-then-ask"})
    not_found = client.get("/api/episodes/ep_missing")

    assert matching.json()["total"] == 1
    assert missing.json()["total"] == 0
    assert not_found.status_code == 404


def test_pathway_examples_filter_at_journey_level(tmp_path: Path):
    data = dataset(tmp_path)
    client = TestClient(create_app(data))

    matching = client.get(
        "/api/pathway-examples",
        params={
            "entry": "before-attempt",
            "use": "exact-transfer-no-edit",
        },
    )
    empty = client.get(
        "/api/pathway-examples",
        params={
            "entry": "after-problem",
            "use": "exact-transfer-no-edit",
        },
    )
    invalid = client.get(
        "/api/pathway-examples",
        params={"entry": "inferred-motivation", "use": "no-code-change"},
    )

    assert matching.status_code == 200
    assert matching.json()["total"] == 1
    assert matching.json()["examples"][0]["pathway"] == {
        "entry_context": "before-attempt",
        "response_use": "exact-transfer-no-edit",
    }
    assert matching.json()["examples"][0]["journey_totals"][
        "attempt_count"
    ] == 1
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert invalid.status_code == 400


def test_overview_use_groups_are_sequence_backed(tmp_path: Path):
    hidden = TestClient(create_app(dataset(tmp_path))).get("/api/overview").json()
    shown = TestClient(
        create_app(dataset(tmp_path), show_transcripts=True)
    ).get("/api/overview").json()
    hidden_paths = hidden["presentation"]["questions"]["2.1"]["use_paths"]
    shown_paths = shown["presentation"]["questions"]["2.1"]["use_paths"]

    assert [path["id"] for path in hidden_paths] == ["before-attempt:tutor-code"]
    assert hidden_paths[0]["student_count"] == 1
    assert hidden_paths[0]["title"] == (
        "Ask tutor → tutor reply → exact tutor-code insert or paste"
    )
    assert "tutor question" in hidden_paths[0]["definition"]
    assert hidden_paths[0]["pattern"].startswith("ask tutor")
    assert hidden_paths[0]["lab"]["student_question_count"] == 1
    assert hidden_paths[0]["lab"]["by_question"][0]["question_id"] == "2.1"
    assert "in_the_data" not in hidden_paths[0]
    assert "example_message" not in shown_paths[0]
    assert hidden_paths == shown_paths

    pathway = TestClient(create_app(pathway_dataset(tmp_path))).get("/api/overview")
    paths = {
        path["id"]: path["student_count"]
        for path in pathway.json()["presentation"]["questions"]["2.1"]["use_paths"]
    }
    assert list(paths) == [
        "before-attempt:no-change",
        "after-attempt:own-code",
        "after-problem:tutor-code",
        "after-pass:tutor-code",
    ]
    assert paths == {
        "before-attempt:no-change": 1,
        "after-attempt:own-code": 1,
        "after-problem:tutor-code": 1,
        "after-pass:tutor-code": 1,
    }


def test_index_serves_observational_viewer(tmp_path: Path):
    response = TestClient(create_app(dataset(tmp_path))).get("/")
    assert response.status_code == 200
    assert "Student Question Interactions" in response.text
    assert "Interaction summary" in response.text
    assert "By question" in response.text
    assert "By student" in response.text
    assert "Recorded progression counts" in response.text
    assert "Explore question interactions" not in response.text
    assert "Code diff unavailable" in response.text
    assert "Full chronological record" in response.text
    assert "Before asking" in response.text
    assert "Student request" in response.text
    assert "Tutor response" in response.text
    assert "Afterward" in response.text
    assert "Student messages in this sequence" not in response.text
    assert "Before the first ask" not in response.text


def test_large_class_api_paginates_and_samples_deterministically(tmp_path: Path):
    generated = generate_cohort(
        CohortConfig(student_count=20, seed=81),
        tmp_path,
    )
    data = build_dataset(Path(generated["event_path"]), source_kind="synthetic")
    client = TestClient(create_app(data))

    insights = client.get("/api/insights").json()
    first = client.get("/api/episodes", params={"limit": 10, "offset": 0}).json()
    second = client.get("/api/episodes", params={"limit": 10, "offset": 10}).json()
    sample_a = client.get(
        "/api/episodes",
        params={"representative_size": 12, "sample_seed": 4},
    ).json()
    sample_b = client.get(
        "/api/episodes",
        params={"representative_size": 12, "sample_seed": 4},
    ).json()

    class_overview = insights["class_overview"]
    assert sum(cell["count"] for cell in class_overview["cells"]) == (
        class_overview["population"]["grid_eligible_tutor_journeys"]
    )
    assert {
        item["id"] for item in class_overview["entry_contexts"]
    } == {
        "before-attempt",
        "after-attempt",
        "after-problem",
        "after-pass",
    }
    assert {
        item["id"] for item in class_overview["response_uses"]
    } == {
        "no-code-change",
        "edited-no-transfer",
        "exact-transfer-no-edit",
        "exact-transfer-then-edit",
    }
    assert insights["questions"] == sorted(
        insights["questions"],
        key=lambda item: (
            -(item["median_attempts"] or 0),
            -(item["median_active_minutes"] or 0),
            item["question_id"],
        ),
    )
    assert first["selection_mode"] == "page"
    assert first["has_more"] is True
    assert second["offset"] == 10
    assert {
        episode["episode_id"] for episode in first["episodes"]
    }.isdisjoint(
        episode["episode_id"] for episode in second["episodes"]
    )
    assert sample_a["selection_mode"] == "representative"
    assert sample_a["episodes"] == sample_b["episodes"]
    assert len(sample_a["episodes"]) == 12
    assert all(episode["journey_summary"] for episode in sample_a["episodes"])
    assert all(len(episode["phases"]) == 5 for episode in sample_a["episodes"])
    all_rows = client.get("/api/episodes", params={"limit": 200}).json()["episodes"]
    multi_session = next(
        episode for episode in all_rows if episode["journey"]["session_count"] > 1
    )
    detail = client.get(
        f"/api/episodes/{multi_session['episode_id']}"
    ).json()
    assert len(detail["related_sessions"]) == (
        detail["journey"]["session_count"] - 1
    )


def test_synthetic_acts_are_separate_filterable_metadata(tmp_path: Path):
    generated = generate_cohort(
        CohortConfig(student_count=20, seed=82, direct_request_share=0.40),
        tmp_path,
    )
    data = build_dataset(Path(generated["event_path"]), source_kind="synthetic")
    client = TestClient(create_app(data))

    meta = client.get("/api/meta").json()
    direct = client.get(
        "/api/episodes",
        params={"interaction_act": "direct-request"},
    ).json()
    questions = client.get("/api/questions").json()

    assert meta["generation"]["scenario_assumptions"][
        "direct_request_share"
    ] == 0.40
    assert meta["interaction_act_counts"]["direct-request"] > 0
    assert direct["total"] > 0
    assert all(
        "direct-request" in episode["interaction_acts"]
        for episode in direct["episodes"]
    )
    assert "pattern_rates" in questions[0]
    assert "no_named_pattern" in questions[0]
