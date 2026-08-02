"""Immutable labeled-corpus snapshots (CLAUDE.md rule 3). The simulation
subsystems consume ONLY these, never the DB. After emitting, add a row to
snapshots.md (the CLI reminds the operator)."""
import json
from datetime import date
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels, classifier_hash
from src.labeling.schema import LabelSchema


def emit_snapshot(conversations: list[Conversation], labels: list[MessageLabels],
                  schema: LabelSchema, model: str, repo_sha: str, data_dir: Path,
                  excluded_conversations: int) -> Path:
    chash = classifier_hash(schema, model)
    snapshot_id = f"{date.today():%Y%m%d}-{schema.version_id}-{chash[:6]}"
    path = data_dir / "snapshots" / snapshot_id
    path.mkdir(parents=True, exist_ok=False)  # immutability: never overwrite

    with (path / "conversations.jsonl").open("w") as f:
        for c in conversations:
            f.write(c.model_dump_json() + "\n")
    with (path / "labels.jsonl").open("w") as f:
        for l in labels:
            f.write(l.model_dump_json() + "\n")
    (path / "schema.json").write_text(schema.model_dump_json(indent=2))

    manifest = {
        "snapshot_id": snapshot_id,
        "export_date": date.today().isoformat(),
        "repo_sha": repo_sha,
        "schema_version": schema.version_id,
        "classifier_hash": chash,
        "row_counts": {
            "conversations": len(conversations),
            "turns": sum(len(c.turns) for c in conversations),
            "label_applications": len(labels),
        },
        "excluded_conversations": excluded_conversations,
    }
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return path
