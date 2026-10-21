"""Opt-in bounded concurrency, independent receipts, rate budgets and measurements."""
from collections import deque
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

from . import analyze_sessions as analyzer, historical as h, provider, runner

VERSION = "session-findings.optimized.v1"


def now(): return datetime.now(timezone.utc).isoformat()


def configuration(sessions, evidence, model, options):
    return {**runner.configuration(sessions, evidence, model), "version": VERSION, "inference": options.inference()}


def plan(prepared, model, options):
    prepared = Path(prepared)
    _, sessions, _, evidence = h.load_prepared(prepared)
    config = configuration(sessions, evidence, model, options)
    folder = prepared / "analysis-optimized"
    folder.mkdir(mode=0o700, exist_ok=True)
    path = folder / "plan.json"
    if not path.exists(): h.private_json(path, config)
    if path.is_symlink() or json.loads(path.read_text()) != config:
        raise ValueError("Optimized configuration changed. Use a separate prepared run; existing receipts are immutable.")
    return folder, config, sessions, evidence


@dataclass
class Unit:
    prepared: Path
    folder: Path
    config_sha256: str
    session: analyzer.Session
    evidence: dict

    @property
    def receipt(self): return self.folder / (h.digest(self.session.session_id) + ".json")


def units(prepared_paths, model, options):
    for prepared in prepared_paths:
        folder, config, sessions, evidence = plan(prepared, model, options)
        for session, item in zip(sessions, evidence):
            yield Unit(Path(prepared), folder, h.digest(config), session, item)


def saved_results(prepared, model, options):
    folder = Path(prepared) / "analysis-optimized"
    if not (folder / "plan.json").exists(): return {}
    _, config, sessions, evidence = plan(prepared, model, options)
    results = {}
    for session, item in zip(sessions, evidence):
        path = folder / (h.digest(session.session_id) + ".json")
        if not path.exists(): continue
        if path.is_symlink(): raise ValueError("Refusing a symlink receipt")
        receipt = json.loads(path.read_text())
        if receipt.get("config_sha256") != h.digest(config) or receipt.get("evidence_sha256") != h.digest(item):
            raise ValueError("Receipt/evidence mismatch")
        if receipt["status"] == "completed":
            assessment = analyzer.Assessment.model_validate(receipt["assessment"])
            results[session.session_id] = analyzer.validate_assessment(session, item, assessment)
        else:
            results[session.session_id] = {"session_id": session.session_id, "decision": "insufficient_evidence", "validation_status": "rejected",
                "scope": "hypothetical_scenario" if "synthetic" in item["origins"] else "recorded_evidence",
                "assessment": {"summary": "Assessment unavailable; no finding accepted.", "findings": []},
                "validation_errors": ["Assessment unavailable; pending or failed optimized request preserved without automatic resend."],
                "notices": item["warnings"], "semantic_interpretations_verified": False}
    return results


@dataclass
class Reservation:
    at: float
    input_tokens: int


class RateLimiter:
    def __init__(self, rpm, tpm, *, window_seconds=60):
        self.rpm, self.tpm, self.window = rpm, tpm, window_seconds
        self.entries = deque()
        self.lock = threading.Lock()

    def acquire(self, tokens, stop):
        if tokens > self.tpm: raise ValueError("A single request exceeds the configured TPM budget")
        while not stop.is_set():
            with self.lock:
                at = time.monotonic()
                while self.entries and self.entries[0].at <= at - self.window: self.entries.popleft()
                if len(self.entries) < self.rpm and sum(r.input_tokens for r in self.entries) + tokens <= self.tpm:
                    entry = Reservation(at, tokens)
                    self.entries.append(entry)
                    return entry
                delay = min(1.0, max(.001, self.entries[0].at + self.window - at))
            stop.wait(delay)
        return False

    def reconcile(self, reservation, input_tokens):
        if type(input_tokens) is int and input_tokens > 0:
            with self.lock: reservation.input_tokens = input_tokens


def receipt_for(unit, key, statistics, *, transport="concurrent"):
    return {"status": "pending", "config_sha256": unit.config_sha256, "evidence_sha256": h.digest(unit.evidence),
            "request_key": key, "transport": transport, "started_at": now(), "assessment": None,
            "logical_requests": 1, "provider_attempts": 1, "input": statistics}


def complete(unit, receipt, result, *, reused=False):
    # Validate original evidence, never the compact transport representation.
    validation = analyzer.validate_assessment(unit.session, unit.evidence, result.assessment)
    receipt.update(status="completed", finished_at=now(), assessment=result.assessment.model_dump(mode="json"),
        validation_status=validation["validation_status"], duration_seconds=result.duration_seconds,
        usage=result.usage, reused_identical_assessment=reused)
    runner.atomic_json(unit.receipt, receipt)
    return receipt


def statistics(prepared_paths):
    counts = {"completed": 0, "failed": 0, "pending": 0, "reused": 0}
    usage_totals, durations, measured = {}, [], 0
    original = sent = reserved_input = measured_counts = 0
    for prepared in prepared_paths:
        for path in (Path(prepared) / "analysis-optimized").glob("*.json"):
            if path.name == "plan.json": continue
            value = json.loads(path.read_text())
            if value.get("status") in counts: counts[value["status"]] += 1
            if value.get("reused_identical_assessment"): counts["reused"] += 1; continue
            if value.get("status") == "completed":
                original += value.get("input", {}).get("original_characters", 0)
                sent += value.get("input", {}).get("sent_characters", 0)
                reserved_input += value.get("input", {}).get("rate_limit_input_tokens", 0)
                measured_counts += value.get("input", {}).get("input_token_source") == "provider_count_full_request"
                if value.get("duration_seconds") is not None: durations.append(value["duration_seconds"])
                reported = value.get("usage") or {}
                if any(v is not None for v in reported.values()): measured += 1
                for key, n in reported.items():
                    if type(n) is int: usage_totals[key] = usage_totals.get(key, 0) + n
    durations.sort()
    return {**counts, "measured_usage_responses": measured, "usage": usage_totals,
            "original_characters": original, "sent_characters": sent,
            "reserved_input_tokens": reserved_input, "provider_counted_responses": measured_counts,
            "mean_call_seconds": sum(durations) / len(durations) if durations else None,
            "p95_call_seconds": durations[min(len(durations) - 1, int(len(durations) * .95))] if durations else None,
            "missing_usage_is_unknown": True}


def run_many(prepared_paths, *, model, options, send=False, generate=None, cache_folder, progress=lambda value: None, limiter=None, token_counter=None, count_limiter=None):
    if not send: raise ValueError("Explicit --send is required")
    if options.transport != "concurrent": raise ValueError("Use the native batch transport for provider batches")
    prepared_paths = [Path(p) for p in prepared_paths]
    total = 0
    for prepared in prepared_paths:
        _, _, sessions, _ = plan(prepared, model, options)
        saved_results(prepared, model, options)  # Reject a changed receipt before ANY dispatch.
        total += len(sessions)
    cache = Path(cache_folder)
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    limiter = limiter or RateLimiter(options.rpm, options.tpm)
    count_limiter = count_limiter or RateLimiter(min(options.rpm, 30), 1)
    input_cache = provider.InputTokenCache(cache / "input-token-counts")
    stop, halted, budget_lock = threading.Event(), threading.Event(), threading.Lock()
    budget = {"requests": 0, "estimated_tokens": 0, "reason": None}
    clients = provider.ClientPool(options) if generate is None else None
    started = time.monotonic()

    def pause(reason, *, provider_stop=False):
        with budget_lock: budget["reason"] = budget["reason"] or reason
        halted.set()
        if provider_stop: stop.set()

    def process(unit):
        if unit.receipt.exists(): return
        text, config, metrics = provider.payload(unit.evidence, options)
        key = provider.fingerprint(text, config, model, options)
        cached = cache / (key + ".json")
        receipt = receipt_for(unit, key, metrics)
        if cached.exists():
            if cached.is_symlink(): raise ValueError("Refusing symlink cache")
            old = json.loads(cached.read_text())
            if old.get("status") == "completed":
                h.private_json(unit.receipt, receipt)
                result = provider.CallResult(analyzer.Assessment.model_validate(old["assessment"]), {}, 0)
                complete(unit, receipt, result, reused=True)
                return
            h.private_json(unit.receipt, {**receipt, "status": "failed", "error_type": "PriorIdenticalRequestUnresolved", "logical_requests": 0})
            return
        # Injected offline generators never cause hidden provider I/O. Tests can
        # also inject a counter to exercise the complete scheduling path.
        counted, count_reused = None, False
        if options.token_counting == "provider" and (generate is None or token_counter is not None):
            def measure(*args):
                if not count_limiter.acquire(0, stop): raise provider.TokenCountError()
                return (token_counter or provider.count_input_tokens)(*args)
            try:
                counted, count_reused = input_cache.count(text, config, model, options, measure=measure)
            except Exception:
                pause("Input token counting failed; untouched analysis was not sent. Retry counting or explicitly choose estimate mode", provider_stop=True)
                return
        metrics = provider.input_accounting(metrics, options, counted=counted)
        metrics["token_count_reused"] = count_reused
        metrics["tokenizer_requests"] = int(counted is not None and not count_reused)
        receipt = receipt_for(unit, key, metrics)
        input_cost, cost = metrics["rate_limit_input_tokens"], metrics["run_budget_tokens"]
        if input_cost > options.tpm: pause("A request exceeds the input TPM setting; raise it within the project quota or prepare smaller units"); return
        with budget_lock:
            if halted.is_set(): return
            if options.max_requests and budget["requests"] >= options.max_requests or options.max_estimated_tokens and budget["estimated_tokens"] + cost > options.max_estimated_tokens:
                budget["reason"] = "Configured request/token run budget reached"; halted.set(); return
            budget["requests"] += 1
            budget["estimated_tokens"] += cost
        reservation = limiter.acquire(input_cost, stop)
        if not reservation: return
        if stop.is_set(): return
        try:
            h.private_json(cached, {"status": "pending", "request_key": key, "started_at": now()})
        except FileExistsError:
            h.private_json(unit.receipt, {**receipt, "status": "failed", "error_type": "ConcurrentIdenticalRequestReserved", "logical_requests": 0})
            return
        h.private_json(unit.receipt, receipt)
        try:
            result = generate(unit.evidence, model, options) if generate is not None else clients.call(text, config, model)
            limiter.reconcile(reservation, result.usage.get("input_tokens"))
            complete(unit, receipt, result)
            runner.atomic_json(cached, {"status": "completed", "assessment": result.assessment.model_dump(mode="json")})
        except Exception as error:
            receipt.update(status="failed", finished_at=now(), error_type=type(error).__name__)
            runner.atomic_json(unit.receipt, receipt)
            code = getattr(error, "code", getattr(error, "status_code", None))
            if code in {400, 401, 403, 404, 422, 429, 500, 502, 503, 504} or isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {"ConnectError", "ReadTimeout"}:
                pause("Provider quota, credentials or connection stopped this run; in-flight calls were preserved", provider_stop=True)

    iterator = iter(units(prepared_paths, model, options))
    exhausted, futures = False, {}
    with ExitStack() as cleanup, ThreadPoolExecutor(max_workers=options.workers) as pool:
        if clients is not None: cleanup.callback(clients.close)
        while futures or not exhausted and not halted.is_set():
            while len(futures) < options.workers and not exhausted and not halted.is_set():
                try: unit = next(iterator)
                except StopIteration: exhausted = True; break
                if not unit.receipt.exists(): futures[pool.submit(process, unit)] = unit.prepared
            if not futures: break
            done, _ = wait(futures, timeout=1, return_when=FIRST_COMPLETED)
            changed = set()
            for future in done:
                changed.add(str(futures.pop(future)))
                try: future.result()
                except Exception: pause("Local persistence or configuration error; no automatic resends", provider_stop=True)
            if done: progress({"phase": "Analyzing", "elapsed_seconds": time.monotonic() - started, "submitted_requests": budget["requests"], "changed_prepared_paths": sorted(changed)})
    report = {**statistics(prepared_paths), "total_units": total, "wall_seconds": time.monotonic() - started,
              "stopped_reason": budget["reason"], "execution": asdict(options)}
    progress(report)
    return report
