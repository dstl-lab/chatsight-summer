"""Convert assembled evidence and saved assessments into the shared UI contract."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from . import analyze_sessions as analyzer
from .contract import ReviewBundle
from .historical import digest

VERSION = "session-findings-integration-v2-pr100"
TITLES = {"persistent_difficulty": "Possible continuing difficulty",
          "request_mismatch": "Possible request mismatch",
          "advice_linked_obstacle": "Possible obstacle after tutor advice"}


def unknown(reason):
    return {"status": "unknown", "value": None, "reason": reason, "evidence_refs": []}


def known(value, refs):
    return {"status": "known", "value": value, "reason": None, "evidence_refs": refs}


def analysis_view(result, model, source):
    if result is None:
        return {"state": "not_analyzed", "decision": None, "summary": "Not analyzed. Opening this dataset makes no model calls.",
                "findings": [], "validation_errors": [], "notices": [], "model": model, "source": source}
    valid = result["validation_status"] == "valid"
    failed = any(error.startswith("Assessment unavailable") or error.startswith("Interrupted") for error in result["validation_errors"])
    return {"state": "completed" if valid else "failed" if failed else "rejected",
        "decision": result["decision"], "summary": result["assessment"]["summary"] if valid else "No finding accepted: assessment failed or did not pass evidence validation.",
        "findings": result["assessment"]["findings"] if valid else [],
        "validation_errors": result["validation_errors"], "notices": result["notices"],
        "model": model, "source": source}


def timeline_view(session, context):
    evidence = analyzer.assemble(session)
    times = Counter(record["timestamp"] for record in evidence["timeline"])
    timeline = []
    previous = {record.revision_id: record for record in session.activity if isinstance(record, analyzer.Revision)}
    for record in evidence["timeline"]:
        kind = record.get("type", record.get("role"))
        kind = {"student": "student_message", "tutor": "tutor_response", "revision": "code_edit", "check": "check_result"}.get(kind, kind)
        meta = [{"label": "Origin", "value": record["origin"]},
                {"label": "Question", "value": record.get("question_id") or "Unknown"}]
        source = context.get("sources", {}).get(record["id"])
        if source:
            meta.extend([{"label": "Timestamp basis", "value": "Event-specific client time" if source.get("timestamp_basis") == "event_specific_client_timestamp" else "Database logging time"},
                         {"label": "Source record hash", "value": source["record_sha256"]}])
        code = None
        if kind in {"student_message", "tutor_response"}:
            title = "Student message" if kind == "student_message" else "Tutor response"
            body = record["text"]
            actor = "Student" if kind == "student_message" else "AI tutor"
        elif kind == "code_edit":
            title, actor, body = "Code edited", "Notebook", "Authored or explicitly supplied revision; no execution inferred."
            prior = previous.get(record.get("previous_revision_id"))
            code = {"before": prior.source if prior else None, "after": record["source"]}
            meta.append({"label": "Revision", "value": record["revision_id"]})
            if record.get("capture_basis", "edit") != "edit":
                kind = "code_capture"
                title = "Source captured at execution" if record["capture_basis"] == "execution_capture" else "Active-cell source captured at tutor request"
                body = "Recorded source capture, not an edit event. " + ("This source is explicitly bound to the execution." if record["capture_basis"] == "execution_capture" else "The active cell is not necessarily the subject of the student's question.")
        elif kind == "execution":
            title, actor = "Cell executed", "Notebook"
            body = record.get("output") or f'Execution status: {record["status"]}.'
            meta.extend([{"label": "Execution", "value": record["execution_id"]},
                         {"label": "Revision", "value": record.get("revision_id") or "Unknown"}])
            if record.get("kernel_id"):
                meta.extend([{"label": "Kernel", "value": record["kernel_id"]},
                             {"label": "Execution status", "value": record["status"]},
                             {"label": "Output complete", "value": str(record.get("output_complete"))}])
        elif kind == "check_result":
            title, actor = f'Check {record["result"]}', "Autograder"
            body = record.get("feedback") or "Supplied check observation."
            meta.append({"label": "Execution", "value": record.get("execution_id") or "Unknown"})
            meta.append({"label": "Grader", "value": record.get("grader_id") or "Unknown"})
            if record.get("verdict_method"):
                meta.append({"label": "Verdict method", "value": record["verdict_method"]})
        else:
            title = {"edit_observation": "Cell edit burst observed", "cell_observation": "Notebook activity", "tutor_failure": "Tutor request failed"}[kind]
            actor, body = "AI tutor" if kind == "tutor_failure" else "Notebook", record["description"]
            kind = "code_edit" if kind == "edit_observation" else "activity"
        if record.get("cell_id"):
            meta.append({"label": "Cell", "value": record["cell_id"]})
        if record.get("request_id"):
            meta.append({"label": "Request", "value": record["request_id"]})
        if record.get("sequence") is not None:
            meta.append({"label": "Client sequence", "value": str(record["sequence"])})
        for observation in context.get("observations", []):
            if observation["event_id"] == record["id"]:
                meta.extend(observation["metadata"])
        timeline.append({"id": record["id"], "source_event_id": source["export_event_id"] if source else record["id"],
            "kind": kind, "actor": actor, "title": title, "body": body, "occurred_at": record["timestamp"],
            "phase": "ambiguous" if times[record["timestamp"]] > 1 else "unpartitioned",
            "order_uncertain": times[record["timestamp"]] > 1,
                "source_pointers": [f'line:{source["line"]}'] if source else [], "code_diff": code,
                "metadata": list({(item["label"], item["value"]): item for item in meta}.values())})
    timeline.extend(context.get("events", []))
    times = Counter(event["occurred_at"] for event in timeline)
    for event in timeline:
        if times[event["occurred_at"]] > 1:
            event.update(order_uncertain=True, phase="ambiguous")
    return sorted(timeline, key=lambda event: (event["occurred_at"], event["id"]))


def build(sessions, *, input_hash, context=None, results=None, model=None, source="not analyzed"):
    context, results = context or {}, results or {}
    origins = {record.origin for session in sessions for record in [*session.messages, *session.activity]}
    if origins not in ({"recorded"}, {"synthetic"}):
        raise ValueError("Keep recorded and synthetic datasets separate.")
    synthetic = origins == {"synthetic"}
    views = []
    for number, session in enumerate(sessions, 1):
        ctx = context.get(session.session_id, {})
        analysis = analysis_view(results.get(session.session_id), model, source)
        timeline = timeline_view(session, ctx)
        refs = {event["id"]: event for event in timeline}
        reasons = []
        for index, finding in enumerate(analysis["findings"], 1):
            highlighted = list(dict.fromkeys(finding["highlight_ids"] + finding["recovery_evidence_ids"]))
            reasons.append({"id": f"finding-{index}", "title": TITLES[finding["category"]],
                "description": finding["explanation"], "supporting_refs": highlighted,
                "supporting_event_ids": [refs[ref]["source_event_id"] for ref in highlighted]})
        no_link = "Unavailable: question applicability, action timing and completion are not established."
        questions = {record.question_id for record in [*session.messages, *session.activity] if record.question_id}
        qid = next(iter(questions)) if len(questions) == 1 else None
        completed_responses = [message.id for message in session.messages if message.role == "tutor"]
        views.append({"id": session.session_id, "review_rank": number,
            "flagged": analysis["state"] == "completed" and analysis["decision"] == "surface",
            "priority": None, "priority_basis": "Model decisions are review findings, not priority scores.",
            "scenario": analysis["summary"], "synthetic": synthetic,
            "scope": ctx.get("scope", "question_episode" if qid else "conversation"),
            "student_id": ctx.get("student_id", "Authored example"), "question_id": qid,
            "assignment_id": ctx.get("notebook"),
            "outcome": unknown(no_link), "active_time": unknown("No validated active-work measure."),
            "post_help_active_time": unknown(no_link), "elapsed_time": unknown("Recorded span is not active work time."),
            "reference_active_time": {"status": "unknown", "lower_seconds": None, "upper_seconds": None,
                                      "basis": "No valid question-level active-time baseline."},
            "failed_checks_after_help": unknown(no_link), "repeated_failures": unknown(no_link),
            "tutor_requests": known(sum(message.role == "student" for message in session.messages),
                                    [message.id for message in session.messages if message.role == "student"]),
            "completed_tutor_responses": known(len(completed_responses), completed_responses) if ctx.get("scope") == "notebook_session" else unknown("Recorded messages do not certify response completion."),
            "continued_after_help": unknown(no_link), "resumed_after_help": unknown(no_link),
            "reasons": reasons, "timeline": timeline, "source_event_refs": list(refs),
            "quality_warnings": list(dict.fromkeys([*ctx.get("warnings", []), *analyzer.assemble(session)["warnings"]])),
            "analysis": analysis})
    # Dataset identity binds the exact evidence and analysis configuration/results.
    dataset_id = "findings-" + digest([input_hash, context, results, model, VERSION])[:24]
    doc = {"contract_version": 2,
        "dataset": {"id": dataset_id, "synthetic": synthetic,
            "label": "Synthetic session findings" if synthetic else "Private PR100 notebook session findings" if any(s.get("scope") == "notebook_session" for s in views) else "Private historical session findings",
            "notice": "All events are invented." if synthetic else "Private recent PR100 course observations. Actual edit bursts and source-bound executions; question applicability may remain unknown." if any(s.get("scope") == "notebook_session" for s in views) else "Private recorded course content. Conversation scope; notebook actions and question applicability may be unknown.",
            "priority_method": "No automatic priority score", "input_sha256": input_hash, "model": model,
            "prompt_sha256": hashlib.sha256(analyzer.PROMPT.encode()).hexdigest(), "analysis_version": VERSION},
        "summary": {"total_sessions": len(views), "flagged_sessions": sum(view["flagged"] for view in views),
                    "high_priority_sessions": 0}, "sessions": views}
    return ReviewBundle.model_validate(doc).model_dump(mode="json")
