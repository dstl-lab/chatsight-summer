"""CourseProfile: pinned course-context input to the classifier
(2026-08-06 memo, 'Generalization beyond DSC 10')."""
from src.labeling.course import DSC10_PROFILE, CourseProfile


def _profile(**overrides) -> CourseProfile:
    base = dict(
        course_name="CSE 99", domain_description="intro C++ course",
        tooling="g++, gradescope autograder",
        paste_conventions="students paste compiler errors and segfault output",
        reference_conventions="students reference problems as 'PA3 part 2'",
        message_shape_notes="most messages are short",
    )
    base.update(overrides)
    return CourseProfile(**base)


def test_profile_id_is_stable_and_content_sensitive():
    a, b = _profile(), _profile()
    assert a.profile_id == b.profile_id
    assert len(a.profile_id) == 12
    assert a.profile_id != _profile(tooling="clang").profile_id


def test_render_context_contains_every_field():
    p = _profile()
    text = p.render_context()
    for value in p.model_dump().values():
        assert value in text


def test_dsc10_profile_mentions_course_and_tooling():
    text = DSC10_PROFILE.render_context()
    assert "DSC 10" in text
    assert "babypandas" in text
