"""Robust, question-specific descriptive baselines for Phase 3B."""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from statistics import median


QUESTION_SCOPE_FIELDS = (
    "course_id",
    "cohort_id",
    "assignment_id",
    "assignment_version",
    "question_id",
)

METRIC_SPECS = {
    "total_observed_active_time": {
        "label": "Total observed active time",
        "path": ("time", "total_observed_active_time"),
        "unit": "seconds",
    },
    "post_help_active_time": {
        "label": "Post-help observed active time",
        "path": ("time", "active_time_after_first_help"),
        "unit": "seconds",
    },
    "failed_checks_after_help": {
        "label": "Failed checks after tutor help",
        "path": ("activity", "failed_check_count", "after_first_help"),
        "unit": "events",
    },
    "tutor_requests": {
        "label": "Tutor requests in the observed session",
        "path": ("activity", "tutor_request_count"),
        "unit": "events",
    },
    "repeated_failed_checks_after_help": {
        "label": "Repeated failed checks after tutor help",
        "path": (),
        "unit": "events",
        "derived": "post_help_logical_check_groups",
    },
}


@dataclass(frozen=True)
class BaselineConfig:
    """Minimum number of other sessions required to score one session."""

    minimum_reference_sessions: int = 8

    def __post_init__(self):
        if type(self.minimum_reference_sessions) is not int or self.minimum_reference_sessions < 4:
            raise ValueError("minimum_reference_sessions must be an integer of at least 4")


def question_scope(episode):
    scope = episode.get("scope", {})
    return {field: scope.get(field) for field in QUESTION_SCOPE_FIELDS}


def question_key(episode):
    scope = question_scope(episode)
    return tuple(scope[field] for field in QUESTION_SCOPE_FIELDS)


def question_key_string(key):
    return "|".join(value if value is not None else "unknown" for value in key)


def metric_value(episode, metric_name):
    """Return a Phase 3A metric, preserving missing paths as explicit unknowns."""
    spec = METRIC_SPECS[metric_name]
    if spec.get("derived") == "post_help_logical_check_groups":
        return _post_help_repeated_failures(episode)
    value = episode
    for part in spec["path"]:
        if not isinstance(value, dict) or part not in value:
            return {
                "status": "unknown",
                "value": None,
                "reason": "metric_path_missing",
                "evidence_refs": [],
            }
        value = value[part]
    if not isinstance(value, dict):
        return {
            "status": "unknown",
            "value": None,
            "reason": "metric_shape_invalid",
            "evidence_refs": [],
        }
    return value


def _post_help_repeated_failures(episode):
    """Derive repeats after help without changing the Phase 3A metric contract."""
    activity = episode.get("activity", {})
    post_help = activity.get("failed_check_count", {}).get("after_first_help", {})
    repeated = activity.get("repeated_failure_count", {})
    if post_help.get("status") != "known":
        return {
            "status": "unknown",
            "value": None,
            "reason": post_help.get("reason", "post_help_failure_count_unknown"),
            "evidence_refs": post_help.get("evidence_refs", []),
        }
    post_help_ref_list = list(dict.fromkeys(post_help.get("evidence_refs", [])))
    post_help_refs = set(post_help_ref_list)
    post_help_value = post_help.get("value")
    if type(post_help_value) is not int or post_help_value < 0 or len(post_help_refs) != post_help_value:
        return {
            "status": "unknown",
            "value": None,
            "reason": "post_help_failure_count_evidence_mismatch",
            "evidence_refs": post_help_ref_list,
        }
    if post_help_value == 0:
        return {"status": "known", "value": 0, "evidence_refs": []}
    if repeated.get("status") != "known":
        return {
            "status": "unknown",
            "value": None,
            "reason": repeated.get("reason", "logical_check_groups_unknown"),
            "evidence_refs": post_help_ref_list,
        }
    groups = repeated.get("details", {}).get("logical_check_groups")
    if not isinstance(groups, dict):
        return {
            "status": "unknown",
            "value": None,
            "reason": "post_help_repeat_group_evidence_missing",
            "evidence_refs": post_help_ref_list,
        }
    repeated_count = 0
    grouped_refs = []
    covered = set()
    for refs in groups.values():
        if not isinstance(refs, list):
            return {
                "status": "unknown",
                "value": None,
                "reason": "post_help_repeat_group_evidence_invalid",
                "evidence_refs": post_help_ref_list,
            }
        matching = [ref for ref in refs if ref in post_help_refs]
        if covered.intersection(matching):
            return {
                "status": "unknown",
                "value": None,
                "reason": "post_help_repeat_group_evidence_overlaps",
                "evidence_refs": post_help_ref_list,
            }
        covered.update(matching)
        grouped_refs.extend(matching)
        repeated_count += max(0, len(matching) - 1)
    if covered != post_help_refs:
        return {
            "status": "unknown",
            "value": None,
            "reason": "post_help_failures_not_fully_grouped",
            "evidence_refs": post_help_ref_list,
        }
    return {
        "status": "known",
        "value": repeated_count,
        "evidence_refs": list(dict.fromkeys(grouped_refs)),
        "details": {"derivation": "logical check groups intersected with post-help failures"},
    }


def known_nonnegative_number(metric):
    value = metric.get("value")
    return (
        metric.get("status") == "known"
        and type(value) in {int, float}
        and isfinite(value)
        and value >= 0
    )


def _percentile(sorted_values, probability):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


def describe_values(values, config):
    """Describe values without imputing unknown observations."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {
            "status": "insufficient_data",
            "known_count": 0,
            "minimum_required": config.minimum_reference_sessions,
            "reason": "no_known_reference_values",
        }

    center = float(median(ordered))
    q1 = _percentile(ordered, 0.25)
    q3 = _percentile(ordered, 0.75)
    iqr = q3 - q1
    mad = float(median(abs(value - center) for value in ordered))
    if iqr > 0:
        scale = iqr
        scale_basis = "interquartile_range"
    elif mad > 0:
        scale = mad * 1.4826
        scale_basis = "scaled_median_absolute_deviation"
    else:
        scale = max(abs(center) * 0.1, 1.0)
        scale_basis = "constant_value_fallback"

    ready = len(ordered) >= config.minimum_reference_sessions
    result = {
        "status": "ready" if ready else "insufficient_data",
        "known_count": len(ordered),
        "minimum_required": config.minimum_reference_sessions,
        "minimum": ordered[0],
        "p25": q1,
        "median": center,
        "p75": q3,
        "p90": _percentile(ordered, 0.9),
        "maximum": ordered[-1],
        "iqr": iqr,
        "mad": mad,
        "robust_scale": scale,
        "scale_basis": scale_basis,
        "upper_reference_threshold": q3 + 1.5 * scale,
        "threshold_rule": "p75 + 1.5 * robust_scale",
    }
    if not ready:
        result["reason"] = "fewer_than_minimum_reference_sessions"
    return result


def calculate_question_baselines(metrics_report, config=None, episode_ids=None):
    """Calculate descriptive baselines for exact question scopes.

    These summaries may include every selected session and are descriptive only.
    Ranking uses ``leave_one_out_reference`` so the evaluated session never sets
    its own threshold.
    """
    config = config or BaselineConfig()
    selected = set(episode_ids) if episode_ids is not None else None
    groups = defaultdict(list)
    for episode in metrics_report.get("episodes", []):
        if selected is None or episode.get("episode_id") in selected:
            groups[question_key(episode)].append(episode)

    questions = []
    for key, episodes in sorted(groups.items(), key=lambda item: question_key_string(item[0])):
        metrics = {}
        for metric_name, spec in METRIC_SPECS.items():
            known = []
            unknown = []
            for episode in episodes:
                metric = metric_value(episode, metric_name)
                if known_nonnegative_number(metric):
                    known.append(metric["value"])
                else:
                    unknown.append({
                        "episode_id": episode.get("episode_id"),
                        "reason": metric.get("reason", "metric_unknown"),
                    })
            metrics[metric_name] = {
                "label": spec["label"],
                "unit": spec["unit"],
                "summary": describe_values(known, config),
                "missing_count": len(unknown),
                "unknown_sessions": unknown,
            }
        outcomes = defaultdict(int)
        for episode in episodes:
            outcome = episode.get("recovery", {}).get("question_outcome", {})
            name = str(outcome.get("value")) if outcome.get("status") == "known" else "unknown"
            outcomes[name] += 1
        questions.append({
            "question_key": question_key_string(key),
            "scope": question_scope(episodes[0]),
            "session_count": len(episodes),
            "episode_ids": [episode.get("episode_id") for episode in episodes],
            "outcome_counts": dict(sorted(outcomes.items())),
            "metrics": metrics,
            "usage": "descriptive_only; ranking thresholds are leave-one-out",
        })

    return {
        "version": 1,
        "method": "question-level-robust-baselines-v1",
        "dataset_id": metrics_report.get("dataset_id"),
        "origin": metrics_report.get("origin"),
        "config": {"minimum_reference_sessions": config.minimum_reference_sessions},
        "questions": questions,
        "limitations": [
            "Baselines apply only within an exact course, cohort, assignment version, and question scope.",
            "Unknown values are excluded and reported; they are never imputed as zero.",
            "Unfinished outcomes remain descriptive categories and are not treated as failures.",
            "Question summaries are descriptive; scored thresholds must exclude the evaluated session.",
            "Small cohorts remain insufficient rather than producing unstable anomaly scores.",
        ],
    }


def leave_one_out_reference(episodes, evaluated_episode_id, metric_name, config=None):
    """Build a scoring reference from same-question peers, excluding the target."""
    config = config or BaselineConfig()
    evaluated = next(
        (episode for episode in episodes if episode.get("episode_id") == evaluated_episode_id),
        None,
    )
    if evaluated is None:
        raise KeyError(f"Unknown episode: {evaluated_episode_id}")
    key = question_key(evaluated)
    peers = [
        episode for episode in episodes
        if episode.get("episode_id") != evaluated_episode_id and question_key(episode) == key
    ]
    known = []
    unknown = []
    for peer in peers:
        metric = metric_value(peer, metric_name)
        if known_nonnegative_number(metric):
            known.append(float(metric["value"]))
        else:
            unknown.append({
                "episode_id": peer.get("episode_id"),
                "reason": metric.get("reason", "metric_unknown"),
            })
    return {
        "question_key": question_key_string(key),
        "scope": question_scope(evaluated),
        "evaluated_episode_id": evaluated_episode_id,
        "evaluated_episode_excluded": True,
        "reference_episode_ids": [
            peer.get("episode_id") for peer in peers
            if peer.get("episode_id") not in {item["episode_id"] for item in unknown}
        ],
        "unknown_reference_sessions": unknown,
        "statistics": describe_values(known, config),
    }
