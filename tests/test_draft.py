from src.labeling.draft import (CLASSIFY_PROMPT, LabelVerdict, LabelVerdicts, MessageLabels,
                                classifier_hash, draft_labels)
from src.labeling.elicit import draft_schema
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelDef
import tests.test_elicit as te
from tests.test_cli import make_fake_generate
from tests.test_sampler import CONVS


def _msg(i: int) -> SampledMessage:
    return SampledMessage(chatlog_id=100 + i, conv_id="c", message_index=i,
                          text=f"invented question {i}", context_before=None,
                          context_after="try a hint", stratum="short/early")


def fake_generate(prompt: str, response_model):
    assert response_model is LabelVerdicts
    fake_generate.prompts.append(prompt)
    return LabelVerdicts(verdicts=[LabelVerdict(
        label="concept-confusion", applies=True,
        rationale="mentions not understanding",
    )])


fake_generate.prompts = []


def _schema():
    return draft_schema("who is confused", te.fake_generate)


def test_draft_labels_one_result_per_message():
    fake_generate.prompts = []
    results = draft_labels([_msg(0), _msg(1)], _schema(), fake_generate)
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
    results = draft_labels([_msg(0)], _schema(), fake_generate_stray_and_missing)
    assert len(results) == 1
    r = results[0]
    assert "extra-label" not in r.labels
    assert "extra-label" not in r.rationales
    assert r.labels == {"concept-confusion": False}
    assert r.rationales == {"concept-confusion": "(no verdict returned)"}


def test_classifier_hash_pins_schema_and_model():
    s = _schema()
    h = classifier_hash(s, "gemini-2.5-flash")
    assert len(h) == 12
    assert h != classifier_hash(s, "gemini-3.0")
    revised = draft_schema("who is angry", te.fake_generate)
    assert h != classifier_hash(revised, "gemini-2.5-flash")


def test_draft_labels_calls_on_result_per_message():
    gen = make_fake_generate()
    schema = draft_schema("intent", gen)
    sample = stratified_sample(CONVS, n=4, seed=0)
    seen: list[tuple[int, int]] = []
    results = draft_labels(
        sample, schema, gen,
        on_result=lambda m, r: seen.append((m.chatlog_id, m.message_index)))
    assert seen == [(m.chatlog_id, m.message_index) for m in sample]
    assert len(results) == 4
