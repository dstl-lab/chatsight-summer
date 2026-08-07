import json

import pytest
from pydantic import BaseModel

from src.ingest.rawlog import Conversation, Turn
from src.labeling.explore import (EXPLORE_PROMPT, ExplorationDraft,
                                  build_digest, explore, write_draft)
from src.labeling.profile2 import CourseProfileV2


def _conv(i, texts):
    turns = []
    for j, t in enumerate(texts):
        turns.append(Turn(index=2 * j, role="student", text=t,
                          student_index=j))
        turns.append(Turn(index=2 * j + 1, role="tutor", text=f"reply {j}"))
    return Conversation(conv_id=f"c{i}", chatlog_id=i, notebook="lab01.ipynb",
                        started_at=None, turns=turns)


CONVS = [_conv(1, ["help with 1.2", "what is a for loop"]),
         _conv(2, ["my code errors", "why", "test"]),
         _conv(3, ["invented question about histograms"])]


def _draft(**kw):
    base = dict(course_name="Drafted 101", domain_description="d",
                tooling="t", paste_conventions="p",
                reference_conventions="r", message_shape_notes="m",
                concepts=[], affect_labels=[], intent_labels=[])
    base.update(kw)
    return ExplorationDraft(**base)


def fake_generate(prompt, response_model):
    fake_generate.prompts.append(prompt)
    assert response_model is ExplorationDraft
    return _draft()


fake_generate.prompts = []


def test_digest_covers_conversations_without_tutor_text():
    d = build_digest(CONVS)
    assert "lab01.ipynb" in d
    assert "help with 1.2" in d          # student excerpts included
    assert "reply 0" not in d            # tutor text never in digest


def test_explore_prompt_contents_and_provenance():
    fake_generate.prompts = []
    v2 = explore(CONVS, ["Syllabus: loops, tables"], fake_generate,
                 sample_meta={"conversations": 3, "seed": 4},
                 repo_sha="abc1234", explored_on="2026-08-07")
    p = fake_generate.prompts[0]
    assert "Syllabus: loops, tables" in p
    assert "help with 1.2" in p                       # digest present
    assert "judgeable on messages as they actually occur" in p
    assert "never quote" in p.lower()
    assert isinstance(v2, CourseProfileV2)
    assert v2.materials_provided is True
    assert v2.corpus_sample == {"conversations": 3, "seed": 4}
    assert v2.repo_sha == "abc1234" and v2.accepted is False

    v2b = explore(CONVS, [], fake_generate, sample_meta={"conversations": 3,
                  "seed": 4}, repo_sha="abc1234", explored_on="2026-08-07")
    assert v2b.materials_provided is False


def test_write_draft_lint_gate(tmp_path):
    quoting = _draft(domain_description=(
        "students say invented question about histograms all the time in "
        "this course"))
    # 'invented question about histograms' is only 5 words — extend the turn
    long_turn = _conv(9, ["one two three four five six seven eight nine"])
    quoting2 = _draft(domain_description=(
        "seen: one two three four five six seven eight nine"))
    with pytest.raises(ValueError, match="lint"):
        write_draft(explore(  # artifact quoting a student turn is refused
            [long_turn], [], lambda p, m: quoting2,
            sample_meta={"conversations": 1, "seed": 0}, repo_sha="x",
            explored_on="2026-08-07"),
            [long_turn], tmp_path / "bad-draft.json")
    ok = explore(CONVS, [], lambda p, m: _draft(),
                 sample_meta={"conversations": 3, "seed": 0}, repo_sha="x",
                 explored_on="2026-08-07")
    path = write_draft(ok, CONVS, tmp_path / "t101-draft.json")
    assert json.loads(path.read_text())["accepted"] is False


def test_wire_model_has_no_dict_fields():
    for f in ExplorationDraft.model_fields.values():
        assert "dict" not in str(f.annotation)


def test_wire_model_is_pydantic():
    assert issubclass(ExplorationDraft, BaseModel)
