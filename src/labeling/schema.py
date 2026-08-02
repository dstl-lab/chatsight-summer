"""Label schemas. Every instructor tweak creates a new content-hashed version
chained via parent_version (CLAUDE.md invariant 6)."""
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class LabelDef(BaseModel):
    name: str
    kind: Literal["conceptual", "behavioral", "other"]
    description: str
    positive_criteria: str
    negative_criteria: str


class LabelSchema(BaseModel):
    instructor_intent: str
    labels: list[LabelDef]
    parent_version: str | None = None
    feedback_applied: str | None = None

    @property
    def version_id(self) -> str:
        canonical = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _schemas_dir(data_dir: Path) -> Path:
    d = data_dir / "labeling" / "schemas"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_schema(schema: LabelSchema, data_dir: Path) -> Path:
    path = _schemas_dir(data_dir) / f"{schema.version_id}.json"
    path.write_text(schema.model_dump_json(indent=2))
    return path


def load_schema(version_id: str, data_dir: Path) -> LabelSchema:
    path = _schemas_dir(data_dir) / f"{version_id}.json"
    return LabelSchema.model_validate_json(path.read_text())
