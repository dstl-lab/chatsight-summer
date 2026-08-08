import json
import math
from pathlib import Path

import pytest

from src.eval.validation import (AuditRow, build_validation_report, confusion,
                                 corrected_prevalence, kappa,
                                 validation_report_table, validation_table)
from src.labeling.draft import MessageLabels
from src.labeling.schema import LabelDef, LabelSchema


def _model(i, **labels):
    return MessageLabels(chatlog_id=1, message_index=i, labels=labels,
                         rationales={k: "r" for k in labels})


def _audit(i, **labels):
    return AuditRow(key=(1, i), labels=labels, no_label_fits=False)


# 10 audited messages, one label "x":
#   human True on 0-3 (4), model True on 0-2 and 5-6 -> tp=3 fp=2 fn=1 tn=4
MODEL = ([_model(i, x=True) for i in (0, 1, 2, 5, 6)]
         + [_model(i, x=False) for i in (3, 4, 7, 8, 9)])
AUDIT = ([_audit(i, x=True) for i in (0, 1, 2, 3)]
         + [_audit(i, x=False) for i in (4, 5, 6, 7, 8, 9)])


def test_confusion_counts():
    c = confusion(AUDIT, MODEL, "x")
    assert (c.tp, c.fp, c.fn, c.tn) == (3, 2, 1, 4)
    assert c.support == 4
    assert math.isclose(c.precision, 3 / 5)
    assert math.isclose(c.recall, 3 / 4)
    assert math.isclose(c.specificity, 4 / 6)
    assert math.isclose(c.agreement, 7 / 10)


def test_kappa_matches_hand_computation():
    c = confusion(AUDIT, MODEL, "x")
    po = 0.7
    pyes = (5 / 10) * (4 / 10)
    pno = (5 / 10) * (6 / 10)
    pe = pyes + pno
    assert math.isclose(kappa(c), (po - pe) / (1 - pe))


def test_corrected_prevalence_rogan_gladen():
    c = confusion(AUDIT, MODEL, "x")
    raw = 5 / 10                      # model prevalence
    sens, spec = 3 / 4, 4 / 6
    expected = (raw + spec - 1) / (sens + spec - 1)
    assert math.isclose(corrected_prevalence(c), expected)
    # degenerate classifier (sens+spec == 1) -> None, never a number
    degenerate = confusion(
        [_audit(0, x=True), _audit(1, x=False)],
        [_model(0, x=False), _model(1, x=True)], "x")
    assert corrected_prevalence(degenerate) is None


def test_validation_table_renders_all_labels_and_flags_chance():
    # add a label where the model is at chance agreement with the human
    model = [r.model_copy(update={"labels": {**r.labels,
                                             "coin": r.message_index % 2 == 0}})
             for r in MODEL]
    audit = [AuditRow(key=a.key,
                      labels={**a.labels, "coin": a.key[1] < 5},
                      no_label_fits=False) for a in AUDIT]
    table = validation_table(audit, model)
    assert "x" in table and "coin" in table
    assert "recall" in table.lower()
    assert "≈ chance" in table          # LACA move: flag guessing labels
    assert "corrected prev" in table.lower()


def _snapshot(tmp_path: Path) -> tuple[Path, LabelSchema]:
    schema = LabelSchema(instructor_intent="i", labels=[
        LabelDef(name="x", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n"),
        LabelDef(name="y", kind="behavioral", description="d",
                 positive_criteria="p", negative_criteria="n"),
    ])
    rows = [
        _model(0, x=True, y=False),
        _model(1, x=True, y=False),
        _model(2, x=False, y=True),
        _model(3, x=False, y=False),
    ]
    snap = tmp_path / "snap1"
    snap.mkdir()
    (snap / "schema.json").write_text(schema.model_dump_json())
    (snap / "labels.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in rows))
    (snap / "manifest.json").write_text(json.dumps({
        "snapshot_id": snap.name,
        "schema_version": schema.version_id,
        "classifier_hash": "hash123",
        "repo_sha": "abc",
    }))
    return snap, schema


def _audit_file(tmp_path: Path, snap: Path, schema: LabelSchema,
                **metadata_overrides) -> Path:
    metadata = {
        "snapshot_id": snap.name,
        "schema_version": schema.version_id,
        "classifier_hash": "hash123",
        "annotator": "steven",
    }
    metadata.update(metadata_overrides)
    rows = [
        {"key": [1, 0], "labels": {"x": True, "y": False},
         "no_label_fits": False},
        {"key": [1, 1], "labels": {"x": False, "y": False},
         "no_label_fits": False},
        {"key": [1, 2], "labels": {"x": True, "y": True},
         "no_label_fits": False},
        {"key": [1, 3], "labels": {"x": False, "y": False},
         "no_label_fits": False},
    ]
    path = tmp_path / "human-labels-steven.json"
    path.write_text(json.dumps({"metadata": metadata, "rows": rows,
                                "strata": {}}))
    return path


def test_validation_report_carries_provenance_and_metrics(tmp_path):
    snap, schema = _snapshot(tmp_path)
    audit = _audit_file(tmp_path, snap, schema)
    report = build_validation_report(snap, audit)
    assert report["metadata"]["snapshot_id"] == snap.name
    assert report["metadata"]["schema_version"] == schema.version_id
    assert report["metadata"]["classifier_hash"] == "hash123"
    assert report["metadata"]["audit_metadata_present"] is True
    assert report["metadata"]["audited_messages"] == 4

    by_label = {r["label"]: r for r in report["labels"]}
    assert by_label["x"]["tp"] == 1
    assert by_label["x"]["fp"] == 1
    assert by_label["x"]["fn"] == 1
    assert by_label["x"]["tn"] == 1
    assert by_label["x"]["precision"] == 0.5
    assert by_label["x"]["recall"] == 0.5
    assert by_label["y"]["tp"] == 1
    assert by_label["y"]["support"] == 1

    table = validation_report_table(report)
    assert f"Snapshot: {snap.name}" in table
    assert f"Schema version: {schema.version_id}" in table
    assert "Classifier hash: hash123" in table


def test_validation_report_rejects_mismatched_audit_metadata(tmp_path):
    snap, schema = _snapshot(tmp_path)
    audit = _audit_file(tmp_path, snap, schema, snapshot_id="other")
    with pytest.raises(ValueError, match="snapshot_id"):
        build_validation_report(snap, audit)
