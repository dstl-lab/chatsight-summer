"""Localhost web UI for the draft->review->tweak loop. Same building blocks as
the CLI (cli.py stays canonical for scripted runs); drafting is anchored, which
is fine for drafting and forbidden for measurement (CLAUDE.md invariant 8).

Single in-process session: this is a one-instructor localhost research tool.
Binds 127.0.0.1 only — student text never leaves the machine (rule 4)."""
import threading
from pathlib import Path
from typing import Callable

from src.ingest.rawlog import Conversation, count_conversations, fetch_conversations
from src.labeling.cli import ACCEPT_NOTE
from src.labeling.draft import MessageLabels, draft_labels
from src.labeling.elicit import draft_schema, revise_schema
from src.labeling.llm import DEFAULT_MODEL, Generate
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema, save_schema
from src.labeling.snapshot import emit_snapshot

WORKING_PHASES = ("fetching", "drafting", "mass_labeling")


class PhaseError(Exception):
    def __init__(self, phase: str):
        self.phase = phase
        super().__init__(f"action not valid in phase {phase!r}")


def _thread_runner(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


class LoopSession:
    def __init__(self, *, fetch=fetch_conversations, count=count_conversations,
                 generate: Generate, ext_db_url: str, data_dir: Path,
                 repo_sha: str, runner: Callable[[Callable[[], None]], None]
                 = _thread_runner):
        self.fetch = fetch
        self.count = count
        self.generate = generate
        self.ext_db_url = ext_db_url
        self.data_dir = data_dir
        self.repo_sha = repo_sha
        self.runner = runner
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.phase = "idle"
        self.error: str | None = None
        self.conversations: list[Conversation] = []
        self.provenance: dict | None = None
        self.schema: LabelSchema | None = None
        self.sample: list[SampledMessage] = []
        self.labeled: list[MessageLabels] = []
        self.snapshot_path: Path | None = None
        self.progress: dict | None = None
        self.seed = 0

    def _set_progress(self, done: int, total: int) -> None:
        with self._lock:
            self.progress = {"done": done, "total": total}

    def _run(self, job: Callable[[], None]) -> None:
        def guarded() -> None:
            try:
                job()
            except Exception as e:  # surfaced to the UI, quit recovers
                with self._lock:
                    self.phase = "error"
                    self.error = str(e)
        self.runner(guarded)

    def _require(self, *phases: str) -> None:
        if self.phase not in phases:
            raise PhaseError(self.phase)

    def start(self, intent: str, max_conversations: int = 200,
              sample_size: int = 25, seed: int = 0) -> None:
        with self._lock:
            self._require("idle")
            self._reset()
            self.seed = seed
            self.phase = "fetching"

        def job() -> None:
            convs = self.fetch(self.ext_db_url, max_conversations)
            total = self.count(self.ext_db_url)
            with self._lock:
                self.conversations = convs
                self.provenance = {"fetched": len(convs), "total": total,
                                   "excluded": max(0, total - len(convs))}
                self.phase = "drafting"
            schema = draft_schema(intent, self.generate)
            sample = stratified_sample(convs, n=sample_size, seed=seed)
            labeled = draft_labels(sample, schema, self.generate,
                                   on_progress=self._set_progress)
            with self._lock:
                self.schema, self.sample, self.labeled = schema, sample, labeled
                self.phase = "review"
        self._run(job)

    def tweak(self, feedback: str) -> None:
        with self._lock:
            self._require("review")
            self.phase = "drafting"
            self.progress = None

        def job() -> None:
            schema = revise_schema(self.schema, feedback, self.generate)
            labeled = draft_labels(self.sample, schema, self.generate,
                                   on_progress=self._set_progress)
            with self._lock:
                self.schema, self.labeled = schema, labeled
                self.phase = "review"
        self._run(job)

    def accept(self) -> None:
        with self._lock:
            self._require("review")
            self.phase = "mass_labeling"
            self.progress = None

        def job() -> None:
            save_schema(self.schema, self.data_dir)
            all_messages = stratified_sample(self.conversations, n=10**9,
                                             seed=self.seed)
            labeled = draft_labels(all_messages, self.schema, self.generate,
                                   on_progress=self._set_progress)
            path = emit_snapshot(
                self.conversations, labeled, self.schema, model=DEFAULT_MODEL,
                repo_sha=self.repo_sha, data_dir=self.data_dir,
                excluded_conversations=self.provenance["excluded"])
            with self._lock:
                self.snapshot_path = path
                self.phase = "done"
        self._run(job)

    def quit(self) -> None:
        with self._lock:
            self._require("review", "error", "done")
            self._reset()

    def state(self) -> dict:
        with self._lock:
            by_key = {(r.chatlog_id, r.message_index): r for r in self.labeled}
            sample = None
            if self.phase in ("review", "mass_labeling", "done") and self.sample:
                sample = []
                for m in self.sample:
                    r = by_key.get((m.chatlog_id, m.message_index))
                    applied = [k for k, v in r.labels.items() if v] if r else []
                    sample.append({
                        "stratum": m.stratum, "text": m.text, "labels": applied,
                        "rationales": {k: r.rationales.get(k, "")
                                       for k in applied} if r else {},
                    })
            schema = None
            if self.schema is not None:
                schema = {
                    "version_id": self.schema.version_id,
                    "intent": self.schema.instructor_intent,
                    "labels": [{"name": l.name, "kind": l.kind,
                                "description": l.description}
                               for l in self.schema.labels],
                }
            return {
                "phase": self.phase,
                "error": self.error,
                "accept_note": ACCEPT_NOTE,
                "provenance": self.provenance,
                "progress": self.progress,
                "schema": schema,
                "sample": sample,
                "snapshot_path": (str(self.snapshot_path)
                                  if self.snapshot_path else None),
            }


# --- FastAPI layer ---------------------------------------------------------

import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

STATIC_DIR = Path(__file__).parent / "static"


class StartRequest(BaseModel):
    intent: str
    max_conversations: int = 200
    sample_size: int = 25
    seed: int = 0


class TweakRequest(BaseModel):
    feedback: str


def create_app(session: LoopSession) -> FastAPI:
    app = FastAPI(title="label-loop")

    @app.exception_handler(PhaseError)
    async def phase_error(request, exc: PhaseError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/state")
    def state() -> dict:
        return session.state()

    @app.post("/api/start")
    def start(req: StartRequest) -> dict:
        session.start(req.intent, max_conversations=req.max_conversations,
                      sample_size=req.sample_size, seed=req.seed)
        return {"ok": True}

    @app.post("/api/tweak")
    def tweak(req: TweakRequest) -> dict:
        session.tweak(req.feedback)
        return {"ok": True}

    @app.post("/api/accept")
    def accept() -> dict:
        session.accept()
        return {"ok": True}

    @app.post("/api/quit")
    def quit_() -> dict:
        session.quit()
        return {"ok": True}

    return app


def _repo_sha(repo_root: Path) -> str:
    import subprocess
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True,
                             cwd=repo_root).stdout.strip()
    except OSError:
        sha = ""
    return sha or "unknown"


def main() -> None:
    import uvicorn

    from src.config import Settings
    from src.labeling.llm import make_generate

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    session = LoopSession(generate=make_generate(settings.gemini_api_key),
                          ext_db_url=settings.ext_db_url,
                          data_dir=settings.data_dir,
                          repo_sha=_repo_sha(settings.repo_root))
    # 127.0.0.1 only: student text never leaves the machine (CLAUDE.md rule 4)
    print("label-loop web UI on http://127.0.0.1:8321 (is bin/tunnel running?)")
    uvicorn.run(create_app(session), host="127.0.0.1", port=8321)
