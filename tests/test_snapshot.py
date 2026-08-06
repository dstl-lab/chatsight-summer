import json
from pathlib import Path

import pytest

from src.labeling.draft import MessageLabels, classifier_hash
from src.labeling.elicit import draft_schema
from src.labeling.snapshot import emit_snapshot
import tests.test_elicit as te
from tests.test_sampler import _conv


def _fixtures():
    convs = [_conv("a", 2), _conv("b", 1)]
    schema = draft_schema("who is confused", te.fake_generate)
    labels = [MessageLabels(chatlog_id=convs[0].chatlog_id, message_index=0,
                            labels={"concept-confusion": True},
                            rationales={"concept-confusion": "invented"})]
    return convs, schema, labels


def test_emit_snapshot_writes_manifest_and_rows(tmp_path: Path):
    convs, schema, labels = _fixtures()
    path = emit_snapshot(convs, labels, schema, model="gemini-2.5-flash",
                         repo_sha="abc1234", data_dir=tmp_path,
                         excluded_conversations=17)
    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["schema_version"] == schema.version_id
    assert manifest["classifier_hash"] == classifier_hash(schema, "gemini-2.5-flash")
    assert manifest["repo_sha"] == "abc1234"
    assert manifest["row_counts"] == {
        "conversations": 2, "turns": 6, "label_applications": 1}
    assert manifest["excluded_conversations"] == 17
    assert len((path / "conversations.jsonl").read_text().splitlines()) == 2
    assert len((path / "labels.jsonl").read_text().splitlines()) == 1


def test_snapshot_collision_gets_unique_dir_not_overwrite(tmp_path: Path):
    convs, schema, labels = _fixtures()
    first = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                          data_dir=tmp_path, excluded_conversations=0)
    second = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                           data_dir=tmp_path, excluded_conversations=0)
    third = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                          data_dir=tmp_path, excluded_conversations=0)
    assert first != second != third
    assert second.name == first.name + "-2"
    assert third.name == first.name + "-3"
    # first snapshot untouched (immutability), and every manifest's
    # snapshot_id matches its directory name
    for path in (first, second, third):
        manifest = json.loads((path / "manifest.json").read_text())
        assert manifest["snapshot_id"] == path.name
