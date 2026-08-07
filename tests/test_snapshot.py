import json
from pathlib import Path

from src.labeling.course import CourseProfile
from src.labeling.draft import MessageLabels, classifier_hash
from src.labeling.elicit import draft_schema
from src.labeling.snapshot import emit_snapshot
import tests.test_elicit as te
from tests.test_sampler import _conv


PROFILE = CourseProfile(
    course_name="Test 101",
    domain_description="test course for unit testing",
    tooling="test tooling",
    paste_conventions="test paste conventions",
    reference_conventions="test reference conventions",
    message_shape_notes="test message shape notes",
)


def _fixtures():
    convs = [_conv("a", 2), _conv("b", 1)]
    schema = draft_schema("who is confused", PROFILE, te.fake_generate)
    labels = [MessageLabels(chatlog_id=convs[0].chatlog_id, message_index=0,
                            labels={"concept-confusion": True},
                            rationales={"concept-confusion": "invented"})]
    return convs, schema, labels


def test_emit_snapshot_writes_manifest_and_rows(tmp_path: Path):
    convs, schema, labels = _fixtures()
    path = emit_snapshot(convs, labels, schema, model="gemini-2.5-flash",
                         repo_sha="abc1234", data_dir=tmp_path,
                         excluded_conversations=17, profile=PROFILE)
    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["schema_version"] == schema.version_id
    assert manifest["classifier_hash"] == classifier_hash(schema, "gemini-2.5-flash", PROFILE)
    assert manifest["repo_sha"] == "abc1234"
    assert manifest["row_counts"] == {
        "conversations": 2, "turns": 6, "label_applications": 1}
    assert manifest["excluded_conversations"] == 17
    assert manifest["profile_id"] == PROFILE.profile_id
    assert manifest["course_profile"]["course_name"] == "Test 101"
    assert len((path / "conversations.jsonl").read_text().splitlines()) == 2
    assert len((path / "labels.jsonl").read_text().splitlines()) == 1


def test_snapshot_collision_gets_unique_dir_not_overwrite(tmp_path: Path):
    convs, schema, labels = _fixtures()
    first = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                          data_dir=tmp_path, excluded_conversations=0, profile=PROFILE)
    second = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                           data_dir=tmp_path, excluded_conversations=0, profile=PROFILE)
    third = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                          data_dir=tmp_path, excluded_conversations=0, profile=PROFILE)
    assert first != second != third
    assert second.name == first.name + "-2"
    assert third.name == first.name + "-3"
    # first snapshot untouched (immutability), and every manifest's
    # snapshot_id matches its directory name
    for path in (first, second, third):
        manifest = json.loads((path / "manifest.json").read_text())
        assert manifest["snapshot_id"] == path.name


def test_mid_write_failure_leaves_no_final_dir(tmp_path: Path, monkeypatch):
    """A crash partway through writing must not leave a manifest-less
    orphan under data/snapshots/<id> — that dir is authoritative provenance
    (rule 3) and a retry must not treat the orphan as taken (it shouldn't
    exist at all, and a retry gets the same id back, not a -2 sibling)."""
    import src.labeling.schema as schema_mod

    convs, schema, labels = _fixtures()

    real_dumps = schema_mod.LabelSchema.model_dump_json

    def boom(self, *args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(schema_mod.LabelSchema, "model_dump_json", boom)
    try:
        emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                      data_dir=tmp_path, excluded_conversations=0, profile=PROFILE)
        raise AssertionError("expected emit_snapshot to raise")
    except RuntimeError as e:
        assert "disk full" in str(e)

    snapshots_dir = tmp_path / "snapshots"
    remaining = list(snapshots_dir.iterdir()) if snapshots_dir.exists() else []
    assert remaining == []

    monkeypatch.setattr(schema_mod.LabelSchema, "model_dump_json", real_dumps)
    retried = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                            data_dir=tmp_path, excluded_conversations=0, profile=PROFILE)
    # retry lands on the same id, not a -2 collision sibling, since the
    # failed attempt left nothing behind under the final name
    base_id = retried.name
    assert not base_id.endswith("-2")
    assert (retried / "manifest.json").exists()
