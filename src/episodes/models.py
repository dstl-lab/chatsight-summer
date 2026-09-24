"""Canonical, question-scoped episode models.

These models deliberately do not use a tutor conversation as their unit of
analysis. ``conversation_id`` is retained only as optional source metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EVENT_SCHEMA_VERSION = "1.0.0"
RECONSTRUCTION_VERSION = "1.0.0"
INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000
MAX_PAYLOAD_BYTES = 32 * 1024

EventType = Literal[
    "notebook_session_started",
    "active_question_changed",
    "cell_edit",
    "cell_execution_started",
    "cell_execution_completed",
    "cell_error",
    "tutor_query",
    "tutor_response",
    "tutor_code_inserted",
    "tutor_code_copied",
    "notebook_paste",
    "autograder_completed",
]
QuestionSource = Literal[
    "grader_id", "nearest_markdown", "notebook_cell", "unknown"
]
SourceKind = Literal["synthetic", "real", "unknown"]
EndReason = Literal["autograder_success", "inactivity", "end_of_data"]
Provenance = Literal[
    "inserted_from_tutor", "copied_then_pasted", "tutor_copy_only", "unknown"
]

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "clipboard",
        "clipboard_contents",
        "clipboard_text",
        "pasted_text",
        "source",
        "full_source",
        "code",
        "traceback",
        "full_traceback",
    }
)


class EpisodeEvent(BaseModel):
    """Validated event envelope emitted by the Jupyter extension."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"]
    event_id: str = Field(min_length=1)
    event_type: EventType
    occurred_at: datetime
    client_sequence: int = Field(ge=1)
    analytics_session_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    notebook_path: str | None
    notebook_name: str | None
    cell_id: str | None
    cell_index: int | None
    question_id: str = Field(min_length=1)
    question_source: QuestionSource
    conversation_id: str | None
    turn_id: str | None
    response_id: str | None
    correlation_id: str | None
    payload: dict[str, Any]


class TranscriptTurn(BaseModel):
    role: Literal["student", "tutor"]
    text: str
    conversation_id: str
    occurred_at: datetime | None = None
    event_id: str | None = None
    turn_id: str | None = None
    response_id: str | None = None


class Ratio(BaseModel):
    numerator: int
    denominator: int
    value: float | None


class EpisodeMeasures(BaseModel):
    attempted_before_asking: bool | None
    edits_before_asking: int | None
    executions_before_asking: int | None
    errors_before_asking: int | None
    time_to_first_ask_ms: int | None
    tutor_turn_count: int
    tutor_code_provenance: Provenance
    edited_after_response: bool | None
    tested_after_response: bool | None
    errors_after_response: int | None
    eventually_passed: bool
    attempt_count: int
    time_to_pass_ms: int | None
    prior_pass_recorded: bool = False


class Episode(BaseModel):
    """Canonical episode. Source identity is intentionally excluded."""

    episode_id: str
    student_key: str
    notebook_id: str
    question_id: str
    question_source: QuestionSource
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    end_reason: EndReason
    conversation_ids: list[str]
    patterns: list[str]
    measures: EpisodeMeasures
    events: list[EpisodeEvent]


class QuestionSummary(BaseModel):
    notebook_id: str
    question_id: str
    student_count: int
    episode_count: int
    pct_recorded_struggle: Ratio
    pct_repeated_attempts: Ratio
    pct_used_tutor: Ratio
    pct_asked_before_attempting: Ratio
    median_errors_before_asking: float | None
    pct_used_tutor_code: Ratio
    pct_tested_after_tutor: Ratio
    pct_passed_after_tutor: Ratio
    pct_unresolved: Ratio
    pattern_counts: dict[str, int]
    pattern_rates: dict[str, Ratio]
    no_named_pattern: Ratio


class ImportQuality(BaseModel):
    total_rows: int = 0
    accepted_events: int = 0
    duplicate_events: int = 0
    rejected_rows: int = 0
    legacy_rows: int = 0
    unknown_question_events: int = 0
    rejection_reasons: dict[str, int] = Field(default_factory=dict)


class DatasetMeta(BaseModel):
    bundle_id: str
    source_kind: SourceKind
    source_file: str
    event_schema_version: str
    reconstruction_version: str
    inactivity_timeout_ms: int
    episode_count: int
    question_count: int
    quality: ImportQuality
    generation: dict[str, Any] | None = None


class EpisodeDataset(BaseModel):
    meta: DatasetMeta
    episodes: list[Episode]
    questions: list[QuestionSummary]
    transcripts: dict[str, list[TranscriptTurn]] = Field(default_factory=dict)
