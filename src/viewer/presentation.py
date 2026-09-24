"""Fixed presentation slots computed from complete student-question records."""

from src.episodes.models import EpisodeDataset
from src.viewer.classification import ClassificationArtifact
from src.viewer.insights import StudentQuestionJourney, build_journeys
from src.viewer.overview import LabOverviewArtifact
from src.viewer.use_groups import attach_lab_breakdown, build_use_paths
from src.viewer.interactions import build_progressions


def ratio(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _had_error(journey: StudentQuestionJourney) -> bool:
    return any(
        event.event_type == "cell_error"
        or (
            event.event_type == "autograder_completed"
            and event.payload.get("success") is False
        )
        for event in journey.events
    )


def build_presentation(
    dataset: EpisodeDataset,
    overview: LabOverviewArtifact,
    classifications: ClassificationArtifact | None = None,
    *,
    include_transcripts: bool = False,
) -> dict:
    journeys = build_journeys(dataset.episodes)
    students = {item.student_key for item in journeys}
    tutor_students = {item.student_key for item in journeys if item.tutor_used}
    classified_count = len(classifications.classifications) if classifications else 0
    by_question: dict[str, list[StudentQuestionJourney]] = {}
    for journey in journeys:
        by_question.setdefault(journey.question_id, []).append(journey)

    question_views = {}
    for question in overview.questions:
        items = by_question.get(question.question_id, [])
        tutor = [item for item in items if item.tutor_used]
        question_views[question.question_id] = {
            "has_data": bool(items),
            "error_students": ratio(sum(_had_error(item) for item in items), len(items)),
            "passed": ratio(sum(item.eventually_passed for item in items), len(items)),
            "tutor_student_count": len(tutor),
            "use_paths": build_use_paths(items),
            "progressions": build_progressions(items),
            "journey_ids": [item.journey_id for item in items],
        }
    attach_lab_breakdown(
        question_views,
        [question.question_id for question in overview.questions],
    )
    return {
        "student_count": len(students),
        "interaction_count": len(journeys),
        "tutor_students": ratio(len(tutor_students), len(students)),
        "question_count": len(overview.questions),
        "classification_coverage": ratio(
            classified_count, sum(item.tutor_used for item in journeys)
        ),
        "questions": question_views,
    }
