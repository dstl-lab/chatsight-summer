from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ingest.episode_events import build_dataset
from src.synthetic.cohort import generate_cohort
from src.synthetic.config import CohortConfig
from src.viewer.classification import (
    ClassificationDraft,
    ClassificationDraftItem,
    build_classification_inputs,
    classify_dataset,
)
from src.viewer.overview import (
    DraftQuestionLine,
    OverviewDraft,
    build_overview_packet,
    generate_overview,
    load_cached_overview,
)
from src.viewer.presentation import build_presentation
from src.viewer.insights import build_journeys, entry_context, response_use
from src.viewer.overview import overview_for_dataset


@pytest.fixture
def dataset(tmp_path: Path):
    generated = generate_cohort(
        CohortConfig(student_count=16, seed=151),
        tmp_path,
    )
    return build_dataset(Path(generated["event_path"]), source_kind="synthetic")


@pytest.fixture
def classifications(dataset):
    inputs = build_classification_inputs(dataset)
    draft = ClassificationDraft(
        records=[
            ClassificationDraftItem(
                journey_id=record.journey_id,
                primary_purpose="validation",
                confidence="medium",
            )
            for record in inputs
        ]
    )
    return classify_dataset(dataset, lambda prompt: draft)


def _draft(packet):
    return OverviewDraft(
        notes=[
            "The most common tutor-use pattern was validation after passing the autograder.",
            "Later questions had more recorded debugging after failed checks.",
            "Some students asked for a direct answer before editing or running code.",
        ],
        question_summaries=[
            DraftQuestionLine(
                question_id=question.question_id,
                one_line="Students often asked for validation after passing.",
            )
            for question in packet.questions
        ],
    )


def test_packet_has_lab_and_question_stats(dataset, classifications):
    packet = build_overview_packet(dataset, classifications)

    assert packet.lab_label == "Lab 1"
    assert packet.tutor_use.denominator > 0
    assert packet.questions
    first = packet.questions[0]
    assert first.student_count > 0
    assert first.median_active_display
    assert first.most_common_purpose_label
    assert len(first.top_patterns) <= 5
    assert packet.notable_questions


def test_generate_overview_uses_computed_numbers(dataset, classifications):
    packet = build_overview_packet(dataset, classifications)
    artifact = generate_overview(
        dataset,
        lambda prompt: _draft(packet),
        classifications=classifications,
        model="test-model",
        now=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )

    assert artifact.generation_mode == "gemini"
    assert 3 <= len(artifact.notes) <= 5
    assert artifact.questions[0].tutor_use == packet.questions[0].tutor_use
    assert artifact.questions[0].one_line.startswith("Students often")


def test_question_ids_in_notes_are_allowed(dataset, classifications):
    packet = build_overview_packet(dataset, classifications)
    draft = _draft(packet)
    draft.notes[1] = (
        f"Recorded errors were highest on Question {packet.questions[-1].question_id}."
    )

    artifact = generate_overview(
        dataset,
        lambda prompt: draft,
        classifications=classifications,
        model="test-model",
    )

    assert artifact.generation_mode == "gemini"


def test_numbers_in_notes_fall_back(dataset, classifications):
    packet = build_overview_packet(dataset, classifications)
    draft = _draft(packet)
    draft.notes[0] = "37% of students used the tutor."

    artifact = generate_overview(
        dataset,
        lambda prompt: draft,
        classifications=classifications,
    )

    assert artifact.generation_mode == "deterministic-fallback"
    assert artifact.questions[0].one_line


def test_cached_overview_requires_matching_packet(
    dataset,
    classifications,
    tmp_path: Path,
):
    packet = build_overview_packet(dataset, classifications)
    artifact = generate_overview(
        dataset,
        lambda prompt: _draft(packet),
        classifications=classifications,
    )
    path = tmp_path / "overview.json"
    path.write_text(artifact.model_dump_json(), encoding="utf-8")

    assert load_cached_overview(path, dataset, classifications) == artifact


def test_presentation_counts_unique_students_and_preserves_ties(dataset, classifications):
    overview = overview_for_dataset(dataset, classifications=classifications)
    result = build_presentation(dataset, overview, classifications)
    journeys = build_journeys(dataset.episodes)
    assert result["tutor_students"]["numerator"] == len({
        item.student_key for item in journeys if item.tutor_used
    })
    assert result["tutor_students"]["denominator"] == len({
        item.student_key for item in journeys
    })
    assert result["tutor_students"]["denominator"] < overview.tutor_use.denominator
    for question in overview.questions:
        items = [item for item in journeys if item.question_id == question.question_id]
        actual = result["questions"][question.question_id]
        error_students = sum(
            any(
                event.event_type == "cell_error"
                or (
                    event.event_type == "autograder_completed"
                    and event.payload.get("success") is False
                )
                for event in item.events
            )
            for item in items
        )
        assert actual["error_students"]["numerator"] == error_students
        assert actual["error_students"]["denominator"] == len(items)
        assert actual["tutor_student_count"] == sum(item.tutor_used for item in items)
        paths = actual["use_paths"]
        counted = {
            journey_id
            for path in paths
            for journey_id in path["journey_ids"]
        }
        tutor_ids = {item.journey_id for item in items if item.tutor_used}
        assert counted == tutor_ids
        after_ids = {
            "edited-no-transfer": "own-code",
            "exact-transfer-no-edit": "tutor-code",
            "exact-transfer-then-edit": "tutor-code",
            "no-code-change": "no-change",
            None: "no-change",
        }
        assert [path["student_count"] for path in paths] == sorted(
            (path["student_count"] for path in paths), reverse=True
        )
        for path in paths:
            members = [
                item
                for item in items
                if item.journey_id in set(path["journey_ids"])
            ]
            assert path["student_count"] == len(members)
            assert path["student_count"]
            assert path["student_count"] <= actual["tutor_student_count"]
            assert path["title"]
            assert path["label"] == path["title"]
            assert path["unit"] == "student-question journey"
            assert "Message wording does not determine" in path["grouping_basis"]
            assert path["definition"]
            assert path["how_built"]
            assert path["pattern"]
            assert path["lab"]["student_question_count"] >= path["student_count"]
            assert path["lab"]["tutor_student_question_count"] >= actual["tutor_student_count"]
            assert [item["question_id"] for item in path["lab"]["by_question"]] == [
                question.question_id for question in overview.questions
            ]
            assert "in_the_data" not in path
            assert "example_message" not in path
            assert all(entry_context(item) == path["entry_id"] for item in members)
            assert all(
                after_ids[response_use(item)] == path["after_id"]
                for item in members
            )
        titles = [path["title"] for path in paths]
        assert len(titles) == len(set(titles))


def test_presentation_use_groups_do_not_require_classifications(dataset):
    result = build_presentation(dataset, overview_for_dataset(dataset), None)
    assert result["classification_coverage"]["numerator"] == 0
    assert any(view["use_paths"] for view in result["questions"].values())
