"""Clearly synthetic Phase 3B metric inputs for ranking demonstrations."""
import argparse
import json
from pathlib import Path

from .ranking import RankingConfig, rank_sessions


def _metric(value, ref, reason=None):
    if value is None:
        return {"status": "unknown", "value": None, "reason": reason, "evidence_refs": [ref]}
    return {"status": "known", "value": value, "evidence_refs": [ref]}


def _episode(identity, learner, question, total, post, failures, requests, repeated,
             outcome="completed", unknown_reason=None):
    prefix = f"syn-{identity}"
    known = unknown_reason is None
    failure_refs = [f"{prefix}-fail-{index + 1}" for index in range(failures or 0)]
    request_refs = [f"{prefix}-request-{index + 1}" for index in range(requests or 0)]
    if known and repeated > max(0, failures - 1):
        raise ValueError("Synthetic repeated failures cannot exceed failures minus one.")
    logical_groups = {}
    if failure_refs:
        repeated_group_size = repeated + 1
        logical_groups["synthetic-check-group-1"] = failure_refs[:repeated_group_size]
        for index, ref in enumerate(failure_refs[repeated_group_size:], 2):
            logical_groups[f"synthetic-check-group-{index}"] = [ref]
    failed_metric = (
        {"status": "known", "value": failures, "evidence_refs": failure_refs}
        if known else _metric(None, f"{prefix}-fail-unknown", unknown_reason)
    )
    repeated_metric = (
        {
            "status": "known",
            "value": repeated,
            "evidence_refs": failure_refs,
            "details": {"logical_check_groups": logical_groups},
        }
        if known else _metric(None, f"{prefix}-repeat-unknown", unknown_reason)
    )
    return {
        "episode_id": identity,
        "scope": {
            "learner_id": learner,
            "course_id": "synthetic-course",
            "cohort_id": "synthetic-cohort",
            "assignment_id": "synthetic-lab",
            "assignment_version": "v1",
            "notebook_id": f"notebook-{learner}",
            "question_id": question,
        },
        "eligibility": {
            "common_comparison_population": {
                "eligible": known,
                "reasons": [] if known else [unknown_reason],
            }
        },
        "time": {
            "total_observed_active_time": _metric(total, f"{prefix}-total", unknown_reason),
            "active_time_after_first_help": _metric(post, f"{prefix}-post", unknown_reason),
        },
        "activity": {
            "failed_check_count": {
                "after_first_help": failed_metric,
            },
            "tutor_request_count": (
                {"status": "known", "value": requests, "evidence_refs": request_refs}
                if known else _metric(None, f"{prefix}-request-unknown", unknown_reason)
            ),
            "repeated_failure_count": repeated_metric,
        },
        "recovery": {
            "question_outcome": (
                {"status": "known", "value": outcome, "evidence_refs": [f"{prefix}-outcome"]}
                if outcome != "unknown" else
                {"status": "unknown", "value": None, "reason": "outcome_not_observed",
                 "evidence_refs": [f"{prefix}-outcome"]}
            )
        },
    }


SYNTHETIC_ROWS = [
    ("q1-quick-recovery", "SYN-001", "Q1", 40, 12, 0, 1, 0, "completed", None),
    ("q1-normal-02", "SYN-002", "Q1", 42, 14, 0, 1, 0, "completed", None),
    ("q1-normal-03", "SYN-003", "Q1", 44, 16, 1, 1, 0, "completed", None),
    ("q1-normal-04", "SYN-004", "Q1", 46, 18, 0, 1, 0, "completed", None),
    ("q1-normal-05", "SYN-005", "Q1", 48, 20, 1, 1, 0, "unfinished", None),
    ("q1-normal-06", "SYN-006", "Q1", 50, 22, 0, 1, 0, "completed", None),
    ("q1-normal-07", "SYN-007", "Q1", 52, 24, 1, 1, 0, "completed", None),
    ("q1-normal-08", "SYN-008", "Q1", 54, 26, 0, 1, 0, "completed", None),
    ("q1-long-independent", "SYN-009", "Q1", 160, 20, 0, 1, 0, "completed", None),
    ("q1-post-help-struggle", "SYN-010", "Q1", 130, 110, 4, 3, 3, "unfinished", None),
    ("q1-multiple-help", "SYN-011", "Q1", 70, 38, 1, 3, 0, "completed", None),
    ("q1-ambiguous", "SYN-012", "Q1", None, None, None, None, None, "unknown",
     "activity_order_ambiguous"),
    ("q2-small-01", "SYN-101", "Q2", 35, 15, 0, 1, 0, "completed", None),
    ("q2-small-02", "SYN-102", "Q2", 50, 22, 1, 1, 0, "completed", None),
    ("q2-small-03", "SYN-103", "Q2", 90, 50, 2, 2, 1, "unfinished", None),
]


def build_synthetic_metrics_report():
    return {
        "version": 1,
        "method": "behavioral-metrics-v1",
        "dataset_id": "synthetic-phase3b-demonstration",
        "origin": "synthetic",
        "episodes": [_episode(*row) for row in SYNTHETIC_ROWS],
        "limitations": ["Invented metric values for software demonstration only."],
    }


def build_synthetic_evidence_index(metrics_report=None):
    metrics_report = metrics_report or build_synthetic_metrics_report()
    refs = set()

    def collect(value, key=""):
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect(child, child_key)
        elif isinstance(value, list):
            if key == "evidence_refs":
                refs.update(value)
            else:
                for child in value:
                    collect(child)

    collect(metrics_report)
    return {
        ref: {
            "source_event_id": ref.replace("syn-", "source-"),
            "source_pointers": [f"/synthetic/{position}"],
        }
        for position, ref in enumerate(sorted(refs))
    }


def build_synthetic_ranking_report(config=None):
    metrics = build_synthetic_metrics_report()
    return rank_sessions(
        metrics,
        build_synthetic_evidence_index(metrics),
        config or RankingConfig(),
    )


def comparison_summary(report=None):
    report = report or build_synthetic_ranking_report()
    return {
        "synthetic": True,
        "warning": "Illustrative software output, not research evidence.",
        "eligible_sessions": report["eligible_population"]["count"],
        "excluded_sessions": len(report["eligible_population"]["excluded"]),
        "total_time_top_three": [
            {"episode_id": item["episode_id"], "score": item["score"]}
            for item in report["rankings"]["total_time"]["entries"][:3]
        ],
        "post_help_top_three": [
            {"episode_id": item["episode_id"], "score": item["score"]}
            for item in report["rankings"]["post_help"]["entries"][:3]
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_synthetic_ranking_report()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2, ensure_ascii=True, allow_nan=False)
            file.write("\n")
    except OSError as error:
        parser.exit(2, f"Cannot write synthetic ranking output; existing output is never overwritten: {error}\n")
    print(json.dumps(comparison_summary(report)))


if __name__ == "__main__":
    main()
