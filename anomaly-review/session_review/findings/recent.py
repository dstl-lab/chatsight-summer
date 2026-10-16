"""PR100 observations: explicit request/execution bindings, actual edit summaries."""
from collections import Counter, defaultdict
from datetime import timedelta
import hashlib
import json
from pathlib import Path

from . import analyze_sessions as analyzer
from .historical import digest, file_hash, private_json, rows, timestamp, source_ref

VERSION = "pr100-notebook-observation-windows-v1"
BEFORE_MINUTES = 3
AFTER_MINUTES = 7


def scope(row):
    payload = row["payload"]
    values = (row.get("user_email"), payload.get("analytics_session_id"), payload.get("notebook_session_id"))
    return values if all(isinstance(value, str) and value.strip() for value in values) else None


def common(row, *, ref=None):
    payload = row["payload"]
    at = payload.get("timestamp")
    timestamp(at)  # Event-specific client timestamp; no server-time substitution.
    return {"id": ref or payload["event_id"], "timestamp": at, "origin": "recorded", "question_id": None,
            "cell_id": payload.get("cell_id") or payload.get("active_cell_id"),
            "order_stream_id": payload["analytics_session_id"], "sequence": payload["client_sequence"],
            "timestamp_basis": "event_specific_client_timestamp"}


def task_note(payload):
    ctx = payload.get("task_context") or payload.get("active_task_context") or {}
    if not isinstance(ctx, dict):
        ctx = {}
    return f'Task context: {ctx.get("task_id") or "unknown"}; attribution: {ctx.get("attribution") or "unknown"}. This is notebook structure, not verified question intent.'


def normalize_session(records, input_hash, *, window=None):
    """Build the full observed page/notebook scope, retaining exact source provenance."""
    quality = Counter()
    by_uuid = {}
    by_seq = {}
    usable = []
    for line, row in records:
        p = row["payload"]
        eid, seq = p.get("event_id"), p.get("client_sequence")
        if not isinstance(eid, str) or not eid or type(seq) is not int or seq < 1:
            quality["invalid_event_identity_or_sequence"] += 1
            continue
        try:
            timestamp(p.get("timestamp"))
        except (TypeError, ValueError):
            # Some legacy/non-observation events have only client logging time;
            # retain them in the source export, not as timed model observations.
            quality["missing_event_specific_timestamp"] += 1
            continue
        if eid in by_uuid:
            if digest(by_uuid[eid]) != digest(row):
                raise ValueError("Conflicting event UUID within observation scope.")
            quality["duplicate_event_uuid"] += 1
            continue
        if seq in by_seq:
            raise ValueError("Conflicting client sequence within one page/notebook scope.")
        by_uuid[eid] = row
        by_seq[seq] = row
        usable.append((line, row))
    usable.sort(key=lambda item: (timestamp(item[1]["payload"]["timestamp"]), item[1]["payload"]["client_sequence"]))
    if not usable:
        raise ValueError("No valid PR100 observations")
    account, page, notebook_session = scope(usable[0][1])
    session_id = "pr100-" + digest([account, page, notebook_session, window])[:24]
    messages, activity, display, sources = [], [], [], {}
    warnings = [
        "Recent PR100 production observations; recorded notebook actions, not historical chat-only data.",
        "Scope is one page/notebook observation session and may contain several tutor conversations/questions.",
        "Task metadata and active-cell context do not establish the subject of a tutor request. Question intent remains unknown.",
        "Source captures at execution/request time are not edit events; actual edit summaries omit source text.",
        "Check verdicts are text heuristics for the bound command, not proof of answer correctness, kernel memory, or learning.",
        "Observation end is the export boundary; missing events, page reloads, foreign executions and silent work may remain unobserved.",
        "Client sequence orders logging calls; occurrence timestamps govern event-time order. Retained page sequence gaps may include other notebooks or excluded events.",
    ]
    if window:
        warnings.append(f'Fixed observation window: {window["start"]} through {window["end"]}; 3 minutes before and 7 after the anchor request. Events outside it, including later recovery, are not analyzed. This is not a complete question attempt.')
    request_rows = defaultdict(list)
    response_rows = defaultdict(list)
    execution_rows = defaultdict(list)
    finish_rows = defaultdict(list)
    for line, row in usable:
        p, kind = row["payload"], row["event_type"]
        eid = p["event_id"]
        sources[eid] = {**source_ref(line, row, input_hash), "timestamp_basis": "event_specific_client_timestamp", "adapter": VERSION}
        if kind == "tutor_query": request_rows[p.get("request_id")].append((line, row))
        if kind in {"tutor_response", "tutor_request_failed"}: response_rows[p.get("request_id")].append((line, row))
        key = (p.get("kernel_id"), p.get("execution_id"), p.get("cell_id"))
        if kind == "notebook_execution_requested": execution_rows[key].append((line, row))
        if kind == "notebook_execution_finished": finish_rows[key].append((line, row))
    revision_by_execution, execution_id_by_key, valid_queries = {}, {}, set()
    for rid, queries in request_rows.items():
        if rid and len(queries) == 1:
            p = queries[0][1]["payload"]
            request = p.get("request")
            if isinstance(request, dict) and request.get("request_id") == rid and isinstance(p.get("question"), str) and p["question"].strip():
                valid_queries.add(rid)
    for key, submitted in execution_rows.items():
        if not all(key) or len(submitted) != 1 or len(finish_rows.get(key, [])) > 1:
            quality["ambiguous_execution_binding"] += 1
            continue
        line, row = submitted[0]
        p = row["payload"]
        if not isinstance(p.get("source"), str) or p.get("source_capture") != "execute_request":
            quality["unverified_execution_source"] += 1
            continue
        ref = "source-" + p["event_id"]
        binding = "exec-" + digest([page, *key])[:24]
        revision = "revision-" + digest([page, *key, p["source"]])[:24]
        activity.append({**common(row, ref=ref), "type": "revision", "revision_id": revision,
                         "source": p["source"], "capture_basis": "execution_capture"})
        sources[ref] = sources[p["event_id"]]
        revision_by_execution[key] = (revision, row, ref)
        execution_id_by_key[key] = binding
    for line, row in usable:
        p, kind = row["payload"], row["event_type"]
        eid = p["event_id"]
        base = common(row)
        key = (p.get("kernel_id"), p.get("execution_id"), p.get("cell_id"))
        meta = [{"label": "Client sequence", "value": str(p["client_sequence"])},
                {"label": "Task context", "value": task_note(p)}]
        if kind == "tutor_query":
            request = p.get("request")
            rid = p.get("request_id")
            if rid not in valid_queries:
                quality["invalid_or_duplicate_tutor_request_binding"] += 1
                continue
            text = p.get("question")
            if not isinstance(text, str) or not text.strip():
                quality["missing_question_text"] += 1
                continue
            messages.append({**base, "role": "student", "text": text, "request_id": rid})
            quality["tutor_requests"] += 1
            raw_snapshot, expected_hash = request.get("notebook_json"), p.get("notebook_sha256")
            hash_valid = isinstance(raw_snapshot, str) and isinstance(expected_hash, str) and hashlib.sha256(raw_snapshot.encode()).hexdigest() == expected_hash
            quality["request_snapshot_hash_verified" if hash_valid else "request_snapshot_hash_unverified"] += 1
            if hash_valid:
                try:
                    notebook = json.loads(raw_snapshot)
                    cells = notebook.get("cells", []) if isinstance(notebook, dict) else []
                    active = [cell for cell in cells if isinstance(cell, dict) and cell.get("id") == p.get("active_cell_id") and cell.get("cell_type") == "code"]
                    if len(active) == 1 and isinstance(active[0].get("source"), str):
                        ref = "snapshot-" + eid
                        activity.append({**common(row, ref=ref), "type": "revision", "revision_id": ref,
                            "source": active[0]["source"], "capture_basis": "request_snapshot"})
                        sources[ref] = sources[eid]
                except ValueError:
                    quality["invalid_snapshot_json"] += 1
            meta.extend([{"label": "Request", "value": rid}, {"label": "Snapshot SHA256", "value": "Verified" if hash_valid else "Unverified"}])
        elif kind == "tutor_response":
            rid, text = p.get("request_id"), p.get("response")
            matched = rid in valid_queries and len(response_rows.get(rid, [])) == 1
            if not matched or p.get("status") != "completed" or not isinstance(text, str) or not text.strip():
                quality["unmatched_or_incomplete_tutor_response"] += 1
                continue
            query = request_rows[rid][0][1]
            if timestamp(query["payload"]["timestamp"]) > timestamp(p["timestamp"]):
                quality["reversed_tutor_response_time"] += 1
                continue
            messages.append({**base, "role": "tutor", "text": text, "request_id": rid})
            quality["matched_completed_tutor_responses"] += 1
            meta.extend([{"label": "Request", "value": rid}, {"label": "Completion", "value": "Client observed completed stream"}])
        elif kind == "notebook_execution_finished":
            submitted = revision_by_execution.get(key)
            valid = submitted and timestamp(submitted[1]["payload"]["timestamp"]) <= timestamp(p["timestamp"])
            if not valid or p.get("source") != submitted[1]["payload"].get("source"):
                quality["unmatched_or_conflicting_execution_result"] += 1
                continue
            status = "success" if p.get("status") == "ok" else "error" if p.get("status") == "error" else "unknown"
            activity.append({**base, "type": "execution", "execution_id": execution_id_by_key[key],
                "revision_id": submitted[0], "kernel_id": p.get("kernel_id"), "status": status,
                "output": p.get("output") if isinstance(p.get("output"), str) else None,
                "output_complete": p.get("output_complete") if type(p.get("output_complete")) is bool else None})
            quality["matched_execution_results"] += 1
            meta.append({"label": "Execution", "value": str(p["execution_id"])})
        elif kind == "autograder_info":
            finishes = finish_rows.get(key, [])
            submitted = revision_by_execution.get(key)
            matched = bool(submitted) and len(finishes) == 1 and p.get("checked_source") == submitted[1]["payload"].get("source")
            if matched and timestamp(finishes[0][1]["payload"]["timestamp"]) > timestamp(p["timestamp"]):
                matched = False
            # A result must have been accepted as an actual finished execution above.
            accepted_execs = {r["execution_id"] for r in activity if r.get("type") == "execution"}
            binding = execution_id_by_key.get(key)
            matched = matched and binding in accepted_execs
            success = p.get("success")
            result = "pass" if success is True else "fail" if success is False else "unknown"
            if not p.get("output_complete") or p.get("execution_status") != "ok":
                result = "unknown"
            activity.append({**base, "type": "check", "check_id": eid,
                "execution_id": binding if matched else None, "result": result,
                "feedback": p.get("output") if isinstance(p.get("output"), str) else None,
                "grader_id": str(p.get("grader_id")) if p.get("grader_id") else None,
                "verdict_method": p.get("verdict_method")})
            quality["matched_execution_checks" if matched else "unlinked_checks"] += 1
            meta.extend([{"label": "Grader", "value": str(p.get("grader_id") or "Unknown")},
                         {"label": "Execution binding", "value": "Verified" if matched else "Unknown"}])
        elif kind == "notebook_cell_source_changed":
            activity.append({**base, "type": "edit_observation", "source_revision": p.get("source_revision"),
                "description": f'Recorded edit burst: {p.get("source_change_count")} source changes; final source length {p.get("source_length")}; interval {p.get("edit_started_at")} to {p.get("edit_ended_at")}. Source text is not included in this edit event. ' + task_note(p)})
            quality["edit_observations"] += 1
        elif kind in {"notebook_cell_created", "notebook_cell_deleted", "notebook_cell_moved", "notebook_active_cell_changed", "notebook_cell_task_context_changed"}:
            activity.append({**base, "type": "cell_observation", "description": f'Recorded {kind}: cell {p.get("cell_id")}, index {p.get("cell_index")}. ' + task_note(p)})
            quality["cell_observations"] += 1
        elif kind == "tutor_request_failed":
            activity.append({**base, "type": "tutor_failure", "description": f'Tutor request terminal status: {p.get("status")}; request {p.get("request_id")}. Any partial response is not a completed tutor answer.'})
            quality["tutor_failures"] += 1
        elif kind == "notebook_execution_requested":
            # The captured source becomes a typed capture above; preserve the raw
            # submit event as a UI observation distinct from completion.
            meta.append({"label": "Execution", "value": str(p.get("execution_id"))})
        else:
            quality["context_only_rows"] += 1
            continue
        display.append({"event_id": eid, "metadata": meta, "event_type": kind,
                        "occurred_at": p["timestamp"], "source_line": line})
    session = analyzer.Session(session_id=session_id, messages=messages, activity=activity)
    evidence = analyzer.assemble(session)
    evidence["warnings"].extend(warnings)
    ctx = {"student_id": account, "notebook": usable[0][1]["payload"].get("notebook_path") or usable[0][1]["payload"].get("notebook_name"),
        "scope": "notebook_session", "events": [], "sources": sources, "warnings": warnings,
        "observations": display, "quality": dict(quality), "page_id": page, "notebook_session_id": notebook_session,
        "window": window}
    # Keep UI submit observations that do not already have an analysis record.
    analysis_refs = {r.id for r in [*session.messages, *session.activity]}
    for item in display:
        if item["event_id"] not in analysis_refs:
            ctx["events"].append({"id": item["event_id"], "source_event_id": item["event_id"],
                "kind": "activity", "actor": "Notebook", "title": "Execution submitted",
                "body": "Recorded execute_request submission; completion is a separate linked event.",
                "occurred_at": item["occurred_at"], "phase": "unpartitioned", "order_uncertain": False,
                "source_pointers": [f'line:{item["source_line"]}'], "metadata": item["metadata"], "code_diff": None})
    return session, ctx, evidence, quality


def prepare(path, destination, *, count=5, seed=15, max_records=500, max_characters=160000):
    """Freeze fixed observation windows; no historical fallback, no model call."""
    path, destination = Path(path), Path(destination)
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("Choose 1–20 recent notebook observation sessions.")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    groups = defaultdict(list)
    input_hash = file_hash(path)
    accounting = Counter()
    for line, row in rows(path, accounting):
        if row["payload"].get("schema_version") != 1:
            accounting["not_pr100_schema"] += 1
            continue
        key = scope(row)
        if key is None:
            accounting["missing_page_notebook_identity"] += 1
            continue
        groups[key].append((line, row))
    eligible, exclusions, window_counts = [], Counter(), Counter()
    for key, records in groups.items():
        candidates = []
        anchors = [row for _, row in records if row["event_type"] == "tutor_query" and row["payload"].get("mode") == "tutor"]
        for anchor in anchors:
            window_counts["candidate_windows"] += 1
            try:
                at = timestamp(anchor["payload"].get("timestamp"))
                start, end = at - timedelta(minutes=BEFORE_MINUTES), at + timedelta(minutes=AFTER_MINUTES)
                window = {"anchor_event_id": anchor["payload"].get("event_id"), "start": start.isoformat(), "end": end.isoformat()}
                observed = []
                for line, row in records:
                    try:
                        occurred = timestamp(row["payload"].get("timestamp"))
                    except (TypeError, ValueError):
                        continue
                    if start <= occurred <= end:
                        observed.append((line, row))
                query_modes = {row["payload"].get("mode") for _, row in observed if row["event_type"] == "tutor_query"}
                if query_modes != {"tutor"}:
                    exclusions["mixed_or_unknown_mode_window"] += 1
                    continue
                session, ctx, evidence, quality = normalize_session(observed, input_hash, window=window)
                required = ["tutor_requests", "matched_completed_tutor_responses", "matched_execution_results", "matched_execution_checks", "edit_observations", "request_snapshot_hash_verified"]
                if not all(quality[name] for name in required):
                    exclusions["missing_required_observation_family"] += 1
                    continue
                serialized = json.dumps(evidence, ensure_ascii=False)
                if len(session.messages) + len(session.activity) > max_records or len(serialized) > max_characters:
                    exclusions["oversized_observation_window"] += 1
                    continue
                candidates.append((session, ctx, evidence))
            except ValueError:
                exclusions["invalid_observation_links"] += 1
        window_counts["eligible_windows"] += len(candidates)
        if candidates:
            # At most one window per page/notebook; no model result or pass/fail
            # value participates in selection. Coverage requirements bias this
            # development sample and are not a detection-performance benchmark.
            candidates.sort(key=lambda item: digest([seed, item[0].session_id]))
            eligible.append(candidates[0])
    eligible.sort(key=lambda item: digest([seed, item[0].session_id]))
    if len(eligible) < count:
        raise ValueError(f"Only {len(eligible)} recent notebook scopes have eligible bounded windows; requested {count}. Exclusions: {dict(exclusions)}")
    selected = eligible[:count]
    sessions_doc = {"sessions": [s.model_dump(mode="json") for s, _, _ in selected]}
    contexts = {s.session_id: ctx for s, ctx, _ in selected}
    if file_hash(path) != input_hash:
        raise ValueError("Source changed during preparation")
    manifest = {"format": "session-findings.preparation.v1", "adapter": VERSION, "origin": "recorded",
        "input_file_sha256": input_hash, "sessions_sha256": digest(sessions_doc), "context_sha256": digest(contexts),
        "selected_session_ids": [s.session_id for s, _, _ in selected], "quality": dict(accounting),
        "eligible_notebook_sessions": len(eligible), "window_counts": dict(window_counts), "exclusions": dict(exclusions),
        "selection": {"count": count, "seed": seed, "max_records": max_records, "max_evidence_characters": max_characters,
                      "method": "fixed-seeded-coverage-windows-v1", "before_minutes": BEFORE_MINUTES, "after_minutes": AFTER_MINUTES,
                      "purpose": "coverage-selected development integration test, not representative evaluation; later recovery outside window is unobserved"},
        "source_basename": path.name, "contains_private_course_content": True,
        "historical_fallback": False, "sends_source_captures_and_execution_outputs": True}
    destination.mkdir(parents=True, mode=0o700)
    for name, value in [("sessions.json", sessions_doc), ("context.json", contexts), ("manifest.json", manifest)]:
        private_json(destination / name, value)
    return manifest
