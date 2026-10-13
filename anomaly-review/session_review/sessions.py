"""Deterministic question episodes with explicit uncertainty and evidence links."""
from collections import defaultdict
from dataclasses import dataclass

from .normalize import digest
from .schema import Activity, CheckResult, Execution, QuestionStatus, StudentMessage, TutorResponse

SCOPE = ("learner_id", "course_id", "cohort_id", "assignment_id",
         "assignment_version", "notebook_id")
BEHAVIOR = {"student_message", "code_edit", "execution", "check_result", "activity"}


@dataclass(frozen=True)
class SessionConfig:
    gap_seconds: int = 1800

    def __post_init__(self):
        if type(self.gap_seconds) is not int or self.gap_seconds <= 0:
            raise ValueError("The work-bout gap must be a positive integer.")


def relation(a, b):
    """Compare event occurrence, never ingestion time or a guessed ID order."""
    x, y = a.event, b.event
    if x.occurred_at != y.occurred_at:
        return -1 if x.occurred_at < y.occurred_at else 1
    if x.order_stream_id is not None and x.order_stream_id == y.order_stream_id:
        if x.sequence != y.sequence:
            return -1 if x.sequence < y.sequence else 1
    return None


def timeline(records):
    groups = defaultdict(list)
    for record in records:
        groups[record.event.occurred_at].append(record)
    ordered, ties = [], []
    for at, group in sorted(groups.items()):
        streams = {r.event.order_stream_id for r in group}
        sequences = {r.event.sequence for r in group}
        certain = len(group) == 1 or (len(streams) == 1 and None not in streams
                                      and len(sequences) == len(group))
        group.sort(key=(lambda r: r.event.sequence) if certain and len(group) > 1
                   else (lambda r: r.ref))
        ordered.extend(group)
        if not certain:
            ties.append({"at": at.isoformat(), "event_refs": [r.ref for r in group]})
    return ordered, ties


def _scope(record):
    return tuple(getattr(record.event, key) for key in SCOPE) + (record.event.question.question_id,)


def _invalid_streams(records):
    streams = defaultdict(list)
    for r in records:
        if r.event.order_stream_id is not None:
            streams[r.event.order_stream_id].append(r)
    invalid = set()
    for stream, members in streams.items():
        values = sorted(members, key=lambda r: r.event.sequence)
        if len({r.event.sequence for r in values}) != len(values):
            invalid.add(stream)
        dated = [r for r in values if r.event.occurred_at is not None]
        if any(a.event.occurred_at > b.event.occurred_at for a, b in zip(dated, dated[1:])):
            invalid.add(stream)
    return invalid


def _bouts(records, episode_id, config):
    bouts, gaps = [], []
    previous = None
    for r in records:
        reason = None
        if previous is not None:
            delta = (r.event.occurred_at - previous.event.occurred_at).total_seconds()
            if delta > config.gap_seconds:
                reason = "observed_event_gap"
            elif relation(previous, r) == -1:
                if isinstance(previous.event.detail, Activity) and previous.event.detail.action == "pause":
                    reason = "explicit_pause"
                elif isinstance(r.event.detail, Activity) and r.event.detail.action == "resume":
                    reason = "explicit_resume"
            if reason:
                gaps.append({"from_ref": previous.ref, "to_ref": r.ref,
                             "elapsed_seconds": delta, "reason": reason})
        if previous is None or reason:
            bouts.append({"bout_id": f"{episode_id}/bout-{len(bouts) + 1}",
                          "resumed_from": bouts[-1]["bout_id"] if bouts else None,
                          "start_at": r.event.occurred_at.isoformat(),
                          "boundary_reason": reason or "first_observed_event",
                          "event_refs": []})
        bouts[-1]["event_refs"].append(r.ref)
        bouts[-1]["end_at"] = r.event.occurred_at.isoformat()
        previous = r
    return bouts, gaps


def _partition(records, boundary):
    partitions = {"before_refs": [], "after_refs": [], "ambiguous_refs": []}
    for r in records:
        if r.ref == boundary.ref:
            continue
        order = relation(r, boundary)
        key = "before_refs" if order == -1 else "after_refs" if order == 1 else "ambiguous_refs"
        partitions[key].append(r.ref)
    return partitions


def _help(records, unsafe_completion_refs):
    complete = [r for r in records if isinstance(r.event.detail, TutorResponse)
                and r.event.detail.status == "completed" and r.ref not in unsafe_completion_refs]
    unresolved = [r.ref for r in records if r.ref in unsafe_completion_refs
                  and isinstance(r.event.detail, TutorResponse)
                  and r.event.detail.status == "completed"]
    earliest = [r for r in complete if not any(relation(other, r) == -1 for other in complete
                                              if other.ref != r.ref)]
    behaviors = [r for r in records if r.event.detail.type in BEHAVIOR]
    boundaries = []
    for boundary in complete:
        windows = {"before_refs": [], "after_until_next_help_refs": [], "ambiguous_refs": [],
                   "later_help_period_refs": []}
        for r in behaviors:
            order = relation(r, boundary)
            if order == -1:
                windows["before_refs"].append(r.ref)
            elif order is None:
                windows["ambiguous_refs"].append(r.ref)
            else:
                others = [other for other in complete if other.ref != boundary.ref
                          and relation(other, boundary) != -1]
                if any(relation(boundary, other) == -1 and relation(other, r) == -1 for other in others):
                    windows["later_help_period_refs"].append(r.ref)
                elif any(relation(boundary, other) is None or relation(other, r) is None for other in others):
                    windows["ambiguous_refs"].append(r.ref)
                else:
                    windows["after_until_next_help_refs"].append(r.ref)
        boundaries.append({"response_ref": boundary.ref,
                           "completed_at": boundary.event.occurred_at.isoformat(),
                           "completion_basis": boundary.event.detail.completion_basis,
                           "all_events_relative_to_response": _partition(records, boundary),
                           "behavior_window": windows})
    first_known = len(earliest) == 1 and not unresolved
    return {
        "first_completed_response_ref": earliest[0].ref if first_known else None,
        "first_boundary_status": ("known" if first_known else "ambiguous"
                                  if earliest or unresolved else "not_observed"),
        "first_boundary_candidate_refs": list(dict.fromkeys(
            [r.ref for r in earliest] + unresolved
        )),
        "boundaries": boundaries,
        "unresolved_completed_response_refs": unresolved,
    }


def _interactions(records, conflict_refs):
    groups = defaultdict(list)
    for r in records:
        detail = r.event.detail
        if isinstance(detail, TutorResponse) or (isinstance(detail, StudentMessage) and detail.request_id):
            key = ("request", detail.request_id) if detail.request_id else ("unlinked", r.ref)
            groups[key].append(r)
    interactions = []
    for (kind, identity), members in sorted(groups.items()):
        requests = [r for r in members if isinstance(r.event.detail, StudentMessage)]
        responses = [r for r in members if isinstance(r.event.detail, TutorResponse)]
        linkage = "matched" if len(requests) == 1 and responses else "ambiguous" if len(requests) > 1 else "unmatched"
        if any(r.ref in conflict_refs for r in members):
            linkage = "ambiguous"
        interactions.append({
            "request_id": identity if kind == "request" else None,
            "linkage": linkage,
            "request_refs": [r.ref for r in requests],
            "response_refs": [r.ref for r in responses],
            "completed_response_refs": [r.ref for r in responses if r.event.detail.status == "completed"],
            "response_statuses": [{"ref": r.ref, "status": r.event.detail.status} for r in responses],
        })
    return interactions


def _linkage_conflicts(records):
    requests, responses = defaultdict(list), defaultdict(list)
    for r in records:
        d = r.event.detail
        if isinstance(d, (StudentMessage, TutorResponse)) and d.request_id:
            requests[d.request_id].append(r)
        if isinstance(d, TutorResponse) and d.response_id:
            responses[d.response_id].append(r)
    conflicts = []
    for members in requests.values():
        scopes = {_scope(r) for r in members if all(v is not None for v in _scope(r))}
        if len(scopes) > 1:
            conflicts.append({"code": "request_spans_question_scopes", "event_refs": [r.ref for r in members]})
    for members in responses.values():
        terminal = [r for r in members if r.event.detail.status in {"completed", "failed", "cancelled"}]
        scopes = {_scope(r) for r in members}
        request_ids = {r.event.detail.request_id for r in members if r.event.detail.request_id is not None}
        if len(terminal) > 1 or len(scopes) > 1 or len(request_ids) > 1:
            conflicts.append({"code": "response_lifecycle_ambiguous", "event_refs": [r.ref for r in members]})
    return conflicts


def _check_links(records):
    links = []
    for r in records:
        d = r.event.detail
        if not isinstance(d, CheckResult):
            continue
        candidates = [x for x in records if isinstance(x.event.detail, Execution)
                      and d.execution_id is not None and x.event.detail.execution_id == d.execution_id]
        completed = [x for x in candidates if x.event.detail.status in {"completed", "error"}]
        reasons = []
        if len(completed) != 1:
            reasons.append("missing_or_ambiguous_execution")
        else:
            execution = completed[0]
            if relation(execution, r) != -1:
                reasons.append("execution_order_unverified")
            if d.revision_id is None or execution.event.detail.revision_id is None:
                reasons.append("revision_missing")
            elif d.revision_id != execution.event.detail.revision_id:
                reasons.append("revision_mismatch")
        links.append({"check_ref": r.ref, "outcome": d.outcome, "scope": d.scope,
                      "execution_refs": [x.ref for x in candidates],
                      "binding": "verified" if not reasons else "unverified", "reasons": reasons})
    return links


def _outcome(records):
    statuses = [r for r in records if isinstance(r.event.detail, QuestionStatus)]
    latest = [r for r in statuses if not any(relation(r, other) == -1 for other in statuses
                                            if r.ref != other.ref)]
    state = "unknown"
    later = []
    if len(latest) > 1:
        state = "ambiguous"
    elif latest:
        last = latest[0]
        state = last.event.detail.status
        if state == "completed":
            activity = [r for r in records if r.event.detail.type in BEHAVIOR]
            later = [r.ref for r in activity if relation(last, r) == -1]
            if later:
                state = "activity_after_completion"
            elif any(relation(last, r) is None for r in activity):
                state = "ambiguous"
    return {"status": state, "status_evidence_refs": [r.ref for r in latest],
            "completion_event_refs": [r.ref for r in statuses if r.event.detail.status == "completed"],
            "later_activity_refs": later,
            "passing_check_refs": [r.ref for r in records if isinstance(r.event.detail, CheckResult)
                                   and r.event.detail.outcome == "pass"]}


def reconstruct(normalized, config=None):
    config = config or SessionConfig()
    invalid_streams = _invalid_streams(normalized.records)
    linkage_conflicts = _linkage_conflicts(normalized.records)
    conflict_refs = {ref for issue in linkage_conflicts for ref in issue["event_refs"]}
    groups, unassigned = defaultdict(list), []
    for r in normalized.records:
        reasons = ["missing_" + field for field in SCOPE if getattr(r.event, field) is None]
        if r.event.occurred_at is None:
            reasons.append("missing_occurred_at")
        if r.event.question.basis not in {"explicit", "verified_mapping"}:
            reasons.append("question_" + r.event.question.basis)
        if r.event.order_stream_id in invalid_streams:
            reasons.append("inconsistent_order_stream")
        if reasons:
            unassigned.append({"event_ref": r.ref, "reasons": reasons})
        else:
            groups[_scope(r)].append(r)
    episodes = []
    for key, members in sorted(groups.items()):
        records, ties = timeline(members)
        episode_id = "episode-" + digest([normalized.dataset_id, *key])
        bouts, gaps = _bouts(records, episode_id, config)
        scope = dict(zip((*SCOPE, "question_id"), key))
        help_info = _help(records, conflict_refs)
        outcome = _outcome(records)
        interactions = _interactions(records, conflict_refs)
        warnings = []
        if ties:
            warnings.append("timestamp_order_ambiguous")
        if any(isinstance(r.event.detail, TutorResponse) and r.event.detail.status == "unknown" for r in records):
            warnings.append("some_response_completion_unknown")
        if any(i["linkage"] != "matched" for i in interactions):
            warnings.append("some_tutor_interactions_unmatched")
        if help_info["unresolved_completed_response_refs"]:
            warnings.append("some_completed_response_boundaries_unresolved")
        if normalized.coverage is None or normalized.coverage.completeness != "declared_complete":
            warnings.append("observation_coverage_incomplete_or_unknown")
        episodes.append({
            "episode_id": episode_id, "scope": scope,
            "event_refs": [r.ref for r in records],
            "observed_start_at": records[0].event.occurred_at.isoformat(),
            "observed_end_at": records[-1].event.occurred_at.isoformat(),
            "observation_end_reason": "export_window_end" if normalized.coverage else "export_boundary_unknown",
            "bouts": bouts, "gaps": gaps, "ambiguous_order_groups": ties,
            "tutor_interactions": interactions, "help": help_info,
            "checks": _check_links(records), "outcome": outcome,
            "quality_warnings": warnings,
            "active_seconds": None,
        })
    return {
        "version": 1, "method": "question-episodes-v1", "dataset_id": normalized.dataset_id,
        "origin": normalized.origin, "input_sha256": normalized.input_sha256,
        "config": {"gap_seconds": config.gap_seconds},
        "coverage": normalized.coverage.model_dump(mode="json") if normalized.coverage else None,
        "episodes": episodes, "unassigned": unassigned, "linkage_conflicts": linkage_conflicts,
        "normalization": normalized.model_dump(mode="json"),
        "limitations": ["Work bouts describe observed event clusters, not active time.",
                        "A check pass does not establish question completion.",
                        "Temporal ordering does not establish tutor causation.",
                        "Missing data and outcomes remain unknown."],
    }
