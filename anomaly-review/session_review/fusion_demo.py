"""Generate an explicitly synthetic combined-priority browser demonstration."""
import argparse
import hashlib
import json
from pathlib import Path

from .findings import analyze_sessions as analyzer
from .findings import bundle, historical
from .fusion import fuse_review_bundle


def _contribution(name, label, value, ref, source_id, *, above, tail, weight):
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
        "reason": (
            f"{label} was above its synthetic leave-one-out reference threshold."
            if above else f"{label} was within its synthetic leave-one-out reference threshold."
        ),
        "reference": {
            "evaluated_episode_excluded": True,
            "reference_episode_ids": [f"synthetic-peer-{number}" for number in range(1, 9)],
            "statistics": {
                "status": "ready", "p25": 120, "p75": 300,
                "upper_reference_threshold": 570, "robust_scale": 180,
            },
        },
        "evidence_refs": [ref],
        "source_event_ids": [source_id],
        "source_pointers": [],
        "unresolved_evidence_refs": [],
    }


def _entry(session, *, strength, use_finding_evidence=True):
    finding_refs = [
        ref for finding in session["analysis"]["findings"]
        for ref in [*finding["highlight_ids"], *finding["recovery_evidence_ids"]]
    ]
    chosen = finding_refs[0] if use_finding_evidence and finding_refs else session["timeline"][0]["id"]
    if not use_finding_evidence:
        chosen = next(
            event["id"] for event in session["timeline"] if event["id"] not in set(finding_refs)
        )
    event = next(item for item in session["timeline"] if item["id"] == chosen)
    source_id = event["source_event_id"]
    above_count = {"none": 0, "moderate": 1, "strong": 2}[strength]
    specs = [
        ("post_help_active_time", "Post-help active time", 720, .35),
        ("failed_checks_after_help", "Failed checks after help", 4, .30),
        ("repeated_failed_checks_after_help", "Repeated failed checks after help", 2, .20),
        ("tutor_requests", "Tutor requests", 3, .15),
    ]
    contributions = [
        _contribution(name, label, value, chosen, source_id,
                      above=index < above_count, tail=95 if strength == "strong" else 60,
                      weight=weight)
        for index, (name, label, value, weight) in enumerate(specs)
    ]
    score = sum(item["weighted_points"] for item in contributions)
    return {
        "episode_id": session["id"], "score_status": "known", "score": score,
        "priority_reasons": [item["reason"] for item in contributions
                             if item["status"] == "above_reference_threshold"] or
                            ["No included metric exceeded its synthetic reference threshold."],
        "metric_contributions": contributions,
        "evidence_refs": [chosen], "source_event_ids": [source_id],
        "source_pointers": [], "unresolved_evidence_refs": [], "data_limitations": [],
    }


def build_demo():
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "findings"
    raw = (fixtures / "sessions.json").read_bytes()
    cache = json.loads((fixtures / "authored_assessments.json").read_text())
    if hashlib.sha256(raw).hexdigest() != cache["input_sha256"]:
        raise ValueError("Authored assessments do not match fixture bytes.")
    sessions = analyzer.Input.model_validate_json(raw).sessions
    evidence = [analyzer.assemble(session) for session in sessions]
    authored = {item["session_id"]: analyzer.Assessment.model_validate(item)
                for item in cache["assessments"]}
    results = {
        session.session_id: analyzer.validate_assessment(session, item, authored[session.session_id])
        for session, item in zip(sessions, evidence)
    }
    review = bundle.build(
        sessions,
        input_hash=hashlib.sha256(raw).hexdigest(),
        results=results,
        source="authored offline assessments, not model inference",
    )
    by_id = {session["id"]: session for session in review["sessions"]}
    strengths = {
        "S01-persistence": ("strong", True),
        "S02-progress": ("none", True),
        "S03-mismatch": ("moderate", True),
        "S05-unchanged-retries": ("moderate", True),
        "S06-recovered-obstacle": ("strong", False),
    }
    post_entries = [
        _entry(by_id[identity], strength=strength, use_finding_evidence=overlap)
        for identity, (strength, overlap) in strengths.items()
    ]
    total_entries = []
    for post in post_entries:
        session = by_id[post["episode_id"]]
        ref = post["evidence_refs"][0]
        source_id = next(item["source_event_id"] for item in session["timeline"] if item["id"] == ref)
        total = _contribution(
            "total_observed_active_time", "Total observed active time", 900,
            ref, source_id, above=post["score"] > 0, tail=80, weight=1,
        )
        total_entries.append({**post, "score": total["weighted_points"],
                              "metric_contributions": [total]})
    ranking = {
        "version": 1, "method": "question-level-review-ranking-v1",
        "dataset_id": "synthetic-combined-priority-demo", "origin": "synthetic",
        "eligible_population": {
            "excluded": [{
                "episode_id": "S04-other-question",
                "reasons": ["one_or_more_required_metrics_unknown"],
                "missing_metrics": [{"metric": "post_help_active_time",
                                     "reason": "question_scope_incomplete"}],
            }],
        },
        "rankings": {
            "post_help": {"entries": post_entries},
            "total_time": {"entries": total_entries},
        },
    }
    combined = fuse_review_bundle(review, ranking)
    combined["dataset"]["label"] = "Synthetic combined-priority demonstration"
    combined["dataset"]["notice"] = (
        "All events, metric values, references, and model assessments are authored examples. "
        "They are not research evidence."
    )
    return combined


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    historical.private_json(args.output, build_demo())
    print(f"Wrote synthetic combined-priority demonstration to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
