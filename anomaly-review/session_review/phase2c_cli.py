"""Validate an approved local JSON export with a provisional, declarative mapping."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .json_adapter import JsonMapping
from .metrics import MetricsConfig
from .normalize import parse_json
from .phase2c import run_phase2c
from .schema import Coverage
from .sessions import SessionConfig


def _write_new(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=True, allow_nan=False)
        file.write("\n")


def _coverage(args):
    supplied = [args.coverage_start, args.coverage_end, args.coverage_completeness]
    if not any(supplied):
        return None
    if not all(supplied):
        raise ValueError("Coverage start, end, and completeness must be supplied together.")
    return Coverage(start_at=args.coverage_start, end_at=args.coverage_end,
                    completeness=args.coverage_completeness)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Approved, deidentified local JSON export")
    parser.add_argument("--mapping", required=True, type=Path,
                        help="Provisional JSON mapping document")
    parser.add_argument("--dataset-id", required=True,
                        help="Local analysis identifier, not a student identifier")
    parser.add_argument("--quality-output", required=True, type=Path)
    parser.add_argument("--artifacts-dir", type=Path,
                        help="Optional private directory for normalized, session, and metric artifacts")
    parser.add_argument("--gap-seconds", type=int, default=1800)
    parser.add_argument("--active-interval-seconds", type=int, default=300)
    parser.add_argument("--coverage-start")
    parser.add_argument("--coverage-end")
    parser.add_argument("--coverage-completeness",
                        choices=["unknown", "partial", "declared_complete"])
    args = parser.parse_args()

    outputs = [args.quality_output]
    if args.artifacts_dir:
        outputs.extend(args.artifacts_dir / name for name in (
            "normalization.json", "question-sessions.json", "behavioral-metrics.json"
        ))
    if any(path.exists() for path in outputs):
        parser.exit(2, "An output already exists; this command never overwrites artifacts.\n")

    try:
        mapping = JsonMapping.model_validate(parse_json(args.mapping.read_bytes()))
        result = run_phase2c(
            args.input.read_bytes(), mapping, args.dataset_id,
            coverage=_coverage(args),
            session_config=SessionConfig(args.gap_seconds),
            metrics_config=MetricsConfig(args.active_interval_seconds),
        )
        if args.artifacts_dir:
            _write_new(args.artifacts_dir / "normalization.json", result.normalization)
            _write_new(args.artifacts_dir / "question-sessions.json", result.sessions)
            _write_new(args.artifacts_dir / "behavioral-metrics.json", result.metrics)
        _write_new(args.quality_output, result.quality)
    except (OSError, ValueError, TypeError, KeyError, ValidationError):
        parser.exit(2, "Cannot validate export; verify JSON, mapping, paths, and configuration. Source files were not modified.\n")

    summary = {
        "method": result.quality["method"],
        "input_records": result.quality["counts"]["input_records"],
        "question_sessions": result.quality["counts"]["reconstructed_question_sessions"],
        "rejected_records": result.quality["counts"]["rejected_records"],
        "unassigned_events": result.quality["counts"]["unassigned_events"],
        "validation_gate": result.quality["validation_gate"]["status"],
        "real_data_validated": False,
    }
    print(json.dumps(summary, ensure_ascii=True, allow_nan=False))
    if result.quality["validation_gate"]["status"] == "blocked":
        parser.exit(1, "Quality report saved; blocking mapping or data issues require review.\n")


if __name__ == "__main__":
    main()
