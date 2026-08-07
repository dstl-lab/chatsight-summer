from src.labeling.course import CourseProfile
from src.labeling.elicit import DraftedLabels, draft_schema, revise_schema
from src.labeling.schema import LabelDef


PROFILE = CourseProfile(
    course_name="Test 101", domain_description="a test course",
    tooling="pytest", paste_conventions="students paste tracebacks",
    reference_conventions="by number", message_shape_notes="short")


FAKE_LABELS = [LabelDef(
    name="concept-confusion", kind="behavioral",
    description="student is confused about a course concept",
    positive_criteria="expresses not understanding a concept",
    negative_criteria="logistics or syntax-only questions",
)]


def fake_generate(prompt: str, response_model):
    assert response_model is DraftedLabels
    fake_generate.last_prompt = prompt
    return DraftedLabels(labels=FAKE_LABELS)


def test_draft_schema_wraps_llm_labels_with_intent():
    s = draft_schema("show me who is confused", PROFILE, fake_generate)
    assert s.instructor_intent == "show me who is confused"
    assert s.labels == FAKE_LABELS
    assert s.parent_version is None
    assert "show me who is confused" in fake_generate.last_prompt


def test_revise_schema_chains_lineage_and_carries_feedback():
    parent = draft_schema("show me who is confused", PROFILE, fake_generate)
    child = revise_schema(parent, "also split out anger", PROFILE, fake_generate)
    assert child.parent_version == parent.version_id
    assert child.feedback_applied == "also split out anger"
    assert "also split out anger" in fake_generate.last_prompt
    assert parent.labels[0].name in fake_generate.last_prompt


def test_elicit_prompt_carries_course_context_and_judgeability():
    captured = {}

    def fake_generate(prompt, response_model):
        captured["prompt"] = prompt
        return DraftedLabels(labels=[LabelDef(
            name="x", kind="other", description="d",
            positive_criteria="p", negative_criteria="n")])

    draft_schema("intent", PROFILE, fake_generate)
    assert "Test 101" in captured["prompt"]
    assert "judgeable on messages as they actually occur" in captured["prompt"]
