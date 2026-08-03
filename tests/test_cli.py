from src.labeling.cli import run_loop
from src.labeling.draft import LabelVerdict, LabelVerdicts
from src.labeling.elicit import DraftedLabels
from src.labeling.schema import LabelDef
from tests.test_sampler import CONVS


def _label(name: str) -> LabelDef:
    return LabelDef(name=name, kind="behavioral", description="d",
                    positive_criteria="p", negative_criteria="n")


def make_fake_generate():
    def fake_generate(prompt: str, response_model):
        if response_model is DraftedLabels:
            fake_generate.schema_calls += 1
            name = f"label-v{fake_generate.schema_calls}"
            return DraftedLabels(labels=[_label(name)])
        return LabelVerdicts(verdicts=[
            LabelVerdict(label="x", applies=True, rationale="r")])
    fake_generate.schema_calls = 0
    return fake_generate


def test_accept_returns_first_schema():
    answers = iter(["accept"])
    schema = run_loop("intent", CONVS, make_fake_generate(), sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lambda _: None)
    assert schema is not None
    assert schema.labels[0].name == "label-v1"
    assert schema.parent_version is None


def test_tweak_then_accept_chains_versions():
    answers = iter(["tweak", "split confusion by cause", "accept"])
    schema = run_loop("intent", CONVS, make_fake_generate(), sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lambda _: None)
    assert schema.labels[0].name == "label-v2"
    assert schema.parent_version is not None
    assert schema.feedback_applied == "split confusion by cause"


def test_quit_returns_none_and_renders_sample():
    lines: list[str] = []
    answers = iter(["quit"])
    result = run_loop("intent", CONVS, make_fake_generate(), sample_size=4,
                      seed=6, ask=lambda _: next(answers), say=lines.append)
    assert result is None
    joined = "\n".join(lines)
    assert "label-v1" in joined          # schema shown
    assert "q0" in joined                # sampled message text shown
