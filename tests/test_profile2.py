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
