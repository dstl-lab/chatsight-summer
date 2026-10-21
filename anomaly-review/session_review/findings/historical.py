"""Streaming, local-only adapter for the original ChatSight event export."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path

from .analyze_sessions import Input, assemble

CHAT_TYPES = {"tutor_query", "tutor_response"}
MAX_MESSAGES = 150
MAX_CHARACTERS = 80_000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing recorded timestamp")
    at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if at.utcoffset() is None:
        raise ValueError("Recorded timestamp has no timezone")
    return at


def rows(path, quality=None):
    opener = gzip.open if str(path).endswith(".gz") else open
    seen = set()
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if quality is not None:
                quality["input_lines"] += 1
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("payload"), dict):
                    raise ValueError("Invalid event object")
                if type(row.get("id")) not in (int, str) or not str(row["id"]):
                    raise ValueError("Missing event ID")
                if str(row["id"]) in seen:
                    raise ValueError("Duplicate export event ID")
                if not isinstance(row.get("event_type"), str):
                    raise ValueError("Missing event type")
                timestamp(row.get("created_at"))
            except (ValueError, TypeError):
                if quality is not None:
                    quality["invalid_or_duplicate_lines"] += 1
                continue
            seen.add(str(row["id"]))
            if quality is not None:
                quality["accepted_lines"] += 1
                quality["type:" + row["event_type"]] += 1
            yield line_number, row


def identity(row):
    payload = row["payload"]
    values = (payload.get("conversation_id"), row.get("user_email"), payload.get("notebook"))
    return values if all(isinstance(v, str) and v.strip() for v in values) else None


def source_ref(line, row, input_hash):
    return {"input_sha256": input_hash, "line": line, "export_event_id": str(row["id"]),
            "record_sha256": digest(row), "timestamp_basis": "database_created_at",
            "adapter": "original-chatsight-jsonl-v1"}


def snapshot_excerpt(payload):
    """A bounded display excerpt, never an inferred executed revision or model input."""
    value = payload.get("initial_notebook_json")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return "Capture format is unavailable; inspect the original source record."
    cells = value.get("cells") if isinstance(value, dict) else value if isinstance(value, list) else None
    if not isinstance(cells, list):
        return "Capture format is unavailable; inspect the original source record."
    pieces = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            source = "".join(source)
        if isinstance(source, str) and source.strip():
            pieces.append(f"Captured cell {index + 1}:\n{source[:5000]}")
        if sum(map(len, pieces)) >= 5000:
            break
    text = "\n\n".join(pieces)
    return (text[:5000] + "\n[Display excerpt only; full snapshot remains in the private source export.]") if text else "No code cells available in this capture."


def prepare(path, destination, *, count=20, seed=15):
    """Freeze a bounded development sample. No model, network, or database calls."""
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("The initial pilot allows 1–20 conversations.")
    path, destination = Path(path), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    input_hash = file_hash(path)
    quality = Counter()
    conversations = {}
    for _, row in rows(path, quality):
        if row["event_type"] not in CHAT_TYPES:
            continue
        conv = row["payload"].get("conversation_id")
        if not isinstance(conv, str) or not conv.strip():
            quality["chat_rows_missing_identity"] += 1
            continue
        item = conversations.setdefault(conv, {"identities": set(), "accounts": set(), "notebooks": set(), "modes": set(), "queries": 0,
            "responses": 0, "characters": 0, "rows": 0, "bad_text": False})
        account, notebook = row.get("user_email"), row["payload"].get("notebook")
        if isinstance(account, str) and account.strip():
            item["accounts"].add(account)
        if isinstance(notebook, str) and notebook.strip():
            item["notebooks"].add(notebook)
        if row["event_type"] == "tutor_query":
            item["modes"].add(row["payload"].get("mode", "unknown"))
            item["queries"] += 1
            text = row["payload"].get("question")
        else:
            item["responses"] += 1
            text = row["payload"].get("response")
        item["bad_text"] |= not isinstance(text, str) or not text.strip()
        item["characters"] += len(text) if isinstance(text, str) else 0
        item["rows"] += 1
    strata = defaultdict(list)
    exclusions = Counter()
    for conv, item in conversations.items():
        if len(item["accounts"]) == len(item["notebooks"]) == 1:
            item["identities"] = {(conv, next(iter(item["accounts"])), next(iter(item["notebooks"])))}
        reason = ("conflicting_identity" if len(item["accounts"]) > 1 or len(item["notebooks"]) > 1 else
                  "missing_identity" if not item["accounts"] or not item["notebooks"] else
                  "not_exclusively_tutor_mode" if item["modes"] != {"tutor"} else
                  "missing_dialogue_or_text" if not item["queries"] or not item["responses"] or item["bad_text"] else
                  "oversized_dialogue" if item["rows"] > MAX_MESSAGES or item["characters"] > MAX_CHARACTERS else None)
        if reason:
            exclusions[reason] += 1
            continue
        notebook = next(iter(item["identities"]))[2]
        strata[notebook].append(conv)
    for values in strata.values():
        values.sort(key=lambda conv: digest([seed, conv]))
    # Deterministic round-robin across notebook strata; never select on model findings.
    selected = []
    keys = sorted(strata, key=lambda notebook: digest([seed, notebook]))
    offset = 0
    while len(selected) < count:
        added = False
        for key in keys:
            if offset < len(strata[key]) and len(selected) < count:
                selected.append(strata[key][offset])
                added = True
        if not added:
            break
        offset += 1
    if len(selected) < count:
        raise ValueError(f"Only {len(selected)} eligible conversations; requested {count}.")
    sessions = {conv: {"session_id": conv, "messages": [], "activity": []} for conv in selected}
    context = {conv: {"student_id": next(iter(conversations[conv]["identities"]))[1],
                     "notebook": next(iter(conversations[conv]["identities"]))[2],
                     "scope": "conversation", "events": [], "sources": {}, "warnings": [
                         "Recorded times are database logging times, not verified client action times.",
                         "Question identity and request/response completion links are unknown.",
                         "No continuous notebook edit/execution observations; absence is not inactivity.",
                         "Nearby checks are contextual, not question or execution-linked evidence.",
                         "Notebook snapshots stay outside the model prompt; they do not establish edits or executions."]}
               for conv in selected}
    windows = {}
    for line, row in rows(path):
        conv = row["payload"].get("conversation_id")
        if conv not in sessions or row["event_type"] not in CHAT_TYPES:
            continue
        at = timestamp(row["created_at"])
        ref = "event-" + str(row["id"])
        sessions[conv]["messages"].append({"id": ref, "timestamp": row["created_at"],
            "origin": "recorded", "question_id": None,
            "role": "student" if row["event_type"] == "tutor_query" else "tutor",
            "text": row["payload"]["question" if row["event_type"] == "tutor_query" else "response"]})
        context[conv]["sources"][ref] = source_ref(line, row, input_hash)
        lower, upper = windows.get(conv, (at, at))
        windows[conv] = min(lower, at), max(upper, at)
    by_account_notebook = defaultdict(list)
    for conv in selected:
        by_account_notebook[(context[conv]["student_id"], context[conv]["notebook"])].append(conv)
    for line, row in rows(path):
        if row["event_type"] not in {"autograder_info", "tutor_notebook_info"}:
            continue
        if row["event_type"] == "tutor_notebook_info":
            conv = row["payload"].get("conversation_id")
            targets = [conv] if conv in sessions and row.get("user_email") == context[conv]["student_id"] else []
        else:
            targets = by_account_notebook.get((row.get("user_email"), row["payload"].get("notebook")), [])
        for conv in targets:
            at = timestamp(row["created_at"])
            lower, upper = windows[conv]
            if not lower - timedelta(minutes=30) <= at <= upper + timedelta(minutes=30):
                continue
            ref = "event-" + str(row["id"])
            check = row["event_type"] == "autograder_info"
            success = row["payload"].get("success")
            result = "pass" if success is True else "fail" if success is False else "unknown"
            context[conv]["events"].append({"id": ref, "source_event_id": str(row["id"]),
                "kind": "check_result" if check else "notebook_snapshot",
                "actor": "Autograder" if check else "Notebook",
                "title": f"Contextual check: {result}" if check else "Recorded notebook snapshot",
                "body": ("Nearby check on this account/notebook. Question applicability and executed source are unverified."
                         if check else "Captured notebook state; not a verified revision or execution. Capture timing relative to work is unverified.\n\n" + snapshot_excerpt(row["payload"])),
                "occurred_at": row["created_at"], "phase": "unpartitioned", "order_uncertain": False,
                "source_pointers": [f"line:{line}"], "code_diff": None,
                "metadata": [{"label": "Timestamp basis", "value": "Database logging time"},
                    {"label": "Grader" if check else "Source", "value": str(row["payload"].get("grader_id", "unknown")) if check else "Original notebook capture"}]})
            context[conv]["sources"][ref] = source_ref(line, row, input_hash)
    ordered = [sessions[conv] for conv in selected]
    payload = Input.model_validate({"sessions": ordered})
    for session in payload.sessions:
        assemble(session)
        messages = session.messages
        ties = Counter(message.timestamp for message in messages)
        if any(n > 1 for n in ties.values()):
            context[session.session_id]["warnings"].append("Some messages share a timestamp; display ordering is not verified action ordering.")
        if messages and min(messages, key=lambda m: m.timestamp).role == "tutor":
            context[session.session_id]["warnings"].append("A tutor response precedes the first observed student request; source context may be incomplete.")
    # Verify the source did not change between streaming passes.
    if file_hash(path) != input_hash:
        raise ValueError("Source changed during preparation.")
    manifest = {"format": "session-findings.preparation.v1", "origin": "recorded",
        "input_file_sha256": input_hash, "selected_session_ids": selected,
        "selection": {"count": count, "seed": seed, "mode": "tutor",
            "method": "fixed-notebook-stratified-round-robin-v1", "max_messages": MAX_MESSAGES,
            "max_dialogue_characters": MAX_CHARACTERS, "purpose": "development pilot, not evaluation"},
        "quality": dict(quality), "conversation_exclusions": dict(exclusions),
        "eligible_conversations": sum(map(len, strata.values())),
        "scope": "conversation", "sends_notebook_captures": False,
        "context_window_minutes": 30, "contains_private_course_content": True,
        "source_basename": path.name}
    input_doc = payload.model_dump(mode="json")
    manifest["sessions_sha256"] = digest(input_doc)
    manifest["context_sha256"] = digest(context)
    destination.mkdir(parents=True, mode=0o700)
    for name, data in [("sessions.json", input_doc), ("context.json", context), ("manifest.json", manifest)]:
        private_json(destination / name, data)
    return manifest


def private_json(path, data):
    import os
    path = Path(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def load_prepared(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    sessions_doc = json.loads((folder / "sessions.json").read_text())
    context = json.loads((folder / "context.json").read_text())
    if digest(sessions_doc) != manifest["sessions_sha256"] or digest(context) != manifest["context_sha256"]:
        raise ValueError("Prepared evidence changed; refuse reuse or sending.")
    sessions = Input.model_validate(sessions_doc).sessions
    if [session.session_id for session in sessions] != manifest["selected_session_ids"]:
        raise ValueError("Session selection changed.")
    evidence = []
    for session in sessions:
        item = assemble(session)
        item["warnings"].extend(context[session.session_id]["warnings"])
        evidence.append(item)
    return manifest, sessions, context, evidence
