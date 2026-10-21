import json
import subprocess
import sys
from pathlib import Path

import pytest

from session_review.baselines import (
    BaselineConfig,
    calculate_question_baselines,
    describe_values,
    leave_one_out_reference,
    metric_value,
)
from session_review.normalize import load_json
from session_review.phase3b_demo import (
    build_synthetic_evidence_index,
    build_synthetic_metrics_report,
    build_synthetic_ranking_report,
    comparison_summary,
)
from session_review.ranking import (
    RankingConfig,
    build_frontend_ranking_overlay,
    evidence_index_from_session_report,
    rank_sessions,
)
from session_review.sessions import reconstruct


FIXTURE = Path(__file__).parents[1] / "fixtures" / "frontend_demo_sessions.json"


@pytest.fixture
def metrics():
    return build_synthetic_metrics_report()


@pytest.fixture
def ranking():
    return build_synthetic_ranking_report()


def test_question_baselines_are_separate_and_report_unknowns(metrics):
    result = calculate_question_baselines(metrics)
    by_question = {item["scope"]["question_id"]: item for item in result["questions"]}
    assert set(by_question) == {"Q1", "Q2"}
    assert by_question["Q1"]["metrics"]["total_observed_active_time"]["summary"]["median"] == 50
    assert by_question["Q1"]["metrics"]["total_observed_active_time"]["missing_count"] == 1
    assert by_question["Q2"]["metrics"]["total_observed_active_time"]["summary"]["status"] == "insufficient_data"
    assert by_question["Q1"]["outcome_counts"]["unfinished"] == 2


def test_leave_one_out_reference_never_contains_evaluated_session(metrics):
    reference = leave_one_out_reference(
        metrics["episodes"], "q1-long-independent", "total_observed_active_time"
    )
    assert reference["evaluated_episode_excluded"] is True
    assert "q1-long-independent" not in reference["reference_episode_ids"]
    assert reference["statistics"]["maximum"] == 130
    assert reference["statistics"]["status"] == "ready"


def test_total_time_and_post_help_rank_different_synthetic_scenarios(ranking):
    total = ranking["rankings"]["total_time"]["entries"]
    post = ranking["rankings"]["post_help"]["entries"]
    assert total[0]["episode_id"] == "q1-long-independent"
    assert post[0]["episode_id"] == "q1-post-help-struggle"
    long_post = next(item for item in post if item["episode_id"] == "q1-long-independent")
    assert long_post["score"] == 0
    assert "No included metric exceeded" in long_post["priority_reasons"][0]


def test_all_three_methods_use_same_population(ranking):
    expected = set(ranking["eligible_population"]["episode_ids"])
    assert expected
    for method in ("random", "total_time", "post_help"):
        actual = {item["episode_id"] for item in ranking["rankings"][method]["entries"]}
        assert actual == expected
    assert ranking["eligible_population"]["same_population_for_all_methods"] is True


def test_unknown_metrics_and_small_questions_are_unscored(ranking):
    excluded = {item["episode_id"]: item for item in ranking["eligible_population"]["excluded"]}
    assert "one_or_more_required_metrics_unknown" in excluded["q1-ambiguous"]["reasons"]
    assert excluded["q1-ambiguous"]["missing_metrics"]
    for identity in ("q2-small-01", "q2-small-02", "q2-small-03"):
        assert excluded[identity]["reasons"] == ["insufficient_same_question_reference_sessions"]
    ranked = {item["episode_id"] for item in ranking["rankings"]["total_time"]["entries"]}
    assert not ranked.intersection(excluded)


def test_unfinished_session_is_not_automatically_excluded(ranking):
    eligible = set(ranking["eligible_population"]["episode_ids"])
    assert "q1-normal-05" in eligible
    assert "q1-post-help-struggle" in eligible
    entry = next(item for item in ranking["rankings"]["post_help"]["entries"]
                 if item["episode_id"] == "q1-post-help-struggle")
    assert entry["data_limitations"]


def test_successful_recovery_scenario_remains_low_priority(ranking):
    entry = next(item for item in ranking["rankings"]["post_help"]["entries"]
                 if item["episode_id"] == "q1-quick-recovery")
    assert entry["score"] == 0
    assert not entry["data_limitations"]


def test_post_help_repeat_derivation_excludes_pre_help_failure():
    episode = {
        "activity": {
            "failed_check_count": {
                "after_first_help": {
                    "status": "known", "value": 2, "evidence_refs": ["fail-2", "fail-3"]
                }
            },
            "repeated_failure_count": {
                "status": "known", "value": 2,
                "evidence_refs": ["fail-1", "fail-2", "fail-3"],
                "details": {
                    "logical_check_groups": {"check@v1": ["fail-1", "fail-2", "fail-3"]}
                },
            },
        }
    }
    derived = metric_value(episode, "repeated_failed_checks_after_help")
    assert derived["status"] == "known"
    assert derived["value"] == 1
    assert derived["evidence_refs"] == ["fail-2", "fail-3"]


def test_robust_summary_reports_percentiles_and_constant_fallback():
    summary = describe_values([10] * 8, BaselineConfig())
    assert summary["status"] == "ready"
    assert summary["median"] == 10
    assert summary["p25"] == 10
    assert summary["p75"] == 10
    assert summary["p90"] == 10
    assert summary["iqr"] == 0
    assert summary["mad"] == 0
    assert summary["scale_basis"] == "constant_value_fallback"


def test_rankings_preserve_metric_and_source_event_evidence(ranking):
    entry = ranking["rankings"]["post_help"]["entries"][0]
    assert entry["evidence_refs"]
    assert entry["source_event_ids"]
    assert entry["source_pointers"]
    assert not entry["unresolved_evidence_refs"]
    for contribution in entry["metric_contributions"]:
        assert contribution["reference"]["evaluated_episode_excluded"] is True
        assert entry["episode_id"] not in contribution["reference"]["reference_episode_ids"]
        assert contribution["evidence_refs"]
        assert contribution["source_event_ids"]


def test_missing_source_index_is_explicit(metrics):
    result = rank_sessions(metrics)
    entry = result["rankings"]["post_help"]["entries"][0]
    assert not entry["source_event_ids"]
    assert entry["unresolved_evidence_refs"]


def test_frontend_overlay_is_joinable_without_changing_demo_contract(ranking):
    overlay = build_frontend_ranking_overlay(ranking, "post_help")
    assert overlay["contract"] == "anomaly-review.frontend-ranking-overlay.v1"
    assert overlay["sessions"][0]["episode_id"] == "q1-post-help-struggle"
    assert overlay["sessions"][0]["metric_contributions"]
    assert overlay["sessions"][0]["source_pointers"]
    assert overlay["excluded_sessions"]
    with pytest.raises(ValueError):
        build_frontend_ranking_overlay(ranking, "unsupported")


def test_synthetic_comparison_is_explicitly_not_research_evidence(ranking):
    summary = comparison_summary(ranking)
    assert summary["synthetic"] is True
    assert "not research evidence" in summary["warning"]
    assert summary["total_time_top_three"][0]["episode_id"] == "q1-long-independent"
    assert summary["post_help_top_three"][0]["episode_id"] == "q1-post-help-struggle"


def test_configs_reject_unreliable_reference_sizes():
    with pytest.raises(ValueError):
        BaselineConfig(1)
    with pytest.raises(ValueError):
        RankingConfig(minimum_reference_sessions=1)
    with pytest.raises(ValueError):
        BaselineConfig(3)
    with pytest.raises(ValueError):
        RankingConfig(random_seed=1.5)


def test_evidence_index_resolves_reconstructed_source_events():
    sessions = reconstruct(load_json(FIXTURE.read_bytes()))
    index = evidence_index_from_session_report(sessions)
    record = sessions["normalization"]["records"][0]
    assert index[record["ref"]]["source_event_id"] == record["event"]["event_id"]
    assert index[record["ref"]]["source_pointers"]


def test_ranking_cli_is_create_only(tmp_path):
    session_path = tmp_path / "sessions.json"
    output_path = tmp_path / "ranking.json"
    sessions = reconstruct(load_json(FIXTURE.read_bytes()))
    session_path.write_text(json.dumps(sessions), encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "session_review.ranking_cli",
        str(session_path),
        "--output",
        str(output_path),
    ]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(output_path.read_text())["method"] == "question-level-review-ranking-v1"
    saved = output_path.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2
    assert output_path.read_bytes() == saved


def test_synthetic_demo_cli_is_create_only(tmp_path):
    output_path = tmp_path / "synthetic-ranking.json"
    command = [
        sys.executable,
        "-m",
        "session_review.phase3b_demo",
        "--output",
        str(output_path),
    ]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    output = json.loads(output_path.read_text())
    assert output["origin"] == "synthetic"
    assert output["eligible_population"]["count"] == 11
    saved = output_path.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2
    assert output_path.read_bytes() == saved


def test_demo_evidence_index_covers_every_metric_reference(metrics):
    index = build_synthetic_evidence_index(metrics)
    for episode in metrics["episodes"]:
        for section in (episode["time"], episode["activity"]):
            text = json.dumps(section)
            for ref in index:
                if ref in text:
                    assert index[ref]["source_event_id"].startswith("source-")
