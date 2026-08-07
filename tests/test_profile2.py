import pytest

from src.ingest.rawlog import Conversation, Turn
from src.labeling.course import CourseProfile
from src.labeling.profile2 import (ConceptDef, CourseProfileV2, lint_profile,
                                   load_profile, save_profile)

V1 = CourseProfile(
    course_name="Test 101", domain_description="a test course",
    tooling="pytest", paste_conventions="students paste tracebacks",
    reference_conventions="by number", message_shape_notes="short")


def _v2(**kw):
    base = dict(
        base=V1,
        concepts=[ConceptDef(name="loops",
                             description="iteration with for and while")],
        affect_labels=[], intent_labels=[],
        explored_on="2026-08-07",
        corpus_sample={"conversations": 10, "seed": 0},
        materials_provided=False, repo_sha="abc1234")
    base.update(kw)
    return CourseProfileV2(**base)


def _conv(texts):
    turns = [Turn(index=i, role="student", text=t, student_index=i)
             for i, t in enumerate(texts)]
    return Conversation(conv_id="c", chatlog_id=1, notebook=None,
                        started_at=None, turns=turns)


def test_round_trip_and_stable_id(tmp_path):
    v2 = _v2()
    p = save_profile(v2, tmp_path / "t101.json")
    loaded = load_profile(p)
    assert loaded == v2
    assert len(v2.profile_id) == 12
    assert v2.profile_id == loaded.profile_id
    assert v2.profile_id != _v2(materials_provided=True).profile_id


def test_promoted_requires_criteria():
    with pytest.raises(ValueError):
        ConceptDef(name="loops", description="d", promoted=True)
    ok = ConceptDef(name="loops", description="d", promoted=True,
                    positive_criteria="p", negative_criteria="n")
    assert ok.promoted


def test_render_context_carries_v1_and_concepts():
    ctx = _v2().render_context()
    assert "Test 101" in ctx
    assert "students paste tracebacks" in ctx
    assert "loops" in ctx


def test_lint_catches_verbatim_run():
    turn = ("my homework question three is about how while loops "
            "terminate when the condition changes")
    convs = [_conv([turn])]
    bad = _v2(concepts=[ConceptDef(
        name="loops",
        description=("students ask how while loops terminate when the "
                     "condition changes during class"))])
    findings = lint_profile(bad, convs)
    assert findings, "8-word verbatim run must be flagged"
    good = _v2(concepts=[ConceptDef(
        name="loops", description="loop termination conditions")])
    assert lint_profile(good, convs) == []


def test_accepted_defaults_false():
    assert _v2().accepted is False


def _instructor_schema():
    from src.labeling.schema import LabelDef, LabelSchema
    return LabelSchema(instructor_intent="who is confused", labels=[
        LabelDef(name="asks-help", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n")])


def test_compose_schema_layers_and_chains():
    from src.labeling.schema import LabelDef
    from src.labeling.profile2 import compose_schema
    v2 = _v2(
        concepts=[ConceptDef(name="loops", description="d"),
                  ConceptDef(name="recursion", description="d",
                             promoted=True, positive_criteria="p",
                             negative_criteria="n")],
        affect_labels=[LabelDef(name="frustrated", kind="behavioral",
                                description="d", positive_criteria="p",
                                negative_criteria="n")],
        accepted=True)
    base = _instructor_schema()
    composed = compose_schema(v2, base)
    names = [l.name for l in composed.labels]
    # instructor labels first, then promoted concepts, then layers;
    # non-promoted concepts are a facet, not labels
    assert names == ["asks-help", "recursion", "frustrated"]
    kinds = {l.name: l.kind for l in composed.labels}
    assert kinds["recursion"] == "conceptual"
    assert kinds["frustrated"] == "behavioral"
    assert composed.parent_version == base.version_id
    assert v2.profile_id in (composed.feedback_applied or "")


def test_compose_schema_collision_raises():
    from src.labeling.schema import LabelDef
    from src.labeling.profile2 import compose_schema
    v2 = _v2(affect_labels=[LabelDef(
        name="asks-help", kind="behavioral", description="d",
        positive_criteria="p", negative_criteria="n")], accepted=True)
    with pytest.raises(ValueError, match="asks-help"):
        compose_schema(v2, _instructor_schema())


def test_compose_schema_requires_accepted():
    with pytest.raises(ValueError, match="accepted"):
        from src.labeling.profile2 import compose_schema
        compose_schema(_v2(), _instructor_schema())


def test_cli_refuses_unaccepted_profile(tmp_path):
    from src.labeling.cli import load_accepted_profile
    p = save_profile(_v2(), tmp_path / "draft.json")
    with pytest.raises(SystemExit, match="accepted: false"):
        load_accepted_profile(str(p))
    ok = save_profile(_v2(accepted=True), tmp_path / "ok.json")
    assert load_accepted_profile(str(ok)).accepted is True


def test_snapshot_manifest_records_profile2(tmp_path):
    import json
    from src.labeling.draft import classifier_hash
    from src.labeling.snapshot import emit_snapshot
    v2 = _v2(accepted=True)
    schema = _instructor_schema()
    path = emit_snapshot([], [], schema, model="m", repo_sha="x",
                         data_dir=tmp_path, excluded_conversations=0,
                         profile=V1, profile2=v2)
    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["profile2_id"] == v2.profile_id
    assert manifest["classifier_hash"] == classifier_hash(
        schema, "m", V1, profile2=v2)
    path1 = emit_snapshot([], [], schema, model="m", repo_sha="x",
                          data_dir=tmp_path, excluded_conversations=0,
                          profile=V1)
    manifest1 = json.loads((path1 / "manifest.json").read_text())
    assert manifest1["profile2_id"] is None
    assert manifest1["classifier_hash"] != manifest["classifier_hash"]
