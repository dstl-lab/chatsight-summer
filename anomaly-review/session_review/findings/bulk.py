"""Disk-backed PR100 import and exhaustive bounded tutor-window preparation."""
from collections import Counter
from datetime import timedelta, timezone
import gzip
import json
import os
from pathlib import Path
import sqlite3

from . import historical as h, recent
from .production import DEPLOYED, EXPORT_FORMAT, MAX_EXPANDED, MAX_LINE, MAX_ROWS

VERSION = "pr100-all-request-windows-v1"


def utc(value):
    return h.timestamp(value).astimezone(timezone.utc).isoformat()


def index_source(source, destination, *, progress=lambda value: None):
    """Validate once; keep records/identity indexes on disk, not in a Python list."""
    db = sqlite3.connect(destination)
    os.chmod(destination, 0o600)
    counts = Counter()
    first = last = None
    header = None
    try:
        db.execute("PRAGMA cache_size=-16000")
        db.execute("CREATE TABLE events (eid TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, line INTEGER, scope TEXT, occurred TEXT, kind TEXT, mode TEXT, raw TEXT NOT NULL)")
        opener = gzip.open if str(source).endswith(".gz") else open
        with opener(source, "rb") as stream:
            while line := stream.readline(MAX_LINE + 1):
                counts["lines"] += 1
                counts["expanded_bytes"] += len(line)
                if len(line) > MAX_LINE or counts["expanded_bytes"] > MAX_EXPANDED:
                    raise ValueError("Export exceeds the line or expanded-size limit. Extract a smaller date range.")
                if not line.strip():
                    continue
                row = json.loads(line)
                if counts["lines"] == 1 and isinstance(row, dict) and row.get("format") == EXPORT_FORMAT:
                    header = row
                    if not DEPLOYED <= h.timestamp(row["since"]) < h.timestamp(row["until"]):
                        raise ValueError("Export boundaries precede the observed PR100 production start.")
                    continue
                p = row.get("payload") if isinstance(row, dict) else None
                if not isinstance(p, dict) or type(p.get("schema_version")) is not int or p["schema_version"] != 1:
                    raise ValueError("Use a PR100 production export, not historical records or a saved review bundle.")
                received = h.timestamp(row.get("created_at"))
                if received < DEPLOYED or (header and not h.timestamp(header["since"]) <= received < h.timestamp(header["until"])):
                    raise ValueError("A record falls outside the export's PR100 production boundaries.")
                eid = p.get("event_id")
                if not isinstance(eid, str) or not eid or type(row.get("id")) not in (str, int) or not isinstance(row.get("event_type"), str):
                    raise ValueError("A record is missing its event identity or type.")
                counts["input_events"] += 1
                if counts["input_events"] > MAX_ROWS:
                    raise ValueError("Export exceeds ten million events. Extract a smaller date range.")
                key = recent.scope(row)
                try:
                    occurred = utc(p.get("timestamp"))
                except (ValueError, TypeError):
                    occurred = None
                # Re-delivery can assign a new DB row ID/received time. Compare
                # the client event itself; retain the first row as provenance.
                fingerprint = h.digest({"event_type": row["event_type"], "user_email": row.get("user_email"), "payload": p})
                try:
                    db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", (eid, fingerprint, counts["lines"], json.dumps(key) if key else None,
                        occurred, row["event_type"], p.get("mode") if isinstance(p.get("mode"), str) else None, line.decode()))
                    counts["events"] += 1
                    counts["type:" + row["event_type"]] += 1
                    if not key: counts["missing_scope"] += 1
                    if not occurred: counts["missing_occurrence_time"] += 1
                except sqlite3.IntegrityError:
                    old = db.execute("SELECT fingerprint FROM events WHERE eid=?", (eid,)).fetchone()[0]
                    if old != fingerprint:
                        raise ValueError("Conflicting records share an event UUID; no analysis was started.") from None
                    counts["duplicate_events"] += 1
                first = min(first, received) if first else received
                last = max(last, received) if last else received
                if counts["input_events"] % 10000 == 0:
                    db.commit()
                    progress({"phase": "Reading events", "events": counts["events"]})
        if not counts["events"]:
            raise ValueError("The export contains no events.")
        db.execute("CREATE INDEX scope_time ON events(scope,occurred)")
        db.execute("CREATE INDEX event_kind ON events(kind)")
        db.commit()
        return {**dict(counts), "first_event_at": first.isoformat(), "last_event_at": last.isoformat(),
                "export": header, "input_sha256": h.file_hash(source)}
    finally:
        db.close()


def prepare_batches(index, output, source, *, minutes=25, batch_size=20, progress=lambda value: None):
    """Account for EVERY tutor_query; never choose only one request per notebook."""
    output = Path(output)
    output.mkdir(mode=0o700)
    db = sqlite3.connect(index)
    before, after = (5, 20) if minutes == 25 else (3, 7)
    max_records, max_chars = (1500, 450000) if minutes == 25 else (500, 160000)
    coverage = Counter()
    pending, batches = [], []
    export = source.get("export") or {}
    end_boundary = h.timestamp(export.get("until", source["last_event_at"]))
    start_boundary = h.timestamp(export.get("since", source["first_event_at"]))
    def flush():
        if not pending: return
        folder = output / f"batch-{len(batches) + 1:04d}"
        folder.mkdir(mode=0o700)
        sessions = {"sessions": [s.model_dump(mode="json") for s, _, _ in pending]}
        contexts = {s.session_id: ctx for s, ctx, _ in pending}
        manifest = {"format": "session-findings.preparation.v1", "adapter": VERSION,
            "input_file_sha256": source["input_sha256"], "sessions_sha256": h.digest(sessions), "context_sha256": h.digest(contexts),
            "selected_session_ids": list(contexts), "selection": {"method": VERSION, "count": len(pending), "before_minutes": before, "after_minutes": after},
            "contains_private_course_content": True, "historical_fallback": False}
        for name, value in [("sessions.json", sessions), ("context.json", contexts), ("manifest.json", manifest)]:
            h.private_json(folder / name, value)
        batches.append({"folder": folder.name, "count": len(pending)})
        pending.clear()
    try:
        with (output / "coverage.private.jsonl").open("x", encoding="utf-8") as audit:
            os.chmod(audit.name, 0o600)
            anchors = db.execute("SELECT eid,scope,occurred,mode FROM events WHERE kind='tutor_query' ORDER BY occurred,eid")
            for eid, scope, occurred, mode in anchors:
                coverage["tutor_requests"] += 1
                reason, sid = None, None
                if mode != "tutor": reason = "not_tutor_mode"
                elif not scope: reason = "missing_scope"
                elif not occurred: reason = "missing_occurrence_time"
                elif h.timestamp(occurred) < DEPLOYED: reason = "before_production_observation_start"
                elif h.timestamp(occurred) + timedelta(minutes=after) > end_boundary: reason = "awaiting_followup_window"
                if reason is None:
                    at = h.timestamp(occurred)
                    start, end = at - timedelta(minutes=before), at + timedelta(minutes=after)
                    window = {"anchor_event_id": eid, "start": start.isoformat(), "end": end.isoformat(), "before_minutes": before, "after_minutes": after}
                    records, raw_size = [], 0
                    for line, raw in db.execute("SELECT line,raw FROM events WHERE scope=? AND occurred>=? AND occurred<=? ORDER BY occurred,line", (scope, start.isoformat(), end.isoformat())):
                        raw_size += len(raw.encode())
                        if len(records) >= 3000 or raw_size > 64 * 1024**2:
                            reason = "oversized_window"
                            break
                        records.append((line, json.loads(raw)))
                    if reason is None:
                        try:
                            modes = {r["payload"].get("mode") for _, r in records if r["event_type"] == "tutor_query"}
                            if modes != {"tutor"}:
                                reason = "mixed_or_unknown_tutor_mode"
                            else:
                                session, ctx, evidence, quality = recent.normalize_session(records, source["input_sha256"], window=window)
                                anchor_messages = [m for m in session.messages if m.id == eid]
                                if not anchor_messages:
                                    reason = "invalid_anchor_request"
                                elif not any(m.role == "tutor" and m.request_id == anchor_messages[0].request_id for m in session.messages):
                                    reason = "no_completed_response_for_anchor"
                                elif len(session.messages) + len(session.activity) > max_records or len(json.dumps(evidence, ensure_ascii=False)) > max_chars:
                                    reason = "oversized_window"
                                else:
                                    if start < start_boundary:
                                        ctx["warnings"].append("This window reaches before the export start; earlier context is unavailable.")
                                        coverage["eligible_with_partial_start"] += 1
                                    sid = session.session_id
                                    pending.append((session, ctx, evidence))
                                    reason = "eligible"
                                    if len(pending) == batch_size: flush()
                        except (ValueError, TypeError, KeyError):
                            reason = "invalid_observation_links"
                coverage[reason] += 1
                audit.write(json.dumps({"anchor_event_id": eid, "state": reason, "session_id": sid}) + "\n")
                if coverage["tutor_requests"] % 100 == 0:
                    progress({"phase": "Preparing review batches", "requests": coverage["tutor_requests"], "eligible": coverage["eligible"]})
            flush()
        return {"coverage": dict(coverage), "batches": batches,
            "note": "One bounded window per eligible tutor request; overlapping windows are not independent student attempts. Excluded requests are not negative findings."}
    finally:
        db.close()
