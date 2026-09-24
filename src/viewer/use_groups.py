"""Group tutor use from recorded before/after context, not message wording."""

from __future__ import annotations

from typing import Any

from src.viewer.insights import (
    StudentQuestionJourney,
    entry_context,
    response_use,
)

ENTRY_ROWS = (
    "before-attempt",
    "after-attempt",
    "after-problem",
    "after-pass",
)

AFTER_COLUMNS = (
    "own-code",
    "tutor-code",
    "no-change",
)

_AFTER_IDS = {
    "edited-no-transfer": "own-code",
    "exact-transfer-no-edit": "tutor-code",
    "exact-transfer-then-edit": "tutor-code",
    "no-code-change": "no-change",
    None: "no-change",
}

_BEFORE = {
    "before-attempt": {
        "start": (),
        "rule": (
            "The first recorded step is the tutor question. No notebook edit, "
            "code run, error, failed autograder check, or passing autograder "
            "check is recorded before it."
        ),
        "pattern": "ask tutor",
    },
    "after-attempt": {
        "start": ("Code edit or run",),
        "rule": (
            "A notebook edit or code run is recorded first. No error, failed "
            "autograder check, or passing autograder check is recorded before "
            "the tutor question."
        ),
        "pattern": "code edit or run → ask tutor",
    },
    "after-problem": {
        "start": ("Error or failed autograder check",),
        "rule": (
            "An execution error or failed autograder check is recorded first, "
            "then the tutor question."
        ),
        "pattern": "error or failed autograder check → ask tutor",
    },
    "after-pass": {
        "start": ("Pass autograder",),
        "rule": (
            "A passing autograder check is recorded first, then the tutor "
            "question."
        ),
        "pattern": "pass autograder → ask tutor",
    },
}

_AFTER = {
    "own-code": {
        "end": "notebook edit, no exact tutor-code insert or paste",
        "rule": (
            "After the tutor reply, a notebook edit is recorded. No exact "
            "tutor-code insert or paste matched to that reply is recorded."
        ),
        "pattern": "tutor reply → notebook edit, no matched tutor-code paste",
    },
    "tutor-code": {
        "end": "exact tutor-code insert or paste",
        "rule": (
            "After the tutor reply, an exact tutor-code insert or a paste "
            "matched to that reply is recorded. A later edit may also be "
            "present. That later edit is not treated as changing the pasted "
            "code."
        ),
        "pattern": "tutor reply → exact tutor-code insert or paste",
    },
    "no-change": {
        "end": "no insert, paste, or notebook edit",
        "rule": (
            "After the tutor reply, no exact tutor-code insert or paste and "
            "no notebook edit is recorded. If there was no tutor reply, this "
            "same bucket is used."
        ),
        "pattern": "tutor reply → no insert, paste, or notebook edit",
    },
}


def _after_id(journey: StudentQuestionJourney) -> str:
    return _AFTER_IDS.get(response_use(journey), "no-change")


def _query_ids(journey: StudentQuestionJourney) -> list[str]:
    return [
        event.event_id
        for event in journey.events
        if event.event_type == "tutor_query"
    ]


def _path_copy(entry_id: str, after_id: str) -> dict[str, str]:
    before = _BEFORE[entry_id]
    after = _AFTER[after_id]
    title = " → ".join((*before["start"], "ask tutor", "tutor reply", after["end"]))
    title = title[0].upper() + title[1:]
    return {
        "title": title,
        "label": title,
        "unit": "student-question journey",
        "grouping_basis": (
            "Recorded events before the first tutor question and after the "
            "first tutor reply. Message wording does not determine the group."
        ),
        "definition": (
            f"{before['rule']} {after['rule']} The question ID is notebook "
            "context on those events."
        ),
        "how_built": (
            "Assigned from the first tutor question and the first tutor reply "
            "on one student–question record."
        ),
        "pattern": f"{before['pattern']} → {after['pattern']}",
    }


def build_use_paths(journeys: list[StudentQuestionJourney]) -> list[dict[str, Any]]:
    tutor = [item for item in journeys if item.tutor_used]
    buckets: dict[tuple[str, str], list[StudentQuestionJourney]] = {
        (entry_id, after_id): []
        for entry_id in ENTRY_ROWS
        for after_id in AFTER_COLUMNS
    }
    for journey in tutor:
        entry_id = entry_context(journey)
        if entry_id is None:
            continue
        buckets[(entry_id, _after_id(journey))].append(journey)

    paths = []
    for entry_index, entry_id in enumerate(ENTRY_ROWS):
        for after_index, after_id in enumerate(AFTER_COLUMNS):
            members = buckets[(entry_id, after_id)]
            if not members:
                continue
            path = {
                "id": f"{entry_id}:{after_id}",
                "entry_id": entry_id,
                "after_id": after_id,
                "student_count": len(members),
                "tutor_student_count": len(tutor),
                "journey_ids": [item.journey_id for item in members],
                "event_ids": [
                    event_id
                    for item in members
                    for event_id in _query_ids(item)
                ],
                **_path_copy(entry_id, after_id),
            }
            path["_order"] = (entry_index, after_index)
            paths.append(path)
    paths.sort(key=lambda item: (-item["student_count"], item["_order"]))
    for path in paths:
        del path["_order"]
    return paths


def attach_lab_breakdown(
    question_views: dict[str, dict[str, Any]],
    question_ids: list[str],
) -> None:
    tutor_records = sum(
        view["tutor_student_count"] for view in question_views.values()
    )
    counts: dict[str, dict[str, int]] = {}
    for question_id, view in question_views.items():
        for path in view["use_paths"]:
            counts.setdefault(path["id"], {})[question_id] = path["student_count"]
    for view in question_views.values():
        for path in view["use_paths"]:
            by_question = [
                {
                    "question_id": question_id,
                    "student_count": counts[path["id"]].get(question_id, 0),
                    "tutor_student_count": question_views[question_id][
                        "tutor_student_count"
                    ],
                }
                for question_id in question_ids
            ]
            path["lab"] = {
                "student_question_count": sum(
                    item["student_count"] for item in by_question
                ),
                "tutor_student_question_count": tutor_records,
                "by_question": by_question,
            }
