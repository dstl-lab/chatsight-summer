"""One durable receipt per selected session; interrupted/failed requests are not rerolled."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from . import analyze_sessions as analyzer
from .historical import digest, private_json


def atomic_json(path, value):
    if path.is_symlink():
        raise ValueError("Refusing a symlink receipt.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def configuration(sessions, evidence, model):
    return {"version": 1, "model": model, "session_ids": [s.session_id for s in sessions],
        "evidence_sha256": digest(evidence),
        "prompt_sha256": hashlib.sha256(analyzer.PROMPT.encode()).hexdigest(),
        "schema_sha256": digest(analyzer.Assessment.model_json_schema()),
        "analyzer_sha256": hashlib.sha256(Path(analyzer.__file__).read_bytes()).hexdigest()}


def saved_results(folder, sessions, evidence, model):
    folder = Path(folder)
    config = configuration(sessions, evidence, model)
    plan_path = folder / "plan.json"
    if not plan_path.exists():
        return {}
    if plan_path.is_symlink() or json.loads(plan_path.read_text()) != config:
        raise ValueError("Analysis configuration changed; use a new output directory.")
    results = {}
    for session, item in zip(sessions, evidence):
        path = folder / (digest(session.session_id) + ".json")
        if not path.exists():
            continue
        if path.is_symlink():
            raise ValueError("Receipt must not be a symlink.")
        receipt = json.loads(path.read_text())
        if receipt.get("config_sha256") != digest(config) or receipt.get("evidence_sha256") != digest(item):
            raise ValueError("Saved receipt does not match evidence/configuration.")
        if receipt["status"] == "completed":
            assessment = analyzer.Assessment.model_validate(receipt["assessment"])
            result = analyzer.validate_assessment(session, item, assessment)
        else:
            result = {"session_id": session.session_id, "decision": "insufficient_evidence",
                "validation_status": "rejected", "scope": "hypothetical_scenario" if "synthetic" in item["origins"] else "recorded_evidence",
                "assessment": {"summary": "Assessment unavailable; no finding accepted.", "findings": []},
                "validation_errors": ["Interrupted request preserved; no automatic retry." if receipt["status"] == "pending" else "Assessment unavailable; no automatic retry."],
                "notices": item["warnings"], "semantic_interpretations_verified": False}
        results[session.session_id] = result
    return results


def run(folder, sessions, evidence, *, model, send=False, generate=None):
    if not send:
        raise ValueError("Analysis requires --send; selected evidence will be sent to Gemini.")
    if len(sessions) > 20:
        raise ValueError("Initial real-data pilot is capped at 20 sessions.")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.is_symlink():
        raise ValueError("Analysis folder cannot be a symlink.")
    config = configuration(sessions, evidence, model)
    plan = folder / "plan.json"
    if not plan.exists():
        private_json(plan, config)
    saved_results(folder, sessions, evidence, model)  # Complete preflight before any send.
    generate = generate or analyzer.generate
    for session, item in zip(sessions, evidence):
        path = folder / (digest(session.session_id) + ".json")
        if path.exists():
            continue
        receipt = {"status": "pending", "config_sha256": digest(config),
            "evidence_sha256": digest(item), "logical_requests": 1,
            "provider_attempts": "SDK transport attempts unmeasured", "assessment": None}
        private_json(path, receipt)  # Exclusive create guards concurrent duplicate sends.
        try:
            assessment = generate(item, model)
            receipt.update(status="completed", assessment=assessment.model_dump(mode="json"))
            stop_batch = False
        except Exception as error:
            # Provider diagnostics may contain prompts/credentials; preserve only its type.
            receipt.update(status="failed", error_type=type(error).__name__)
            stop_batch = getattr(error, "code", None) in {401, 403, 404, 429} or type(error).__name__ == "ConnectError"
        atomic_json(path, receipt)
        if stop_batch:
            break  # Preserve this failure; do not repeat account/network errors across the pilot.
    return saved_results(folder, sessions, evidence, model)
