"""Build the synthetic, evidence-linked data contract used by the UI prototype."""
import argparse
import json
from pathlib import Path

from .metrics import calculate_metrics
from .normalize import load_json
from .schema import Activity, CheckResult, CodeEdit, Execution, QuestionStatus, StudentMessage, TutorResponse
from .sessions import reconstruct


DEMO_METADATA = {
    "Q5.1": {
        "review_rank": 1,
        "flagged": True,
        "priority": "high",
        "scenario": "Repeated failures after tutor help",
        "reference": {"status": "illustrative", "lower_seconds": 35, "upper_seconds": 70},
        "reasons": [
            {"id": "post-help-failures", "title": "Repeated failed checks after help",
             "description": "Three failed question checks were observed after the completed tutor response.",
             "event_ids": ["b06", "b09", "b13"]},
            {"id": "resumed-work", "title": "Work resumed after an inactivity gap",
             "description": "The session resumed in a later work bout after more than 30 minutes without an observed event.",
             "event_ids": ["b09", "b10", "b11"]},
            {"id": "unfinished-outcome", "title": "Question remained unfinished",
             "description": "The final explicit status in this synthetic session is unfinished, not failed.",
             "event_ids": ["b14"]},
        ],
    },
    "Q2.4": {
        "review_rank": 2,
        "flagged": True,
        "priority": "medium",
        "scenario": "Multiple tutor responses before recovery",
        "reference": {"status": "illustrative", "lower_seconds": 30, "upper_seconds": 75},
        "reasons": [
            {"id": "multiple-help", "title": "Multiple tutor interactions before recovery",
             "description": "The student requested help twice before a question-level passing check was observed.",
             "event_ids": ["c03", "c07", "c08", "c11"]},
            {"id": "failed-after-first-help", "title": "A failed check followed the first response",
             "description": "The first code attempt after tutor help was followed by another failed question check.",
             "event_ids": ["c03", "c04", "c05", "c06"]},
        ],
    },
    "Q4.3": {
        "review_rank": 3,
        "flagged": True,
        "priority": "high",
        "scenario": "Missing or ambiguous activity data",
        "reference": {"status": "unknown", "lower_seconds": None, "upper_seconds": None},
        "reasons": [
            {"id": "ambiguous-order", "title": "Message and response order is uncertain",
             "description": "The student message and completed response share a timestamp without a trusted ordering sequence.",
             "event_ids": ["d01", "d02"]},
            {"id": "unknown-outcome", "title": "Outcome was not observed",
             "description": "The final check result and question outcome are unknown in the available events.",
             "event_ids": ["d04"]},
        ],
    },
    "Q3.2": {
        "review_rank": 4,
        "flagged": False,
        "priority": "routine",
        "scenario": "Quick recovery after tutor assistance",
        "reference": {"status": "illustrative", "lower_seconds": 20, "upper_seconds": 60},
        "reasons": [
            {"id": "quick-recovery", "title": "Reference recovery pattern",
             "description": "One edit and execution followed the response, then the question-level check passed.",
             "event_ids": ["a03", "a04", "a05", "a06"]},
        ],
    },
}


def _metric(value):
    return {
        "status": value["status"],
        "value": value["value"],
        "reason": value.get("reason"),
        "evidence_refs": value.get("evidence_refs", []),
    }


def _phase(ref, episode):
    if episode["help"]["first_boundary_status"] != "known":
        return "ambiguous" if any(
            ref in group["event_refs"] for group in episode["ambiguous_order_groups"]
        ) else "unpartitioned"
    boundary = next(item for item in episode["help"]["boundaries"]
                    if item["response_ref"] == episode["help"]["first_completed_response_ref"])
    relative = boundary["all_events_relative_to_response"]
    if ref == boundary["response_ref"]:
        return "help_boundary"
    if ref in relative["before_refs"]:
        return "before_help"
    if ref in relative["after_refs"]:
        return "after_help"
    return "ambiguous"


def _event_view(record, episode):
    detail = record.event.detail
    base = {
        "id": record.ref,
        "source_event_id": record.event.event_id,
        "occurred_at": record.event.occurred_at.isoformat(),
        "phase": _phase(record.ref, episode),
        "order_uncertain": any(record.ref in group["event_refs"]
                               for group in episode["ambiguous_order_groups"]),
        "source_pointers": [source.record_pointer for source in record.sources],
        "code_diff": None,
        "metadata": [],
    }
    if isinstance(detail, StudentMessage):
        base.update(kind="student_message", actor="Student", title="Student message",
                    body=detail.text or "Message content unavailable")
        base["metadata"] = [{"label": "Request", "value": detail.request_id or "unknown"}]
    elif isinstance(detail, TutorResponse):
        base.update(kind="tutor_response", actor="AI tutor", title="Tutor response",
                    body=detail.text or "Response content unavailable")
        base["metadata"] = [
            {"label": "Status", "value": detail.status},
            {"label": "Response", "value": detail.response_id or "unknown"},
        ]
    elif isinstance(detail, CodeEdit):
        base.update(kind="code_edit", actor="Notebook", title="Code edited",
                    body=f"Cell {detail.cell_id or 'unknown'} changed to revision {detail.revision_id or 'unknown'}.")
        base["code_diff"] = {"before": detail.before_source, "after": detail.after_source}
        base["metadata"] = [{"label": "Revision", "value": detail.revision_id or "unknown"}]
    elif isinstance(detail, Execution):
        base.update(kind="execution", actor="Notebook", title="Cell executed",
                    body=detail.output or f"Execution finished with status: {detail.status}.")
        base["metadata"] = [
            {"label": "Execution", "value": detail.execution_id or "unknown"},
            {"label": "Status", "value": detail.status},
        ]
        if detail.submitted_source:
            base["code_diff"] = {"before": None, "after": detail.submitted_source}
    elif isinstance(detail, CheckResult):
        base.update(kind="check_result", actor="Autograder",
                    title=f"Check {detail.outcome}",
                    body=f"A {detail.scope} check reported {detail.outcome}.")
        base["metadata"] = [
            {"label": "Check", "value": detail.check_id or "unknown"},
            {"label": "Grader", "value": detail.grader_id or "unknown"},
        ]
    elif isinstance(detail, QuestionStatus):
        base.update(kind="question_status", actor="Session", title="Question status updated",
                    body=f"The explicit question status became {detail.status}.")
        base["metadata"] = [{"label": "Status", "value": detail.status}]
    elif isinstance(detail, Activity):
        base.update(kind="activity", actor="Activity log", title=f"Work {detail.action}",
                    body=f"The activity stream recorded {detail.action}.")
    else:  # pragma: no cover - the canonical union makes this unreachable
        raise TypeError("Unsupported canonical event type")
    return base


def _gap_view(gap, index):
    start = index[gap["from_ref"]]
    end = index[gap["to_ref"]]
    return {
        "id": "gap-" + gap["from_ref"][-10:] + "-" + gap["to_ref"][-10:],
        "kind": "inactivity",
        "actor": "Observed gap",
        "title": "Inactivity or unobserved work",
        "body": "No event was observed during this interval. This is not treated as active work or as failure.",
        "occurred_at": end.event.occurred_at.isoformat(),
        "duration_seconds": gap["elapsed_seconds"],
        "phase": "after_help",
        "order_uncertain": False,
        "source_event_id": None,
        "source_pointers": [],
        "supporting_refs": [start.ref, end.ref],
        "code_diff": None,
        "metadata": [{"label": "Boundary", "value": gap["reason"]}],
    }


def build_demo(input_path: Path):
    normalized = load_json(input_path.read_bytes())
    if normalized.origin != "synthetic":
        raise ValueError("The UI demo exporter accepts synthetic data only.")
    sessions = reconstruct(normalized)
    metrics = calculate_metrics(sessions)
    records = {record.ref: record for record in normalized.records}
    metric_by_episode = {item["episode_id"]: item for item in metrics["episodes"]}
    event_id_to_ref = {record.event.event_id: record.ref for record in normalized.records}
    output_sessions = []
    for episode in sessions["episodes"]:
        metric = metric_by_episode[episode["episode_id"]]
        question_id = episode["scope"]["question_id"]
        metadata = DEMO_METADATA[question_id]
        timeline = []
        gap_by_destination = {gap["to_ref"]: gap for gap in episode["gaps"]}
        for ref in episode["event_refs"]:
            if ref in gap_by_destination:
                timeline.append(_gap_view(gap_by_destination[ref], records))
            timeline.append(_event_view(records[ref], episode))
        reasons = []
        for reason in metadata["reasons"]:
            refs = [event_id_to_ref[event_id] for event_id in reason["event_ids"]]
            reasons.append({**{key: value for key, value in reason.items() if key != "event_ids"},
                            "supporting_refs": refs,
                            "supporting_event_ids": reason["event_ids"]})
        output_sessions.append({
            "id": episode["episode_id"],
            "review_rank": metadata["review_rank"],
            "flagged": metadata["flagged"],
            "priority": metadata["priority"],
            "priority_basis": "Illustrative manual priority for the UI demonstration, not an anomaly score.",
            "scenario": metadata["scenario"],
            "synthetic": True,
            "student_id": episode["scope"]["learner_id"],
            "question_id": question_id,
            "assignment_id": episode["scope"]["assignment_id"],
            "outcome": _metric(metric["recovery"]["question_outcome"]),
            "active_time": _metric(metric["time"]["total_observed_active_time"]),
            "post_help_active_time": _metric(metric["time"]["active_time_after_first_help"]),
            "elapsed_time": _metric(metric["time"]["observed_elapsed_span"]),
            "reference_active_time": {
                **metadata["reference"],
                "basis": "Illustrative UI reference only. No research baseline has been calculated.",
            },
            "failed_checks_after_help": _metric(
                metric["activity"]["failed_check_count"]["after_first_help"]
            ),
            "tutor_requests": _metric(metric["activity"]["tutor_request_count"]),
            "completed_tutor_responses": _metric(
                metric["activity"]["completed_tutor_response_count"]
            ),
            "repeated_failures": _metric(metric["activity"]["repeated_failure_count"]),
            "continued_after_help": _metric(metric["recovery"]["continued_work_after_help"]),
            "resumed_after_help": _metric(metric["recovery"]["resumed_work_after_help"]),
            "reasons": reasons,
            "timeline": timeline,
            "source_event_refs": episode["event_refs"],
            "quality_warnings": episode["quality_warnings"],
        })
    output_sessions.sort(key=lambda session: session["review_rank"])
    return {
        "contract_version": 1,
        "dataset": {
            "id": sessions["dataset_id"],
            "synthetic": True,
            "label": "Synthetic HCI workflow demonstration",
            "notice": "All students, conversations, metrics, reference ranges, and priorities shown here are synthetic.",
            "priority_method": "Manual illustrative ordering. No anomaly-ranking algorithm is implemented.",
        },
        "summary": {
            "total_sessions": len(output_sessions),
            "flagged_sessions": sum(session["flagged"] for session in output_sessions),
            "high_priority_sessions": sum(session["priority"] == "high" for session in output_sessions),
        },
        "sessions": output_sessions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build_demo(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=True, allow_nan=False)
            file.write("\n")
    except (OSError, ValueError, KeyError):
        parser.exit(2, "Cannot build synthetic demo data; existing output is never overwritten.\n")
    print(json.dumps({"synthetic": True, "sessions": len(result["sessions"]),
                      "flagged": result["summary"]["flagged_sessions"]}))


if __name__ == "__main__":
    main()
