"""Immutable labeled-corpus snapshots (CLAUDE.md rule 3). The simulation
subsystems consume ONLY these, never the DB. After emitting, add a row to
snapshots.md (the CLI reminds the operator)."""
import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.course import CourseProfile
from src.labeling.draft import MessageLabels, classifier_hash
from src.labeling.schema import LabelSchema


def emit_snapshot(conversations: list[Conversation], labels: list[MessageLabels],
                  schema: LabelSchema, model: str, repo_sha: str, data_dir: Path,
                  excluded_conversations: int, profile: CourseProfile,
                  profile2=None) -> Path:
    chash = classifier_hash(schema, model, profile, profile2=profile2)
    base_id = f"{date.today():%Y%m%d}-{schema.version_id}-{chash[:6]}"
    snapshots_dir = data_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snapshot_id, n = base_id, 2
    while (snapshots_dir / snapshot_id).exists():
        snapshot_id = f"{base_id}-{n}"       # never overwrite (rule 3):
        n += 1                               # a collision gets a NEW dir
    final_path = snapshots_dir / snapshot_id

    # Write to a temp dir first and rename into place as the last step, so a
    # mid-write failure never leaves a manifest-less orphan under the final
    # name (rule 3: dirs under snapshots/ are authoritative provenance).
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{snapshot_id}.tmp-", dir=snapshots_dir))
    try:
        with (tmp_dir / "conversations.jsonl").open("w") as f:
            for c in conversations:
                f.write(c.model_dump_json() + "\n")
        with (tmp_dir / "labels.jsonl").open("w") as f:
            for l in labels:
                f.write(l.model_dump_json() + "\n")
        (tmp_dir / "schema.json").write_text(schema.model_dump_json(indent=2))

        manifest = {
            "snapshot_id": snapshot_id,
            "export_date": date.today().isoformat(),
            "repo_sha": repo_sha,
            "schema_version": schema.version_id,
            "classifier_hash": chash,
            "course_profile": profile.model_dump(),
            "profile_id": profile.profile_id,
            # v2 exploration artifact, when one grounded this run
            # (2026-08-07 memo); the artifact itself is git-tracked.
            "profile2_id": (profile2.profile_id
                            if profile2 is not None else None),
            "row_counts": {
                "conversations": len(conversations),
                "turns": sum(len(c.turns) for c in conversations),
                "label_applications": len(labels),
            },
            "excluded_conversations": excluded_conversations,
        }
        (tmp_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        tmp_dir.rename(final_path)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return final_path
