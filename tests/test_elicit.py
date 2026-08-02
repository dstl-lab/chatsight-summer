from src.labeling.elicit import DraftedLabels, draft_schema, revise_schema
from src.labeling.schema import LabelDef


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
    s = draft_schema("show me who is confused", fake_generate)
    assert s.instructor_intent == "show me who is confused"
    assert s.labels == FAKE_LABELS
    assert s.parent_version is None
    assert "show me who is confused" in fake_generate.last_prompt


def test_revise_schema_chains_lineage_and_carries_feedback():
    parent = draft_schema("show me who is confused", fake_generate)
    child = revise_schema(parent, "also split out anger", fake_generate)
    assert child.parent_version == parent.version_id
    assert child.feedback_applied == "also split out anger"
    assert "also split out anger" in fake_generate.last_prompt
    assert parent.labels[0].name in fake_generate.last_prompt
