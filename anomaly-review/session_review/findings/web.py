"""Local upload/analysis dashboard. No database client or extraction endpoint."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid

from . import analyze_sessions as analyzer
from . import bundle, historical, recent, runner

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
    def __init__(self, root, *, model="gemini-3.8-flash", generate=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.model = model
        self.generate = generate
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.futures = []
        for path in self.root.iterdir():
            if path.is_symlink() or not JOB_ID.fullmatch(path.name):
                continue
            try:
                state = self.read(path.name)
                if state["status"] == "preparing":
                    complete = (path / "prepared/manifest.json").exists() and (path / "bundle.private.json").exists()
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

    def listing(self):
        jobs = []
        for path in self.root.iterdir():
            if JOB_ID.fullmatch(path.name) and path.is_dir() and not path.is_symlink():
                try:
                    jobs.append(self.summary(path.name))
                except (OSError, ValueError, KeyError):
                    continue
        return sorted(jobs, key=lambda s: s["created_at"], reverse=True)

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
        results = runner.saved_results(folder / "prepared" / "analysis", sessions, evidence, state["model"])
        doc = bundle.build(sessions, input_hash=manifest["input_file_sha256"], context=context, results=results,
            model=state["model"] if results else None, source="Saved Gemini assessments from uploaded PR100 data" if results else "Uploaded PR100 data; not analyzed")
        runner.atomic_json(folder / "bundle.private.json", doc)

    def start(self, job_id):
        with self.lock:
            state = self.read(job_id)
            if state["status"] not in {"ready", "stopped", "interrupted"}:
                raise InputError("This job is already running or finished. Open its saved results.")
            if not (self.folder(job_id) / "prepared" / "manifest.json").exists():
                raise InputError("Preparation was interrupted. Upload the file again.")
            if self.generate is None and not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
                raise InputError("The analysis service needs a Gemini API key. Database access is not needed.")
            manifest, sessions, _, evidence = historical.load_prepared(self.folder(job_id) / "prepared")
            runner.saved_results(self.folder(job_id) / "prepared" / "analysis", sessions, evidence, state["model"])
            state.update(status="analyzing", error=None)
            self.save(job_id, state)
            self.futures.append(self.executor.submit(self.analyze, job_id))
        return self.summary(job_id)

    def analyze(self, job_id):
        state = self.read(job_id)
        folder = self.folder(job_id)
        try:
            _, sessions, _, evidence = historical.load_prepared(folder / "prepared")
            if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
                os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
            results = runner.run(folder / "prepared" / "analysis", sessions, evidence,
                                 model=state["model"], send=True, generate=self.generate)
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
                    return self.send(200, {"ready": True, "model": jobs.model, "max_upload_bytes": MAX_UPLOAD,
                        "gemini_configured": bool(jobs.generate or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))})
                if path == "/api/jobs":
                    return self.send(200, {"jobs": jobs.listing()})
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
                if not 0 <= length <= MAX_UPLOAD:
                    return self.send(413, {"error": "Upload a file under 50 MB."})
                if parsed.path == "/api/uploads":
                    options = parse_qs(parsed.query)
                    count = int(options.get("count", ["10"])[0])
                    minutes = int(options.get("minutes", ["25"])[0])
                    self.connection.settimeout(60)
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
    parser.add_argument("--storage", type=Path, default=Path("private-data/uploads"))
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--frontend", type=Path, default=Path(__file__).resolve().parents[2] / "frontend" / "dist")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Choose a port between 1 and 65535.")
    os.umask(0o077)
    jobs = Jobs(args.storage, model=args.model)
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
