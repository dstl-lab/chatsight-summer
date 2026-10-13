"""Privacy-safe aggregate quality checks for provisional real-data ingestion."""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from .json_adapter import MISSING, JsonMapping, resolve_pointer
from .schema import CheckResult, Normalization, TutorResponse


def _metric(status: str, evaluated: int, issue_count: int, unit: str,
            notes: list[str] | None = None) -> dict:
    result = {
        "status": status,
        "unit": unit,
        "evaluated": evaluated,
        "passed": max(0, evaluated - issue_count),
        "issues": issue_count,
    }
    if notes:
        result["notes"] = notes
    return result


def _status(issue_count: int, blocking=False) -> str:
    if not issue_count:
        return "pass"
    return "fail" if blocking else "warning"


def _identity_key(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError):
        return None


def _raw_event_id_quality(records: list[object], mapping: JsonMapping):
    pointer = mapping.common_fields.get("event_id")
    missing = set()
    groups = defaultdict(list)
    for index, record in enumerate(records):
        if not isinstance(record, dict) or pointer is None:
            missing.add(index)
            continue
        value = resolve_pointer(record, pointer)
        key = _identity_key(value)
        if value is MISSING or value is None or value == "" or key is None:
            missing.add(index)
        else:
            groups[key].append(index)
    duplicate = {index for members in groups.values() if len(members) > 1 for index in members}
    return missing, duplicate


def _raw_timestamp_quality(records: list[object], mapping: JsonMapping):
    pointer = mapping.common_fields.get("occurred_at")
    missing = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or pointer is None:
            missing.add(index)
            continue
        value = resolve_pointer(record, pointer)
        if value is MISSING or value is None or value == "":
            missing.add(index)
    return missing


def _raw_type_pointers(records: list[object], record_pointers: list[str],
                       mapping: JsonMapping, canonical_type: str) -> set[str]:
    pointers = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        raw_type = resolve_pointer(record, mapping.event_type_pointer)
        type_mapping = mapping.event_types.get(raw_type) if isinstance(raw_type, str) else None
        if type_mapping is not None and type_mapping.canonical_type == canonical_type:
            pointers.add(record_pointers[index])
    return pointers


def _source_pointer_index(normalized: Normalization):
    return {
        record.ref: [source.record_pointer for source in record.sources]
        for record in normalized.records
    }


def _accepted_index(normalized: Normalization):
    return {record.ref: record for record in normalized.records}


def build_quality_report(records: list[object], record_pointers: list[str], mapping: JsonMapping,
                         normalized: Normalization, sessions: dict, metrics: dict) -> dict:
    """Build diagnostics that never include raw message, code, output, or identity values."""
    ref_pointers = _source_pointer_index(normalized)
    accepted = _accepted_index(normalized)
    rejected_by_pointer = defaultdict(list)
    for issue in normalized.rejected:
        rejected_by_pointer[issue.record_pointer].append(issue)

    missing_ids, duplicate_ids = _raw_event_id_quality(records, mapping)
    missing_times = _raw_timestamp_quality(records, mapping)
    invalid_timestamp_pointers = {
        issue.record_pointer for issue in normalized.rejected
        if issue.code == "invalid_event"
        and any(location in {"occurred_at", "received_at"} for location in issue.locations)
    }
    received_before_occurred = set()
    for record in normalized.records:
        event = record.event
        if event.occurred_at is not None and event.received_at is not None:
            if event.received_at < event.occurred_at:
                received_before_occurred.update(source.record_pointer for source in record.sources)

    unassigned_by_ref = {item["event_ref"]: item["reasons"] for item in sessions["unassigned"]}
    question_refs = {
        ref for ref, reasons in unassigned_by_ref.items()
        if any(reason in {"question_missing", "question_ambiguous"} for reason in reasons)
    }
    order_refs = {
        ref for ref, reasons in unassigned_by_ref.items()
        if "inconsistent_order_stream" in reasons
    }
    identity_refs = {
        ref for ref, reasons in unassigned_by_ref.items()
        if any(reason.startswith("missing_") and reason not in {"missing_occurred_at"}
               for reason in reasons)
    }

    completion_refs = set()
    unknown_completion_refs = set()
    check_question_refs = set()
    for ref, record in accepted.items():
        if isinstance(record.event.detail, TutorResponse) and record.event.detail.status == "unknown":
            unknown_completion_refs.add(ref)
        if isinstance(record.event.detail, CheckResult) and ref in question_refs:
            check_question_refs.add(ref)
    for issue in normalized.rejected:
        if issue.code == "invalid_event" and any(
            location.startswith("detail.tutor_response") or "completion_basis" in location
            for location in issue.locations
        ):
            completion_refs.add(issue.record_pointer)
    completion_conflict_refs = {
        ref for conflict in sessions["linkage_conflicts"]
        if conflict["code"] == "response_lifecycle_ambiguous"
        for ref in conflict["event_refs"]
    }
    linkage_conflict_refs = {
        ref for conflict in sessions["linkage_conflicts"] for ref in conflict["event_refs"]
    }
    completion_refs.update(completion_conflict_refs)

    interactions = [interaction for episode in sessions["episodes"]
                    for interaction in episode["tutor_interactions"]]
    unmatched = [item for item in interactions if item["linkage"] != "matched"]
    insufficient = [item for item in metrics["episodes"]
                    if not item["eligibility"]["common_comparison_population"]["eligible"]]
    ambiguous_order_records = {
        ref for episode in sessions["episodes"] for group in episode["ambiguous_order_groups"]
        for ref in group["event_refs"]
    }
    order_issue_refs = order_refs | ambiguous_order_records

    missing_id_pointers = {record_pointers[index] for index in missing_ids}
    duplicate_id_pointers = {record_pointers[index] for index in duplicate_ids}
    missing_time_pointers = {record_pointers[index] for index in missing_times}
    timestamp_problem_pointers = missing_time_pointers | invalid_timestamp_pointers | received_before_occurred
    question_pointers = {pointer for ref in question_refs for pointer in ref_pointers.get(ref, [])}
    identity_pointers = {pointer for ref in identity_refs for pointer in ref_pointers.get(ref, [])}
    completion_pointers = {
        pointer for value in completion_refs | unknown_completion_refs
        for pointer in ([value] if value.startswith("/") else ref_pointers.get(value, []))
    }
    check_pointers = {pointer for ref in check_question_refs for pointer in ref_pointers.get(ref, [])}
    tutor_record_pointers = _raw_type_pointers(
        records, record_pointers, mapping, "tutor_response"
    )
    check_record_pointers = _raw_type_pointers(
        records, record_pointers, mapping, "check_result"
    )

    unexpected = {issue.record_pointer for issue in normalized.rejected
                  if issue.code in {"unexpected_event_type", "missing_event_type"}}
    conflict_id_pointers = {issue.record_pointer for issue in normalized.rejected
                            if issue.code == "conflicting_event_id"}
    linkage_conflict_pointers = {
        pointer for ref in linkage_conflict_refs for pointer in ref_pointers.get(ref, [])
    }
    identifier_pointers = identity_pointers | conflict_id_pointers | linkage_conflict_pointers

    checks = {
        "event_ids": _metric(
            _status(len(missing_id_pointers | duplicate_id_pointers), blocking=True),
            len(records), len(missing_id_pointers | duplicate_id_pointers), "records",
            ["Duplicate counts include every record participating in a duplicate-ID group."],
        ),
        "timestamps": _metric(
            _status(len(timestamp_problem_pointers), blocking=True), len(records),
            len(timestamp_problem_pointers), "records",
            ["Missing, invalid, or received-before-occurred timestamps are counted."],
        ),
        "chronological_order": _metric(
            _status(len(order_issue_refs)), len(normalized.records),
            len(order_issue_refs), "accepted_records",
            ["Timestamp ties without a trusted sequence are ambiguous, not reordered by guesswork."],
        ),
        "question_attribution": _metric(
            _status(len(question_pointers), blocking=True), len(normalized.records),
            len(question_pointers), "accepted_records",
        ),
        "tutor_response_completion": _metric(
            _status(len(completion_pointers), blocking=True), len(tutor_record_pointers),
            len(completion_pointers), "tutor_response_records",
        ),
        "tutor_request_response_linkage": _metric(
            _status(len(unmatched)), len(interactions), len(unmatched), "interactions",
        ),
        "check_question_association": _metric(
            _status(len(check_pointers), blocking=True),
            len(check_record_pointers),
            len(check_pointers), "check_records",
        ),
        "session_activity_evidence": _metric(
            _status(len(insufficient)), len(metrics["episodes"]), len(insufficient), "sessions",
            ["Insufficient sessions remain present but are ineligible for common metric comparison."],
        ),
        "event_types": _metric(
            _status(len(unexpected), blocking=True), len(records), len(unexpected), "records",
        ),
        "cross_source_identifiers": _metric(
            _status(len(identifier_pointers), blocking=True), len(records),
            len(identifier_pointers), "records",
            ["Includes incomplete session scope, conflicting event IDs, and linkage scope conflicts."],
        ),
    }

    unresolved = []
    for pointer in record_pointers:
        codes = [issue.code for issue in rejected_by_pointer.get(pointer, [])]
        locations = sorted({location for issue in rejected_by_pointer.get(pointer, [])
                            for location in issue.locations})
        if pointer in missing_id_pointers:
            codes.append("missing_event_id")
        if pointer in duplicate_id_pointers:
            codes.append("duplicate_event_id")
        if pointer in received_before_occurred:
            codes.append("received_before_occurred")
        if codes:
            unresolved.append({"record_pointer": pointer, "codes": sorted(set(codes)),
                               "locations": locations})
    for ref, reasons in unassigned_by_ref.items():
        for pointer in ref_pointers.get(ref, []):
            unresolved.append({"record_pointer": pointer,
                               "codes": ["unassigned_event", *sorted(reasons)],
                               "locations": []})

    issue_counts = Counter(
        code for item in unresolved for code in item["codes"]
    )
    limitations = []
    if normalized.rejected:
        limitations.append("Rejected records cannot contribute to reconstructed sessions.")
    if sessions["unassigned"]:
        limitations.append("Accepted but unassigned events cannot contribute to question sessions.")
    if any(item["quality_warnings"] for item in sessions["episodes"]):
        limitations.append("One or more sessions contain ordering, coverage, or tutor-linkage uncertainty.")
    if insufficient:
        limitations.append("Some sessions lack sufficient evidence for the common metric population.")
    limitations.append("The source mapping is provisional until compared manually with the real export.")

    blocking_checks = [name for name, item in checks.items() if item["status"] == "fail"]
    gate_status = "blocked" if blocking_checks else "review_required"
    return {
        "version": 1,
        "method": "phase2c-data-quality-v1",
        "dataset_id": normalized.dataset_id,
        "origin": normalized.origin,
        "input_sha256": normalized.input_sha256,
        "mapping": {"adapter_name": mapping.adapter_name, "status": mapping.status,
                    "mapping_version": mapping.mapping_version},
        "privacy": {
            "contains_raw_student_messages": False,
            "contains_raw_notebook_code": False,
            "contains_source_identifier_values": False,
            "diagnostic_locator": "JSON record pointers only",
        },
        "counts": {
            "input_records": len(records),
            "accepted_normalized_records": len(normalized.records),
            "rejected_records": len(normalized.rejected),
            "coalesced_duplicate_records": normalized.duplicate_records,
            "unassigned_events": len(sessions["unassigned"]),
            "reconstructed_question_sessions": len(sessions["episodes"]),
            "metric_sessions": len(metrics["episodes"]),
        },
        "checks": checks,
        "issue_counts": dict(sorted(issue_counts.items())),
        "unresolved_record_manifest": unresolved,
        "reconstruction_impact": {
            "rejected_record_count": len(normalized.rejected),
            "unassigned_event_count": len(sessions["unassigned"]),
            "sessions_with_metric_limitations": len(insufficient),
        },
        "validation_gate": {
            "status": gate_status,
            "blocking_checks": blocking_checks,
            "real_data_validated": False,
        },
        "limitations": limitations,
    }
