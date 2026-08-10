import json
from pathlib import Path

from src.eval.audit_server import build_payload
from src.ingest.rawlog import Conversation, Turn
from src.labeling.draft import MessageLabels
from src.labeling.schema import LabelDef, LabelSchema


def _snapshot(tmp_path: Path) -> Path:
    turns = []
    for i in range(30):
        turns.append(Turn(index=2 * i, role="student",
                          text=f"invented q{i}", student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"a{i}"))
    conv = Conversation(conv_id="c", chatlog_id=1, notebook=None,
                        started_at=None, turns=turns)
    schema = LabelSchema(instructor_intent="i", labels=[
        LabelDef(name="x", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n"),
        LabelDef(name="y", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n")])
    rows = [MessageLabels(chatlog_id=1, message_index=2 * i,
                          labels={"x": i < 5, "y": False},
                          rationales={"x": "r", "y": "r"},
                          no_label_fits=(i == 6))
            for i in range(30)]
    d = tmp_path / "snap"
    d.mkdir()
    (d / "conversations.jsonl").write_text(conv.model_dump_json() + "\n")
    (d / "schema.json").write_text(schema.model_dump_json())
    (d / "labels.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in rows))
    return d


def test_per_label_payload_is_blind_and_sized(tmp_path):
    snap = _snapshot(tmp_path)
    payload, strata = build_payload(snap, n=25, seed=0, n_per_label=8)
    assert [len(l["keys"]) for l in payload["labels"]] == [8, 8]
    # strata never enter the page payload (invariant 8)
    assert "strata" not in payload
    assert "model-positive" not in json.dumps(payload)
    # ...but are recorded per label for scoring
    assert "model-positive" in json.dumps(strata["x"])
    # no nofit pass in the payload: no_label_fits is derived at submit
    # time (all judged labels "no"), never asked
    assert "nofit_keys" not in payload
    union = {k for l in payload["labels"] for k in l["keys"]}
    assert set(payload["msgs"]) == union


def test_label_subset_and_legacy_mode(tmp_path):
    snap = _snapshot(tmp_path)
    payload, _ = build_payload(snap, n=25, seed=0, n_per_label=6,
                               only_labels=["x"])
    assert [l["name"] for l in payload["labels"]] == ["x"]
    legacy, strata = build_payload(snap, n=10, seed=0)
    assert [len(l["keys"]) for l in legacy["labels"]] == [10, 10]
    assert "_message" in strata


def test_page_autosaves_and_resumes():
    from src.eval.audit_server import PAGE
    assert '"/draft"' in PAGE          # every answer POSTs a draft
    assert "D.draft" in PAGE           # reload restores answers + position


def test_reveal_gated_and_payload_still_blind():
    from src.eval.audit_server import PAGE
    # reveal fetched only after save; payload itself never carries verdicts
    assert '"/reveal"' in PAGE
    assert "showReveal" in PAGE


def test_evidence_field_on_message_labels():
    from src.labeling.draft import MessageLabels
    r = MessageLabels(chatlog_id=1, message_index=0, labels={"x": True},
                      rationales={"x": "r"}, evidence={"x": "span"})
    assert r.evidence["x"] == "span"
    legacy = MessageLabels(chatlog_id=1, message_index=0,
                           labels={}, rationales={})
    assert legacy.evidence == {}
