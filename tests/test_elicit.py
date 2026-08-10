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


def test_draft_schema_sees_profile_layers_and_distinctness_rule():
    from src.labeling.profile2 import ConceptDef, CourseProfileV2
    captured = {}

    def gen(prompt, response_model):
        captured["prompt"] = prompt
        return DraftedLabels(labels=[LabelDef(
            name="x", kind="other", description="d",
            positive_criteria="p", negative_criteria="n")])

    v2 = CourseProfileV2(
        base=PROFILE,
        concepts=[ConceptDef(name="loops", description="d", promoted=True,
                             positive_criteria="pc", negative_criteria="nc")],
        affect_labels=[LabelDef(name="frustration", kind="behavioral",
                                description="fd", positive_criteria="fp",
                                negative_criteria="fn")],
        intent_labels=[], explored_on="2026-08-07",
        corpus_sample={"conversations": 1, "seed": 0},
        materials_provided=False, repo_sha="x", accepted=True)
    draft_schema("intent", PROFILE, gen, profile2=v2)
    p = captured["prompt"]
    assert "frustration" in p and "fd" in p     # covered layer shown
    assert "loops" in p                          # promoted concept shown
    assert "do NOT draft duplicates" in p
    assert "mutually distinct" in p

    draft_schema("intent", PROFILE, gen)         # no profile: block absent
    assert "frustration" not in captured["prompt"]
    assert "mutually distinct" in captured["prompt"]


def test_draft_schema_reprompts_once_then_fails_on_fat_criteria():
    import pytest

    from src.labeling.elicit import DraftedLabels, draft_schema
    from src.labeling.schema import CRITERIA_WORD_CAP, LabelDef

    fat = LabelDef(name="fat", kind="behavioral", description="d",
                   positive_criteria=" ".join(["w"] * (CRITERIA_WORD_CAP + 5)),
                   negative_criteria="n")
    calls = []

    def gen(prompt, response_model):
        calls.append(prompt)
        return DraftedLabels(labels=[fat])

    with pytest.raises(ValueError, match="brevity caps"):
        draft_schema("intent", PROFILE, gen)
    assert len(calls) == 2                      # one retry, then hard fail
    assert "broke the brevity caps" in calls[1]


def test_draft_schema_accepts_tight_criteria_first_try():
    from src.labeling.elicit import DraftedLabels, draft_schema
    from src.labeling.schema import LabelDef

    tight = LabelDef(name="tight", kind="behavioral", description="short",
                     positive_criteria="short", negative_criteria="short")
    calls = []

    def gen(prompt, response_model):
        calls.append(prompt)
        assert "BREVITY IS A HARD REQUIREMENT" in prompt
        return DraftedLabels(labels=[tight])

    schema = draft_schema("intent", PROFILE, gen)
    assert len(calls) == 1
    assert schema.labels[0].name == "tight"
