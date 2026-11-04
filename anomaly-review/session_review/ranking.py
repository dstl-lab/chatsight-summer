"""Explainable, question-specific review rankings for Phase 3B."""
from dataclasses import dataclass
from hashlib import sha256
from math import exp

from .baselines import (
    BaselineConfig,
    METRIC_SPECS,
    calculate_question_baselines,
    known_nonnegative_number,
    leave_one_out_reference,
    metric_value,
    question_key,
    question_key_string,
    question_scope,
)


TOTAL_TIME_METRICS = ("total_observed_active_time",)
POST_HELP_WEIGHTS = {
    "post_help_active_time": 0.35,
    "failed_checks_after_help": 0.30,
    "repeated_failed_checks_after_help": 0.20,
    "tutor_requests": 0.15,
}
COMMON_REQUIRED_METRICS = tuple(dict.fromkeys((*TOTAL_TIME_METRICS, *POST_HELP_WEIGHTS)))


@dataclass(frozen=True)
class RankingConfig:
    minimum_reference_sessions: int = 8
    random_seed: int = 0

    def __post_init__(self):
        BaselineConfig(self.minimum_reference_sessions)
        if type(self.random_seed) is not int:
            raise ValueError("random_seed must be an integer")


def evidence_index_from_session_report(session_report):
    """Resolve canonical metric references to source event IDs and JSON pointers."""
    index = {}
    normalization = session_report.get("normalization", {})
    for record in normalization.get("records", []):
        index[record["ref"]] = {
            "source_event_id": record.get("event", {}).get("event_id"),
            "source_pointers": [source.get("record_pointer") for source in record.get("sources", [])],
        }
    return index


def _unique(values):
    return list(dict.fromkeys(value for value in values if value is not None))


def _resolve_evidence(refs, evidence_index):
    resolved = [evidence_index[ref] for ref in refs if ref in evidence_index]
    return {
        "evidence_refs": _unique(refs),
        "source_event_ids": _unique(item.get("source_event_id") for item in resolved),
        "source_pointers": _unique(
            pointer for item in resolved for pointer in item.get("source_pointers", [])
        ),
        "unresolved_evidence_refs": [ref for ref in refs if ref not in evidence_index],
    }


def _base_eligibility(episode):
    reasons = []
    scope = question_scope(episode)
    if any(value is None for value in scope.values()):
        reasons.append("question_scope_incomplete")
    phase3a = episode.get("eligibility", {}).get("common_comparison_population", {})
    if not phase3a.get("eligible", False):
        reasons.extend(phase3a.get("reasons", ["phase3a_common_population_ineligible"]))
    missing = []
    for metric_name in COMMON_REQUIRED_METRICS:
        metric = metric_value(episode, metric_name)
        if not known_nonnegative_number(metric):
            missing.append({
                "metric": metric_name,
                "reason": metric.get("reason", "metric_not_known_nonnegative_number"),
                "evidence_refs": metric.get("evidence_refs", []),
            })
    if missing:
        reasons.append("one_or_more_required_metrics_unknown")
    return reasons, missing


def _comparison_population(metrics_report, config):
    episodes = metrics_report.get("episodes", [])
    base_candidates = []
    excluded = []
    for episode in episodes:
        reasons, missing = _base_eligibility(episode)
        if reasons:
            excluded.append({
                "episode_id": episode.get("episode_id"),
                "scope": question_scope(episode),
                "reasons": _unique(reasons),
                "missing_metrics": missing,
            })
        else:
            base_candidates.append(episode)

    group_sizes = {}
    for episode in base_candidates:
        key = question_key(episode)
        group_sizes[key] = group_sizes.get(key, 0) + 1

    eligible = []
    for episode in base_candidates:
        peers = group_sizes[question_key(episode)] - 1
        if peers >= config.minimum_reference_sessions:
            eligible.append(episode)
        else:
            excluded.append({
                "episode_id": episode.get("episode_id"),
                "scope": question_scope(episode),
                "reasons": ["insufficient_same_question_reference_sessions"],
                "missing_metrics": [],
                "available_reference_sessions": peers,
                "minimum_reference_sessions": config.minimum_reference_sessions,
            })
    return eligible, sorted(excluded, key=lambda item: item["episode_id"] or "")


def _tail_contribution(eligible_episodes, episode, metric_name, weight, config, evidence_index):
    metric = metric_value(episode, metric_name)
    reference = leave_one_out_reference(
        eligible_episodes,
        episode["episode_id"],
        metric_name,
        BaselineConfig(config.minimum_reference_sessions),
    )
    statistics = reference["statistics"]
    value = float(metric["value"])
    threshold = statistics["upper_reference_threshold"]
    scale = statistics["robust_scale"]
    excess = max(0.0, value - threshold)
    tail_score = 0.0 if excess == 0 else 100.0 * (1.0 - exp(-excess / scale))
    peer_values = sorted(
        float(metric_value(peer, metric_name)["value"])
        for peer in eligible_episodes
        if peer["episode_id"] in reference["reference_episode_ids"]
    )
    percentile = 100.0 * sum(peer <= value for peer in peer_values) / len(peer_values)
    state = "above_reference_threshold" if excess > 0 else "within_reference_threshold"
    label = METRIC_SPECS[metric_name]["label"]
    reason = (
        f"{label} was {value:g}, above the leave-one-out upper reference "
        f"threshold of {threshold:.2f}."
        if excess > 0 else
        f"{label} was {value:g}, within the leave-one-out upper reference "
        f"threshold of {threshold:.2f}."
    )
    return {
        "metric": metric_name,
        "label": label,
        "status": state,
        "value": value,
        "unit": METRIC_SPECS[metric_name]["unit"],
        "weight": weight,
        "tail_score": round(tail_score, 6),
        "weighted_points": round(tail_score * weight, 6),
        "empirical_peer_percentile": round(percentile, 6),
        "reason": reason,
        "reference": reference,
        **_resolve_evidence(metric.get("evidence_refs", []), evidence_index),
    }


def _entry(eligible_episodes, episode, metric_weights, config, evidence_index):
    contributions = [
        _tail_contribution(
            eligible_episodes, episode, metric_name, weight, config, evidence_index
        )
        for metric_name, weight in metric_weights.items()
    ]
    score = sum(item["weighted_points"] for item in contributions)
    above = sorted(
        (item for item in contributions if item["status"] == "above_reference_threshold"),
        key=lambda item: (-item["weighted_points"], item["metric"]),
    )
    reasons = [item["reason"] for item in above]
    if not reasons:
        reasons = ["No included metric exceeded its leave-one-out upper reference threshold."]
    outcome = episode.get("recovery", {}).get("question_outcome", {})
    data_limitations = []
    if outcome.get("status") != "known":
        data_limitations.append(
            "Question outcome was not observed; the score describes only the observed session prefix."
        )
    elif outcome.get("value") in {"unfinished", "reopened", "activity_after_completion"}:
        data_limitations.append(
            "Question completion was not final; the score describes observed behavior, not final outcome."
        )
    return {
        "episode_id": episode["episode_id"],
        "scope": episode["scope"],
        "score_status": "known",
        "score": round(score, 6),
        "priority_reasons": reasons,
        "metric_contributions": contributions,
        "evidence_refs": _unique(
            ref for item in contributions for ref in item["evidence_refs"]
        ),
        "source_event_ids": _unique(
            event_id for item in contributions for event_id in item["source_event_ids"]
        ),
        "source_pointers": _unique(
            pointer for item in contributions for pointer in item["source_pointers"]
        ),
        "unresolved_evidence_refs": _unique(
            ref for item in contributions for ref in item["unresolved_evidence_refs"]
        ),
        "data_limitations": data_limitations,
        "interpretation": "Review priority only; this score does not establish tutor failure or causation.",
    }


def _rank(entries):
    ordered = sorted(entries, key=lambda item: (-item["score"], item["episode_id"]))
    for position, item in enumerate(ordered, 1):
        item["rank"] = position
    return ordered


def _random_ranking(episodes, dataset_id, seed):
    entries = []
    for episode in episodes:
        key = sha256(
            f"{dataset_id}|{seed}|{episode['episode_id']}".encode("utf-8")
        ).hexdigest()
        entries.append({
            "episode_id": episode["episode_id"],
            "scope": episode["scope"],
            "selection_key": key,
            "score_status": "not_applicable",
            "score": None,
            "priority_reasons": ["Deterministic random comparator; no behavioral evidence was scored."],
            "metric_contributions": [],
            "evidence_refs": [],
            "source_event_ids": [],
            "source_pointers": [],
            "unresolved_evidence_refs": [],
            "data_limitations": [],
            "interpretation": "Random evaluation comparator, not an anomaly judgment.",
        })
    entries.sort(key=lambda item: (item["selection_key"], item["episode_id"]))
    for position, item in enumerate(entries, 1):
        item["rank"] = position
    return entries


def rank_sessions(metrics_report, evidence_index=None, config=None):
    """Rank one common eligible population with three evaluation methods."""
    config = config or RankingConfig()
    evidence_index = evidence_index or {}
    eligible, excluded = _comparison_population(metrics_report, config)
    total = _rank([
        _entry(
            eligible,
            episode,
            {"total_observed_active_time": 1.0},
            config,
            evidence_index,
        )
        for episode in eligible
    ])
    post_help = _rank([
        _entry(eligible, episode, POST_HELP_WEIGHTS, config, evidence_index)
        for episode in eligible
    ])
    baselines = calculate_question_baselines(
        metrics_report,
        BaselineConfig(config.minimum_reference_sessions),
        episode_ids=[episode["episode_id"] for episode in eligible],
    )
    return {
        "version": 1,
        "method": "question-level-review-ranking-v1",
        "dataset_id": metrics_report.get("dataset_id"),
        "origin": metrics_report.get("origin"),
        "source_metrics_method": metrics_report.get("method"),
        "config": {
            "minimum_reference_sessions": config.minimum_reference_sessions,
            "random_seed": config.random_seed,
            "post_help_weights": POST_HELP_WEIGHTS,
            "tail_score_rule": "100 * (1 - exp(-max(0, value-threshold) / robust_scale))",
        },
        "eligible_population": {
            "definition": "Known required metrics plus sufficient same-question leave-one-out peers.",
            "episode_ids": [episode["episode_id"] for episode in eligible],
            "count": len(eligible),
            "excluded": excluded,
            "same_population_for_all_methods": True,
        },
        "question_baselines": baselines,
        "rankings": {
            "random": {
                "method": "deterministic-random-comparator-v1",
                "entries": _random_ranking(
                    eligible, metrics_report.get("dataset_id"), config.random_seed
                ),
            },
            "total_time": {
                "method": "leave-one-out-total-active-time-v1",
                "entries": total,
            },
            "post_help": {
                "method": "leave-one-out-post-help-composite-v1",
                "entries": post_help,
            },
        },
        "limitations": [
            "Scores prioritize sessions for review and do not identify tutor-caused harm.",
            "Every scoring reference excludes the evaluated session.",
            "Comparisons never cross exact question scopes.",
            "Unknown metrics and small question cohorts remain explicitly unscored.",
            "Repeated-failure counts depend on stable grader identifiers and versions.",
            "Weights and thresholds are preregistration candidates, not validated research findings.",
        ],
    }


def build_frontend_ranking_overlay(ranking_report, method):
    """Return a UI-ready overlay without modifying the current frontend contract."""
    if method not in {"random", "total_time", "post_help"}:
        raise ValueError("method must be random, total_time, or post_help")
    ranking = ranking_report["rankings"][method]
    return {
        "contract_version": 1,
        "contract": "anomaly-review.frontend-ranking-overlay.v1",
        "dataset_id": ranking_report["dataset_id"],
        "origin": ranking_report["origin"],
        "ranking_method": method,
        "ranking_method_version": ranking["method"],
        "sessions": [
            {
                "episode_id": entry["episode_id"],
                "rank": entry["rank"],
                "score_status": entry["score_status"],
                "score": entry["score"],
                "priority_reasons": entry["priority_reasons"],
                "metric_contributions": entry["metric_contributions"],
                "evidence_refs": entry["evidence_refs"],
                "source_event_ids": entry["source_event_ids"],
                "source_pointers": entry["source_pointers"],
                "data_limitations": entry["data_limitations"],
                "interpretation": entry["interpretation"],
            }
            for entry in ranking["entries"]
        ],
        "excluded_sessions": ranking_report["eligible_population"]["excluded"],
        "integration_note": "Join sessions to the existing UI by episode_id; do not replace timeline evidence.",
    }
