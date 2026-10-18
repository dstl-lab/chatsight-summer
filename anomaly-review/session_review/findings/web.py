"""Local upload/analysis dashboard. No database client or extraction endpoint."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from dataclasses import asdict
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit
import uuid

from . import analyze_sessions as analyzer
from . import bulk, bundle, historical, recent, runner, production
from . import grouped, native_batch, optimized, provider

MAX_UPLOAD = 50 * 1024 * 1024
MAX_EXPANDED = 300 * 1024 * 1024
MAX_LINE = 8 * 1024 * 1024
MAX_ROWS = 100_000
DEPLOYED = historical.timestamp("2026-10-13T17:30:00Z")
JOB_ID = re.compile(r"^[a-f0-9]{32}$")


class InputError(ValueError):
    pass


def inspect_upload(path):
    """Bound decompression and reject legacy-only/mixed uploads before preparation."""
    opener = gzip.open if path.suffix == ".gz" else open
    count, expanded = 0, 0
    first = last = None
    try:
        with opener(path, "rb") as stream:
            while line := stream.readline(MAX_LINE + 1):
                expanded += len(line)
                if len(line) > MAX_LINE or expanded > MAX_EXPANDED:
                    raise InputError("The export is too large. Extract a smaller date range or fewer notebook sessions.")
                if not line.strip():
                    continue
                count += 1
                if count > MAX_ROWS:
                    raise InputError("Upload at most 100,000 events per file. Extract a smaller batch.")
                row = json.loads(line)
                p = row.get("payload") if isinstance(row, dict) else None
                if not isinstance(p, dict) or type(p.get("schema_version")) is not int or p["schema_version"] != 1:
                    raise InputError("Upload a recent PR100 JSONL export. Historical and saved-results files use a different format.")
                at = historical.timestamp(row.get("created_at"))
                if at < DEPLOYED or not isinstance(p.get("event_id"), str) or not isinstance(p.get("analytics_session_id"), str):
                    raise InputError("The file contains records outside the recent PR100 observation format.")
                if type(row.get("id")) not in (str, int) or not isinstance(row.get("event_type"), str):
                    raise InputError("The export is missing event identities or types.")
                first = min(first, at) if first else at
                last = max(last, at) if last else at
    except InputError:
        raise
    except (ValueError, TypeError, OSError, EOFError, AttributeError):
        raise InputError("Could not read this export. Choose an intact .jsonl or .jsonl.gz PR100 file.") from None
    if not count:
        raise InputError("The export contains no events.")
    return {"events": count, "first_event_at": first.isoformat(), "last_event_at": last.isoformat()}


class Jobs:
    def __init__(self, root, *, model="gemini-3.8-flash", generate=None, optimization=None, group_overlap=False, optimized_generate=None, batch_api_factory=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.model = model
        self.generate = generate
        self.optimization = optimization
        self.group_overlap = group_overlap
        self.optimized_generate = optimized_generate
        self.batch_api_factory = batch_api_factory
        self.limiters = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.futures = []
        for path in self.root.iterdir():
            if path.is_symlink() or not JOB_ID.fullmatch(path.name):
                continue
            try:
                state = self.read(path.name)
                if state["status"] == "preparing":
                    complete = state.get("kind") != "collection" and (path / "prepared/manifest.json").exists() and (path / "bundle.private.json").exists()
                    state.update(status="ready" if complete else "failed", error=None if complete else "Preparation was interrupted. Upload the file again; no model request was made.")
                    self.save(path.name, state)
                elif state["status"] == "analyzing":
                    state.update(status="interrupted", error="The service stopped before this job finished. Completed responses are saved.")
                    self.save(path.name, state)
            except (OSError, ValueError, KeyError):
                continue

    def folder(self, job_id):
        if not JOB_ID.fullmatch(job_id):
            raise KeyError("Unknown job")
        path = self.root / job_id
        if path.is_symlink() or not path.is_dir():
            raise KeyError("Unknown job")
        return path

    def read(self, job_id):
        return json.loads((self.folder(job_id) / "state.private.json").read_text())

    def save(self, job_id, state):
        runner.atomic_json(self.folder(job_id) / "state.private.json", state)

    def summary(self, job_id):
        state = self.read(job_id)
        if state.get("kind") == "collection":
            children = [self.summary(child) for child in state.get("children", [])]
            state["batches"] = [{key: child.get(key) for key in ("id", "filename", "status", "count", "progress")} for child in children]
            state["progress"] = {key: sum(child["progress"][key] for child in children) for key in ("completed", "failed", "pending")}
            if state.get("optimization"):
                state["runtime"] = self.optimized_runtime(state, [self.folder(child) / "prepared" for child in state["children"]])
            return state
        if state.get("optimization"):
            metrics = self.optimized_runtime(state, [self.folder(job_id) / "prepared"])
            state["runtime"] = metrics
            state["progress"] = {key: metrics[key] for key in ("completed", "failed", "pending")}
            return state
        counts = {"completed": 0, "failed": 0, "pending": 0}
        for path in (self.folder(job_id) / "prepared" / "analysis").glob("*.json"):
            if path.name == "plan.json":
                continue
            receipt = json.loads(path.read_text())
            if receipt["status"] == "pending" and state["status"] != "analyzing":
                counts["failed"] += 1
            elif receipt["status"] in counts:
                counts[receipt["status"]] += 1
        state["progress"] = counts
        return state

    def optimized_runtime(self, state, paths):
        metrics = optimized.statistics(paths)
        options = provider.Options(**state["optimization"])
        remaining = max(0, state["count"] - metrics["completed"] - metrics["failed"])
        mean = metrics["mean_call_seconds"]
        if options.transport == "concurrent" and mean is not None:
            measured = max(1, metrics["completed"] - metrics["reused"])
            token_mean = metrics["sent_characters"] / 3 / measured + options.max_output_tokens
            metrics["estimated_remaining_seconds"] = max(remaining * mean / options.workers, remaining * 60 / options.rpm, remaining * token_mean * 60 / options.tpm)
        else: metrics["estimated_remaining_seconds"] = None
        metrics["eta_is_estimate"] = True
        metrics["workers"] = options.workers if options.transport == "concurrent" else None
        metrics["transport"] = options.transport
        return metrics

    def listing(self):
        jobs = []
        for path in self.root.iterdir():
            if JOB_ID.fullmatch(path.name) and path.is_dir() and not path.is_symlink():
                try:
                    state = self.read(path.name)
                    if not state.get("parent_id"):
                        jobs.append(self.summary(path.name))
                except (OSError, ValueError, KeyError):
                    continue
        return sorted(jobs, key=lambda s: s["created_at"], reverse=True)

    def upload_collection(self, stream, length, filename, *, minutes=25):
        if minutes not in {10, 25} or not 0 < length <= production.MAX_UPLOAD:
            raise InputError("Choose a nonempty PR100 export up to 2 GB and a 10- or 25-minute window.")
        job_id = uuid.uuid4().hex
        folder = self.root / job_id
        folder.mkdir(mode=0o700)
        source = folder / "upload.partial"
        sha = hashlib.sha256()
        magic = b""
        try:
            with source.open("xb") as target:
                os.chmod(source, 0o600)
                remaining = length
                while remaining:
                    block = stream.read(min(1024**2, remaining))
                    if not block: raise InputError("Upload interrupted. Choose the file again.")
                    if not magic: magic = block[:2]
                    sha.update(block)
                    target.write(block)
                    remaining -= len(block)
            fingerprint = sha.hexdigest()
            with self.lock:
                for old in self.listing():
                    if old.get("kind") == "collection" and old.get("source_sha256") == fingerprint and old["minutes"] == minutes and old["status"] != "failed" and old.get("optimization") == (asdict(self.optimization) if self.optimization else None) and bool(old.get("grouped")) == self.group_overlap:
                        source.unlink()
                        folder.rmdir()
                        return old
                source = source.rename(folder / ("source.jsonl.gz" if magic == b"\x1f\x8b" else "source.jsonl"))
                state = {"id": job_id, "kind": "collection", "filename": Path(filename.replace("\\", "/")).name[:120],
                    "created_at": datetime.now(timezone.utc).isoformat(), "status": "preparing", "count": 0, "minutes": minutes,
                    "model": self.model, "error": None, "source_file": source.name, "source_sha256": fingerprint,
                    "source": None, "children": [], "coverage": None, "import_progress": {"phase": "Starting import"}}
                if self.optimization: state.update(optimization=asdict(self.optimization), grouped=self.group_overlap)
                self.save(job_id, state)
                self.futures.append(self.executor.submit(self.prepare_collection, job_id))
            return self.summary(job_id)
        except Exception:
            if source.exists() and source.name == "upload.partial":
                source.unlink()
                folder.rmdir()
            raise

    def prepare_collection(self, job_id):
        state = self.read(job_id)
        folder = self.folder(job_id)
        def progress(value):
            state["import_progress"] = value
            self.save(job_id, state)
        try:
            source = bulk.index_source(folder / state["source_file"], folder / "events.sqlite", progress=progress)
            state["source"] = source
            prepare_function = grouped.prepare_batches if state.get("grouped") else bulk.prepare_batches
            prepared = prepare_function(folder / "events.sqlite", folder / "batches", source, minutes=state["minutes"], progress=progress)
            state["coverage"] = prepared["coverage"]
            state["coverage_note"] = prepared["note"]
            for number, batch in enumerate(prepared["batches"], 1):
                child_id = uuid.uuid4().hex
                child = self.root / child_id
                child.mkdir(mode=0o700)
                (folder / "batches" / batch["folder"]).rename(child / "prepared")
                child_state = {"id": child_id, "parent_id": job_id, "filename": f'{state["filename"]} · batch {number}',
                    "created_at": state["created_at"], "status": "ready", "count": batch["count"], "minutes": state["minutes"],
                    "model": state["model"], "error": None, "source": {k: source[k] for k in ("events", "first_event_at", "last_event_at")},
                    "selection": None, "eligible_sessions": prepared["coverage"].get("eligible", 0)}
                if state.get("optimization"): child_state.update(optimization=state["optimization"], grouped=state.get("grouped", False))
                self.save(child_id, child_state)
                state["children"].append(child_id)
                state["import_progress"] = {"phase": "Registering review batches", "requests": prepared["coverage"]["tutor_requests"]}
                self.save(job_id, state)
            state.update(status="ready", count=sum(b["count"] for b in prepared["batches"]), import_progress=None)
        except (ValueError, OSError, EOFError, KeyError, TypeError):
            state.update(status="failed", error="Import failed. Check the export format, boundaries, event identities and size. No model calls were made.")
        except Exception:
            state.update(status="failed", error="Preparation failed. The uploaded source remains saved; no model calls were made.")
        self.save(job_id, state)

    def analyze_collection(self, job_id):
        state = self.read(job_id)
        try:
            for child_id in state["children"]:
                child = self.read(child_id)
                if child["status"] == "completed": continue
                child.update(status="analyzing", error=None)
                self.save(child_id, child)
                self.analyze(child_id)
                child = self.read(child_id)
                if child["status"] != "completed":
                    state.update(status="stopped", error="Analysis stopped at a batch. Saved responses are preserved; continue untouched windows later.")
                    break
            else:
                state.update(status="completed", error=None)
        except Exception:
            state.update(status="interrupted", error="Analysis interrupted. Saved responses are preserved.")
        self.save(job_id, state)

    def upload(self, data, filename, *, count=10, minutes=25):
        if type(count) is not int or not 1 <= count <= 20 or minutes not in {10, 25}:
            raise InputError("Choose 1–20 sessions and a 10- or 25-minute window.")
        if not data or len(data) > MAX_UPLOAD:
            raise InputError("Choose a nonempty export under 50 MB.")
        job_id = uuid.uuid4().hex
        folder = self.root / job_id
        folder.mkdir(mode=0o700)
        source = folder / ("source.jsonl.gz" if data[:2] == b"\x1f\x8b" else "source.jsonl")
        with source.open("xb") as stream:
            os.chmod(source, 0o600)
            stream.write(data)
        state = {"id": job_id, "filename": Path(filename.replace("\\", "/")).name[:120],
                 "created_at": datetime.now(timezone.utc).isoformat(), "status": "preparing",
                 "count": count, "minutes": minutes, "model": self.model, "error": None,
                 "source_file": source.name, "source": None, "selection": None, "eligible_sessions": None}
        if self.optimization: state.update(optimization=asdict(self.optimization), grouped=False)
        self.save(job_id, state)
        self.futures.append(self.executor.submit(self.prepare, job_id))
        return self.summary(job_id)

    def prepare(self, job_id):
        state = self.read(job_id)
        folder = self.folder(job_id)
        try:
            state["source"] = inspect_upload(folder / state["source_file"])
            long = state["minutes"] == 25
            manifest = recent.prepare(folder / state["source_file"], folder / "prepared", count=state["count"],
                coverage="dialogue", before_minutes=5 if long else 3, after_minutes=20 if long else 7,
                max_records=1500 if long else 500, max_characters=450000 if long else 160000)
            state["selection"] = {"coverage": manifest["selection"]["coverage"], "exclusions": manifest["exclusions"],
                                  "quality": manifest["quality"]}
            state["eligible_sessions"] = manifest["eligible_notebook_sessions"]
            self.write_bundle(job_id)
            state.update(status="ready", error=None)
        except InputError as error:
            state.update(status="failed", error=str(error))
        except ValueError as error:
            # Preparation's insufficient-count diagnostic contains aggregate
            # counts only. Never return arbitrary exceptions or student content.
            message = str(error)
            matched = re.match(r"Only (\d+) recent notebook scopes", message)
            state.update(status="failed", error=f"Only {matched[1]} eligible notebook sessions fit these settings. Choose fewer sessions or upload a larger export." if matched else "The export could not be prepared. Check its format and observation identities.")
        except Exception:
            state.update(status="failed", error="Preparation failed. The source is saved locally; no data was sent to Gemini.")
        self.save(job_id, state)

    def write_bundle(self, job_id):
        folder = self.folder(job_id)
        state = self.read(job_id)
        manifest, sessions, context, evidence = historical.load_prepared(folder / "prepared")
        if state.get("optimization"):
            results = optimized.saved_results(folder / "prepared", state["model"], provider.Options(**state["optimization"]))
        else:
            results = runner.saved_results(folder / "prepared" / "analysis", sessions, evidence, state["model"])
        doc = bundle.build(sessions, input_hash=manifest["input_file_sha256"], context=context, results=results,
            model=state["model"] if results else None, source="Saved Gemini assessments from uploaded PR100 data" if results else "Uploaded PR100 data; not analyzed")
        runner.atomic_json(folder / "bundle.private.json", doc)

    def start(self, job_id):
        with self.lock:
            state = self.read(job_id)
            if state["status"] not in {"ready", "stopped", "interrupted"}:
                raise InputError("This job is already running or finished. Open its saved results.")
            if state.get("parent_id") and self.read(state["parent_id"])["status"] in {"preparing", "analyzing", "failed"}:
                raise InputError("The export is still processing or failed preparation. Open the export first.")
            if state.get("kind") != "collection" and not (self.folder(job_id) / "prepared" / "manifest.json").exists():
                raise InputError("Preparation was interrupted. Upload the file again.")
            if self.generate is None and self.optimized_generate is None and self.batch_api_factory is None and not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
                raise InputError("The analysis service needs a Gemini API key. Database access is not needed.")
            if state.get("optimization"):
                if state.get("kind") == "collection":
                    if not state.get("children"): raise InputError("No eligible analysis units")
                    if any(self.read(child)["status"] == "analyzing" for child in state["children"]): raise InputError("A batch is already running")
                state.update(status="analyzing", error=None, analysis_started_at=datetime.now(timezone.utc).isoformat())
                self.save(job_id, state)
                self.futures.append(self.executor.submit(self.analyze_optimized, job_id))
                return self.summary(job_id)
            if state.get("kind") == "collection":
                if not state.get("children"):
                    raise InputError("No eligible windows. Inspect the coverage counts before exporting another range.")
                if any(self.read(child)["status"] == "analyzing" for child in state["children"]):
                    raise InputError("A batch is already running. Wait for it to finish.")
                state.update(status="analyzing", error=None)
                self.save(job_id, state)
                self.futures.append(self.executor.submit(self.analyze_collection, job_id))
                return self.summary(job_id)
            manifest, sessions, _, evidence = historical.load_prepared(self.folder(job_id) / "prepared")
            runner.saved_results(self.folder(job_id) / "prepared" / "analysis", sessions, evidence, state["model"])
            state.update(status="analyzing", error=None)
            self.save(job_id, state)
            self.futures.append(self.executor.submit(self.analyze, job_id))
        return self.summary(job_id)

    def analyze_optimized(self, job_id):
        state = self.read(job_id)
        options = provider.Options(**state["optimization"])
        children = state["children"] if state.get("kind") == "collection" else [job_id]
        paths = [self.folder(child) / "prepared" for child in children]
        path_ids = {str(path): child for path, child in zip(paths, children)}
        for child in children:
            if child == job_id: continue
            value = self.read(child)
            value.update(status="analyzing", error=None)
            self.save(child, value)
        def progress(value):
            for path in value.get("changed_prepared_paths", []):
                child = path_ids[path]; item = self.read(child)
                stats = optimized.statistics([path])
                if stats["completed"] + stats["failed"] >= item["count"]:
                    item["status"] = "completed"; self.save(child, item); self.write_bundle(child)
        try:
            if options.transport == "concurrent":
                key = (options.rpm, options.tpm)
                limiter = self.limiters.setdefault(key, optimized.RateLimiter(*key))
                report = optimized.run_many(paths, model=state["model"], options=options, send=True, generate=self.optimized_generate,
                    cache_folder=self.root / "optimized-cache", progress=progress, limiter=limiter)
            else:
                remote = self.folder(job_id) / "native-batch"
                if not (remote / "batch-state.private.json").exists():
                    native_batch.prepare(paths, remote, model=state["model"], options=options, cache_folder=self.root / "optimized-cache")
                api = self.batch_api_factory(options) if self.batch_api_factory else provider.client(options)
                try:
                    while True:
                        native_batch.submit(remote, options=options, api=api, send=True)
                        report = native_batch.collect(remote, options=options, api=api)
                        progress({"changed_prepared_paths": list(path_ids)})
                        if report["provider_status"] == "completed": break
                        time.sleep(15)
                finally:
                    api.close()
            runner.atomic_json(self.folder(job_id) / "optimization-report.private.json", report)
            finished = report["completed"] + report["failed"]
            state.update(status="completed" if finished >= state["count"] and not report.get("stopped_reason") else "stopped",
                error=report.get("stopped_reason"), analysis_finished_at=datetime.now(timezone.utc).isoformat())
        except Exception:
            state.update(status="interrupted", error="Optimized analysis stopped. Receipts and remote job IDs are preserved; no uncertain request will be resent.")
        for child in children:
            if child == job_id: continue
            item = self.read(child); stats = optimized.statistics([self.folder(child) / "prepared"])
            item["status"] = "completed" if stats["completed"] + stats["failed"] >= item["count"] else "stopped"
            self.save(child, item)
        for child in children:
            try: self.write_bundle(child)
            except Exception: pass
        self.save(job_id, state)

    def analyze(self, job_id):
        state = self.read(job_id)
        folder = self.folder(job_id)
        try:
            _, sessions, _, evidence = historical.load_prepared(folder / "prepared")
            if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
                os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
            results = runner.run(folder / "prepared" / "analysis", sessions, evidence,
                                 model=state["model"], send=True, generate=self.generate, cache_folder=self.root / "assessment-cache")
            self.write_bundle(job_id)
            state.update(status="completed" if len(results) == len(sessions) else "stopped",
                         error=None if len(results) == len(sessions) else "The provider stopped the batch. Completed and failed requests are saved. You can continue untouched sessions later.")
        except Exception:
            state.update(status="interrupted", error="Analysis stopped. Saved responses are preserved; continuing will skip previous requests.")
            try:
                self.write_bundle(job_id)
            except Exception:
                pass
        self.save(job_id, state)

    def get_bundle(self, job_id):
        path = self.folder(job_id) / "bundle.private.json"
        if not path.exists() and (self.folder(job_id) / "prepared/manifest.json").exists():
            # Bulk import freezes all evidence, but renders only the batch being
            # opened. Analysis writes an updated bundle after saving receipts.
            with self.lock:
                if not path.exists():
                    self.write_bundle(job_id)
        if not path.exists():
            raise InputError("This job has no prepared review bundle yet.")
        return path.read_bytes()


def handler_for(jobs, frontend, port):
    frontend = Path(frontend).resolve()
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {"http://" + host for host in hosts} | {"http://127.0.0.1:4173", "http://localhost:4173"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, content_type="application/json", *, download=False):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="pr100-review.private.json"')
            self.end_headers()
            self.wfile.write(body)

        def guard(self, mutate=False):
            if self.headers.get("Host") not in hosts or self.headers.get("Origin") not in origins | {None}:
                self.send(403, {"error": "Only the local dashboard can access this service."})
                return False
            if mutate and self.headers.get("X-Review-Request") != "1":
                self.send(403, {"error": "Missing dashboard request header."})
                return False
            return True

        def do_GET(self):
            if not self.guard():
                return
            path = unquote(urlsplit(self.path).path)
            try:
                if path == "/api/status":
                    return self.send(200, {"ready": True, "model": jobs.model, "max_upload_bytes": production.MAX_UPLOAD,
                        "optimization": asdict(jobs.optimization) if jobs.optimization else None, "grouped": jobs.group_overlap,
                        "gemini_configured": bool(jobs.generate or jobs.optimized_generate or jobs.batch_api_factory or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))})
                if path == "/api/jobs":
                    return self.send(200, {"jobs": jobs.listing()})
                coverage_match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})/coverage", path)
                if coverage_match:
                    return self.send(200, (jobs.folder(coverage_match[1]) / "batches/coverage.private.jsonl").read_bytes(), "application/x-ndjson")
                match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})(/bundle)?", path)
                if match:
                    return self.send(200, jobs.get_bundle(match[1]), download=True) if match[2] else self.send(200, jobs.summary(match[1]))
                if path.startswith("/api/"):
                    return self.send(404, {"error": "Unknown endpoint."})
                target = (frontend / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
                if not target.is_relative_to(frontend) or not target.is_file():
                    return self.send(404, {"error": "Build the frontend first, or use the development server."})
                return self.send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            except KeyError:
                self.send(404, {"error": "Unknown upload."})
            except InputError as error:
                self.send(409, {"error": str(error)})
            except Exception:
                self.send(500, {"error": "The saved job could not be opened."})

        def do_POST(self):
            if not self.guard(mutate=True):
                return
            parsed = urlsplit(self.path)
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= production.MAX_UPLOAD:
                    return self.send(413, {"error": "Upload a file up to 2 GB."})
                if parsed.path == "/api/uploads":
                    options = parse_qs(parsed.query)
                    count = int(options.get("count", ["10"])[0])
                    minutes = int(options.get("minutes", ["25"])[0])
                    self.connection.settimeout(60)
                    if options.get("mode", [""])[0] == "all":
                        return self.send(202, jobs.upload_collection(self.rfile, length,
                            unquote(self.headers.get("X-File-Name", "events.jsonl.gz")), minutes=minutes))
                    if length > MAX_UPLOAD:
                        raise InputError("Sample uploads are limited to 50 MB. Choose all eligible windows for a larger export.")
                    data = self.rfile.read(length)
                    if len(data) != length:
                        raise InputError("The upload was interrupted. Choose the file again.")
                    return self.send(202, jobs.upload(data, unquote(self.headers.get("X-File-Name", "events.jsonl.gz")), count=count, minutes=minutes))
                match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})/analyze", parsed.path)
                if match:
                    return self.send(202, jobs.start(match[1]))
                return self.send(404, {"error": "Unknown endpoint."})
            except KeyError:
                self.send(404, {"error": "Unknown upload."})
            except (InputError, ValueError) as error:
                self.send(400, {"error": str(error) if isinstance(error, InputError) else "Choose valid upload options."})
            except Exception:
                self.send(500, {"error": "The request failed. Existing jobs and responses are preserved."})

    return Handler


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--storage", type=Path)
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--key-file", type=Path, help="Explicit dotenv file; reads only GEMINI_API_KEY or GOOGLE_API_KEY, never database credentials.")
    parser.add_argument("--optimized", action="store_true", help="Opt-in measured parallel/compact runner for NEW imports")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rpm", type=int, default=30)
    parser.add_argument("--tpm", type=int, default=200000)
    parser.add_argument("--group-overlap", action="store_true", help="Opt-in bounded grouping; changes the analysis unit")
    parser.add_argument("--provider-mode", choices=["concurrent", "batch"], default="concurrent")
    parser.add_argument("--thinking", choices=["default", "low", "medium", "high"], default="default")
    parser.add_argument("--original-prompt", action="store_true")
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--max-estimated-tokens", type=int, default=0)
    parser.add_argument("--batch-enqueued-tokens", type=int, default=0)
    parser.add_argument("--recover-saved-jobs", action="store_true", help="Only after the prior service has stopped: recover saved in-progress jobs")
    parser.add_argument("--frontend", type=Path, default=Path(__file__).resolve().parents[2] / "frontend" / "dist")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Choose a port between 1 and 65535.")
    if (args.group_overlap or args.provider_mode == "batch") and not args.optimized:
        parser.error("Grouping and native batch processing require --optimized")
    args.storage = args.storage or Path("private-data/optimized-uploads" if args.optimized else "private-data/uploads")
    if args.optimized and not args.recover_saved_jobs:
        for path in args.storage.glob("*/state.private.json"):
            if json.loads(path.read_text()).get("status") in {"preparing", "analyzing"}:
                parser.error("Storage has in-progress jobs. Use separate storage; recover only after its prior service has stopped.")
    if args.optimized and args.provider_mode == "batch" and args.batch_enqueued_tokens < 1:
        parser.error("Native Batch API requires an explicit --batch-enqueued-tokens allowance from the account's quota")
    if args.key_file:
        from dotenv import dotenv_values
        values = dotenv_values(args.key_file)
        key = values.get("GEMINI_API_KEY") or values.get("GOOGLE_API_KEY")
        if not key: parser.error("The selected file has no Gemini API key.")
        os.environ["GEMINI_API_KEY"] = key
    os.umask(0o077)
    options = provider.Options(workers=args.workers, rpm=args.rpm, tpm=args.tpm, compact=not args.original_prompt,
        thinking=args.thinking, max_output_tokens=args.max_output_tokens, max_requests=args.max_requests,
        max_estimated_tokens=args.max_estimated_tokens, transport=args.provider_mode, batch_enqueued_tokens=args.batch_enqueued_tokens) if args.optimized else None
    jobs = Jobs(args.storage, model=args.model, optimization=options, group_overlap=args.group_overlap)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(jobs, args.frontend, args.port))
    print(f"Local upload dashboard: http://127.0.0.1:{args.port}. No database access is configured.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        jobs.executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
