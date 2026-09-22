"""Build private, local-only observation packets without generation or execution."""
import argparse
from contextlib import ExitStack
import fcntl
from hashlib import sha256
import json
from pathlib import Path
import re

from src.agents import notebook_student as student


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _file_digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _finalize(packet):
    packet = packet | {"sha256": student.digest(packet)}
    return packet


def _turn(role, text, *, origin, source_index, observed_at=None):
    if role not in ("student", "tutor") or not isinstance(text, str) or not text.strip():
        raise ValueError("Dialogue needs nonblank student/tutor turns.")
    if type(source_index) is not int or source_index < 0:
        raise ValueError("Dialogue source indices must be nonnegative integers.")
    if observed_at is not None and not isinstance(observed_at, str):
        raise ValueError("Turn timestamps must be text or null.")
    return {"role": role, "text": text, "origin": origin,
            "source_index": source_index, "observed_at": observed_at}


def _boundary(dialogue):
    index = len(dialogue) - 1
    if index < 0 or dialogue[index]["role"] != "tutor":
        raise ValueError("An observation boundary must end at a tutor turn.")
    turn = dialogue[index]
    return {"dialogue_index": index, "source_turn_index": turn["source_index"],
            "observed_at": turn["observed_at"], "turn_sha256": student.digest(turn)}


def recorded_packet(conversation, *, source_sha256, through_turn=None):
    """Project one recorded prefix; later turns and raw identifiers are excluded."""
    if not isinstance(conversation, dict) or not SHA256.fullmatch(source_sha256):
        raise ValueError("Supply a recorded conversation and its source SHA-256.")
    turns = conversation.get("turns")
    if not isinstance(turns, list) or not turns:
        raise ValueError("A recorded conversation needs turns.")
    through_turn = len(turns) - 1 if through_turn is None else through_turn
    if type(through_turn) is not int or not 0 <= through_turn < len(turns):
        raise ValueError("Choose an in-range tutor-turn boundary.")
    selected = turns[:through_turn + 1]
    dialogue = []
    for position, value in enumerate(selected):
        if not isinstance(value, dict):
            raise ValueError("Recorded turns must be objects.")
        source_index = value.get("index", position)
        dialogue.append(_turn(value.get("role"), value.get("text"), origin="recorded",
                              source_index=source_index, observed_at=value.get("at")))
    boundary = _boundary(dialogue)
    identifiers = {key: conversation.get(key) for key in ("chatlog_id", "conv_id")}
    if any(value is None for value in identifiers.values()):
        raise ValueError("Recorded conversation identifiers are required for provenance.")
    notebook = conversation.get("notebook")
    if notebook is not None and not isinstance(notebook, str):
        raise ValueError("The recorded notebook reference must be text or null.")
    observed_record = {"identifiers": identifiers, "notebook": notebook,
                       "turns": selected}
    packet = {
        "version": 1,
        "contains_private_content": True,
        "origin": "recorded-conversation",
        "provenance": {
            "source_kind": "snapshot-conversations-jsonl",
            "source_sha256": source_sha256,
            "record_sha256": student.digest(observed_record),
            "opaque_record_id": student.digest(identifiers),
            "notebook_reference_sha256": student.digest(notebook) if notebook else None,
        },
        "dialogue": dialogue,
        "tutor_boundary": boundary,
        "task": {"status": "unavailable", "identity_sha256": None,
                 "version_sha256": None, "text": None},
        "work": {"status": "unavailable", "cell_identity_kind": None,
                 "cell_identity_sha256": None, "cell_index": None, "source": None,
                 "source_sha256": None, "revision": None},
        "check": {"status": "unavailable", "bound_revision": None,
                  "outcome": None, "success": None, "value": None,
                  "error": None, "output": None},
        "session": {"status": "recorded-context", "decisions_used": None,
                    "max_decisions": None},
        "limitations": [
            "task-version-unavailable",
            "notebook-work-unavailable",
            "stable-cell-identity-unavailable",
            "source-bound-check-unavailable",
            "later-turns-excluded",
        ],
    }
    return _finalize(packet)


def simulation_packet(folder):
    """Project one verified saved state; never invoke its model or notebook runtime."""
    folder = Path(folder)
    with ExitStack() as stack:
        lock = folder / ".lock"
        try:
            stream = stack.enter_context(lock.open("rb"))
        except FileNotFoundError:
            stream = None
        if stream is not None:
            try:
                fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError("This student session is busy.") from exc
        manifest, state, paths, decisions = student._load(folder)
        # A fresh session has no lock until its first writer opens it.
        if stream is None and (paths or lock.exists()):
            raise ValueError("The session changed during inspection or its saved lock is missing.")
        observation = state["observation"]
        if observation is not None:
            student.notebook_runtime.require_current(
                observation, state["work"], **student.notebook_session._check_args(state))
        feedback = student.notebook_session._feedback(observation)
        if feedback is not None and feedback["status"] == "environment-error":
            feedback["error"] = {"message": "Local execution was unavailable; this work is ungraded. "
                                 "The saved receipt retains the diagnostic."}
            feedback["output"] = ""

        dialogue = [_turn(value.get("role"), value.get("text"),
                          origin=value.get("origin", "supplied"), source_index=index)
                    for index, value in enumerate(state["dialogue"])]
        boundary = _boundary(dialogue)
        work = state["work"]
        cell_identity = {"branch_id": state["branch_id"], "cell_index": work["cell_index"]}
        if observation is None:
            check = {"status": "not-recorded", "bound_revision": None,
                     "outcome": None, "success": None, "value": None,
                     "error": None, "output": None}
        else:
            check = {"status": "recorded", "bound_revision": observation["binding"]["revision"],
                     "outcome": feedback["status"], "success": feedback["success"],
                     "value": feedback["value"], "error": feedback["error"],
                     "output": feedback["output"]}
        packet = {
            "version": 1,
            "contains_private_content": True,
            "origin": "saved-notebook-simulation",
            "provenance": {
                "source_kind": "saved-notebook-session",
                "source_sha256": student.digest(manifest),
                "record_sha256": student.digest(state),
                "opaque_record_id": student.digest({"branch_id": state["branch_id"]}),
                "notebook_reference_sha256": None,
            },
            "dialogue": dialogue,
            "tutor_boundary": boundary,
            "task": {"status": "supplied", "identity_sha256": student.digest(state["task"]),
                     "version_sha256": student.digest({"initialization": state["initialization"],
                                                        "task": state["task"]}),
                     "text": state["task"]},
            "work": {"status": "saved-simulation",
                     "cell_identity_kind": "session-branch-index",
                     "cell_identity_sha256": student.digest(cell_identity),
                     "cell_index": work["cell_index"], "source": work["source"],
                     "source_sha256": student.digest(work["source"]),
                     "revision": work["revision"]},
            "check": check,
            "session": {"status": state["status"], "decisions_used": decisions,
                        "max_decisions": manifest["max_decisions"]},
            "limitations": [
                "simulated-not-observed-student",
                "task-identity-derived-from-supplied-content",
                "cell-identity-stable-only-inside-saved-branch",
                "single-selected-cell-scope",
            ],
        }
    return _finalize(packet)


def read_packet(path):
    packet = student._read(Path(path))
    if (not isinstance(packet, dict) or packet.get("version") != 1
            or packet.get("contains_private_content") is not True
            or packet.get("origin") not in ("recorded-conversation", "saved-notebook-simulation")
            or packet.get("sha256") != student.digest({key: value for key, value in packet.items()
                                                        if key != "sha256"})):
        raise ValueError("Observation packet is unsupported or its content hash changed.")
    return packet


def write_packet(packet, path):
    student._save(Path(path), packet, exclusive=True)
    return Path(path)


def summary(packet):
    return {"origin": packet["origin"], "dialogue_turns": len(packet["dialogue"]),
            "task": packet["task"]["status"], "work": packet["work"]["status"],
            "check": packet["check"]["status"], "sha256": packet["sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    recorded = commands.add_parser("recorded", help="Create from one snapshot conversation prefix.")
    recorded.add_argument("snapshot", type=Path)
    recorded.add_argument("output", type=Path)
    recorded.add_argument("--conversation-index", type=int, required=True)
    recorded.add_argument("--through-turn", type=int)
    simulation = commands.add_parser("simulation", help="Create from one saved notebook simulation.")
    simulation.add_argument("session", type=Path)
    simulation.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "recorded":
        source = args.snapshot / "conversations.jsonl"
        rows = source.read_text(encoding="utf-8").splitlines()
        if not 0 <= args.conversation_index < len(rows):
            parser.error("--conversation-index is outside the snapshot.")
        packet = recorded_packet(json.loads(rows[args.conversation_index]),
                                 source_sha256=_file_digest(source),
                                 through_turn=args.through_turn)
    else:
        packet = simulation_packet(args.session)
    write_packet(packet, args.output)
    print(json.dumps(summary(packet) | {"output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
