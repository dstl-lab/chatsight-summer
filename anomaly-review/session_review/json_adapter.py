"""Configurable, provisional adapter for an as-yet unverified JSON export."""
from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .normalize import AdapterConversionError, normalize, parse_json
from .schema import Coverage, Envelope, Normalization


MISSING = object()


class MappingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_pointer(value: str) -> str:
    if value and not value.startswith("/"):
        raise ValueError("JSON pointers must be empty or start with '/'.")
    return value


class QuestionMapping(MappingModel):
    question_id_pointer: str
    certain_basis: Literal["explicit", "verified_mapping"]
    mapping_ref: str | None = None
    candidates_pointer: str | None = None

    @model_validator(mode="after")
    def valid(self):
        _check_pointer(self.question_id_pointer)
        if self.candidates_pointer is not None:
            _check_pointer(self.candidates_pointer)
        if self.certain_basis == "verified_mapping" and not self.mapping_ref:
            raise ValueError("A verified question mapping requires mapping_ref.")
        if self.certain_basis == "explicit" and self.mapping_ref is not None:
            raise ValueError("An explicit question mapping cannot claim a mapping_ref.")
        return self


class EventTypeMapping(MappingModel):
    canonical_type: Literal[
        "student_message",
        "tutor_response",
        "code_edit",
        "execution",
        "check_result",
        "question_status",
        "activity",
    ]
    fields: dict[str, str] = Field(default_factory=dict)
    constants: dict[str, Any] = Field(default_factory=dict)
    value_maps: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid(self):
        for pointer in self.fields.values():
            _check_pointer(pointer)
        if set(self.fields) & set(self.constants):
            raise ValueError("A detail field cannot be both mapped and constant.")
        if not set(self.value_maps) <= set(self.fields):
            raise ValueError("Value maps may only target mapped detail fields.")
        return self


class JsonMapping(MappingModel):
    """Declarative mapping. A real mapping remains provisional until hand validation."""

    mapping_version: Literal[1] = 1
    status: Literal["provisional"]
    adapter_name: str = Field(min_length=1)
    records_pointer: str
    event_type_pointer: str
    common_fields: dict[str, str] = Field(default_factory=dict)
    question: QuestionMapping | None = None
    event_types: dict[str, EventTypeMapping]

    @model_validator(mode="after")
    def valid(self):
        _check_pointer(self.records_pointer)
        _check_pointer(self.event_type_pointer)
        for pointer in self.common_fields.values():
            _check_pointer(pointer)
        if not self.event_types:
            raise ValueError("At least one source event type must be mapped.")
        if any(not key for key in self.event_types):
            raise ValueError("Source event type names cannot be empty.")
        return self


def _tokens(pointer: str) -> list[str]:
    if pointer == "":
        return []
    _check_pointer(pointer)
    return [token.replace("~1", "/").replace("~0", "~")
            for token in pointer[1:].split("/")]


def resolve_pointer(value: object, pointer: str, default=MISSING):
    """Resolve RFC 6901-style object and array pointers without evaluating code."""
    current = value
    for token in _tokens(pointer):
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return default
    return current


def _pointer_child(parent: str, index: int) -> str:
    return f"{parent}/{index}" if parent else f"/{index}"


class ConfigurableJsonAdapter:
    """Translate records according to a reviewed mapping document."""

    def __init__(self, mapping: JsonMapping):
        self.mapping = mapping
        self.name = mapping.adapter_name

    def _get(self, record: dict, pointer: str):
        return resolve_pointer(record, pointer)

    def convert(self, record: object) -> dict:
        if not isinstance(record, dict):
            raise AdapterConversionError("record_not_object")
        raw_type = self._get(record, self.mapping.event_type_pointer)
        if raw_type is MISSING or raw_type is None:
            raise AdapterConversionError("missing_event_type", ["event_type"])
        if not isinstance(raw_type, str) or raw_type not in self.mapping.event_types:
            raise AdapterConversionError("unexpected_event_type", ["event_type"])

        converted = {}
        for field, pointer in self.mapping.common_fields.items():
            value = self._get(record, pointer)
            if value is not MISSING:
                converted[field] = value

        question = self.mapping.question
        if question is None:
            converted["question"] = {"basis": "missing"}
        else:
            question_id = self._get(record, question.question_id_pointer)
            candidates = (self._get(record, question.candidates_pointer)
                          if question.candidates_pointer is not None else MISSING)
            if question_id is not MISSING and question_id is not None and question_id != "":
                converted["question"] = {
                    "basis": question.certain_basis,
                    "question_id": question_id,
                }
                if question.mapping_ref is not None:
                    converted["question"]["mapping_ref"] = question.mapping_ref
            elif isinstance(candidates, list) and candidates:
                converted["question"] = {"basis": "ambiguous", "candidates": candidates}
            else:
                converted["question"] = {"basis": "missing"}

        type_mapping = self.mapping.event_types[raw_type]
        detail = {"type": type_mapping.canonical_type, **type_mapping.constants}
        for field, pointer in type_mapping.fields.items():
            value = self._get(record, pointer)
            if value is MISSING:
                continue
            if field in type_mapping.value_maps:
                key = str(value)
                if key not in type_mapping.value_maps[field]:
                    raise AdapterConversionError("unmapped_field_value", [f"detail.{field}"])
                value = type_mapping.value_maps[field][key]
            detail[field] = value
        converted["detail"] = detail
        return converted


def records_from_export(content: bytes, mapping: JsonMapping) -> tuple[object, list[object], list[str]]:
    root = parse_json(content)
    records = resolve_pointer(root, mapping.records_pointer)
    if records is MISSING:
        raise ValueError("The configured records pointer does not exist.")
    if not isinstance(records, list):
        raise ValueError("The configured records pointer must identify a JSON array.")
    pointers = [_pointer_child(mapping.records_pointer, index) for index in range(len(records))]
    return root, records, pointers


def normalize_mapped_json(content: bytes, mapping: JsonMapping, dataset_id: str,
                          origin: Literal["synthetic", "recorded"] = "recorded",
                          coverage: Coverage | None = None) -> Normalization:
    """Normalize a mapped export while retaining pointers into the original file."""
    _, records, pointers = records_from_export(content, mapping)
    envelope = Envelope(
        format="anomaly-review.canonical.v1",
        dataset_id=dataset_id,
        origin=origin,
        coverage=coverage,
        events=records,
    )
    return normalize(
        envelope,
        hashlib.sha256(content).hexdigest(),
        ConfigurableJsonAdapter(mapping),
        record_pointers=pointers,
    )
