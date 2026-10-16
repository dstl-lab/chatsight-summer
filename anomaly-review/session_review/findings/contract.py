"""Versioned UI bundle. Model findings and instructor reviews remain separate."""
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from .analyze_sessions import Finding


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Metric(Model):
    status: Literal["known", "unknown"]
    value: float | str | bool | None
    reason: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "unknown") != (self.value is None):
            raise ValueError("Unknown metrics require null; known metrics require a value.")
        return self


class ReferenceTime(Model):
    status: Literal["illustrative", "unknown"]
    lower_seconds: float | None = None
    upper_seconds: float | None = None
    basis: str


class Reason(Model):
    id: str
    title: str
    description: str
    supporting_refs: list[str]
    supporting_event_ids: list[str]


class Metadata(Model):
    label: str
    value: str


class CodeDiff(Model):
    before: str | None = None
    after: str | None = None


class TimelineEvent(Model):
    id: str
    source_event_id: str | None = None
    kind: Literal["student_message", "tutor_response", "code_edit", "execution",
                  "check_result", "question_status", "activity", "inactivity", "notebook_snapshot"]
    actor: str
    title: str
    body: str
    occurred_at: str
    phase: Literal["before_help", "help_boundary", "after_help", "ambiguous", "unpartitioned"] = "unpartitioned"
    order_uncertain: bool = False
    duration_seconds: float | None = None
    source_pointers: list[str] = Field(default_factory=list)
    supporting_refs: list[str] = Field(default_factory=list)
    code_diff: CodeDiff | None = None
    metadata: list[Metadata] = Field(default_factory=list)

    @field_validator("occurred_at")
    @classmethod
    def timezone(cls, value):
        if datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError("Timeline timestamp needs a timezone.")
        return value


class Analysis(Model):
    state: Literal["not_analyzed", "completed", "failed", "rejected"]
    decision: Literal["surface", "no_supported_finding", "insufficient_evidence"] | None
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)
    model: str | None = None
    source: str
    semantic_interpretations_verified: Literal[False] = False

    @model_validator(mode="after")
    def safe_states(self):
        if self.state != "completed" and self.findings:
            raise ValueError("Only completed validated analyses can expose findings.")
        if self.state in {"failed", "rejected"} and self.decision != "insufficient_evidence":
            raise ValueError("Failed and rejected results must remain insufficient evidence.")
        if self.state == "not_analyzed" and self.decision is not None:
            raise ValueError("Unanalyzed data cannot have an analysis decision.")
        if self.state == "completed" and (self.decision is None or (self.decision == "surface") != bool(self.findings)):
            raise ValueError("Completed decisions and findings must agree.")
        return self


class ReviewSession(Model):
    id: str
    review_rank: int
    flagged: bool
    priority: Literal["high", "medium", "routine"] | None = None
    priority_basis: str
    scenario: str
    synthetic: bool
    scope: Literal["conversation", "question_episode"]
    student_id: str
    question_id: str | None = None
    assignment_id: str | None = None
    outcome: Metric
    active_time: Metric
    post_help_active_time: Metric
    elapsed_time: Metric
    reference_active_time: ReferenceTime
    failed_checks_after_help: Metric
    tutor_requests: Metric
    completed_tutor_responses: Metric
    repeated_failures: Metric
    continued_after_help: Metric
    resumed_after_help: Metric
    reasons: list[Reason] = Field(default_factory=list)
    timeline: list[TimelineEvent]
    source_event_refs: list[str]
    quality_warnings: list[str]
    analysis: Analysis

    @model_validator(mode="after")
    def evidence(self):
        ids = [event.id for event in self.timeline]
        refs = set(ids)
        if len(ids) != len(refs):
            raise ValueError("Duplicate timeline references.")
        if self.flagged != (self.analysis.state == "completed" and self.analysis.decision == "surface"):
            raise ValueError("Flag status must derive from validated findings.")
        cited = set(self.source_event_refs)
        for reason in self.reasons:
            cited.update(reason.supporting_refs)
        for finding in self.analysis.findings:
            cited.update(finding.highlight_ids + finding.recovery_evidence_ids)
            for interpretation in finding.interpretations:
                cited.update(interpretation.evidence_ids)
                if not set(interpretation.evidence_ids) <= set(finding.highlight_ids + finding.recovery_evidence_ids):
                    raise ValueError("Interpretation evidence is not highlighted or recovery evidence.")
            for fact in finding.facts:
                cited.add(fact.record_id)
                if fact.related_id:
                    cited.add(fact.related_id)
        for name in ("outcome", "active_time", "post_help_active_time", "elapsed_time",
                     "failed_checks_after_help", "tutor_requests", "completed_tutor_responses",
                     "repeated_failures", "continued_after_help", "resumed_after_help"):
            cited.update(getattr(self, name).evidence_refs)
        if not cited <= refs:
            raise ValueError("Review bundle cites missing timeline events.")
        return self


class DatasetInfo(Model):
    id: str
    synthetic: bool
    label: str
    notice: str
    priority_method: str
    input_sha256: str
    model: str | None = None
    prompt_sha256: str
    analysis_version: str


class Summary(Model):
    total_sessions: int
    flagged_sessions: int
    high_priority_sessions: int


class ReviewBundle(Model):
    contract_version: Literal[2] = 2
    dataset: DatasetInfo
    summary: Summary
    sessions: list[ReviewSession]

    @model_validator(mode="after")
    def consistent(self):
        if len({s.id for s in self.sessions}) != len(self.sessions):
            raise ValueError("Duplicate session identities.")
        if any(s.synthetic != self.dataset.synthetic for s in self.sessions):
            raise ValueError("Bundle origin must match session origins.")
        if self.summary.total_sessions != len(self.sessions) or self.summary.flagged_sessions != sum(s.flagged for s in self.sessions):
            raise ValueError("Summary counts disagree with sessions.")
        if self.summary.high_priority_sessions != sum(s.priority == "high" for s in self.sessions):
            raise ValueError("Priority count disagrees with sessions.")
        return self
