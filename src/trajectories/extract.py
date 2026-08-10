"""Extract label-space trajectories from immutable snapshots.

Phase 2 consumes snapshots only, never the live DB. The output intentionally
omits student text and model rationales: trajectories are ordered label states
plus provenance, not another copy of IRB-covered conversations.
"""
import argparse
import json
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels
from src.labeling.schema import LabelSchema

Key = tuple[int, int]


def load_snapshot(snapshot_dir: Path) -> tuple[
    list[Conversation], list[MessageLabels], LabelSchema, dict
]:
    snapshot_dir = Path(snapshot_dir)
    conversations = [
        Conversation.model_validate_json(line)
        for line in (snapshot_dir / "conversations.jsonl").open()
    ]
    labels = [
        MessageLabels.model_validate_json(line)
        for line in (snapshot_dir / "labels.jsonl").open()
    ]
    schema = LabelSchema.model_validate_json(
        (snapshot_dir / "schema.json").read_text())
    manifest_path = snapshot_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) \
        if manifest_path.exists() else {}
    return conversations, labels, schema, manifest


def _snapshot_metadata(snapshot_dir: Path, schema: LabelSchema,
                       manifest: dict) -> dict:
    return {
        "snapshot_id": manifest.get("snapshot_id", snapshot_dir.name),
        "schema_version": manifest.get("schema_version", schema.version_id),
        "classifier_hash": manifest.get("classifier_hash"),
        "repo_sha": manifest.get("repo_sha"),
        "source": str(snapshot_dir),
        "label_names": [label.name for label in schema.labels],
    }


def _labels_by_key(labels: list[MessageLabels]) -> dict[Key, MessageLabels]:
    out: dict[Key, MessageLabels] = {}
    for row in labels:
        key = (row.chatlog_id, row.message_index)
        if key in out:
            raise ValueError(f"duplicate label row for key {key!r}")
        out[key] = row
    return out


def _student_keys(conversations: list[Conversation]) -> set[Key]:
    return {
        (conv.chatlog_id, turn.index)
        for conv in conversations
        for turn in conv.turns
        if turn.role == "student"
    }


def _active_labels(row: MessageLabels) -> list[str]:
    return [name for name, value in row.labels.items() if value]


def _step(row: MessageLabels, student_index: int | None) -> dict:
    return {
        "message_index": row.message_index,
        "student_index": student_index,
        "active_labels": _active_labels(row),
        "no_label_fits": row.no_label_fits,
        "move": row.move,
        "latency_seconds": row.latency_seconds,
        "latency_bucket": row.latency_bucket,
        "forms": list(row.forms),
        "concepts": list(row.concepts),
    }


def extract_trajectories(conversations: list[Conversation],
                         labels: list[MessageLabels],
                         metadata: dict) -> dict:
    by_key = _labels_by_key(labels)
    student_keys = _student_keys(conversations)
    missing = sorted(student_keys - set(by_key))
    if missing:
        raise ValueError(
            f"missing labels for {len(missing)} student messages; "
            f"first missing key {missing[0]!r}")
    extra = sorted(set(by_key) - student_keys)
    if extra:
        raise ValueError(
            f"labels contain {len(extra)} keys not found in conversations; "
            f"first extra key {extra[0]!r}")

    trajectories = []
    for conv in conversations:
        steps = []
        for turn in sorted(conv.turns, key=lambda t: t.index):
            if turn.role != "student":
                continue
            row = by_key[(conv.chatlog_id, turn.index)]
            steps.append(_step(row, turn.student_index))
        trajectories.append({
            "conv_id": conv.conv_id,
            "chatlog_id": conv.chatlog_id,
            "notebook": conv.notebook,
            "steps": steps,
        })

    return {
        "metadata": {
            **metadata,
            "row_counts": {
                "conversations": len(conversations),
                "trajectories": len(trajectories),
                "steps": sum(len(t["steps"]) for t in trajectories),
            },
        },
        "trajectories": trajectories,
    }


def build_trajectory_report(snapshot_dir: Path) -> dict:
    snapshot_dir = Path(snapshot_dir)
    conversations, labels, schema, manifest = load_snapshot(snapshot_dir)
    metadata = _snapshot_metadata(snapshot_dir, schema, manifest)
    return extract_trajectories(conversations, labels, metadata)


def default_output_path(snapshot_dir: Path) -> Path:
    snapshot_dir = Path(snapshot_dir)
    return snapshot_dir.parent.parent / "trajectories" / snapshot_dir.name / \
        "trajectories.json"


def write_trajectory_report(report: dict, out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract label-space trajectories from a snapshot")
    parser.add_argument("snapshot_dir")
    parser.add_argument("--out", default=None,
                        help="output JSON path; defaults under data/trajectories")
    args = parser.parse_args()
    snapshot_dir = Path(args.snapshot_dir)
    report = build_trajectory_report(snapshot_dir)
    out = Path(args.out) if args.out else default_output_path(snapshot_dir)
    write_trajectory_report(report, out)
    counts = report["metadata"]["row_counts"]
    print(f"wrote {out} ({counts['trajectories']} trajectories, "
          f"{counts['steps']} steps)")


if __name__ == "__main__":
    main()
