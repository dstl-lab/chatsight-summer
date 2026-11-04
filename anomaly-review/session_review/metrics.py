"""Evidence-linked behavioral metrics over reconstructed question episodes."""
from dataclasses import dataclass

from .schema import (
    Activity,
    CheckResult,
    CodeEdit,
    Execution,
    NormalizedEvent,
    StudentMessage,
    TutorResponse,
)
from .sessions import relation


CONCRETE_ACTIONS = (StudentMessage, CodeEdit, Execution, CheckResult)
ACTIVE_OBSERVATIONS = (StudentMessage, CodeEdit, Execution, CheckResult, Activity)


@dataclass(frozen=True)
class MetricsConfig:
    """Conservative interval cap for the observed-active-time estimate."""

    active_interval_seconds: int = 300

    def __post_init__(self):
        if type(self.active_interval_seconds) is not int or self.active_interval_seconds <= 0:
            raise ValueError("The active interval cap must be a positive integer.")


def _refs(values):
    return list(dict.fromkeys(value for value in values if value is not None))


def _known(value, evidence_refs=(), **details):
    result = {"status": "known", "value": value, "evidence_refs": _refs(evidence_refs)}
    if details:
        result["details"] = details
    return result


def _unknown(reason, evidence_refs=(), **details):
    result = {"status": "unknown", "value": None, "reason": reason,
              "evidence_refs": _refs(evidence_refs)}
    if details:
        result["details"] = details
    return result


def _is_active(record):
    detail = record.event.detail
    return isinstance(detail, ACTIVE_OBSERVATIONS) and not (
        isinstance(detail, Activity) and detail.action in {"blur", "pause"}
    )


def _is_concrete_action(record):
    return isinstance(record.event.detail, CONCRETE_ACTIONS)


def _bout_map(episode):
    return {ref: bout["bout_id"] for bout in episode["bouts"] for ref in bout["event_refs"]}


def _ambiguous_refs(episode):
    return {ref for group in episode["ambiguous_order_groups"] for ref in group["event_refs"]}


def _active_time(records, episode, config, allowed_refs=None):
    allowed = set(allowed_refs) if allowed_refs is not None else None
    bout_for = _bout_map(episode)
    ambiguous = _ambiguous_refs(episode)
    relevant_ambiguous = [r.ref for r in records if _is_active(r) and r.ref in ambiguous
                          and (allowed is None or r.ref in allowed)]
    if relevant_ambiguous:
        return _unknown("activity_order_ambiguous", relevant_ambiguous)

    intervals = []
    excluded = []
    for left, right in zip(records, records[1:]):
        if allowed is not None and (left.ref not in allowed or right.ref not in allowed):
            continue
        if not (_is_active(left) and _is_active(right)):
            continue
        seconds = (right.event.occurred_at - left.event.occurred_at).total_seconds()
        if relation(left, right) != -1 or seconds <= 0:
            excluded.append({"from_ref": left.ref, "to_ref": right.ref,
                             "reason": "order_or_elapsed_time_uncertain"})
        elif bout_for.get(left.ref) != bout_for.get(right.ref):
            excluded.append({"from_ref": left.ref, "to_ref": right.ref,
                             "elapsed_seconds": seconds, "reason": "work_bout_boundary"})
        elif seconds > config.active_interval_seconds:
            excluded.append({"from_ref": left.ref, "to_ref": right.ref,
                             "elapsed_seconds": seconds, "reason": "active_interval_cap_exceeded"})
        else:
            intervals.append({"from_ref": left.ref, "to_ref": right.ref,
                              "seconds": seconds})
    evidence = [ref for interval in intervals for ref in (interval["from_ref"], interval["to_ref"])]
    if not intervals:
        return _unknown("insufficient_observed_activity_intervals", evidence,
                        excluded_intervals=excluded)
    return _known(sum(interval["seconds"] for interval in intervals), evidence,
                  unit="seconds", intervals=intervals, excluded_intervals=excluded,
                  estimator="adjacent-observed-activity-intervals")


def _elapsed_span(records):
    if not records:
        return _unknown("no_session_events")
    seconds = (records[-1].event.occurred_at - records[0].event.occurred_at).total_seconds()
    return _known(seconds, [records[0].ref, records[-1].ref], unit="seconds")


def _first_help(episode, index):
    ref = episode["help"]["first_completed_response_ref"]
    return index.get(ref) if episode["help"]["first_boundary_status"] == "known" else None


def _partition_for_first_help(records, episode, index):
    boundary = _first_help(episode, index)
    if boundary is None:
        return None, None, None
    before, after, ambiguous = [], [], []
    for record in records:
        if not _is_active(record):
            continue
        order = relation(record, boundary)
        if order == -1:
            before.append(record.ref)
        elif order == 1:
            after.append(record.ref)
        elif record.ref != boundary.ref:
            ambiguous.append(record.ref)
    return before, after, ambiguous


def _partitioned_count(records, episode, index, predicate):
    before, after, ambiguous = _partition_for_first_help(records, episode, index)
    if before is None:
        refs = episode["help"]["first_boundary_candidate_refs"]
        return {
            "before_first_help": _unknown("first_completed_response_not_known", refs),
            "after_first_help": _unknown("first_completed_response_not_known", refs),
        }
    relevant_ambiguous = [ref for ref in ambiguous if predicate(index[ref])]
    if relevant_ambiguous:
        unknown = _unknown("event_position_relative_to_help_ambiguous", relevant_ambiguous)
        return {"before_first_help": unknown, "after_first_help": dict(unknown)}
    before_matches = [record.ref for record in records if record.ref in before and predicate(record)]
    after_matches = [record.ref for record in records if record.ref in after and predicate(record)]
    return {
        "before_first_help": _known(len(before_matches), before_matches, unit="events"),
        "after_first_help": _known(len(after_matches), after_matches, unit="events"),
    }


def _completed_response_count(records, episode):
    complete = [r.ref for r in records if isinstance(r.event.detail, TutorResponse)
                and r.event.detail.status == "completed"]
    unresolved = episode["help"]["unresolved_completed_response_refs"]
    if unresolved:
        return _unknown("completed_response_lifecycle_ambiguous", complete,
                        unresolved_response_refs=unresolved)
    return _known(len(complete), complete, unit="events")


def _repeated_failures(records):
    failures = [r for r in records if isinstance(r.event.detail, CheckResult)
                and r.event.detail.outcome == "fail"]
    missing = [r.ref for r in failures if not r.event.detail.grader_id
               or not r.event.detail.grader_version]
    if missing:
        return _unknown("logical_check_identifier_missing", [r.ref for r in failures],
                        unidentified_failure_refs=missing)
    groups = {}
    for record in failures:
        detail = record.event.detail
        key = f"{detail.grader_id}@{detail.grader_version}"
        groups.setdefault(key, []).append(record.ref)
    repeated = sum(max(0, len(refs) - 1) for refs in groups.values())
    return _known(repeated, [r.ref for r in failures], unit="repeat_failures",
                  logical_check_groups=groups)


def _safe_boundaries(records, episode, index):
    return [index[item["response_ref"]] for item in episode["help"]["boundaries"]]


def _response_action_latencies(records, episode, index):
    boundaries = _safe_boundaries(records, episode, index)
    if not boundaries:
        return _unknown("no_completed_tutor_response")
    items = []
    for position, boundary in enumerate(boundaries):
        next_boundary = boundaries[position + 1] if position + 1 < len(boundaries) else None
        candidates = []
        ambiguous = []
        for record in records:
            if not _is_concrete_action(record):
                continue
            after = relation(boundary, record)
            before_next = relation(record, next_boundary) if next_boundary else -1
            if after is None or (next_boundary and before_next is None):
                ambiguous.append(record.ref)
            elif after == -1 and (next_boundary is None or before_next == -1):
                candidates.append(record)
        if ambiguous:
            items.append(_unknown("action_order_relative_to_response_ambiguous",
                                  [boundary.ref, *ambiguous], response_ref=boundary.ref))
            continue
        earliest = [candidate for candidate in candidates
                    if not any(relation(other, candidate) == -1 for other in candidates
                               if other.ref != candidate.ref)]
        if len(earliest) != 1:
            reason = "no_action_before_next_help" if next_boundary else "no_subsequent_action_observed"
            refs = [boundary.ref, next_boundary.ref if next_boundary else None]
            items.append(_unknown(reason, refs, response_ref=boundary.ref))
            continue
        action = earliest[0]
        seconds = (action.event.occurred_at - boundary.event.occurred_at).total_seconds()
        items.append(_known(seconds, [boundary.ref, action.ref], unit="seconds",
                            response_ref=boundary.ref, action_ref=action.ref,
                            action_type=action.event.detail.type))
    status = "known" if all(item["status"] == "known" for item in items) else "unknown"
    return {"status": status, "value": items,
            "evidence_refs": _refs(ref for item in items for ref in item["evidence_refs"]),
            **({"reason": "one_or_more_response_latencies_unknown"} if status == "unknown" else {})}


def _between_help_active_time(records, episode, index, config):
    boundaries = _safe_boundaries(records, episode, index)
    if len(boundaries) < 2:
        return _unknown("fewer_than_two_completed_tutor_responses",
                        [boundary.ref for boundary in boundaries])
    items = []
    for left, right in zip(boundaries, boundaries[1:]):
        if relation(left, right) != -1:
            items.append(_unknown("response_order_ambiguous", [left.ref, right.ref],
                                  from_response_ref=left.ref, to_response_ref=right.ref))
            continue
        allowed = [record.ref for record in records if relation(left, record) == -1
                   and relation(record, right) == -1 and _is_active(record)]
        metric = _active_time(records, episode, config, allowed)
        metric.setdefault("details", {}).update({"from_response_ref": left.ref,
                                                  "to_response_ref": right.ref})
        metric["evidence_refs"] = _refs([left.ref, *metric["evidence_refs"], right.ref])
        items.append(metric)
    status = "known" if all(item["status"] == "known" for item in items) else "unknown"
    return {"status": status, "value": items,
            "evidence_refs": _refs(ref for item in items for ref in item["evidence_refs"]),
            **({"reason": "one_or_more_between_help_intervals_unknown"} if status == "unknown" else {})}


def _window_count(records, index, included_refs, ambiguous_refs, predicate):
    ambiguous = [ref for ref in ambiguous_refs if predicate(index[ref])]
    if ambiguous:
        return _unknown("event_position_relative_to_response_ambiguous", ambiguous)
    matches = [record.ref for record in records
               if record.ref in included_refs and predicate(record)]
    return _known(len(matches), matches, unit="events")


def _per_response_windows(records, episode, index, config):
    windows = []
    for boundary in episode["help"]["boundaries"]:
        before = boundary["behavior_window"]["before_refs"]
        after = boundary["behavior_window"]["after_until_next_help_refs"]
        ambiguous = boundary["behavior_window"]["ambiguous_refs"]
        if any(ref in ambiguous and _is_active(index[ref]) for ref in ambiguous):
            before_active = _unknown("activity_position_relative_to_response_ambiguous",
                                     [boundary["response_ref"], *ambiguous])
            after_active = dict(before_active)
        else:
            before_active = _active_time(records, episode, config, before)
            after_active = _active_time(records, episode, config, after)
        predicates = {
            "failed_check_count": lambda r: isinstance(r.event.detail, CheckResult)
            and r.event.detail.outcome == "fail",
            "code_edit_count": lambda r: isinstance(r.event.detail, CodeEdit),
            "execution_count": lambda r: isinstance(r.event.detail, Execution),
            "student_message_count": lambda r: isinstance(r.event.detail, StudentMessage),
        }
        before_counts = {name: _window_count(records, index, before, ambiguous, predicate)
                         for name, predicate in predicates.items()}
        after_counts = {name: _window_count(records, index, after, ambiguous, predicate)
                        for name, predicate in predicates.items()}
        evidence = _refs([
            boundary["response_ref"],
            *before_active["evidence_refs"],
            *after_active["evidence_refs"],
            *(ref for metric in [*before_counts.values(), *after_counts.values()]
              for ref in metric["evidence_refs"]),
        ])
        windows.append({
            "response_ref": boundary["response_ref"],
            "completed_at": boundary["completed_at"],
            "completion_basis": boundary["completion_basis"],
            "active_time_before_response": before_active,
            "active_time_after_until_next_response": after_active,
            "activity_before_response": before_counts,
            "activity_after_until_next_response": after_counts,
            "later_help_period_refs": boundary["behavior_window"]["later_help_period_refs"],
            "evidence_refs": evidence,
        })
    return windows


def _eventual_question_pass(records):
    passes = [r.ref for r in records if isinstance(r.event.detail, CheckResult)
              and r.event.detail.scope == "question" and r.event.detail.outcome == "pass"]
    if passes:
        return _known(True, passes, interpretation="at_least_one_question_scope_pass_observed")
    checks = [r.ref for r in records if isinstance(r.event.detail, CheckResult)]
    return _unknown("no_question_scope_pass_observed", checks)


def _failed_checks_to_recovery(records, episode, index):
    boundary = _first_help(episode, index)
    if boundary is None:
        return _unknown("first_completed_response_not_known",
                        episode["help"]["first_boundary_candidate_refs"])
    passes, ambiguous = [], []
    for record in records:
        detail = record.event.detail
        if not (isinstance(detail, CheckResult) and detail.scope == "question"
                and detail.outcome == "pass"):
            continue
        order = relation(boundary, record)
        if order == -1:
            passes.append(record)
        elif order is None:
            ambiguous.append(record.ref)
    if ambiguous:
        return _unknown("recovery_order_ambiguous", [boundary.ref, *ambiguous])
    earliest = [candidate for candidate in passes
                if not any(relation(other, candidate) == -1 for other in passes
                           if other.ref != candidate.ref)]
    if len(earliest) != 1:
        return _unknown("no_unambiguous_post_help_question_pass", [boundary.ref, *[r.ref for r in passes]])
    recovery = earliest[0]
    failures = [r.ref for r in records if isinstance(r.event.detail, CheckResult)
                and r.event.detail.outcome == "fail" and relation(boundary, r) == -1
                and relation(r, recovery) == -1]
    return _known(len(failures), [boundary.ref, *failures, recovery.ref], unit="failed_checks",
                  first_help_ref=boundary.ref, recovery_check_ref=recovery.ref)


def _continuation(records, episode, index):
    boundary = _first_help(episode, index)
    if boundary is None:
        return {
            "continued_work_after_help": _unknown("first_completed_response_not_known"),
            "resumed_work_after_help": _unknown("first_completed_response_not_known"),
        }
    after, ambiguous = [], []
    for record in records:
        if not _is_concrete_action(record):
            continue
        order = relation(boundary, record)
        if order == -1:
            after.append(record)
        elif order is None:
            ambiguous.append(record.ref)
    if ambiguous:
        unknown = _unknown("post_help_activity_order_ambiguous", [boundary.ref, *ambiguous])
        return {"continued_work_after_help": unknown, "resumed_work_after_help": dict(unknown)}
    terminal_known = episode["outcome"]["status"] in {"completed", "unfinished", "reopened"}
    if not after:
        continued = (_known(False, [boundary.ref, *episode["outcome"]["status_evidence_refs"]])
                     if terminal_known else _unknown("no_post_help_action_observed", [boundary.ref]))
        resumed = (_known(False, continued["evidence_refs"])
                   if terminal_known else _unknown("observation_ended_without_known_outcome", [boundary.ref]))
        return {"continued_work_after_help": continued, "resumed_work_after_help": resumed}
    bouts = _bout_map(episode)
    resumed_refs = [r.ref for r in after if bouts.get(r.ref) != bouts.get(boundary.ref)]
    continued = _known(True, [boundary.ref, *[r.ref for r in after]])
    if resumed_refs:
        resumed = _known(True, [boundary.ref, *resumed_refs])
    elif terminal_known:
        resumed = _known(False, [boundary.ref, *episode["outcome"]["status_evidence_refs"]])
    else:
        resumed = _unknown("no_later_bout_observed_before_unknown_outcome", [boundary.ref, *[r.ref for r in after]])
    return {"continued_work_after_help": continued, "resumed_work_after_help": resumed}


def _question_outcome(episode):
    status = episode["outcome"]["status"]
    refs = episode["outcome"]["status_evidence_refs"]
    if status in {"unknown", "ambiguous"}:
        return _unknown("question_outcome_" + status, refs)
    return _known(status, refs)


def calculate_metrics(session_report, config=None):
    """Calculate metrics without scoring, ranking, or imputing absent outcomes."""
    config = config or MetricsConfig()
    index = {item["ref"]: NormalizedEvent.model_validate(item)
             for item in session_report["normalization"]["records"]}
    results = []
    for episode in session_report["episodes"]:
        records = [index[ref] for ref in episode["event_refs"]]
        total_active = _active_time(records, episode, config)
        before, after, ambiguous = _partition_for_first_help(records, episode, index)
        if before is None:
            pre_active = _unknown("first_completed_response_not_known")
            post_active = _unknown("first_completed_response_not_known")
        elif ambiguous:
            pre_active = _unknown("activity_position_relative_to_help_ambiguous", ambiguous)
            post_active = _unknown("activity_position_relative_to_help_ambiguous", ambiguous)
        else:
            pre_active = _active_time(records, episode, config, before)
            post_active = _active_time(records, episode, config, after)

        tutor_requests = [r.ref for r in records if isinstance(r.event.detail, StudentMessage)
                          and r.event.detail.request_id]
        fail_counts = _partitioned_count(
            records, episode, index,
            lambda r: isinstance(r.event.detail, CheckResult) and r.event.detail.outcome == "fail",
        )
        edit_counts = _partitioned_count(
            records, episode, index, lambda r: isinstance(r.event.detail, CodeEdit),
        )
        execution_counts = _partitioned_count(
            records, episode, index, lambda r: isinstance(r.event.detail, Execution),
        )
        continuation = _continuation(records, episode, index)
        completed = _completed_response_count(records, episode)

        post_help_ready = (episode["help"]["first_boundary_status"] == "known"
                           and post_active["status"] == "known")
        total_ready = total_active["status"] == "known"
        results.append({
            "episode_id": episode["episode_id"],
            "scope": episode["scope"],
            "eligibility": {
                "random_selection": {"eligible": True, "reasons": []},
                "total_active_time": {"eligible": total_ready,
                                      "reasons": [] if total_ready else [total_active["reason"]]},
                "post_help_behavior": {"eligible": post_help_ready,
                                       "reasons": [] if post_help_ready else [
                                           post_active.get("reason", "completed_help_boundary_unavailable")
                                       ]},
                "common_comparison_population": {
                    "eligible": total_ready and post_help_ready,
                    "reasons": [] if total_ready and post_help_ready else
                    ["requires_known_total_and_post_help_metrics"],
                },
            },
            "time": {
                "observed_elapsed_span": _elapsed_span(records),
                "total_observed_active_time": total_active,
                "active_time_before_first_help": pre_active,
                "active_time_after_first_help": post_active,
                "response_to_next_action_elapsed_time": _response_action_latencies(
                    records, episode, index
                ),
                "active_time_between_completed_responses": _between_help_active_time(
                    records, episode, index, config
                ),
            },
            "activity": {
                "tutor_request_count": _known(len(tutor_requests), tutor_requests, unit="events"),
                "completed_tutor_response_count": completed,
                "failed_check_count": fail_counts,
                "repeated_failure_count": _repeated_failures(records),
                "code_edit_count": edit_counts,
                "execution_count": execution_counts,
            },
            "per_completed_response": _per_response_windows(
                records, episode, index, config
            ),
            "recovery": {
                "eventually_passed_question_check": _eventual_question_pass(records),
                "failed_checks_between_help_and_recovery": _failed_checks_to_recovery(
                    records, episode, index
                ),
                **continuation,
                "question_outcome": _question_outcome(episode),
                "intermediate_pass_refs": [
                    r.ref for r in records if isinstance(r.event.detail, CheckResult)
                    and r.event.detail.scope == "subcheck" and r.event.detail.outcome == "pass"
                ],
            },
        })
    return {
        "version": 1,
        "method": "behavioral-metrics-v1",
        "dataset_id": session_report["dataset_id"],
        "origin": session_report["origin"],
        "source_session_method": session_report["method"],
        "config": {"active_interval_seconds": config.active_interval_seconds},
        "episodes": results,
        "limitations": [
            "Observed active time is a conservative event-interval estimate, not continuous attention.",
            "Elapsed spans include inactivity and must not be interpreted as productive work.",
            "A passing subcheck is not question completion.",
            "A question-scope pass is observed recovery evidence, not evidence of tutor causation.",
            "Absent events and outcomes remain unknown rather than being imputed as failures.",
        ],
    }
