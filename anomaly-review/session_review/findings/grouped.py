"""Optional, bounded overlapping-window grouping; never claims verified question identity."""
from collections import Counter
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3

from . import historical as h, recent
from .production import DEPLOYED

VERSION = "pr100-bounded-overlap-groups-v1"


def prepare_batches(index, output, source, *, minutes=25, batch_size=20, gap_minutes=10, max_span_minutes=60, progress=lambda value: None):
    if minutes not in {10, 25} or not 1 <= batch_size <= 20 or not 1 <= gap_minutes <= 25 or not minutes <= max_span_minutes <= 90:
        raise ValueError("Invalid grouping/window limits")
    output = Path(output)
    output.mkdir(mode=0o700)
    # Never write to a source index, including an index used by an active service.
    db = sqlite3.connect(Path(index).resolve().as_uri() + "?mode=ro", uri=True)
    before, after = (5, 20) if minutes == 25 else (3, 7)
    max_records, max_chars = (1500, 450000) if minutes == 25 else (500, 160000)
    export = source.get("export") or {}
    end_boundary = h.timestamp(export.get("until", source["last_event_at"]))
    start_boundary = h.timestamp(export.get("since", source["first_event_at"]))
    coverage, pending, batches = Counter(), [], []
    ledger = (output / "coverage.private.jsonl").open("x", encoding="utf-8")
    os.chmod(ledger.name, 0o600)

    def record(eid, state, unit=None):
        coverage[state] += 1
        ledger.write(json.dumps({"anchor_event_id": eid, "state": state, "session_id": unit}) + "\n")

    def flush():
        if not pending: return
        folder = output / f"batch-{len(batches) + 1:04d}"
        folder.mkdir(mode=0o700)
        sessions = {"sessions": [s.model_dump(mode="json") for s, _ in pending]}
        contexts = {s.session_id: ctx for s, ctx in pending}
        manifest = {"format": "session-findings.preparation.v1", "adapter": VERSION,
            "input_file_sha256": source["input_sha256"], "sessions_sha256": h.digest(sessions), "context_sha256": h.digest(contexts),
            "selected_session_ids": list(contexts), "selection": {"method": VERSION, "count": len(pending),
                "gap_minutes": gap_minutes, "max_span_minutes": max_span_minutes, "before_minutes": before, "after_minutes": after},
            "contains_private_course_content": True, "historical_fallback": False}
        for name, value in [("sessions.json", sessions), ("context.json", contexts), ("manifest.json", manifest)]: h.private_json(folder / name, value)
        batches.append({"folder": folder.name, "count": len(pending)})
        pending.clear()

    def process(group):
        if not group: return
        scope = group[0][1]
        start = group[0][2] - timedelta(minutes=before)
        end = group[-1][2] + timedelta(minutes=after)
        records, raw_bytes, problem = [], 0, None
        for line, raw in db.execute("SELECT line,raw FROM events WHERE scope=? AND occurred>=? AND occurred<=? ORDER BY occurred,line", (scope, start.isoformat(), end.isoformat())):
            raw_bytes += len(raw.encode())
            if len(records) >= 3000 or raw_bytes > 64 * 1024**2: problem = "oversized_window"; break
            records.append((line, json.loads(raw)))
        if problem is None:
            try:
                modes = {r["payload"].get("mode") for _, r in records if r["event_type"] == "tutor_query"}
                if modes != {"tutor"}: problem = "mixed_or_unknown_tutor_mode"
                else:
                    window = {"anchor_event_id": group[0][0], "anchor_event_ids": [r[0] for r in group],
                        "start": start.isoformat(), "end": end.isoformat(), "before_minutes": before, "after_minutes": after,
                        "grouping": VERSION, "verified_question_identity": False}
                    session, ctx, evidence, _ = recent.normalize_session(records, source["input_sha256"], window=window)
                    if len(session.messages) + len(session.activity) > max_records or len(json.dumps(evidence, ensure_ascii=False)) > max_chars:
                        problem = "oversized_window"
            except (ValueError, TypeError, KeyError): problem = "invalid_observation_links"
        if problem:
            # Preserve every original anchor and its before/after context when
            # a group cannot fit. No truncation and no blanket group exclusion.
            if len(group) > 1:
                half = len(group) // 2
                process(group[:half]); process(group[half:])
            else: record(group[0][0], problem)
            return
        by_id = {m.id: m for m in session.messages if m.role == "student"}
        answered = {m.request_id for m in session.messages if m.role == "tutor"}
        members = []
        for eid, _, _ in group:
            if eid not in by_id: record(eid, "invalid_anchor_request")
            elif by_id[eid].request_id not in answered: record(eid, "no_completed_response_for_anchor")
            else: members.append(eid)
        if not members: return
        ctx["group_anchor_event_ids"] = members
        ctx["warnings"].append("This is a bounded time-based group of overlapping tutor-request windows, not a verified question attempt. It may contain several questions; retain conflicting evidence and later recovery.")
        if start < start_boundary:
            ctx["warnings"].append("The export starts inside this window; earlier context is unavailable.")
            coverage["eligible_with_partial_start"] += len(members)
        for eid in members: record(eid, "eligible", session.session_id)
        pending.append((session, ctx))
        coverage["analysis_units"] += 1
        if len(pending) == batch_size: flush()

    try:
        current, last_scope = [], None
        for eid, scope, occurred, mode in db.execute("SELECT eid,scope,occurred,mode FROM events WHERE kind='tutor_query' ORDER BY scope,occurred,eid"):
            coverage["tutor_requests"] += 1
            if mode != "tutor": record(eid, "not_tutor_mode"); continue
            if not scope: record(eid, "missing_scope"); continue
            if not occurred: record(eid, "missing_occurrence_time"); continue
            at = h.timestamp(occurred)
            if at < DEPLOYED: record(eid, "before_production_observation_start"); continue
            if at + timedelta(minutes=after) > end_boundary: record(eid, "awaiting_followup_window"); continue
            if current and (scope != last_scope or (at - current[-1][2]).total_seconds() > min(gap_minutes, minutes) * 60 or
                            (at - current[0][2]).total_seconds() + minutes * 60 > max_span_minutes * 60):
                process(current); current = []
            current.append((eid, scope, at)); last_scope = scope
            if coverage["tutor_requests"] % 100 == 0:
                progress({"phase": "Grouping overlapping windows", "requests": coverage["tutor_requests"], "eligible": coverage["eligible"], "units": coverage["analysis_units"]})
        process(current); flush()
        return {"coverage": dict(coverage), "batches": batches,
            "note": "Bounded time-based grouping changes the analysis unit. The ledger maps every tutor-request record to a group or exclusion; groups are not verified questions or independent student attempts."}
    finally:
        ledger.close(); db.close()
