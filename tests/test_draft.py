from src.ingest.rawlog import Turn
from src.labeling.course import CourseProfile
from src.labeling.draft import (CLASSIFY_PROMPT, LabelVerdict, LabelVerdicts, MessageLabels,
                                _render_window, classifier_hash, draft_labels)
from src.labeling.elicit import draft_schema
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelDef, LabelSchema
import tests.test_elicit as te
from tests.test_cli import make_fake_generate
from tests.test_sampler import CONVS

PROFILE = CourseProfile(
    course_name="Test 101", domain_description="a test course",
    tooling="pytest", paste_conventions="students paste tracebacks",
    reference_conventions="by number", message_shape_notes="short")

SCHEMA = LabelSchema(instructor_intent="i", labels=[
    LabelDef(name="asks-help", kind="behavioral", description="d",
             positive_criteria="p", negative_criteria="n")])


def _msg(**kw):
    base = dict(chatlog_id=1, conv_id="c", message_index=2, text="help 1.2",
                context=[Turn(index=0, role="student", text="earlier",
                              student_index=0),
                         Turn(index=1, role="tutor", text="reply")],
                context_after=None, stratum="s")
    base.update(kw)
    return SampledMessage(**base)


def fake_generate(prompt: str, response_model):
    assert response_model is LabelVerdicts
    fake_generate.prompts.append(prompt)
    return LabelVerdicts(verdicts=[LabelVerdict(
        label="concept-confusion", applies=True,
        rationale="mentions not understanding",
    )])


fake_generate.prompts = []


def _schema():
    return draft_schema("who is confused", PROFILE, te.fake_generate)


def _msg_i(i: int) -> SampledMessage:
    return SampledMessage(chatlog_id=100 + i, conv_id="c", message_index=i,
                          text=f"invented question {i}", context=[],
                          context_after="try a hint", stratum="short/early")


def test_draft_labels_one_result_per_message():
    fake_generate.prompts = []
    results = draft_labels([_msg_i(0), _msg_i(1)], _schema(), PROFILE, fake_generate)
    assert [r.message_index for r in results] == [0, 1]
    assert results[0].labels == {"concept-confusion": True}
    assert "invented question 0" in fake_generate.prompts[0]
    assert "concept-confusion" in fake_generate.prompts[0]


def fake_generate_stray_and_missing(prompt: str, response_model):
    assert response_model is LabelVerdicts
    # "concept-confusion" is the only real label in _schema(); this response
    # hallucinates "extra-label" and omits "concept-confusion" entirely.
    return LabelVerdicts(verdicts=[LabelVerdict(
        label="extra-label", applies=True, rationale="hallucinated",
    )])


def test_draft_labels_filters_stray_keys_and_defaults_missing():
    results = draft_labels([_msg_i(0)], _schema(), PROFILE, fake_generate_stray_and_missing)
    assert len(results) == 1
    r = results[0]
    assert "extra-label" not in r.labels
    assert "extra-label" not in r.rationales
    assert r.labels == {"concept-confusion": False}
    assert r.rationales == {"concept-confusion": "(no verdict returned)"}


def test_classifier_hash_pins_schema_and_model():
    s = _schema()
    h = classifier_hash(s, "gemini-2.5-flash", PROFILE)
    assert len(h) == 12
    assert h != classifier_hash(s, "gemini-3.0", PROFILE)
    revised = draft_schema("who is angry", PROFILE, te.fake_generate)
    assert h != classifier_hash(revised, "gemini-2.5-flash", PROFILE)


def test_draft_labels_calls_on_result_per_message():
    gen = make_fake_generate()
    schema = draft_schema("intent", PROFILE, gen)
    sample = stratified_sample(CONVS, n=4, seed=0)
    seen: list[tuple[int, int]] = []
    results = draft_labels(
        sample, schema, PROFILE, gen,
        on_result=lambda m, r: seen.append((m.chatlog_id, m.message_index)))
    assert seen == [(m.chatlog_id, m.message_index) for m in sample]
    assert len(results) == 4


def test_prompt_carries_course_context_and_window():
    captured = {}

    def fake_generate(prompt, response_model):
        captured["prompt"] = prompt
        return LabelVerdicts(verdicts=[LabelVerdict(
            label="asks-help", applies=True, rationale="r")],
            no_label_fits=False)

    draft_labels([_msg()], SCHEMA, PROFILE, fake_generate)
    p = captured["prompt"]
    assert "Test 101" in p
    assert "student: earlier" in p and "tutor: reply" in p
    assert p.index("student: earlier") < p.index("STUDENT MESSAGE TO LABEL")


def test_abstention_flag_lands_on_message_labels():
    def fake_generate(prompt, response_model):
        return LabelVerdicts(verdicts=[], no_label_fits=True)

    out = draft_labels([_msg()], SCHEMA, PROFILE, fake_generate)
    assert out[0].no_label_fits is True
    assert out[0].labels == {"asks-help": False}


def test_render_window_empty():
    assert _render_window([]) == "(conversation start)"


def test_hash_covers_profile_and_window():
    h1 = classifier_hash(SCHEMA, "m", PROFILE)
    h2 = classifier_hash(SCHEMA, "m",
                         PROFILE.model_copy(update={"tooling": "other"}))
    assert h1 != h2


def test_classifier_hash_golden_regression():
    # Golden value computed once from the current CLASSIFY_PROMPT,
    # CourseProfile.canonical()/render_context(), and _render_window's
    # sentinel/format. ANY intentional change to the prompt template, the
    # rendered course context wording, or the window rendering (sentinel
    # text or "role: text" line format) must update this literal — that
    # update, and only that update, is the point of this test.
    h = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h == "2877d889c7a0"
