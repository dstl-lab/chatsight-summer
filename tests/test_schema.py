from pathlib import Path
from src.labeling.schema import LabelDef, LabelSchema, load_schema, save_schema


def _schema(desc: str = "asks for the answer outright") -> LabelSchema:
    return LabelSchema(
        instructor_intent="I want to see who extracts answers vs works for them",
        labels=[LabelDef(
            name="answer-extraction", kind="behavioral", description=desc,
            positive_criteria="directly requests final answer",
            negative_criteria="asks for a hint or explanation",
        )],
        parent_version=None, feedback_applied=None,
    )


def test_version_id_is_stable_and_content_sensitive():
    a, b = _schema(), _schema()
    assert a.version_id == b.version_id
    assert len(a.version_id) == 12
    assert a.version_id != _schema(desc="changed").version_id


def test_save_and_load_roundtrip(tmp_path: Path):
    s = _schema()
    path = save_schema(s, tmp_path)
    assert path.name == f"{s.version_id}.json"
    assert load_schema(s.version_id, tmp_path) == s


def test_tweak_lineage():
    parent = _schema()
    child = LabelSchema(
        instructor_intent=parent.instructor_intent,
        labels=parent.labels,
        parent_version=parent.version_id,
        feedback_applied="split confusion into concept vs logistics",
    )
    assert child.parent_version == parent.version_id
    assert child.version_id != parent.version_id
