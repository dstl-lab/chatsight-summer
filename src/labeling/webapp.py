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
        self.seed = 0

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
            labeled = draft_labels(sample, schema, self.generate)
            with self._lock:
                self.schema, self.sample, self.labeled = schema, sample, labeled
                self.phase = "review"
        self._run(job)

    def tweak(self, feedback: str) -> None:
        with self._lock:
            self._require("review")
            self.phase = "drafting"

        def job() -> None:
            schema = revise_schema(self.schema, feedback, self.generate)
            labeled = draft_labels(self.sample, schema, self.generate)
            with self._lock:
                self.schema, self.labeled = schema, labeled
                self.phase = "review"
        self._run(job)

    def accept(self) -> None:
        with self._lock:
            self._require("review")
            self.phase = "mass_labeling"

        def job() -> None:
            save_schema(self.schema, self.data_dir)
            all_messages = stratified_sample(self.conversations, n=10**9,
                                             seed=self.seed)
            labeled = draft_labels(all_messages, self.schema, self.generate)
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
                "schema": schema,
                "sample": sample,
                "snapshot_path": (str(self.snapshot_path)
                                  if self.snapshot_path else None),
            }
