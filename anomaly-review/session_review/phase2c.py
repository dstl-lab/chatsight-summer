"""End-to-end Phase 2C preparation pipeline for mapped local JSON exports."""
from __future__ import annotations

from dataclasses import dataclass

from .json_adapter import JsonMapping, normalize_mapped_json, records_from_export
from .metrics import MetricsConfig, calculate_metrics
from .quality import build_quality_report
from .schema import Coverage
from .sessions import SessionConfig, reconstruct


@dataclass(frozen=True)
class Phase2CResult:
    normalization: dict
    sessions: dict
    metrics: dict
    quality: dict


def run_phase2c(content: bytes, mapping: JsonMapping, dataset_id: str,
                coverage: Coverage | None = None,
                session_config: SessionConfig | None = None,
                metrics_config: MetricsConfig | None = None,
                origin: str = "recorded") -> Phase2CResult:
    """Run a local export through mapping, validation, sessions, and metrics."""
    _, records, pointers = records_from_export(content, mapping)
    normalized = normalize_mapped_json(
        content, mapping, dataset_id, origin=origin, coverage=coverage
    )
    sessions = reconstruct(normalized, session_config)
    metrics = calculate_metrics(sessions, metrics_config)
    quality = build_quality_report(records, pointers, mapping, normalized, sessions, metrics)
    return Phase2CResult(
        normalization=normalized.model_dump(mode="json"),
        sessions=sessions,
        metrics=metrics,
        quality=quality,
    )
