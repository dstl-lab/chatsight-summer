"""Canonical contract, not an assertion about the tutor's unavailable JSON."""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, field_validator, model_validator

Identifier = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def utc(value: datetime | None) -> datetime | None:
    if value is not None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamps require an explicit UTC offset.")
        return value.astimezone(timezone.utc)
    return None


class QuestionLink(Model):
    basis: Literal["explicit", "verified_mapping", "ambiguous", "missing"]
    question_id: Identifier | None = None
    candidates: list[Identifier] = Field(default_factory=list)
    mapping_ref: Identifier | None = None

    @model_validator(mode="after")
    def consistent(self):
        certain = self.basis in {"explicit", "verified_mapping"}
        if certain != (self.question_id is not None):
            raise ValueError("Only an explicit or verified link has a question ID.")
        if self.basis == "verified_mapping" and self.mapping_ref is None:
            raise ValueError("Verified mappings require a source mapping reference.")
        if self.candidates and self.basis != "ambiguous":
            raise ValueError("Candidates belong only to ambiguous links.")
        return self


class StudentMessage(Model):
    type: Literal["student_message"]
    text: str | None = None
    request_id: Identifier | None = None


class TutorResponse(Model):
    type: Literal["tutor_response"]
    text: str | None = None
    request_id: Identifier | None = None
    response_id: Identifier | None = None
    status: Literal["unknown", "streaming", "completed", "failed", "cancelled"]
    completion_basis: Literal["server_completed", "client_received"] | None = None

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "completed") != (self.completion_basis is not None):
            raise ValueError("A completed response requires its completion evidence basis.")
        return self


class CodeEdit(Model):
    type: Literal["code_edit"]
    cell_id: Identifier | None = None
    previous_revision_id: Identifier | None = None
    revision_id: Identifier | None = None
    before_source: str | None = None
    after_source: str | None = None


class Execution(Model):
    type: Literal["execution"]
    execution_id: Identifier | None = None
    cell_id: Identifier | None = None
    revision_id: Identifier | None = None
    status: Literal["unknown", "submitted", "completed", "error", "cancelled"]
    submitted_source: str | None = None
    output: str | None = None


class CheckResult(Model):
    type: Literal["check_result"]
    check_id: Identifier | None = None
    grader_id: Identifier | None = None
    grader_version: Identifier | None = None
    execution_id: Identifier | None = None
    revision_id: Identifier | None = None
    scope: Literal["unknown", "subcheck", "question"]
    outcome: Literal["unknown", "pass", "fail", "error"]


class QuestionStatus(Model):
    type: Literal["question_status"]
    status: Literal["completed", "reopened", "unfinished", "unknown"]
    evidence_basis: Identifier


class Activity(Model):
    type: Literal["activity"]
    action: Literal["focus", "blur", "heartbeat", "resume", "pause"]


Detail = Annotated[
    StudentMessage | TutorResponse | CodeEdit | Execution | CheckResult | QuestionStatus | Activity,
    Field(discriminator="type"),
]


class Event(Model):
    event_id: Identifier
    occurred_at: datetime | None = None
    received_at: datetime | None = None
    learner_id: Identifier | None = None
    course_id: Identifier | None = None
    cohort_id: Identifier | None = None
    assignment_id: Identifier | None = None
    assignment_version: Identifier | None = None
    notebook_id: Identifier | None = None
    question: QuestionLink = Field(default_factory=lambda: QuestionLink(basis="missing"))
    conversation_id: Identifier | None = None
    mode: Identifier | None = None
    order_stream_id: Identifier | None = None
    sequence: Annotated[StrictInt, Field(ge=0)] | None = None
    detail: Detail

    @field_validator("occurred_at", "received_at", mode="before")
    @classmethod
    def explicit_timestamp_units(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Convert source timestamps to ISO 8601 explicitly in the adapter.")
        return value

    @field_validator("occurred_at", "received_at")
    @classmethod
    def timestamps(cls, value):
        return utc(value)

    @model_validator(mode="after")
    def sequence_scope(self):
        if (self.sequence is None) != (self.order_stream_id is None):
            raise ValueError("Sequence numbers require a declared ordering stream.")
        return self


class Coverage(Model):
    start_at: datetime
    end_at: datetime
    completeness: Literal["unknown", "partial", "declared_complete"]

    @field_validator("start_at", "end_at", mode="before")
    @classmethod
    def explicit_timestamp_units(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Coverage timestamps require explicit ISO 8601 units.")
        return value

    @field_validator("start_at", "end_at")
    @classmethod
    def timestamps(cls, value):
        return utc(value)

    @model_validator(mode="after")
    def ordered(self):
        if self.start_at > self.end_at:
            raise ValueError("Coverage start must not follow end.")
        return self


class Envelope(Model):
    format: Literal["anomaly-review.canonical.v1"]
    dataset_id: Identifier
    origin: Literal["synthetic", "recorded"]
    coverage: Coverage | None = None
    events: list[object]


class Source(Model):
    input_sha256: str
    record_pointer: str
    record_sha256: str
    adapter: str


class NormalizedEvent(Model):
    ref: str
    event: Event
    sources: list[Source]


class Issue(Model):
    code: str
    record_pointer: str
    locations: list[str] = Field(default_factory=list)


class Normalization(Model):
    version: Literal[1] = 1
    dataset_id: str
    origin: Literal["synthetic", "recorded"]
    input_sha256: str
    coverage: Coverage | None
    records: list[NormalizedEvent]
    rejected: list[Issue]
    duplicate_records: int
