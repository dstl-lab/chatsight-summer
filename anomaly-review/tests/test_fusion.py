import copy
import json
from pathlib import Path

import pytest

from session_review.findings.contract import ReviewBundle
from session_review.fusion import FusionConfig, combine_signals, fuse_review_bundle
from session_review.fusion_demo import build_demo


DEMO = Path(__file__).resolve().parents[1] / "frontend" / "src" / "findings-demo.synthetic.json"
COMBINED_DEMO = Path(__file__).resolve().parents[1] / "frontend" / "src" / "combined-demo.synthetic.json"


def metric(status, *, score=None, refs=None, source_ids=None):
    return {
        "status": status,
        "episode_id": "episode-1",
        "score": score,
        "above_threshold_metrics": ["post_help_active_time"] if "outlier" in status else [],
        "reasons": [],
        "evidence_refs": refs or [],
        "source_event_ids": source_ids or [],
        "data_limitations": [],
    }


def llm(status, *, refs=None, source_ids=None):
    return {
        "status": status,
        "model": "gpt-test",
        "finding_categories": ["persistent_difficulty"] if status == "supported_finding" else [],
        "evidence_refs": refs or [],
        "source_event_ids": source_ids or [],
        "data_limitations": [],
    }


@pytest.mark.parametrize(("metric_status", "llm_status", "shared", "priority"), [
    ("strong_outlier", "supported_finding", True, "high"),
    ("strong_outlier", "supported_finding", False, "medium"),
    ("strong_outlier", "no_supported_finding", False, "medium"),
    ("no_outlier", "supported_finding", False, "medium"),
    ("moderate_outlier", "no_supported_finding", False, "low"),
    ("no_outlier", "no_supported_finding", False, "none"),
    ("insufficient_data", "insufficient_evidence", False, "insufficient_data"),
])
def test_priority_rules(metric_status, llm_status, shared, priority):
    refs = ["event-1"] if shared else []
    result = combine_signals(
        metric(metric_status, score=75 if "outlier" in metric_status else 0, refs=refs),
        llm(llm_status, refs=refs),
    )
    assert result["priority"] == priority
    assert result["status"] == ("insufficient_data" if priority == "insufficient_data" else "scored")


def test_metric_strength_uses_multiple_or_extreme_contributions():
    config = FusionConfig(strong_composite_score=50, strong_single_tail_score=90,
                          strong_contribution_count=2)
    moderate = {
        "score_status": "known", "score": 20, "episode_id": "e1",
        "priority_reasons": [], "evidence_refs": ["a"], "source_event_ids": ["a"],
        "data_limitations": [],
        "metric_contributions": [{"metric": "one", "status": "above_reference_threshold",
                                  "tail_score": 40, "evidence_refs": ["a"],
                                  "source_event_ids": ["a"]}],
    }
    extreme = copy.deepcopy(moderate)
    extreme["metric_contributions"][0]["tail_score"] = 95
    from session_review.fusion import _metric_signal
    assert _metric_signal(moderate, None, config)["status"] == "moderate_outlier"
    assert _metric_signal(extreme, None, config)["status"] == "strong_outlier"


def contribution(name, label, value, ref, source_id, *, above=True, tail=95, weight=.25):
    return {
        "metric": name,
        "label": label,
        "status": "above_reference_threshold" if above else "within_reference_threshold",
        "value": value,
        "unit": "seconds" if "time" in name else "events",
        "weight": weight,
        "tail_score": tail if above else 0,
        "weighted_points": tail * weight if above else 0,
        "empirical_peer_percentile": 100 if above else 50,
        "reason": f"{label} exceeded its leave-one-out reference." if above else f"{label} was within reference.",
        "reference": {
            "evaluated_episode_excluded": True,
            "reference_episode_ids": [f"peer-{index}" for index in range(8)],
            "statistics": {"status": "ready", "p25": 10, "p75": 20,
                           "upper_reference_threshold": 30, "robust_scale": 10},
        },
        "evidence_refs": [ref] if value else [],
        "source_event_ids": [source_id] if value else [],
        "source_pointers": [],
        "unresolved_evidence_refs": [],
    }


def ranking_for(session, *, missing_source=False):
    finding_ref = session["analysis"]["findings"][0]["highlight_ids"][0]
    event = next(item for item in session["timeline"] if item["id"] == finding_ref)
    source_id = "missing-source" if missing_source else event["source_event_id"]
    contributions = [
        contribution("post_help_active_time", "Post-help active time", 600, finding_ref, source_id),
        contribution("failed_checks_after_help", "Failed checks", 4, finding_ref, source_id),
        contribution("repeated_failed_checks_after_help", "Repeated failures", 2, finding_ref, source_id,
                     above=False, tail=0, weight=.20),
        contribution("tutor_requests", "Tutor requests", 3, finding_ref, source_id,
                     above=False, tail=0, weight=.15),
    ]
    entry = {
        "episode_id": session["id"], "score_status": "known", "score": 61,
        "priority_reasons": [item["reason"] for item in contributions if item["status"].startswith("above")],
        "metric_contributions": contributions,
        "evidence_refs": [finding_ref], "source_event_ids": [source_id],
        "source_pointers": [], "unresolved_evidence_refs": [], "data_limitations": [],
    }
    total_contribution = contribution(
        "total_observed_active_time", "Total observed active time", 900,
        finding_ref, source_id, weight=1,
    )
    return {
        "version": 1, "method": "question-level-review-ranking-v1",
        "dataset_id": "metric-dataset", "origin": "synthetic",
        "eligible_population": {"excluded": []},
        "rankings": {
            "post_help": {"entries": [entry]},
            "total_time": {"entries": [{**entry, "score": 95,
                                          "metric_contributions": [total_contribution]}]},
        },
    }


def test_bundle_fusion_preserves_both_signals_and_traceability():
    document = json.loads(DEMO.read_text())
    high = document["sessions"][0]
    result = fuse_review_bundle(document, ranking_for(high))
    validated = ReviewBundle.model_validate(result)
    combined = next(item for item in validated.sessions if item.id == high["id"])
    assert result["contract_version"] == 3
    assert combined.priority == "high" and combined.flagged
    assert combined.fusion.metric_signal.status == "strong_outlier"
    assert combined.fusion.llm_signal.status == "supported_finding"
    assert combined.fusion.shared_source_event_ids
    assert combined.active_time.status == "known"
    assert combined.post_help_active_time.status == "known"
    assert combined.reference_active_time.status == "calculated"
    assert any(reason.id.startswith("metric-") for reason in combined.reasons)
    assert result["summary"]["high_priority_sessions"] == 1
    assert result["summary"]["insufficient_data_sessions"] >= 1


def test_bundle_fusion_requires_metric_evidence_in_same_timeline():
    document = json.loads(DEMO.read_text())
    with pytest.raises(ValueError, match="missing from the review timeline"):
        fuse_review_bundle(document, ranking_for(document["sessions"][0], missing_source=True))


def test_explicit_mapping_is_required_when_ids_differ():
    document = json.loads(DEMO.read_text())
    session = document["sessions"][0]
    ranking = ranking_for(session)
    for method in ("post_help", "total_time"):
        ranking["rankings"][method]["entries"][0]["episode_id"] = "different-episode"
    unmapped = fuse_review_bundle(document, ranking)
    first = next(item for item in unmapped["sessions"] if item["id"] == session["id"])
    assert first["priority"] == "medium"
    assert first["fusion"]["metric_signal"]["status"] == "insufficient_data"
    mapped = fuse_review_bundle(document, ranking,
                                session_episode_map={session["id"]: "different-episode"})
    first = next(item for item in mapped["sessions"] if item["id"] == session["id"])
    assert first["priority"] == "high"


def test_combined_demo_is_reproducible_and_covers_every_priority_category():
    generated = build_demo()
    assert generated == json.loads(COMBINED_DEMO.read_text())
    assert {session["priority"] for session in generated["sessions"]} == {
        "high", "medium", "low", "none", "insufficient_data"
    }
    assert generated["dataset"]["synthetic"] is True
    assert "not research evidence" in generated["dataset"]["notice"].lower()
