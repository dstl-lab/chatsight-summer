"""Localhost web UI for the draft->review->tweak loop. Same building blocks as
the CLI (cli.py stays canonical for scripted runs); drafting is anchored, which
is fine for drafting and forbidden for measurement (CLAUDE.md invariant 8).

Single in-process session: this is a one-instructor localhost research tool.
Binds 127.0.0.1 only — student text never leaves the machine (rule 4)."""
import threading
import time
from datetime import date
from pathlib import Path
from typing import Callable

from src.ingest.rawlog import Conversation, count_conversations, fetch_conversations
from src.labeling.cli import ACCEPT_NOTE, load_accepted_profile
from src.labeling.course import DSC10_PROFILE, CourseProfile
from src.labeling.draft import MessageLabels, classifier_hash, draft_labels
from src.labeling.elicit import draft_schema, revise_schema
from src.labeling.explore import explore, write_draft
from src.labeling.llm import DEFAULT_MODEL, Generate
from src.labeling.profile2 import (CourseProfileV2, compose_schema,
                                   lint_profile, save_profile)
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema, save_schema
from src.labeling.snapshot import emit_snapshot
from src.labeling.summary import compute_summary, sample_examples

WORKING_PHASES = ("fetching", "drafting", "mass_labeling")
PEEK_FETCH_CAP = 40   # conversations; spec: docs/superpowers/specs/2026-08-06
EXPLORE_SAMPLE = 150   # conversations read by the exploration pass (explore CLI default)

_TERCILE_WORDS = {"short": "short conversation", "mid": "medium conversation",
                  "long": "long conversation"}
_POSITION_WORDS = {"early": "early turn", "late": "late turn"}


def _plain_stratum(stratum: str) -> str:
    tercile, _, position = stratum.partition("/")
    return (f"{_TERCILE_WORDS.get(tercile, tercile)} · "
            f"{_POSITION_WORDS.get(position, position)}")


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
                 = _thread_runner, profile: CourseProfile = DSC10_PROFILE,
                 workers: int = 8, profiles_dir: Path,
                 course_slug: str = "dsc10"):
        self.fetch = fetch
        self.count = count
        self.generate = generate
        self.ext_db_url = ext_db_url
        self.data_dir = data_dir
        self.repo_sha = repo_sha
        self.runner = runner
        self.profile = profile
        self.workers = workers
        self.profiles_dir = profiles_dir
        self.course_slug = course_slug
        self._lock = threading.Lock()
        # profile2 survives _reset() (quit()): the accepted profile is not
        # part of a labeling run's working state.
        self.profile2: CourseProfileV2 | None = None
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
        self.abstained_count = 0
        self.abstained_recent: list[dict] = []
        self._retry_job: Callable[[], None] | None = None
        self._retry_phase: str = "idle"
        self.seed = 0
        self.profile2_draft: CourseProfileV2 | None = None
        self._explore_convs: list[Conversation] = []

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
                self.abstained_count = 0
                self.abstained_recent = []
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
                if r.no_label_fits:
                    self.abstained_count += 1
                    self.abstained_recent = (
                        [{"text": m.text, "note": r.coverage_note}]
                        + self.abstained_recent)[:3]
            self._note_recent(m, r)

        draft_labels(todo, self.schema, self.profile, self.generate,
                     on_progress=lambda done, total:
                         progress(offset + done, len(messages)),
                     on_result=on_result, workers=self.workers,
                     profile2=self.profile2)

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
                schema = draft_schema(intent, self.profile, self.generate,
                                      profile2=self.profile2)
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
            self.abstained_count = 0
            self.abstained_recent = []
        self._init_steps(("schema", "Revising schema"),
                         ("label", "Labeling review sample"))
        revised = {"done": False}  # retry guard: never revise twice

        def job() -> None:
            self._begin_step("schema")
            if not revised["done"]:
                schema = revise_schema(self.schema, feedback, self.profile,
                                       self.generate)
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
        composed = {"done": False}  # retry guard: never compose twice

        def job() -> None:
            self._begin_step("save")
            save_schema(self.schema, self.data_dir)
            if self.profile2 is not None and not composed["done"]:
                schema = compose_schema(self.profile2, self.schema)
                save_schema(schema, self.data_dir)
                composed["done"] = True
                with self._lock:
                    self.schema = schema
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
            # Without a profile2, this schema is unchanged from the review
            # pass (same-schema, same-classifier), so review-sample labels
            # are reused. With a profile2, composition above just bumped
            # the schema version, so the vintage guard in
            # _label_incremental clears those review labels and this pass
            # relabels the full corpus against the composed schema.
            self._label_incremental(all_messages, "label")
            self._end_step(
                "label", name=f"Labeled {len(all_messages)} messages")
            self._begin_step("snapshot")
            path = emit_snapshot(
                self.conversations, self.labeled, self.schema,
                model=DEFAULT_MODEL, repo_sha=self.repo_sha,
                data_dir=self.data_dir,
                excluded_conversations=self.provenance["excluded"],
                profile=self.profile, profile2=self.profile2)
            self._end_step("snapshot", name="Snapshot written",
                           detail=str(path))
            summary = compute_summary(self.conversations, self.labeled,
                                      self.schema, seed=self.seed)
            summary["classifier"] = {
                "hash": classifier_hash(self.schema, DEFAULT_MODEL,
                                        self.profile, profile2=self.profile2),
                "model": DEFAULT_MODEL,
                "profile_id": self.profile.profile_id,
                "profile2_id": (self.profile2.profile_id
                                if self.profile2 else None),
            }
            with self._lock:
                self.snapshot_path = path
                self.summary = summary
                self.phase = "done"
        self._launch(job, "mass_labeling")

    def explore_course(self, slug: str, materials: list[dict]) -> None:
        """Exploration pass -> CourseProfile v2 draft for skim-and-accept.
        Materials text lives only in this call's closure (rule 4)."""
        with self._lock:
            self._require("idle")
            self.course_slug = slug
            self.phase = "exploring"
        self._init_steps(("fetch", "Fetching conversations"),
                         ("explore", "Reading the corpus"))
        texts = [m["text"] for m in materials]

        def job() -> None:
            self._begin_step("fetch")
            convs = self.fetch(self.ext_db_url, EXPLORE_SAMPLE,
                               on_progress=self._step_progress("fetch"))
            self._end_step("fetch",
                           name=f"Fetched {len(convs)} conversations")
            self._begin_step("explore")
            v2 = explore(convs, texts, self.generate,
                         sample_meta={"conversations": len(convs), "seed": 0},
                         repo_sha=self.repo_sha,
                         explored_on=date.today().isoformat())
            write_draft(v2, convs, self.profiles_dir / f"{slug}-draft.json")
            self._end_step("explore",
                           name=f"Profile drafted: {len(v2.concepts)} concepts")
            with self._lock:
                self.profile2_draft = v2
                self._explore_convs = convs
                self.phase = "profile_review"
        self._launch(job, "exploring")

    def accept_profile(self, deleted: dict[str, list[str]],
                       promoted: list[str]) -> None:
        """Skim-and-accept surgery: delete/promote via model_copy — no LLM
        (spec 2026-08-08). Promotion fills deterministic template criteria;
        wording refinement belongs to the tweak loop. Raises ValueError with
        the reason; phase stays profile_review."""
        with self._lock:
            self._require("profile_review")
            draft = self.profile2_draft

        def _promote(c):
            return c.model_copy(update={
                "promoted": True,
                "positive_criteria": c.positive_criteria or
                    f"The student message substantively engages "
                    f"{c.name} ({c.description})",
                "negative_criteria": c.negative_criteria or
                    f"{c.name} appears only incidentally (e.g. inside "
                    "pasted code or output) without the student engaging it",
            })
        concepts = [_promote(c) if c.name in set(promoted) else c
                    for c in draft.concepts
                    if c.name not in set(deleted.get("concepts", []))]
        affect = [l for l in draft.affect_labels
                  if l.name not in set(deleted.get("affect", []))]
        intent = [l for l in draft.intent_labels
                  if l.name not in set(deleted.get("intent", []))]
        v2 = draft.model_copy(update={
            "concepts": concepts, "affect_labels": affect,
            "intent_labels": intent, "accepted": True})
        names = ([c.name for c in v2.concepts if c.promoted]
                 + [l.name for l in v2.affect_labels + v2.intent_labels])
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError("label name collision across layers: "
                             + ", ".join(sorted(dupes)))
        findings = lint_profile(v2, self._explore_convs)
        if findings:
            raise ValueError("profile quotes student text (rule 4):\n"
                             + "\n".join(findings))
        save_profile(v2, self.profiles_dir / f"{self.course_slug}.json")
        with self._lock:
            self.profile2 = v2
            self.profile2_draft = None
            self._explore_convs = []
            self.phase = "idle"

    def discard_profile(self) -> None:
        """Drop the draft (and any in-session accepted profile) so the
        instructor can re-explore. Files on disk are left; the next accept
        overwrites them."""
        with self._lock:
            self._require("profile_review", "idle")
            self.profile2_draft = None
            self._explore_convs = []
            self.profile2 = None
            self.phase = "idle"

    def quit(self) -> None:
        with self._lock:
            self._require("review", "error", "done", "profile_review")
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

    def peek(self, n: int = 6, seed: int = 0) -> dict:
        """Display-only sample for the idle screen. Reads through the tunnel
        but retains nothing: no session state, no snapshot contact."""
        with self._lock:
            self._require("idle")
        n = max(1, min(12, n))
        convs = self.fetch(self.ext_db_url, PEEK_FETCH_CAP)
        picks = stratified_sample(convs, n=n, seed=seed)
        return {
            "messages": [{"text": m.text,
                          "stratum": _plain_stratum(m.stratum)}
                         for m in picks],
            "total_messages": sum(len(c.student_turns) for c in convs),
        }

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

            def _labels(ls):
                return [{"name": l.name, "kind": l.kind,
                         "description": l.description,
                         "positive_criteria": l.positive_criteria,
                         "negative_criteria": l.negative_criteria}
                        for l in ls]
            profile: dict = {"slug": self.course_slug,
                             "draft": None, "accepted": None}
            if self.profile2_draft is not None:
                d = self.profile2_draft
                profile["draft"] = {
                    "concepts": [{"name": c.name,
                                  "description": c.description,
                                  "aliases": c.aliases,
                                  "promoted": c.promoted}
                                 for c in d.concepts],
                    "affect": _labels(d.affect_labels),
                    "intent": _labels(d.intent_labels),
                }
            if self.profile2 is not None:
                p = self.profile2
                profile["accepted"] = {
                    "profile_id": p.profile_id,
                    "course_name": p.base.course_name,
                    "concepts": len(p.concepts),
                    "promoted": sum(1 for c in p.concepts if c.promoted),
                    "affect": len(p.affect_labels),
                    "intent": len(p.intent_labels),
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
                    "abstention": {"count": self.abstained_count,
                                   "recent": [dict(a) for a in
                                              self.abstained_recent]},
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
                "profile": profile,
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


class MaterialFile(BaseModel):
    name: str
    text: str


class ExploreRequest(BaseModel):
    slug: str = "dsc10"
    materials: list[MaterialFile] = []


class ProfileAcceptRequest(BaseModel):
    deleted: dict[str, list[str]] = {}
    promoted: list[str] = []


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

    @app.get("/api/peek")
    def peek(n: int = 6, seed: int = 0) -> dict:
        return session.peek(n=n, seed=seed)

    @app.post("/api/explore")
    def explore_ep(req: ExploreRequest) -> dict:
        session.explore_course(req.slug,
                               [m.model_dump() for m in req.materials])
        return {"ok": True}

    @app.post("/api/profile/accept")
    def profile_accept(req: ProfileAcceptRequest) -> dict:
        try:
            session.accept_profile(deleted=req.deleted,
                                   promoted=req.promoted)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    @app.post("/api/profile/reexplore")
    def profile_reexplore() -> dict:
        session.discard_profile()
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
    import argparse

    import uvicorn

    from src.config import Settings
    from src.labeling.llm import make_generate

    parser = argparse.ArgumentParser(description="label-loop web UI")
    parser.add_argument("--course", default="dsc10",
                        help="course slug; loads profiles/<slug>.json when "
                             "present and accepted (default: dsc10)")
    args = parser.parse_args()

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    session: LoopSession | None = None
    generate = make_generate(
        settings.gemini_api_key,
        on_retry=lambda info: session.note_retry(info) if session else None)
    profiles_dir = Path(settings.repo_root) / "profiles"
    session = LoopSession(generate=generate,
                          ext_db_url=settings.ext_db_url,
                          data_dir=settings.data_dir,
                          repo_sha=_repo_sha(settings.repo_root),
                          workers=settings.labeling_workers,
                          profiles_dir=profiles_dir,
                          course_slug=args.course)
    profile_path = profiles_dir / f"{args.course}.json"
    if profile_path.exists():
        session.profile2 = load_accepted_profile(str(profile_path))
    # 127.0.0.1 only: student text never leaves the machine (CLAUDE.md rule 4)
    print("label-loop web UI on http://127.0.0.1:8321 (is bin/tunnel running?)")
    uvicorn.run(create_app(session), host="127.0.0.1", port=8321)
