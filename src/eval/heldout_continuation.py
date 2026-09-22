"""Prepare, run once, and replay one target-isolated historical continuation."""
import argparse
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from src.agents import chat_student as chat, notebook_student as store
from src.eval import student_continuation as continuation


SEED = "heldout-continuation-walkthrough-v1"
MODEL = "gemini-2.5-pro"
MAX_PREFIX_TURNS = 8
LEGACY_READER_SOURCE = "c34326095b2223273bed51eab9d7543daad19d5d29a6921cd2e4bbc9aff15829"  # 4d7c2a8


def _source_hashes():
    return {Path(module.__file__).name: store.digest(Path(module.__file__).read_text())
            for module in (chat, continuation)} | {
        Path(__file__).name: store.digest(Path(__file__).read_text())}


def _select(rows):
    candidates = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("turns"), list):
            raise ValueError("Snapshot conversations must contain turn lists.")
        identifiers = {key: row.get(key) for key in ("chatlog_id", "conv_id")}
        if any(value is None for value in identifiers.values()):
            raise ValueError("Snapshot conversations need provenance identifiers.")
        turns = row["turns"]
        for boundary in range(1, len(turns) - 1):
            before, tutor, target = turns[boundary - 1:boundary + 2]
            if ([before.get("role"), tutor.get("role"), target.get("role")]
                    != ["student", "tutor", "student"]):
                continue
            if any(not isinstance(turn.get("text"), str) or not turn["text"].strip()
                   for turn in (before, tutor, target)):
                continue
            rank = store.digest({"seed": SEED, "identifiers": identifiers,
                                 "boundary": boundary})
            candidates.append((rank, row_index, boundary, identifiers))
    if not candidates:
        raise ValueError("No tutor boundary with an immediate recorded student reply was found.")
    return min(candidates)


def _case(rows):
    rank, row_index, boundary, identifiers = _select(rows)
    turns = rows[row_index]["turns"]
    prefix = turns[max(0, boundary + 1 - MAX_PREFIX_TURNS):boundary + 1]
    if [turn.get("role") for turn in prefix[-2:]] != ["student", "tutor"]:
        raise ValueError("The selected prefix needs a final student/tutor exchange.")
    visible = [{"role": turn["role"], "text": turn["text"]} for turn in prefix]
    opaque = store.digest(identifiers)
    query = {"id": "case-" + rank[:16], "conversation_id": "conversation-" + opaque[:16],
             "student_id": None, "prefix": visible}
    reference = {"role": "student", "text": turns[boundary + 1]["text"],
                 "source_turn_index": turns[boundary + 1].get("index", boundary + 1)}
    return {"rank": rank, "row_index": row_index, "boundary": boundary,
            "query": query, "reference": reference}


def _episode(query, reference):
    episode = chat._initial(query)["episode"]
    episode["turns"].append({"id": "recorded-next", "role": "student",
                             "phase": "followup", "text": reference["text"]})
    return episode


def prepare(snapshot, folder):
    """Freeze one prefix and its separate reference without calling a provider."""
    snapshot, folder = Path(snapshot), Path(folder)
    source = snapshot / "conversations.jsonl"
    raw = source.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    case = _case(rows)
    folder.parent.mkdir(parents=True, exist_ok=True)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix=".heldout-") as temporary:
        staged = Path(temporary) / "case"
        staged.mkdir()
        saved = chat.create(staged / "session", query=case["query"], model=MODEL,
                            max_decisions=1)
        prompt = continuation.make_prompt(saved["state"]["episode"])
        reference = {"version": 1, "query_sha256": store.digest(case["query"]),
                     "target": case["reference"]}
        reference["sha256"] = store.digest(reference)
        store._save(staged / "reference.json", reference, exclusive=True)
        authorization = {
            "scope": "One Gemini 2.5 Pro continuation from one recorded prefix; the immediate "
                     "recorded next message is excluded from the request.",
            "user_direction": "ok, lets do the next milestone",
            "standing_approval": "CLAUDE.md standing model-run approval dated 2026-09-11",
        }
        manifest = {
            "version": 1, "status": "prepared", "selector": SEED,
            "max_prefix_turns": MAX_PREFIX_TURNS, "model": MODEL, "requests": 1,
            "source": {"snapshot": snapshot.name, "conversations_sha256": sha256(raw).hexdigest()},
            "case": {"rank": case["rank"], "row_index": case["row_index"],
                     "tutor_boundary": case["boundary"],
                     "query_sha256": store.digest(case["query"]),
                     "reference_sha256": reference["sha256"],
                     "prompt_sha256": store.digest(prompt)},
            "authorization": authorization, "sources": _source_hashes(),
        }
        manifest["sha256"] = store.digest(manifest)
        store._save(staged / "manifest.json", manifest, exclusive=True)
        os.replace(staged, folder)
    return manifest


def _preparation(folder, *, reading=False):
    folder = Path(folder)
    manifest = store._read(folder / "manifest.json")
    reference = store._read(folder / "reference.json")
    session_manifest = store._read(folder / "session" / "session.json")
    sources = _source_hashes()
    supported_sources = [sources]
    if reading:
        supported_sources.append(sources | {"heldout_continuation.py": LEGACY_READER_SOURCE})
    if (manifest.get("version") != 1 or manifest.get("sha256") != store.digest(
            {key: value for key, value in manifest.items() if key != "sha256"})
            or manifest.get("sources") not in supported_sources
            or reference.get("version") != 1
            or reference.get("sha256") != store.digest(
                {key: value for key, value in reference.items() if key != "sha256"})
            or manifest["case"]["query_sha256"] != store.digest(session_manifest["query"])
            or reference["query_sha256"] != manifest["case"]["query_sha256"]
            or manifest["case"]["reference_sha256"] != reference["sha256"]
            or manifest["case"]["prompt_sha256"] != store.digest(
                continuation.make_prompt(chat._initial(session_manifest["query"])["episode"]))):
        raise ValueError("Held-out continuation preparation changed.")
    return manifest, reference, session_manifest


def _saved_continuation(folder):
    """Replay the saved request/result under its existing lock without writing."""
    session = Path(folder) / "session"
    try:
        stream = (session / ".lock").open("rb")
    except FileNotFoundError as exc:
        raise ValueError("The completed continuation needs its saved session lock.") from exc
    with stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("This student session is busy.") from exc
        manifest, reference, session_manifest = _preparation(folder, reading=True)
        verified, _, decisions = chat._load(session)
        receipt = store._read(session / "step-0001.json")
        if (verified != session_manifest or decisions != 1
                or verified["model"] != manifest["model"] or verified["max_decisions"] != 1
                or manifest["requests"] != 1 or receipt.get("status") != "complete"):
            raise ValueError("The saved continuation must contain one completed prepared decision.")
    return manifest, reference, session_manifest, receipt


def _comparison_content(manifest, reference, session_manifest, receipt):
    response = continuation.Continuation.model_validate(receipt["response"])
    episode = _episode(session_manifest["query"], reference["target"])
    review = continuation.behavior_review(episode, response)
    if review["prompt_sha256"] != manifest["case"]["prompt_sha256"]:
        raise ValueError("Comparison prompt differs from the prepared request.")
    return {
        "provenance": {
            "model": manifest["model"],
            "logical_requests": manifest["requests"],
            "provider_attempts": None,
            "prompt_sha256": manifest["case"]["prompt_sha256"],
            "selector": manifest["selector"],
            "source_snapshot": manifest["source"]["snapshot"],
            "source_conversations_sha256": manifest["source"]["conversations_sha256"],
        },
        "review": review,
    }


def finalize(folder):
    """Join one saved response with the separately held-out reference offline."""
    folder = Path(folder)
    manifest, reference, session_manifest, receipt = _saved_continuation(folder)
    comparison = {
        "version": 1, "contains_private_content": True,
        "manifest_sha256": manifest["sha256"],
        "session_sha256": store.digest(session_manifest),
        "receipt_sha256": store.digest(receipt),
        "created_at": datetime.now(timezone.utc).isoformat(),
        **_comparison_content(manifest, reference, session_manifest, receipt),
        "limits": [
            "One exposed development case is not an accuracy or fidelity estimate.",
            "The sample is conditioned on an immediate recorded student reply.",
            "Conversation evidence cannot establish silent notebook actions.",
            "The recorded message is one observed outcome, not the only valid continuation.",
        ],
    }
    comparison["sha256"] = store.digest(comparison)
    store._save(folder / "comparison.json", comparison, exclusive=True)
    return comparison


def run(folder, *, generate):
    """Dispatch exactly one saved-chat decision, then join the hidden reference."""
    folder = Path(folder)
    manifest, _, _ = _preparation(folder)
    if manifest["requests"] != 1 or manifest["model"] != MODEL:
        raise ValueError("Unexpected provider scope.")
    if (folder / "comparison.json").exists() or list((folder / "session").glob("step-*.json")):
        raise FileExistsError("This held-out continuation was already run.")
    saved = chat.show(folder / "session")
    if saved["decisions"] != 0 or saved["state"]["status"] != "ready":
        raise ValueError("The prepared chat session is not fresh.")
    chat.step(folder / "session", binding=saved["binding"], generate=generate)
    return finalize(folder)


def load(folder):
    """Verify and load a completed comparison without provider calls."""
    folder = Path(folder)
    manifest, reference, session_manifest, receipt = _saved_continuation(folder)
    comparison = store._read(folder / "comparison.json")
    expected = _comparison_content(manifest, reference, session_manifest, receipt)
    provenance = [expected["provenance"]]
    if manifest["sources"]["heldout_continuation.py"] == LEGACY_READER_SOURCE:
        legacy = {key: value for key, value in expected["provenance"].items()
                  if key not in ("logical_requests", "provider_attempts")}
        provenance.append(legacy | {"provider_requests": manifest["requests"]})
    if (comparison.get("version") != 1 or comparison.get("contains_private_content") is not True
            or comparison.get("sha256") != store.digest(
                {key: value for key, value in comparison.items() if key != "sha256"})
            or comparison.get("manifest_sha256") != manifest["sha256"]
            or comparison.get("session_sha256") != store.digest(session_manifest)
            or comparison.get("receipt_sha256") != store.digest(receipt)
            or comparison.get("review") != expected["review"]
            or comparison.get("provenance") not in provenance):
        raise ValueError("Held-out comparison changed.")
    return comparison


def summary(comparison):
    recorded, generated = comparison["review"]["candidates"]
    return {"recorded": recorded["status"], "generated": generated["status"],
            "prefix_turns": (len(comparison["review"]["prefix"]["context"])
                             + len(comparison["review"]["prefix"]["turns"])),
            "sha256": comparison["sha256"]}


def main():
    from dotenv import load_dotenv
    from src.labeling import llm

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("prepare")
    prepare_command.add_argument("snapshot", type=Path)
    prepare_command.add_argument("folder", type=Path)
    run_command = commands.add_parser("run")
    run_command.add_argument("folder", type=Path)
    run_command.add_argument("--send", action="store_true")
    show_command = commands.add_parser("show")
    show_command.add_argument("folder", type=Path)
    args = parser.parse_args()

    if args.command == "prepare":
        manifest = prepare(args.snapshot, args.folder)
        output = {"status": "prepared", "model": manifest["model"],
                  "requests": manifest["requests"], "sha256": manifest["sha256"]}
    elif args.command == "run":
        if not args.send:
            parser.error("run requires --send; show is offline.")
        load_dotenv(Path.cwd() / ".env")
        provider = llm.make_generate(os.environ["GEMINI_API_KEY"], model=MODEL)
        output = summary(run(args.folder, generate=provider))
    else:
        output = summary(load(args.folder))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
