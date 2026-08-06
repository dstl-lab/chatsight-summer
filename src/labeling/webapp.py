"""Localhost web UI for the draft->review->tweak loop. Same building blocks as
the CLI (cli.py stays canonical for scripted runs); drafting is anchored, which
is fine for drafting and forbidden for measurement (CLAUDE.md invariant 8).

Single in-process session: this is a one-instructor localhost research tool.
Binds 127.0.0.1 only — student text never leaves the machine (rule 4)."""
import threading
import time
from pathlib import Path
from typing import Callable

from src.ingest.rawlog import Conversation, count_conversations, fetch_conversations
from src.labeling.cli import ACCEPT_NOTE
from src.labeling.draft import MessageLabels, classifier_hash, draft_labels
from src.labeling.elicit import draft_schema, revise_schema
from src.labeling.llm import DEFAULT_MODEL, Generate
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema, save_schema
from src.labeling.snapshot import emit_snapshot
from src.labeling.summary import compute_summary, sample_examples

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
        self._total_conversations: int | None = None
        self.schema: LabelSchema | None = None
        self.sample: list[SampledMessage] = []
        self.labeled: list[MessageLabels] = []
        self._labeled_schema: str | None = None
        self.snapshot_path: Path | None = None
        self.summary: dict | None = None
        self.steps: list[dict] = []
        self.retry_info: dict | None = None
        self.recent: list[dict] = []
        self._retry_job: Callable[[], None] | None = None
        self._retry_phase: str = "idle"
        self.seed = 0

    def _init_steps(self, *specs: tuple[str, str]) -> None:
        with self._lock:
            self.steps = [{"key": k, "name": n, "detail": "",
                           "state": "pending", "progress": None,
                           "started_at": None} for k, n in specs]

    def _step(self, key: str) -> dict:
        return next(s for s in self.steps if s["key"] == key)

    def _begin_step(self, key: str) -> None:
        with self._lock:
            s = self._step(key)
            s["state"], s["started_at"] = "active", time.time()

    def _end_step(self, key: str, name: str | None = None,
                  detail: str = "") -> None:
        with self._lock:
            s = self._step(key)
            s["state"] = "done"
            if name:
                s["name"] = name
            if detail:
                s["detail"] = detail

    def _step_progress(self, key: str) -> Callable[[int, int], None]:
        def cb(done: int, total: int) -> None:
            with self._lock:
                self._step(key)["progress"] = {"done": done, "total": total}
        return cb

    def note_retry(self, info: dict | None) -> None:
        with self._lock:
            self.retry_info = info

    def _note_recent(self, message: SampledMessage,
                     result: MessageLabels) -> None:
        applied = [k for k, v in result.labels.items() if v]
        with self._lock:
            self.recent = ([{"text": message.text, "labels": applied}]
                           + self.recent)[:3]

    def _launch(self, job: Callable[[], None], retry_phase: str) -> None:
        self._retry_job, self._retry_phase = job, retry_phase
        with self._lock:
            self.retry_info = None
        self._run(job)

    def _label_incremental(self, messages: list[SampledMessage],
                           key: str) -> None:
        """Label `messages`, skipping any already in self.labeled (same
        schema), appending each result as it completes so a mid-run failure
        keeps finished work. Progress counts are over the FULL message list.

        Accumulated labels are only reused when they belong to the current
        schema version (self._labeled_schema == self.schema.version_id); a
        mismatch (e.g. a future path swapping self.schema without clearing
        self.labeled) clears self.labeled/self.recent instead of silently
        mixing label vintages into one snapshot (CLAUDE.md rule 2 /
        invariant 6)."""
        if (self.schema is not None and self._labeled_schema is not None
                and self._labeled_schema != self.schema.version_id):
            with self._lock:
                self.labeled = []
                self.recent = []
            self._labeled_schema = None

        done_keys = {(r.chatlog_id, r.message_index) for r in self.labeled}
        todo = [m for m in messages
                if (m.chatlog_id, m.message_index) not in done_keys]
        offset = len(messages) - len(todo)
        progress = self._step_progress(key)
        progress(offset, len(messages))

        def on_result(m: SampledMessage, r: MessageLabels) -> None:
            with self._lock:
                self.labeled.append(r)
                self._labeled_schema = self.schema.version_id
            self._note_recent(m, r)

        draft_labels(todo, self.schema, self.generate,
                     on_progress=lambda done, total:
                         progress(offset + done, len(messages)),
                     on_result=on_result)

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
        self._init_steps(("count", "Counting conversations"),
                         ("fetch", "Fetching conversations"),
                         ("schema", "Drafting schema"),
                         ("label", "Labeling review sample"))

        def job() -> None:
            self._begin_step("count")
            if self._total_conversations is None:
                total = self.count(self.ext_db_url)
                with self._lock:
                    self._total_conversations = total
            self._end_step(
                "count",
                name=f"Counted {self._total_conversations} conversations")
            self._begin_step("fetch")
            if not self.conversations:
                convs = self.fetch(self.ext_db_url, max_conversations,
                                   on_progress=self._step_progress("fetch"))
                total = self._total_conversations
                with self._lock:
                    self.conversations = convs
                    self.provenance = {"fetched": len(convs), "total": total,
                                       "excluded": max(0, total - len(convs))}
            self._end_step(
                "fetch",
                name=f"Fetched {len(self.conversations)} conversations",
                detail=f"{self.provenance['excluded']} excluded")
            with self._lock:
                self.phase = "drafting"
            self._begin_step("schema")
            if self.schema is None:
                schema = draft_schema(intent, self.generate)
                with self._lock:
                    self.schema = schema
            if not self.sample:
                with self._lock:
                    self.sample = stratified_sample(
                        self.conversations, n=sample_size, seed=seed)
            self._end_step(
                "schema", name=f"Schema {self.schema.version_id} drafted",
                detail=f"{len(self.schema.labels)} labels")
            self._begin_step("label")
            self._label_incremental(self.sample, "label")
            self._end_step(
                "label", name=f"Labeled {len(self.sample)} sample messages")
            with self._lock:
                self.phase = "review"
        self._launch(job, "fetching")

    def tweak(self, feedback: str) -> None:
        with self._lock:
            self._require("review")
            self.phase = "drafting"
            self.labeled = []      # new schema version: old labels invalid
            self.recent = []
        self._init_steps(("schema", "Revising schema"),
                         ("label", "Labeling review sample"))
        revised = {"done": False}  # retry guard: never revise twice

        def job() -> None:
            self._begin_step("schema")
            if not revised["done"]:
                schema = revise_schema(self.schema, feedback, self.generate)
                revised["done"] = True
                with self._lock:
                    self.schema = schema
            self._end_step(
                "schema", name=f"Schema {self.schema.version_id} revised",
                detail=f"{len(self.schema.labels)} labels")
            self._begin_step("label")
            self._label_incremental(self.sample, "label")
            self._end_step(
                "label", name=f"Labeled {len(self.sample)} sample messages")
            with self._lock:
                self.phase = "review"
        self._launch(job, "drafting")

    def accept(self) -> None:
        with self._lock:
            self._require("review")
            self.phase = "mass_labeling"
            self.recent = []
        self._init_steps(("save", "Saving schema"),
                         ("sample", "Sampling corpus"),
                         ("label", "Labeling messages"),
                         ("snapshot", "Writing snapshot"))

        def job() -> None:
            self._begin_step("save")
            save_schema(self.schema, self.data_dir)
            self._end_step(
                "save", name=f"Schema {self.schema.version_id} saved",
                detail=f"{len(self.schema.labels)} labels")
            self._begin_step("sample")
            all_messages = stratified_sample(self.conversations, n=10**9,
                                             seed=self.seed)
            self._end_step(
                "sample", name=f"Sampled {len(all_messages)} messages",
                detail=f"from {len(self.conversations)} conversations")
            self._begin_step("label")
            # review-sample labels are same-schema, same-classifier: reused
            self._label_incremental(all_messages, "label")
            self._end_step(
                "label", name=f"Labeled {len(all_messages)} messages")
            self._begin_step("snapshot")
            path = emit_snapshot(
                self.conversations, self.labeled, self.schema,
                model=DEFAULT_MODEL, repo_sha=self.repo_sha,
                data_dir=self.data_dir,
                excluded_conversations=self.provenance["excluded"])
            self._end_step("snapshot", name="Snapshot written",
                           detail=str(path))
            summary = compute_summary(self.conversations, self.labeled,
                                      self.schema, seed=self.seed)
            summary["classifier"] = {
                "hash": classifier_hash(self.schema, DEFAULT_MODEL),
                "model": DEFAULT_MODEL,
            }
            with self._lock:
                self.snapshot_path = path
                self.summary = summary
                self.phase = "done"
        self._launch(job, "mass_labeling")

    def quit(self) -> None:
        with self._lock:
            self._require("review", "error", "done")
            self._reset()

    def retry_step(self) -> None:
        with self._lock:
            self._require("error")
            if self._retry_job is None:
                raise PhaseError(self.phase)
            self.error = None
            self.phase = self._retry_phase
            self.retry_info = None
            job = self._retry_job
        self._run(job)

    def back_to_review(self) -> None:
        with self._lock:
            self._require("error")
            if self.schema is None or not self.sample:
                raise PhaseError(self.phase)
            self.error = None
            self.phase = "review"

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
                "status": {
                    "steps": [dict(s) for s in self.steps],
                    "retry": self.retry_info,
                    "recent": [dict(r) for r in self.recent],
                },
                "recovery": ({
                    "can_retry": self._retry_job is not None,
                    "can_review": self.schema is not None and bool(self.sample),
                    "labeled_count": len(self.labeled),
                    "conversations": len(self.conversations),
                } if self.phase == "error" else None),
                "schema": schema,
                "sample": sample,
                "snapshot_path": (str(self.snapshot_path)
                                  if self.snapshot_path else None),
                "summary": self.summary if self.phase == "done" else None,
            }


# --- FastAPI layer ---------------------------------------------------------

import sys

from fastapi import FastAPI, HTTPException
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

    @app.post("/api/retry")
    def retry() -> dict:
        session.retry_step()
        return {"ok": True}

    @app.post("/api/back-to-review")
    def back_to_review() -> dict:
        session.back_to_review()
        return {"ok": True}

    @app.get("/api/examples")
    def examples(label: str, n: int = 5, seed: int = 0) -> dict:
        session._require("done")
        if label not in {l.name for l in session.schema.labels}:
            raise HTTPException(status_code=404,
                                detail=f"label {label!r} not in schema")
        n = max(1, min(25, n))
        return {"examples": sample_examples(session.conversations,
                                            session.labeled, label,
                                            n=n, seed=seed)}

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
    session: LoopSession | None = None
    generate = make_generate(
        settings.gemini_api_key,
        on_retry=lambda info: session.note_retry(info) if session else None)
    session = LoopSession(generate=generate,
                          ext_db_url=settings.ext_db_url,
                          data_dir=settings.data_dir,
                          repo_sha=_repo_sha(settings.repo_root))
    # 127.0.0.1 only: student text never leaves the machine (CLAUDE.md rule 4)
    print("label-loop web UI on http://127.0.0.1:8321 (is bin/tunnel running?)")
    uvicorn.run(create_app(session), host="127.0.0.1", port=8321)
