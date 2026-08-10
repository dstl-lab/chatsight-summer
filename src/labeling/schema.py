"""Label schemas. Every instructor tweak creates a new content-hashed version
chained via parent_version (CLAUDE.md invariant 6)."""
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


# Brevity caps (2026-08-10 blind-audit finding: verbose criteria corrupt
# the human side of measurement — all four zero-support labels carried
# 39-62-word criteria; a <=25-word rewrite recovered every one). Criteria
# ship at or under these caps or they don't ship.
DESC_WORD_CAP = 20
CRITERIA_WORD_CAP = 25


def oversized_fields(labels: list["LabelDef"]) -> list[str]:
    """One finding per field over its cap, '<label>.<field> (<n>w)'.
    Empty list means every description/criterion is annotator-sized."""
    out = []
    for l in labels:
        for field, cap in (("description", DESC_WORD_CAP),
                           ("positive_criteria", CRITERIA_WORD_CAP),
                           ("negative_criteria", CRITERIA_WORD_CAP)):
            n = len(getattr(l, field).split())
            if n > cap:
                out.append(f"{l.name}.{field} ({n}w > {cap}w)")
    return out


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
