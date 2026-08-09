import src.labeling.cli as cli_mod
from src.labeling.cli import run_loop
from src.labeling.course import DSC10_PROFILE
from src.labeling.draft import CoverageVerdict, SingleLabelVerdict
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
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        if response_model is CoverageVerdict:
            return CoverageVerdict(no_label_fits=False, note="")
        from src.labeling.explore import ExplorationDraft
        if response_model is ExplorationDraft:
            from src.labeling.course import DSC10_PROFILE
            from src.labeling.profile2 import ConceptDef
            from src.labeling.schema import LabelDef
            base = DSC10_PROFILE.model_dump()
            return ExplorationDraft(
                **{k: base[k] for k in ("course_name", "domain_description",
                                        "tooling", "paste_conventions",
                                        "reference_conventions",
                                        "message_shape_notes")},
                concepts=[ConceptDef(name="groupby", description="d"),
                          ConceptDef(name="loops", description="d")],
                affect_labels=[LabelDef(name="frustrated", kind="behavioral",
                                        description="d", positive_criteria="p",
                                        negative_criteria="n")],
                intent_labels=[LabelDef(name="wants-hint", kind="behavioral",
                                        description="d", positive_criteria="p",
                                        negative_criteria="n")])
    fake_generate.schema_calls = 0
    return fake_generate


def test_accept_returns_first_schema():
    answers = iter(["accept"])
    schema = run_loop("intent", CONVS, make_fake_generate(),
                      profile=DSC10_PROFILE, sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lambda _: None)
    assert schema is not None
    assert schema.labels[0].name == "label-v1"
    assert schema.parent_version is None


def test_tweak_then_accept_chains_versions():
    answers = iter(["tweak", "split confusion by cause", "accept"])
    schema = run_loop("intent", CONVS, make_fake_generate(),
                      profile=DSC10_PROFILE, sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lambda _: None)
    assert schema.labels[0].name == "label-v2"
    assert schema.parent_version is not None
    assert schema.feedback_applied == "split confusion by cause"


def test_quit_returns_none_and_renders_sample():
    lines: list[str] = []
    answers = iter(["quit"])
    result = run_loop("intent", CONVS, make_fake_generate(),
                      profile=DSC10_PROFILE, sample_size=4,
                      seed=6, ask=lambda _: next(answers), say=lines.append)
    assert result is None
    joined = "\n".join(lines)
    assert "label-v1" in joined          # schema shown
    assert "q0" in joined                # sampled message text shown


def make_no_coverage_fake_generate():
    # every message "shows an act no label captures" (mass-label coverage
    # branch) so the CLI's coverage summary line is exercised for all rows.
    def fake_generate(prompt: str, response_model):
        if response_model is DraftedLabels:
            return DraftedLabels(labels=[_label("label-v1")])
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        if response_model is CoverageVerdict:
            return CoverageVerdict(no_label_fits=True, note="uncaptured act")
    return fake_generate


def test_mass_label_prints_coverage_summary(monkeypatch, capsys):
    monkeypatch.setenv("EXT_DB_URL", "postgresql://x/y")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(cli_mod, "fetch_conversations",
                        lambda url, limit=None, **kw: CONVS)
    monkeypatch.setattr(cli_mod, "count_conversations", lambda url: len(CONVS))
    monkeypatch.setattr(cli_mod, "make_generate",
                        lambda api_key, **kw: make_no_coverage_fake_generate())
    monkeypatch.setattr(cli_mod, "save_schema", lambda schema, data_dir: None)
    monkeypatch.setattr(cli_mod, "emit_snapshot",
                        lambda *a, **kw: "unused/snapshot/path")
    monkeypatch.setattr("builtins.input", lambda *_: "accept")
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--intent", "test intent", "--max-conversations", "6",
         "--sample-size", "4", "--seed", "0"])

    cli_mod.main()

    assert "showed acts no label captures" in capsys.readouterr().out
