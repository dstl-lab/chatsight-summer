"""Deterministic fusion of Phase 3B metrics and validated LLM findings."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json

from .findings.contract import ReviewBundle


@dataclass(frozen=True)
class FusionConfig:
    """Uncalibrated review rules that must be validated against instructor labels."""

    strong_composite_score: float = 50.0
    strong_single_tail_score: float = 90.0
    strong_contribution_count: int = 2

    def __post_init__(self):
        for name in ("strong_composite_score", "strong_single_tail_score"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not 0 < value <= 100:
                raise ValueError(f"{name} must be greater than 0 and at most 100")
        if type(self.strong_contribution_count) is not int or self.strong_contribution_count < 1:
            raise ValueError("strong_contribution_count must be a positive integer")


def _unique(values):
    return list(dict.fromkeys(value for value in values if value is not None))


def _metric_signal(entry, excluded, config):
    if entry is None:
        limitations = []
        if excluded:
            limitations.extend(excluded.get("reasons", []))
            limitations.extend(
                f"{item.get('metric')}: {item.get('reason')}"
                for item in excluded.get("missing_metrics", [])
            )
        if not limitations:
            limitations.append("no_matching_metric_episode")
        return {
            "status": "insufficient_data",
            "episode_id": excluded.get("episode_id") if excluded else None,
            "score": None,
            "above_threshold_metrics": [],
            "reasons": ["Metric ranking was unavailable for this review session."],
            "evidence_refs": [],
            "source_event_ids": [],
            "data_limitations": _unique(limitations),
        }
    if entry.get("score_status") != "known" or type(entry.get("score")) not in {int, float}:
        return {
            "status": "insufficient_data",
            "episode_id": entry.get("episode_id"),
            "score": None,
            "above_threshold_metrics": [],
            "reasons": ["Metric score was not a known numeric value."],
            "evidence_refs": entry.get("evidence_refs", []),
            "source_event_ids": entry.get("source_event_ids", []),
            "data_limitations": _unique([
                *entry.get("data_limitations", []),
                "metric_score_not_known",
            ]),
        }

    above = [
        contribution for contribution in entry.get("metric_contributions", [])
        if contribution.get("status") == "above_reference_threshold"
    ]
    score = float(entry["score"])
    extreme_single = any(
        float(item.get("tail_score", 0)) >= config.strong_single_tail_score
        for item in above
    )
    if not above:
        status = "no_outlier"
    elif (
        score >= config.strong_composite_score
        or len(above) >= config.strong_contribution_count
        or extreme_single
    ):
        status = "strong_outlier"
    else:
        status = "moderate_outlier"
    return {
        "status": status,
        "episode_id": entry.get("episode_id"),
        "score": score,
        "above_threshold_metrics": [item["metric"] for item in above],
        "reasons": entry.get("priority_reasons", []),
        "evidence_refs": _unique(
            ref for item in above for ref in item.get("evidence_refs", [])
        ),
        "source_event_ids": _unique(
            event_id for item in above for event_id in item.get("source_event_ids", [])
        ),
        "data_limitations": entry.get("data_limitations", []),
    }


def _llm_signal(session):
    analysis = session["analysis"]
    evidence_refs = _unique(
        ref
        for finding in analysis.get("findings", [])
        for ref in [*finding.get("highlight_ids", []), *finding.get("recovery_evidence_ids", [])]
    )
    timeline = {event["id"]: event for event in session["timeline"]}
    source_event_ids = _unique(
        timeline[ref].get("source_event_id") for ref in evidence_refs if ref in timeline
    )
    if analysis["state"] == "completed" and analysis["decision"] == "surface":
        status = "supported_finding"
    elif analysis["state"] == "completed" and analysis["decision"] == "no_supported_finding":
        status = "no_supported_finding"
    elif analysis["state"] == "not_analyzed":
        status = "not_analyzed"
    else:
        status = "insufficient_evidence"
    return {
        "status": status,
        "model": analysis.get("model"),
        "finding_categories": _unique(
            finding["category"] for finding in analysis.get("findings", [])
        ),
        "evidence_refs": evidence_refs,
        "source_event_ids": source_event_ids,
        "data_limitations": _unique([
            *analysis.get("validation_errors", []),
            *analysis.get("notices", []),
        ]),
    }


def combine_signals(metric_signal, llm_signal, config=None):
    """Apply preregistration-candidate rules without treating either signal as truth."""
    config = config or FusionConfig()
    shared_refs = sorted(set(metric_signal["evidence_refs"]) & set(llm_signal["evidence_refs"]))
    shared_source_ids = sorted(
        set(metric_signal["source_event_ids"]) & set(llm_signal["source_event_ids"])
    )
    corroborated = bool(shared_refs or shared_source_ids)
    metric_status = metric_signal["status"]
    llm_status = llm_signal["status"]

    if metric_status == "strong_outlier" and llm_status == "supported_finding" and corroborated:
        priority, rule = "high", "strong_metric_and_supported_llm_with_shared_evidence"
        summary = "Strong metric outlier and validated LLM finding cite overlapping evidence."
    elif metric_status == "strong_outlier" and llm_status == "supported_finding":
        priority, rule = "medium", "strong_metric_and_supported_llm_without_shared_evidence"
        summary = "Both methods produced a signal, but they did not cite overlapping evidence."
    elif metric_status == "strong_outlier":
        priority, rule = "medium", "strong_metric_signal_only"
        summary = "Strong metric outlier warrants review without corroborating LLM evidence."
    elif metric_status == "moderate_outlier" and llm_status == "supported_finding":
        priority, rule = "medium", "moderate_metric_and_supported_llm"
        summary = "A validated LLM finding accompanies a moderate metric outlier."
    elif llm_status == "supported_finding":
        priority, rule = "medium", "supported_llm_finding_only"
        summary = "Validated LLM finding warrants review without a corroborating strong metric signal."
    elif metric_status == "moderate_outlier":
        priority, rule = "low", "moderate_metric_signal_only"
        summary = "A metric exceeded its reference threshold, but corroboration is limited."
    elif metric_status == "no_outlier" and llm_status == "no_supported_finding":
        priority, rule = "none", "both_available_no_signal"
        summary = "Available metrics and validated LLM analysis produced no review signal."
    else:
        priority, rule = "insufficient_data", "one_or_more_signals_unavailable"
        summary = "The available evidence is insufficient to assign a review priority."

    return {
        "status": "insufficient_data" if priority == "insufficient_data" else "scored",
        "priority": priority,
        "rule": rule,
        "summary": summary,
        "metric_signal": metric_signal,
        "llm_signal": llm_signal,
        "shared_evidence_refs": shared_refs,
        "shared_source_event_ids": shared_source_ids,
        "config": {
            "strong_composite_score": config.strong_composite_score,
            "strong_single_tail_score": config.strong_single_tail_score,
            "strong_contribution_count": config.strong_contribution_count,
        },
        "interpretation": (
            "Priority for instructor review only. Agreement does not establish tutor failure, "
            "causation, or model correctness."
        ),
    }


def _ranking_indexes(report):
    if report.get("method") != "question-level-review-ranking-v1":
        raise ValueError("Expected a Phase 3B question-level ranking report.")
    post_help = report.get("rankings", {}).get("post_help", {}).get("entries", [])
    total_time = report.get("rankings", {}).get("total_time", {}).get("entries", [])
    excluded = report.get("eligible_population", {}).get("excluded", [])
    def unique_index(items, label):
        result = {}
        for item in items:
            identity = item.get("episode_id")
            if not isinstance(identity, str) or not identity:
                raise ValueError(f"{label} contains an invalid episode ID.")
            if identity in result:
                raise ValueError(f"{label} contains duplicate episode ID {identity}.")
            result[identity] = item
        return result
    return (
        unique_index(post_help, "Post-help ranking"),
        unique_index(total_time, "Total-time ranking"),
        unique_index(excluded, "Excluded-session list"),
    )


def _timeline_refs(session, source_event_ids, evidence_refs=()):
    direct = set(evidence_refs)
    source_ids = set(source_event_ids)
    return _unique(
        event["id"] for event in session["timeline"]
        if event["id"] in direct or event.get("source_event_id") in source_ids
    )


def _known_metric(contribution, session):
    refs = _timeline_refs(
        session,
        contribution.get("source_event_ids", []),
        contribution.get("evidence_refs", []),
    )
    if contribution.get("value", 0) != 0 and not refs:
        raise ValueError(
            f"Metric evidence for {contribution['metric']} is not present in the review timeline."
        )
    return {"status": "known", "value": contribution["value"], "reason": None,
            "evidence_refs": refs}


def _merge_metric_display(session, post_entry, total_entry):
    if post_entry is None:
        return
    by_metric = {item["metric"]: item for item in post_entry.get("metric_contributions", [])}
    field_map = {
        "post_help_active_time": "post_help_active_time",
        "failed_checks_after_help": "failed_checks_after_help",
        "repeated_failed_checks_after_help": "repeated_failures",
        "tutor_requests": "tutor_requests",
    }
    for metric_name, field in field_map.items():
        if metric_name in by_metric:
            session[field] = _known_metric(by_metric[metric_name], session)
    if total_entry and total_entry.get("metric_contributions"):
        contribution = total_entry["metric_contributions"][0]
        session["active_time"] = _known_metric(contribution, session)
        statistics = contribution.get("reference", {}).get("statistics", {})
        if statistics.get("status") == "ready":
            session["reference_active_time"] = {
                "status": "calculated",
                "lower_seconds": statistics.get("p25"),
                "upper_seconds": statistics.get("p75"),
                "basis": "Leave-one-out same-question interquartile range.",
            }


def fuse_review_bundle(bundle_document, ranking_report, *, session_episode_map=None, config=None):
    """Join explicitly matched metric episodes to findings and return contract version 3."""
    config = config or FusionConfig()
    source = ReviewBundle.model_validate(bundle_document).model_dump(mode="json")
    post_index, total_index, excluded_index = _ranking_indexes(ranking_report)
    mapping = session_episode_map or {session["id"]: session["id"] for session in source["sessions"]}
    if any(not isinstance(key, str) or not isinstance(value, str) or not key or not value
           for key, value in mapping.items()):
        raise ValueError("Session mapping keys and values must be non-empty strings.")
    unknown_sessions = set(mapping) - {session["id"] for session in source["sessions"]}
    if unknown_sessions:
        raise ValueError("Mapping contains unknown review session IDs: " + ", ".join(sorted(unknown_sessions)))
    mapped_episode_ids = list(mapping.values())
    if len(mapped_episode_ids) != len(set(mapped_episode_ids)):
        raise ValueError("Each metric episode may map to at most one review session.")

    result = deepcopy(source)
    for session in result["sessions"]:
        episode_id = mapping.get(session["id"])
        entry = post_index.get(episode_id)
        excluded = excluded_index.get(episode_id)
        metric = _metric_signal(entry, excluded, config)
        llm = _llm_signal(session)
        fusion = combine_signals(metric, llm, config)
        session["fusion"] = fusion
        session["priority"] = fusion["priority"]
        session["priority_basis"] = fusion["summary"]
        session["flagged"] = fusion["priority"] in {"high", "medium", "low"}
        session["scenario"] = fusion["summary"]
        _merge_metric_display(session, entry, total_index.get(episode_id))

        metric_reasons = []
        if entry:
            for contribution in entry.get("metric_contributions", []):
                if contribution.get("status") != "above_reference_threshold":
                    continue
                refs = _timeline_refs(
                    session,
                    contribution.get("source_event_ids", []),
                    contribution.get("evidence_refs", []),
                )
                if not refs:
                    raise ValueError(
                        f"Outlier evidence for {contribution['metric']} is absent from the review timeline."
                    )
                metric_reasons.append({
                    "id": "metric-" + contribution["metric"],
                    "title": contribution["label"],
                    "description": contribution["reason"],
                    "supporting_refs": refs,
                    "supporting_event_ids": _unique(
                        event_id for ref in refs
                        for event_id in [next(
                            event.get("source_event_id") for event in session["timeline"]
                            if event["id"] == ref
                        )]
                    ),
                })
        session["reasons"] = [*metric_reasons, *session["reasons"]]

    order = {"high": 0, "medium": 1, "low": 2, "none": 3, "insufficient_data": 4}
    result["sessions"].sort(key=lambda item: (
        order[item["priority"]],
        -(item["fusion"]["metric_signal"]["score"] or 0),
        item["id"],
    ))
    for rank, session in enumerate(result["sessions"], 1):
        session["review_rank"] = rank
    counts = {name: sum(session["priority"] == name for session in result["sessions"])
              for name in order}
    result["summary"] = {
        "total_sessions": len(result["sessions"]),
        "flagged_sessions": sum(session["flagged"] for session in result["sessions"]),
        "high_priority_sessions": counts["high"],
        "medium_priority_sessions": counts["medium"],
        "low_priority_sessions": counts["low"],
        "no_priority_sessions": counts["none"],
        "insufficient_data_sessions": counts["insufficient_data"],
    }
    result["contract_version"] = 3
    result["dataset"]["priority_method"] = "Deterministic metric and validated LLM fusion v1"
    result["dataset"]["analysis_version"] += "+combined-priority-v1"
    identity = json.dumps({
        "source_dataset": source["dataset"]["id"],
        "ranking_dataset": ranking_report.get("dataset_id"),
        "ranking_sha256": sha256(json.dumps(
            ranking_report, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
        "mapping": mapping,
        "config": {
            "strong_composite_score": config.strong_composite_score,
            "strong_single_tail_score": config.strong_single_tail_score,
            "strong_contribution_count": config.strong_contribution_count,
        },
    }, sort_keys=True, separators=(",", ":"))
    result["dataset"]["id"] = "combined-" + sha256(identity.encode()).hexdigest()[:24]
    return ReviewBundle.model_validate(result).model_dump(mode="json")
