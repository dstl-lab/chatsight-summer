"""Explicit adapter boundary with lossless provenance and non-silent rejection."""
import hashlib
import json
from collections import defaultdict
from typing import Protocol

from pydantic import ValidationError

from .schema import Envelope, Event, Issue, Normalization, NormalizedEvent, Source


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


class Adapter(Protocol):
    name: str

    def convert(self, record: object) -> object: ...


class AdapterConversionError(ValueError):
    """A privacy-safe adapter failure suitable for aggregate diagnostics."""

    def __init__(self, code: str, locations: list[str] | None = None):
        super().__init__(code)
        self.code = code
        self.locations = locations or []


class CanonicalAdapter:
    name = "canonical-v1"

    def convert(self, record: object) -> object:
        return record


def normalize(envelope: Envelope, input_sha256: str, adapter: Adapter | None = None,
              record_pointers: list[str] | None = None) -> Normalization:
    """Adapters populate the canonical contract; reconstruction never sees raw JSON."""
    adapter = adapter or CanonicalAdapter()
    if record_pointers is not None and len(record_pointers) != len(envelope.events):
        raise ValueError("Record pointers must match the number of input events.")
    grouped = defaultdict(list)
    rejected = []
    for i, record in enumerate(envelope.events):
        pointer = record_pointers[i] if record_pointers is not None else f"/events/{i}"
        try:
            event = Event.model_validate(adapter.convert(record))
        except ValidationError as exc:
            # Validation diagnostics must not echo message/code/identity values.
            rejected.append(Issue(code="invalid_event", record_pointer=pointer,
                                  locations=[".".join(map(str, e["loc"])) for e in exc.errors()]))
            continue
        except AdapterConversionError as exc:
            rejected.append(Issue(code=exc.code, record_pointer=pointer,
                                  locations=exc.locations))
            continue
        except (ValueError, KeyError, TypeError):
            rejected.append(Issue(code="adapter_error", record_pointer=pointer))
            continue
        if envelope.coverage and event.occurred_at is not None:
            if not envelope.coverage.start_at <= event.occurred_at <= envelope.coverage.end_at:
                rejected.append(Issue(code="outside_coverage", record_pointer=pointer))
                continue
        source = Source(input_sha256=input_sha256, record_pointer=pointer,
                        record_sha256=digest(record), adapter=adapter.name)
        grouped[event.event_id].append((event, source))
    records = []
    duplicates = 0
    for event_id, copies in sorted(grouped.items()):
        if len({digest(event.model_dump(mode="json")) for event, _ in copies}) > 1:
            rejected.extend(Issue(code="conflicting_event_id", record_pointer=source.record_pointer)
                            for _, source in copies)
            continue
        duplicates += len(copies) - 1
        records.append(NormalizedEvent(
            ref="ev-" + digest([envelope.dataset_id, event_id]), event=copies[0][0],
            sources=[source for _, source in copies],
        ))
    return Normalization(dataset_id=envelope.dataset_id, origin=envelope.origin,
                         input_sha256=input_sha256, coverage=envelope.coverage,
                         records=records, rejected=rejected, duplicate_records=duplicates)


def parse_json(content: bytes):
    """Parse strict JSON without accepting duplicate keys or non-finite numbers."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON object key.")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("Non-finite JSON number.")

    return json.loads(content, object_pairs_hook=pairs, parse_constant=invalid_constant)


def load_json(content: bytes) -> Normalization:
    envelope = Envelope.model_validate(parse_json(content))
    return normalize(envelope, hashlib.sha256(content).hexdigest())
