# Labeling Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A localhost FastAPI + single-HTML-page UI covering the full `label-loop` flow: intent → draft schema + labeled stratified sample → accept/tweak → mass-label → snapshot.

**Architecture:** A pure-Python `LoopSession` state machine (`idle → fetching → drafting → review → mass_labeling → done`, `error` from any working state) with injected dependencies (DB fetchers, LLM generate, job runner), wrapped by a thin FastAPI app that serves one static page which polls `GET /api/state`. Reuses the CLI's building blocks unchanged; `cli.py`/`run_loop` untouched.

**Tech Stack:** FastAPI, uvicorn, vanilla JS single page. Tests: pytest + FastAPI TestClient (httpx), fake `generate`, fabricated conversations from `tests/test_sampler.CONVS`.

Spec: `docs/superpowers/specs/2026-08-03-labeling-web-ui-design.md`.

## Global Constraints

- Python ≥ 3.11 (pyproject `requires-python`).
- Server binds `127.0.0.1` only — student text never leaves the machine (CLAUDE.md rule 4).
- `data/` and `.env` stay gitignored; no student text or fixtures quoting it in git.
- The review screen MUST display `ACCEPT_NOTE` from `src/labeling/cli.py` verbatim (invariant 8).
- Excluded-conversation provenance shown with the same numbers the CLI prints.
- Tests are hermetic: no DB, no Gemini, no network.
- Do not modify `src/labeling/cli.py`, `run_loop`, or any ChatSight code.

---

### Task 1: `LoopSession` state machine

**Files:**
- Create: `src/labeling/webapp.py` (session class only in this task)
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `fetch_conversations(ext_db_url, limit)`, `count_conversations(ext_db_url)` (src/ingest/rawlog.py); `draft_schema(intent_text, generate)`, `revise_schema(current, feedback, generate)` (src/labeling/elicit.py); `stratified_sample(conversations, n, seed)` (src/labeling/sampler.py); `draft_labels(messages, schema, generate)` (src/labeling/draft.py); `save_schema(schema, data_dir)` (src/labeling/schema.py); `emit_snapshot(...)` (src/labeling/snapshot.py); `ACCEPT_NOTE` (src/labeling/cli.py); `DEFAULT_MODEL` (src/labeling/llm.py).
- Produces: class `LoopSession` with methods `start(intent, max_conversations=200, sample_size=25, seed=0) -> None`, `tweak(feedback: str) -> None`, `accept() -> None`, `quit() -> None`, `state() -> dict`. All four mutators raise `PhaseError(current_phase)` when called in an invalid phase. `state()` returns the JSON-ready dict shown below. Task 2 relies on these exact names.

`state()` shape (all keys always present; unavailable values are `None`):

```python
{
    "phase": "idle|fetching|drafting|review|mass_labeling|done|error",
    "error": None,               # str when phase == "error"
    "accept_note": ACCEPT_NOTE,  # constant, always present
    "provenance": None,          # {"fetched": int, "total": int, "excluded": int}
    "schema": None,              # {"version_id": str, "intent": str,
                                 #  "labels": [{"name","kind","description"}]}
    "sample": None,              # [{"stratum","text","labels": [str],
                                 #   "rationales": {label: str}}]
    "snapshot_path": None,       # str when phase == "done"
}
```

- [x] **Step 1: Write the failing tests**

```python
# tests/test_webapp.py
"""Hermetic tests for the labeling web UI. No DB, no Gemini, no network."""
from pathlib import Path

import pytest

from src.labeling.cli import ACCEPT_NOTE
from src.labeling.webapp import LoopSession, PhaseError
from tests.test_cli import make_fake_generate
from tests.test_sampler import CONVS


def make_session(tmp_path: Path) -> LoopSession:
    return LoopSession(
        fetch=lambda url, limit: CONVS[:limit] if limit else CONVS,
        count=lambda url: len(CONVS) + 3,   # 3 "excluded" beyond the fetch cap
        generate=make_fake_generate(),
        ext_db_url="postgresql+psycopg2://unused",
        data_dir=tmp_path,
        repo_sha="testsha",
        runner=lambda job: job(),           # synchronous in tests
    )


def test_initial_state_is_idle(tmp_path):
    s = make_session(tmp_path).state()
    assert s["phase"] == "idle"
    assert s["accept_note"] == ACCEPT_NOTE
    assert s["schema"] is None and s["sample"] is None


def test_start_reaches_review_with_schema_sample_provenance(tmp_path):
    session = make_session(tmp_path)
    session.start("what confuses students", max_conversations=4,
                  sample_size=4, seed=0)
    s = session.state()
    assert s["phase"] == "review"
    assert s["schema"]["labels"][0]["name"] == "label-v1"
    assert s["schema"]["intent"] == "what confuses students"
    assert len(s["sample"]) == 4
    assert all("stratum" in m and "text" in m for m in s["sample"])
    assert s["provenance"] == {"fetched": 4, "total": len(CONVS) + 3,
                               "excluded": len(CONVS) + 3 - 4}


def test_tweak_produces_new_chained_schema_version(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    v1 = session.state()["schema"]["version_id"]
    session.tweak("split confusion by cause")
    s = session.state()
    assert s["phase"] == "review"
    assert s["schema"]["labels"][0]["name"] == "label-v2"
    assert s["schema"]["version_id"] != v1


def test_accept_emits_snapshot_and_saves_schema(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    snap = Path(s["snapshot_path"])
    assert (snap / "manifest.json").exists()
    assert list((tmp_path / "schemas").glob("*.json"))  # save_schema ran


def test_invalid_phase_actions_raise(tmp_path):
    session = make_session(tmp_path)
    with pytest.raises(PhaseError):
        session.tweak("nope")           # idle: no tweak
    with pytest.raises(PhaseError):
        session.accept()                # idle: no accept
    with pytest.raises(PhaseError):
        session.quit()                  # idle: nothing to quit
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.start("again")          # review: no restart without quit


def test_quit_resets_to_idle(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.quit()
    s = session.state()
    assert s["phase"] == "idle"
    assert s["schema"] is None and s["sample"] is None


def test_job_error_surfaces_and_quit_recovers(tmp_path):
    def boom(url, limit):
        raise RuntimeError("tunnel down")
    session = make_session(tmp_path)
    session.fetch = boom
    session.start("intent")
    s = session.state()
    assert s["phase"] == "error"
    assert "tunnel down" in s["error"]
    session.quit()
    assert session.state()["phase"] == "idle"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_webapp.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError`/`ImportError` on `src.labeling.webapp`.

- [x] **Step 3: Write the implementation**

```python
# src/labeling/webapp.py
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_webapp.py -v` — expected: all PASS.
Then: `uv run pytest -q` — expected: whole suite PASS (no regressions).

- [x] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: LoopSession state machine for labeling web UI"
```

---

### Task 2: FastAPI app + entry point

**Files:**
- Modify: `src/labeling/webapp.py` (append app factory + `main()`)
- Modify: `pyproject.toml` (deps `fastapi`, `uvicorn`; dev dep `httpx`; script `label-loop-web`)
- Test: `tests/test_webapp.py` (append API tests)

**Interfaces:**
- Consumes: `LoopSession`, `PhaseError` from Task 1; `Settings.load()` (src/config.py); `make_generate(api_key)` (src/labeling/llm.py).
- Produces: `create_app(session: LoopSession) -> FastAPI` with routes `GET /` (page, added Task 3), `GET /api/state`, `POST /api/start` `{intent, max_conversations?, sample_size?, seed?}`, `POST /api/tweak` `{feedback}`, `POST /api/accept`, `POST /api/quit`; `PhaseError` → HTTP 409 `{"detail": ...}`; `main()` console entry `label-loop-web`.

- [x] **Step 1: Add dependencies and script**

In `pyproject.toml`, extend `dependencies` with:

```toml
    # labeling web UI (localhost-only instructor surface)
    "fastapi>=0.115",
    "uvicorn>=0.30",
```

extend `dev` group with `"httpx>=0.27",` and add under `[project.scripts]`:

```toml
label-loop-web = "src.labeling.webapp:main"
```

Run: `uv sync` — expected: resolves and installs cleanly.

- [x] **Step 2: Write the failing API tests**

Append to `tests/test_webapp.py`:

```python
from fastapi.testclient import TestClient

from src.labeling.webapp import create_app


def test_api_happy_path(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    assert client.get("/api/state").json()["phase"] == "idle"
    r = client.post("/api/start", json={
        "intent": "what confuses students", "max_conversations": 4,
        "sample_size": 4, "seed": 0})
    assert r.status_code == 200
    s = client.get("/api/state").json()
    assert s["phase"] == "review"
    assert s["accept_note"] == ACCEPT_NOTE
    assert client.post("/api/tweak",
                       json={"feedback": "split it"}).status_code == 200
    assert client.post("/api/accept").status_code == 200
    s = client.get("/api/state").json()
    assert s["phase"] == "done"
    assert s["snapshot_path"] is not None


def test_api_invalid_phase_returns_409(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    assert client.post("/api/accept").status_code == 409
    assert client.post("/api/tweak", json={"feedback": "x"}).status_code == 409
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    assert client.post("/api/start", json={"intent": "i"}).status_code == 409
    assert client.post("/api/quit").status_code == 200
    assert client.get("/api/state").json()["phase"] == "idle"
```

- [x] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_webapp.py -v`
Expected: new tests FAIL with `ImportError: cannot import name 'create_app'`.

- [x] **Step 4: Implement the app factory and main**

Append to `src/labeling/webapp.py`:

```python
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
        return JSONResponse(status_code=409,
                            content={"detail": str(exc)})

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
    print("label-loop web UI on http://127.0.0.1:8321 "
          "(is bin/tunnel running?)")
    uvicorn.run(create_app(session), host="127.0.0.1", port=8321)
```

Note: `host="127.0.0.1"` is a Global Constraint — never widen it.

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest -q` — expected: whole suite PASS.

- [x] **Step 6: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py pyproject.toml uv.lock
git commit -m "feat: FastAPI app + label-loop-web entry point"
```

---

### Task 3: The page

**Files:**
- Create: `src/labeling/static/index.html`
- Test: `tests/test_webapp.py` (append one route test)

**Interfaces:**
- Consumes: the Task 2 API exactly as specified (`/api/state` shape from Task 1).
- Produces: the instructor-facing page; `GET /` serves it.

- [x] **Step 1: Write the failing route test**

```python
def test_index_served(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    r = client.get("/")
    assert r.status_code == 200
    assert "label-loop" in r.text
```

Run: `uv run pytest tests/test_webapp.py::test_index_served -v`
Expected: FAIL (file missing → 500/404).

- [x] **Step 2: Write the page**

Create `src/labeling/static/index.html` — self-contained, no external assets, vanilla JS polling `/api/state` every 1.5s. Screens keyed off `phase`:

- `idle`: form — intent textarea, numeric inputs for max-conversations (200), sample-size (25), seed (0); Start button → `POST /api/start`.
- `fetching`/`drafting`/`mass_labeling`: phase name + indeterminate spinner (mass_labeling adds "labeling the full corpus — this takes a while").
- `review`: provenance line ("Fetched X of Y conversations; Z EXCLUDED from this run and the snapshot"); schema panel (version id + each label's name/kind/description); the `accept_note` from state rendered in a highlighted banner; sample grouped by stratum — each message shows `[stratum] text`, applied labels as chips, rationales beneath; footer with tweak textarea + Tweak button (`POST /api/tweak`), Accept button (`POST /api/accept`), Quit button (`POST /api/quit`).
- `done`: snapshot path + "Add a row to snapshots.md with this manifest's provenance."; Quit/reset button.
- `error`: the error text + Quit/reset button.

All content is DOM-inserted via `textContent` (never `innerHTML` with server data — messages are student text). Single `<style>` block; readable defaults (max-width column, system font stack, muted chips); no gradients or animation beyond the spinner.

- [x] **Step 3: Run tests**

Run: `uv run pytest -q` — expected: whole suite PASS.

- [x] **Step 4: Manual smoke check (no DB/LLM needed)**

Verify the wheel would include the page and the app serves it:
`uv run python -c "from src.labeling.webapp import STATIC_DIR; print((STATIC_DIR/'index.html').exists())"` → `True`.
Full live check (tunnel + Gemini key) stays with existing manual Task 9 (`label-loop` smoke test) — record `label-loop-web` there too.

- [x] **Step 5: Commit**

```bash
git add src/labeling/static/index.html tests/test_webapp.py
git commit -m "feat: instructor-facing page for the labeling loop"
```
