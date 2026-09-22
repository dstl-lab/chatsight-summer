"""Common observation packets preserve evidence gaps and replay bindings."""
from copy import deepcopy
import json

import pytest

from src.agents import notebook_student as student
from src.eval.notebook_session import Action
from tests.test_notebook_session import ACTIVITY, TASK, observation


def _conversation():
    return {
        "chatlog_id": "PRIVATE CHATLOG",
        "conv_id": "PRIVATE CONVERSATION",
        "notebook": "PRIVATE NOTEBOOK",
        "started_at": "PRIVATE START",
        "turns": [
            {"index": 4, "role": "student", "text": "Can you explain this?",
             "at": "2026-01-01T00:00:00Z", "mode": ""},
            {"index": 5, "role": "tutor", "text": "Start with the distinct values.",
             "at": "2026-01-01T00:00:01Z", "mode": "tutor"},
            {"index": 6, "role": "student", "text": "PRIVATE FUTURE STUDENT",
             "at": "2026-01-01T00:01:00Z", "mode": ""},
            {"index": 7, "role": "tutor", "text": "PRIVATE FUTURE TUTOR",
             "at": "2026-01-01T00:01:01Z", "mode": "tutor"},
        ],
    }


def _files(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()}


def test_recorded_packet_ends_at_tutor_and_keeps_future_and_identifiers_out():
    from src.eval import observation_contract as contract

    conversation = _conversation()
    packet = contract.recorded_packet(conversation, source_sha256="a" * 64, through_turn=1)
    changed_future = deepcopy(conversation)
    changed_future["turns"][2]["text"] = "A different omitted future"
    changed_future["turns"][3]["text"] = "Another omitted future"
    assert contract.recorded_packet(changed_future, source_sha256="a" * 64,
                                    through_turn=1) == packet
    assert [(turn["role"], turn["text"]) for turn in packet["dialogue"]] == [
        ("student", "Can you explain this?"),
        ("tutor", "Start with the distinct values."),
    ]
    assert packet["tutor_boundary"] == {
        "dialogue_index": 1, "source_turn_index": 5,
        "observed_at": "2026-01-01T00:00:01Z",
        "turn_sha256": student.digest(packet["dialogue"][1]),
    }
    assert packet["task"]["status"] == "unavailable"
    assert packet["work"]["status"] == "unavailable"
    assert packet["check"]["status"] == "unavailable"
    assert packet["session"]["decisions_used"] is None
    encoded = json.dumps(packet)
    for private in ("PRIVATE CHATLOG", "PRIVATE CONVERSATION", "PRIVATE NOTEBOOK",
                    "PRIVATE FUTURE STUDENT", "PRIVATE FUTURE TUTOR", "PRIVATE START"):
        assert private not in encoded
    assert packet["provenance"]["opaque_record_id"]
    assert packet["provenance"]["notebook_reference_sha256"]
    assert packet["sha256"] == student.digest({key: value for key, value in packet.items()
                                                if key != "sha256"})

    for boundary in (True, -1, 0, 4):
        with pytest.raises(ValueError):
            contract.recorded_packet(conversation, source_sha256="a" * 64,
                                     through_turn=boundary)
    with pytest.raises(ValueError):
        contract.recorded_packet(conversation, source_sha256="short", through_turn=1)


def test_simulation_packet_uses_verified_saved_work_and_check_without_dispatch(tmp_path, monkeypatch):
    from src.eval import observation_contract as contract

    folder = tmp_path / "session"
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id="synthetic/contract",
                   max_decisions=4)
    actions = iter([
        Action(decision="revise-work", text="", source="n_shades = 2"),
        Action(decision="request-check", text="", source=None),
    ])
    student.step(folder, generate=lambda *_: next(actions),
                 check=lambda *args, **kwargs: observation(*args, **kwargs, status="checked"),
                 max_actions=2)
    before = _files(folder)
    monkeypatch.setattr(student.llm, "make_generate",
                        lambda *_a, **_kw: pytest.fail("Packet creation dispatched a model."))
    monkeypatch.setattr(student.notebook_runtime, "check_work",
                        lambda *_a, **_kw: pytest.fail("Packet creation executed code."))

    packet = contract.simulation_packet(folder)

    assert _files(folder) == before
    assert packet["origin"] == "saved-notebook-simulation"
    assert packet["task"]["status"] == "supplied" and packet["task"]["text"] == TASK["task"]
    assert packet["work"] == {
        "status": "saved-simulation",
        "cell_identity_kind": "session-branch-index",
        "cell_identity_sha256": student.digest({"branch_id": "synthetic/contract", "cell_index": 1}),
        "cell_index": 1,
        "source": "n_shades = 2",
        "source_sha256": student.digest("n_shades = 2"),
        "revision": 1,
    }
    assert packet["check"] == {
        "status": "recorded", "bound_revision": 1, "outcome": "checked",
        "success": True, "value": 2, "error": None, "output": "",
    }
    assert packet["session"] == {"status": "active", "decisions_used": 2,
                                  "max_decisions": 4}
    assert packet["tutor_boundary"]["dialogue_index"] == 1
    assert "image_id" not in json.dumps(packet)
    assert packet["sha256"] == student.digest({key: value for key, value in packet.items()
                                                if key != "sha256"})


def test_packet_files_are_create_only_and_hash_checked(tmp_path):
    from src.eval import observation_contract as contract

    packet = contract.recorded_packet(_conversation(), source_sha256="b" * 64,
                                      through_turn=1)
    path = tmp_path / "packet.json"
    assert contract.write_packet(packet, path) == path
    assert contract.read_packet(path) == packet
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        contract.write_packet(packet, path)
    assert path.read_bytes() == original
    changed = deepcopy(packet)
    changed["dialogue"][0]["text"] = "Changed"
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="hash changed"):
        contract.read_packet(path)


def test_fresh_simulation_inspection_does_not_create_a_lock(tmp_path):
    from src.eval import observation_contract as contract

    folder = tmp_path / "session"
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id="synthetic/fresh")
    before = _files(folder)
    packet = contract.simulation_packet(folder)
    assert packet["session"]["decisions_used"] == 0
    assert packet["check"]["status"] == "not-recorded"
    assert _files(folder) == before


def test_inspection_uses_shared_lock_and_rejects_missing_saved_lock(tmp_path):
    import fcntl
    from src.eval import observation_contract as contract

    folder = tmp_path / "session"
    student.create(folder, task=TASK, activity=ACTIVITY, branch_id="synthetic/locked")
    student.step(folder, generate=lambda *_: Action(decision="no-reply", text="", source=None),
                 check=lambda *_: pytest.fail("Unexpected notebook execution"))
    lock = folder / ".lock"
    before = _files(folder)
    with lock.open("rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        assert contract.simulation_packet(folder)["session"]["decisions_used"] == 1
    with student._locked(folder), pytest.raises(ValueError, match="busy"):
        contract.simulation_packet(folder)
    assert _files(folder) == before
    lock.unlink()
    before = _files(folder)
    with pytest.raises(ValueError, match="saved lock is missing"):
        contract.simulation_packet(folder)
    assert _files(folder) == before
