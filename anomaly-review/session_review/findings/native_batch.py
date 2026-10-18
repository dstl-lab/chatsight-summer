"""Native Gemini Batch API: bounded files, persisted submission IDs and strict collection.

Preparation is offline. Unknown submission outcomes are NEVER automatically retried.
"""
import json
import os
from pathlib import Path
import sqlite3

from . import analyze_sessions as analyzer, historical as h, optimized as opt, provider, runner

VERSION = "session-findings.gemini-batch.v1"
TERMINAL = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}


def state_path(folder): return Path(folder) / "batch-state.private.json"


def read(folder): return json.loads(state_path(folder).read_text())


def save(folder, state): runner.atomic_json(state_path(folder), state)


def field(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def generation_config(config):
    names = {"temperature": "temperature", "response_mime_type": "responseMimeType", "response_json_schema": "responseJsonSchema", "max_output_tokens": "maxOutputTokens"}
    result = {names[k]: v for k, v in config.items() if k in names}
    if "thinking_config" in config: result["thinkingConfig"] = {"thinkingLevel": config["thinking_config"]["thinking_level"].upper()}
    return result


def prepare(prepared_paths, folder, *, model, options, cache_folder, max_chunk_bytes=64 * 1024**2):
    if options.transport != "batch": raise ValueError("Choose the batch transport")
    if not 1024 <= max_chunk_bytes <= 512 * 1024**2: raise ValueError("Invalid provider file limit")
    paths = [Path(p).resolve() for p in prepared_paths]
    folder = Path(folder)
    if folder.exists(): raise FileExistsError(folder)
    folder.mkdir(parents=True, mode=0o700)
    cache = Path(cache_folder).resolve(); cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = {"format": VERSION, "model": model, "inference": options.inference(), "prepared_paths": [str(p) for p in paths],
        "cache_folder": str(cache), "created_at": opt.now(), "chunks": [], "requests": 0, "estimated_tokens": 0,
        "status": "preparing", "enqueued_token_limit": options.batch_enqueued_tokens, "contains_private_course_content": True}
    stream, routes, size = None, {}, 0
    def flush():
        nonlocal stream, routes, size
        if stream is None: return
        stream.close()
        name = Path(stream.name).name
        route_name = name + ".routes.json"
        h.private_json(folder / route_name, routes)
        state["chunks"].append({"input": name, "sha256": h.file_hash(folder / name), "routes": route_name,
            "routes_sha256": h.file_hash(folder / route_name), "count": len(routes), "estimated_tokens": sum(r["input"]["estimated_tokens"] for r in routes.values()),
            "status": "planned", "remote_name": None})
        stream, routes, size = None, {}, 0
        save(folder, state)
    try:
        for path in paths:
            opt.plan(path, model, options)
            opt.saved_results(path, model, options)
        for unit in opt.units(paths, model, options):
            if unit.receipt.exists(): continue
            text, config, metrics = provider.payload(unit.evidence, options)
            key = provider.fingerprint(text, config, model, options)
            cached = cache / (key + ".json")
            if cached.exists():
                old = json.loads(cached.read_text())
                receipt = opt.receipt_for(unit, key, metrics, transport="batch")
                h.private_json(unit.receipt, receipt)
                if old.get("status") == "completed":
                    result = provider.CallResult(analyzer.Assessment.model_validate(old["assessment"]), {}, 0)
                    opt.complete(unit, receipt, result, reused=True)
                else: runner.atomic_json(unit.receipt, {**receipt, "status": "failed", "error_type": "PriorIdenticalRequestUnresolved", "logical_requests": 0})
                continue
            line = (json.dumps({"key": key, "request": {"contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": generation_config(config)}}, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            if len(line) > max_chunk_bytes: raise ValueError("One request exceeds the provider-file size setting")
            if options.batch_enqueued_tokens and metrics["estimated_tokens"] > options.batch_enqueued_tokens: raise ValueError("One request exceeds the native batch token allowance")
            queued = sum(r["input"]["estimated_tokens"] for r in routes.values())
            if stream is not None and (size + len(line) > max_chunk_bytes or len(routes) >= 1000 or
                    options.batch_enqueued_tokens and queued + metrics["estimated_tokens"] > options.batch_enqueued_tokens): flush()
            if stream is None:
                stream = (folder / f"requests-{len(state['chunks']) + 1:04d}.jsonl").open("xb")
                os.chmod(stream.name, 0o600)
            if key in routes: raise ValueError("Duplicate analysis request key")
            stream.write(line); size += len(line)
            routes[key] = {"prepared": str(unit.prepared), "session_id": unit.session.session_id,
                "evidence_sha256": h.digest(unit.evidence), "config_sha256": unit.config_sha256, "input": metrics}
            state["requests"] += 1; state["estimated_tokens"] += metrics["estimated_tokens"]
        flush()
        if options.max_requests and state["requests"] > options.max_requests: raise ValueError("Native batch exceeds the configured request budget; prepare fewer units or raise it explicitly")
        if options.max_estimated_tokens and state["estimated_tokens"] > options.max_estimated_tokens: raise ValueError("Native batch exceeds the configured estimated-token run budget")
        state["status"] = "ready" if state["requests"] else "completed"
        save(folder, state)
        return state
    except Exception:
        if stream is not None: stream.close()
        state["status"] = "preparation_failed"
        save(folder, state)
        raise


def routes_for(folder, chunk):
    path = Path(folder) / chunk["routes"]
    if path.is_symlink() or h.file_hash(path) != chunk["routes_sha256"]: raise ValueError("Provider routes changed")
    return json.loads(path.read_text())


def resolver(state, options):
    """Keep only one prepared batch in memory; routes are processed in batch order."""
    current, loaded = None, {}
    def get(route):
        nonlocal current, loaded
        if route["prepared"] not in state["prepared_paths"]: raise ValueError("Unknown prepared path")
        if current != route["prepared"]:
            loaded = {u.session.session_id: u for u in opt.units([route["prepared"]], state["model"], options)}
            current = route["prepared"]
        unit = loaded.get(route["session_id"])
        if not unit or h.digest(unit.evidence) != route["evidence_sha256"] or unit.config_sha256 != route["config_sha256"]:
            raise ValueError("Prepared evidence changed")
        return unit
    return get


def validate_state(state, options):
    if state.get("format") != VERSION or state.get("inference") != options.inference(): raise ValueError("Native batch configuration changed")
    if state["status"] in {"preparing", "preparation_failed"}: raise ValueError("Native batch preparation is incomplete")


def submit(folder, *, options, api, send=False):
    if not send: raise ValueError("Explicit --send is required before uploading course evidence")
    folder = Path(folder); state = read(folder); validate_state(state, options)
    resolve = resolver(state, options)
    # Polling existing jobs must not repeatedly hash/load the entire evidence
    # corpus. Preflight only the next quota wave, before any new submission.
    active_tokens = sum(c["estimated_tokens"] for c in state["chunks"] if c.get("remote_name") and c["status"] not in {"completed", "failed"})
    active_jobs = sum(bool(c.get("remote_name")) and c["status"] not in {"completed", "failed"} for c in state["chunks"])
    selected = []
    for chunk in state["chunks"]:
        if chunk["status"] == "submitting" and not chunk.get("remote_name"):
            raise ValueError("Prior submission outcome is unknown. Attach its remote job ID; do not resubmit")
        if chunk.get("remote_name") or chunk["status"] == "completed": continue
        if chunk["status"] != "planned": raise ValueError("Native batch is not ready for a fresh submission")
        if active_jobs >= 100 or state.get("enqueued_token_limit") and active_tokens + chunk["estimated_tokens"] > state["enqueued_token_limit"]:
            continue  # Leave later waves untouched until earlier jobs finish.
        selected.append(chunk)
        active_jobs += 1; active_tokens += chunk["estimated_tokens"]
    for chunk in selected:
        if h.file_hash(folder / chunk["input"]) != chunk["sha256"]: raise ValueError("Provider input file changed")
        for route in routes_for(folder, chunk).values(): resolve(route)
    cache = Path(state["cache_folder"])
    for chunk in selected:
        chunk["status"] = "submitting"; chunk["submission_started_at"] = opt.now(); save(folder, state)
        for key, route in routes_for(folder, chunk).items():
            unit = resolve(route)
            if unit.receipt.exists(): raise ValueError("A native batch request is already reserved")
            h.private_json(cache / (key + ".json"), {"status": "pending", "request_key": key, "transport": "batch"})
            h.private_json(unit.receipt, opt.receipt_for(unit, key, route["input"], transport="batch"))
        # Persist an intent BEFORE both network operations. A lost response must
        # not lead to a second paid batch when the service is restarted.
        uploaded = api.files.upload(file=str(folder / chunk["input"]), config={"mime_type": "application/jsonl", "display_name": f"session-findings-{chunk['sha256'][:16]}"})
        chunk["uploaded_file"] = field(uploaded, "name"); save(folder, state)
        job = api.batches.create(model=state["model"], src=chunk["uploaded_file"], config={"display_name": f"session-findings-{chunk['sha256'][:16]}"})
        name = field(job, "name")
        if not name: raise ValueError("Provider returned no batch identity; submission remains unresolved")
        chunk.update(remote_name=name, status="submitted"); save(folder, state)
    if selected: state["status"] = "submitted"
    save(folder, state)
    return state


def attach(folder, *, chunk_number, remote_name):
    state = read(folder)
    if not remote_name.startswith("batches/") or not 1 <= chunk_number <= len(state["chunks"]): raise ValueError("Invalid provider batch identity")
    chunk = state["chunks"][chunk_number - 1]
    if chunk.get("remote_name") or chunk["status"] != "submitting": raise ValueError("Only an unresolved submission can be attached")
    chunk.update(remote_name=remote_name, status="submitted"); state["status"] = "submitted"; save(folder, state)


def parse_response(response):
    candidates = response.get("candidates") or []
    if not candidates or candidates[0].get("finishReason", candidates[0].get("finish_reason")) != "STOP": raise ValueError("Incomplete batch response")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return provider.CallResult(analyzer.Assessment.model_validate_json(text), provider.usage(response.get("usageMetadata", response.get("usage_metadata"))), None)


def collect(folder, *, options, api):
    folder = Path(folder); state = read(folder); validate_state(state, options)
    cache = Path(state["cache_folder"])
    resolve = resolver(state, options)
    for number, chunk in enumerate(state["chunks"], 1):
        if chunk["status"] in {"completed", "failed"} or not chunk.get("remote_name"): continue
        job = api.batches.get(name=chunk["remote_name"])
        job_state = field(job, "state")
        job_state = getattr(job_state, "value", job_state)
        chunk["provider_state"] = job_state; save(folder, state)
        if job_state not in TERMINAL: continue
        routes = routes_for(folder, chunk)
        if job_state != "JOB_STATE_SUCCEEDED":
            for key, route in routes.items():
                unit = resolve(route)
                receipt = json.loads(unit.receipt.read_text())
                if receipt["status"] != "completed": runner.atomic_json(unit.receipt, {**receipt, "status": "failed", "error_type": job_state, "finished_at": opt.now()})
            chunk["status"] = "failed"; save(folder, state); continue
        output = folder / f"responses-{number:04d}.jsonl"
        if not output.exists():
            remote_file = field(field(job, "dest"), "file_name")
            if not remote_file: raise ValueError("Completed provider batch has no result file")
            temporary = output.with_suffix(".partial")
            with temporary.open("wb") as target:
                os.chmod(temporary, 0o600)
                api.files.download(file=remote_file, destination=target)
            temporary.rename(output)
        if chunk.get("output_sha256") and h.file_hash(output) != chunk["output_sha256"]: raise ValueError("Saved provider result file changed")
        seen = set()
        # Provider output can be arbitrarily ordered. Index it on disk so each
        # prepared batch is loaded once, rather than once per response record.
        output_index = output.with_suffix(".sqlite")
        db = sqlite3.connect(output_index)
        os.chmod(output_index, 0o600)
        try:
            db.execute("DROP TABLE IF EXISTS responses")
            db.execute("CREATE TABLE responses (key TEXT PRIMARY KEY, raw TEXT)")
            with output.open("rb") as stream:
                while line := stream.readline(8 * 1024**2 + 1):
                    if len(line) > 8 * 1024**2: raise ValueError("Oversized provider result line")
                    value = json.loads(line); key = value.get("key")
                    if key not in routes or key in seen: raise ValueError("Unknown or duplicate provider result key")
                    seen.add(key); db.execute("INSERT INTO responses VALUES (?,?)", (key, line.decode()))
            db.commit()
            for key, route in routes.items():
                unit = resolve(route)
                receipt = json.loads(unit.receipt.read_text())
                if receipt["status"] == "completed": continue
                row = db.execute("SELECT raw FROM responses WHERE key=?", (key,)).fetchone()
                if row is None:
                    runner.atomic_json(unit.receipt, {**receipt, "status": "failed", "error_type": "MissingBatchResponse", "finished_at": opt.now()})
                    continue
                value = json.loads(row[0])
                try:
                    if value.get("error") or not isinstance(value.get("response"), dict): raise ValueError("Provider batch record failed")
                    result = parse_response(value["response"])
                    opt.complete(unit, receipt, result)
                    runner.atomic_json(cache / (key + ".json"), {"status": "completed", "assessment": result.assessment.model_dump(mode="json")})
                except (ValueError, KeyError, TypeError):
                    runner.atomic_json(unit.receipt, {**receipt, "status": "failed", "error_type": "InvalidOrFailedBatchResponse", "finished_at": opt.now()})
        finally:
            db.close()
        chunk.update(status="completed", output_sha256=h.file_hash(output), collected_at=opt.now()); save(folder, state)
    state["status"] = "completed" if all(c["status"] in {"completed", "failed"} for c in state["chunks"]) else "submitted"
    save(folder, state)
    return {**opt.statistics(state["prepared_paths"]), "provider_status": state["status"],
            "remote_jobs": [{"name": c.get("remote_name"), "status": c["status"], "provider_state": c.get("provider_state")} for c in state["chunks"]]}
