"""Calculate Phase 3A metrics, baselines, and Phase 3B rankings."""
import argparse
import json
from pathlib import Path

from .metrics import calculate_metrics
from .ranking import RankingConfig, evidence_index_from_session_report, rank_sessions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", type=Path, help="Question-session reconstruction JSON")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-reference-sessions", type=int, default=8)
    parser.add_argument("--random-seed", type=int, default=0)
    args = parser.parse_args()
    try:
        session_report = json.loads(args.sessions.read_text(encoding="utf-8"))
        metrics = calculate_metrics(session_report)
        result = rank_sessions(
            metrics,
            evidence_index_from_session_report(session_report),
            RankingConfig(args.minimum_reference_sessions, args.random_seed),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=True, allow_nan=False)
            file.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Cannot calculate rankings; existing output is never overwritten: {error}\n")
    print(json.dumps({
        "dataset_id": result["dataset_id"],
        "eligible_sessions": result["eligible_population"]["count"],
        "excluded_sessions": len(result["eligible_population"]["excluded"]),
    }))


if __name__ == "__main__":
    main()
