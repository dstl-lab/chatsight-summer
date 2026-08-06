# Labeling UI Live Progress + Work Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the labeling web UI live per-step progress (gate rail, retry banner, ETA, recently-labeled ticker) and make long runs safe (snapshot-collision renaming, incremental label accumulation, resumable errors).

**Architecture:** The polling architecture is unchanged: one static `index.html` polls `GET /api/state` every 1.5s. `LoopSession` (src/labeling/webapp.py) gains a structured `status` object (steps with state/progress, retry info, recent labels) built from small callbacks threaded into `llm.with_retries`, `draft.draft_labels`, and `rawlog.fetch_conversations`. Jobs become resumable closures that skip already-completed work.

**Tech Stack:** Python 3.12, FastAPI, pytest (hermetic — fake `generate` + fake fetch, synchronous runner), vanilla JS/CSS frontend, no build step.

**Spec:** `docs/2026-08-05-labeling-ui-progress-design.md`

## Global Constraints

- Student text in the frontend: **always `textContent`, never `innerHTML`** (CLAUDE.md rule 4).
- The `recent` ticker is in-memory only — nothing new is written to disk.
- Server binds 127.0.0.1 only; do not change host/port.
- Snapshots stay immutable: never overwrite an existing snapshot directory (rule 3) — collisions get a new directory, not a rewrite.
- Tests are hermetic: no DB, no Gemini, no network, no real sleeps. Reuse `make_fake_generate()` (tests/test_cli.py:13), `CONVS` (tests/test_sampler.py), and `runner=lambda job: job()`.
- Out of scope (decided): cancel buttons, disabling in-flight buttons, dead-server detection, smarter polling.
- Run tests with: `python -m pytest tests/ -q` from the repo root.

---

### Task 1: `with_retries` retry callback

**Files:**
- Modify: `src/labeling/llm.py:13-27` (`with_retries`), `src/labeling/llm.py:30-46` (`make_generate`)
- Test: `tests/test_llm.py`

**Interfaces:**
- Produces: `with_retries(generate, attempts=4, base_delay=2.0, sleep=time.sleep, on_retry=None)` where `on_retry: Callable[[dict | None], None]`. Before each backoff sleep it calls `on_retry({"attempt": <1-based attempt about to run>, "max": attempts, "wait_s": <delay>})`; on every successful call it calls `on_retry(None)` (clears the banner). `make_generate(api_key, model=DEFAULT_MODEL, on_retry=None)` threads it through.

- [ ] **Step 1: Write the failing test** (append to `tests/test_llm.py`)

```python
def test_with_retries_reports_and_clears_retry():
    calls: list[int] = []
    events: list[dict | None] = []

    def flaky(prompt, response_model):
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("429")
        return "ok"

    g = with_retries(flaky, sleep=lambda s: None, on_retry=events.append)
    assert g("p", None) == "ok"
    assert events == [
        {"attempt": 2, "max": 4, "wait_s": 2.0},
        {"attempt": 3, "max": 4, "wait_s": 4.0},
        None,
    ]


def test_with_retries_without_callback_still_works():
    g = with_retries(lambda p, m: "ok", sleep=lambda s: None)
    assert g("p", None) == "ok"
```

Make sure `with_retries` is imported at the top of the file (it already is if other tests use it; add if missing).

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `python -m pytest tests/test_llm.py -q`
Expected: FAIL — `with_retries() got an unexpected keyword argument 'on_retry'`

- [ ] **Step 3: Implement**

Replace `with_retries` in `src/labeling/llm.py`:

```python
def with_retries(generate: Generate, attempts: int = 4, base_delay: float = 2.0,
                 sleep: Callable[[float], None] = time.sleep,
                 on_retry: Callable[[dict | None], None] | None = None
                 ) -> Generate:
    """A mass-label run is one call per student message, hundreds deep; a
    single transient 429/5xx must not abort it. Retries everything — a
    permanent error (bad key) just costs a few extra seconds before raising.
    on_retry gets {"attempt", "max", "wait_s"} before each backoff and None
    after any success, so a UI can show and clear a retry banner."""
    def retrying(prompt: str, response_model: type[BaseModel]) -> BaseModel:
        for attempt in range(attempts):
            try:
                result = generate(prompt, response_model)
                if on_retry:
                    on_retry(None)
                return result
            except Exception:
                if attempt == attempts - 1:
                    raise
                delay = base_delay * 2 ** attempt
                if on_retry:
                    on_retry({"attempt": attempt + 2, "max": attempts,
                              "wait_s": delay})
                sleep(delay)
        raise AssertionError("unreachable")
    return retrying
```

And change `make_generate`'s signature/return:

```python
def make_generate(api_key: str, model: str = DEFAULT_MODEL,
                  on_retry: Callable[[dict | None], None] | None = None
                  ) -> Generate:
    ...
    return with_retries(generate, on_retry=on_retry)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_llm.py -q`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add src/labeling/llm.py tests/test_llm.py
git commit -m "feat: with_retries reports retry attempts via on_retry callback"
```

---

### Task 2: `draft_labels` per-result callback

**Files:**
- Modify: `src/labeling/draft.py:80-98` (`draft_labels`)
- Test: `tests/test_draft.py`

**Interfaces:**
- Produces: `draft_labels(messages, schema, generate, on_progress=None, on_result=None)` where `on_result: Callable[[SampledMessage, MessageLabels], None]` is called once per message immediately after its `MessageLabels` is appended, before `on_progress`. Return value unchanged.

- [ ] **Step 1: Write the failing test** (append to `tests/test_draft.py`; reuse that file's existing schema/generate fixtures — it already builds a schema via `draft_schema` and a fake generate; follow the local pattern for constructing `sample`)

```python
def test_draft_labels_calls_on_result_per_message():
    from tests.test_cli import make_fake_generate
    from tests.test_sampler import CONVS
    from src.labeling.elicit import draft_schema
    from src.labeling.sampler import stratified_sample

    gen = make_fake_generate()
    schema = draft_schema("intent", gen)
    sample = stratified_sample(CONVS, n=4, seed=0)
    seen: list[tuple[int, int]] = []
    results = draft_labels(
        sample, schema, gen,
        on_result=lambda m, r: seen.append((m.chatlog_id, m.message_index)))
    assert seen == [(m.chatlog_id, m.message_index) for m in sample]
    assert len(results) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_draft.py -q`
Expected: FAIL — unexpected keyword argument `on_result`

- [ ] **Step 3: Implement**

In `draft_labels`, add the parameter and call it after `out.append(...)`:

```python
def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 generate: Generate,
                 on_progress: Callable[[int, int], None] | None = None,
                 on_result: Callable[[SampledMessage, MessageLabels], None]
                 | None = None) -> list[MessageLabels]:
```

and inside the loop, after the existing `out.append(...)`:

```python
        if on_result:
            on_result(m, out[-1])
        if on_progress:
            on_progress(i + 1, len(messages))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_draft.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/draft.py tests/test_draft.py
git commit -m "feat: draft_labels emits each result via on_result callback"
```

---

### Task 3: snapshot collision gets a unique directory

**Files:**
- Modify: `src/labeling/snapshot.py:16-19`
- Test: `tests/test_snapshot.py:38-44` (rewrite `test_snapshots_are_immutable`)

**Interfaces:**
- Produces: `emit_snapshot(...)` (signature unchanged) never raises `FileExistsError` on an id collision; it appends `-2`, `-3`, … to the snapshot id. `manifest["snapshot_id"]` always equals the directory name.

- [ ] **Step 1: Rewrite the failing test**

Replace `test_snapshots_are_immutable` in `tests/test_snapshot.py` (delete the `pytest.raises(FileExistsError)` version — colliding runs must not lose work):

```python
def test_snapshot_collision_gets_unique_dir_not_overwrite(tmp_path: Path):
    convs, schema, labels = _fixtures()
    first = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                          data_dir=tmp_path, excluded_conversations=0)
    second = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                           data_dir=tmp_path, excluded_conversations=0)
    third = emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                          data_dir=tmp_path, excluded_conversations=0)
    assert first != second != third
    assert second.name == first.name + "-2"
    assert third.name == first.name + "-3"
    # first snapshot untouched (immutability), and every manifest's
    # snapshot_id matches its directory name
    for path in (first, second, third):
        manifest = json.loads((path / "manifest.json").read_text())
        assert manifest["snapshot_id"] == path.name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_snapshot.py -q`
Expected: FAIL — `FileExistsError` on the second emit

- [ ] **Step 3: Implement**

In `emit_snapshot`, replace the id/path/mkdir lines:

```python
    chash = classifier_hash(schema, model)
    base_id = f"{date.today():%Y%m%d}-{schema.version_id}-{chash[:6]}"
    snapshot_id, n = base_id, 2
    while (data_dir / "snapshots" / snapshot_id).exists():
        snapshot_id = f"{base_id}-{n}"       # never overwrite (rule 3):
        n += 1                               # a collision gets a NEW dir
    path = data_dir / "snapshots" / snapshot_id
    path.mkdir(parents=True, exist_ok=False)
```

(`snapshot_id` already flows into the manifest below — no other change.)

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_snapshot.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/snapshot.py tests/test_snapshot.py
git commit -m "fix: colliding snapshot ids get a -2/-3 suffix instead of FileExistsError"
```

---

### Task 4: `fetch_conversations` progress callback

**Files:**
- Modify: `src/ingest/rawlog.py:78-94`

**Interfaces:**
- Produces: `fetch_conversations(ext_db_url, limit=None, on_progress=None)` where `on_progress: Callable[[int, int], None]` is called after each conversation head is processed with `(i + 1, len(heads))`.

Note: existing rawlog tests only cover the pure helpers (Postgres `payload->>` SQL can't run on sqlite), so this loop has no hermetic test of its own — the callback contract is exercised in Task 5 via the fake fetch in `tests/test_webapp.py`.

- [ ] **Step 1: Implement**

```python
def fetch_conversations(ext_db_url: str, limit: int | None = None,
                        on_progress: Callable[[int, int], None] | None = None
                        ) -> list[Conversation]:
    engine = create_engine(ext_db_url)
    sql = _CONV_SQL + (f"\nLIMIT {int(limit)}" if limit is not None else "")
    out: list[Conversation] = []
    with engine.connect() as conn:
        heads = conn.execute(text(sql)).mappings().all()
        for i, h in enumerate(heads):
            rows = [tuple(r) for r in conn.execute(
                text(_TURNS_SQL), {"conv_id": h["conv_id"]}
            ).fetchall()]
            turns = assemble_turns(rows)
            if turns:
                out.append(Conversation(
                    conv_id=h["conv_id"], chatlog_id=h["chatlog_id"],
                    notebook=h["notebook"], started_at=h["started_at"], turns=turns,
                ))
            if on_progress:
                on_progress(i + 1, len(heads))
    return out
```

Add `Callable` to the `typing` import at the top of the file.

- [ ] **Step 2: Run the whole suite (guards the call-site contract)**

Run: `python -m pytest tests/ -q`
Expected: PASS (no behavior change for existing callers — the new arg is optional)

- [ ] **Step 3: Commit**

```bash
git add src/ingest/rawlog.py
git commit -m "feat: fetch_conversations reports per-conversation progress"
```

---

### Task 5: LoopSession structured status (steps, retry, recent, incremental labels)

This is the core task. `LoopSession` replaces the bare `progress` dict with `status = {steps, retry, recent}` and accumulates labels incrementally.

**Files:**
- Modify: `src/labeling/webapp.py` (`_reset`, `start`, `tweak`, `accept`, `state`, `main`; delete `_set_progress`)
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `with_retries`/`make_generate` `on_retry` (Task 1), `draft_labels` `on_result` (Task 2), `fetch_conversations` `on_progress` (Task 4).
- Produces (for Task 6 and the frontend):
  - `session.steps: list[dict]` — each `{"key": str, "name": str, "detail": str, "state": "pending"|"active"|"done", "progress": {"done": int, "total": int} | None, "started_at": float | None}`.
  - `session.note_retry(info: dict | None)` — public; stores to `session.retry_info`.
  - `session.recent: list[dict]` — newest-first, max 3, items `{"text": str, "labels": list[str]}`.
  - `session._launch(job, retry_phase)` — stores `self._retry_job`/`self._retry_phase` then `self._run(job)` (Task 6 consumes these).
  - `state()["status"] = {"steps": [...], "retry": ..., "recent": [...]}`; the old top-level `"progress"` key is **removed**.
  - Step keys per action — start: `fetch`, `schema`, `label`; tweak: `schema`, `label`; accept: `save`, `sample`, `label`, `snapshot`.

- [ ] **Step 1: Update the fake fetch and write failing tests**

In `tests/test_webapp.py`, `make_session` must accept the new fetch kwarg and exercise it:

```python
def make_session(tmp_path: Path) -> LoopSession:
    def fake_fetch(url, limit, on_progress=None):
        convs = CONVS[:limit] if limit else CONVS
        if on_progress:
            for i in range(len(convs)):
                on_progress(i + 1, len(convs))
        return convs
    return LoopSession(
        fetch=fake_fetch,
        count=lambda url: len(CONVS) + 3,   # 3 "excluded" beyond the fetch cap
        generate=make_fake_generate(),
        ext_db_url="postgresql+psycopg2://unused",
        data_dir=tmp_path,
        repo_sha="testsha",
        runner=lambda job: job(),           # synchronous in tests
    )
```

Replace the whole `# --- progress reporting ---` section (keep `test_draft_labels_reports_progress`, drop `test_state_exposes_progress_after_mass_label`) with:

```python
def test_status_steps_after_start(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    st = session.state()["status"]
    assert [s["key"] for s in st["steps"]] == ["fetch", "schema", "label"]
    assert all(s["state"] == "done" for s in st["steps"])
    fetch = st["steps"][0]
    assert "4" in fetch["name"]                      # "Fetched 4 conversations"
    assert fetch["progress"] == {"done": 4, "total": 4}
    label = st["steps"][2]
    assert label["progress"] == {"done": 4, "total": 4}
    assert label["started_at"] is not None
    assert st["retry"] is None


def test_status_steps_after_accept_and_review_labels_reused(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    labeled_after_review = len(session.labeled)
    session.accept()
    st = session.state()["status"]
    assert [s["key"] for s in st["steps"]] == ["save", "sample", "label",
                                               "snapshot"]
    assert all(s["state"] == "done" for s in st["steps"])
    label = st["steps"][2]
    # corpus total, with the review-sample labels counted as already done
    assert label["progress"]["done"] == label["progress"]["total"]
    assert label["progress"]["total"] >= labeled_after_review
    # every corpus message labeled exactly once (review labels reused, not redone)
    keys = [(r.chatlog_id, r.message_index) for r in session.labeled]
    assert len(keys) == len(set(keys)) == label["progress"]["total"]
    assert session.state()["snapshot_path"] is not None


def test_recent_holds_last_three_newest_first(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    recent = session.state()["status"]["recent"]
    assert len(recent) == 3
    assert all(set(r) == {"text", "labels"} for r in recent)
    # newest-first: the last sample message labeled is first in the list
    assert recent[0]["text"] != recent[2]["text"]


def test_tweak_clears_labels_and_recent_for_new_schema(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.tweak("split it")
    st = session.state()
    assert st["phase"] == "review"
    assert [s["key"] for s in st["status"]["steps"]] == ["schema", "label"]
    # all 4 sample messages relabeled under the new schema (not skipped)
    assert len(session.labeled) == 4
    assert all("label-v2" in r.labels for r in session.labeled)


def test_note_retry_surfaces_in_state(tmp_path):
    session = make_session(tmp_path)
    session.note_retry({"attempt": 2, "max": 4, "wait_s": 4.0})
    assert session.state()["status"]["retry"] == {
        "attempt": 2, "max": 4, "wait_s": 4.0}
    session.note_retry(None)
    assert session.state()["status"]["retry"] is None
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python -m pytest tests/test_webapp.py -q`
Expected: new tests FAIL (`KeyError: 'status'`, `no attribute 'note_retry'`); pre-existing tests still pass.

- [ ] **Step 3: Implement in `src/labeling/webapp.py`**

Add `import time` at the top. In `_reset`, replace `self.progress: dict | None = None` with:

```python
        self.steps: list[dict] = []
        self.retry_info: dict | None = None
        self.recent: list[dict] = []
        self._retry_job: Callable[[], None] | None = None
        self._retry_phase: str = "idle"
```

Delete `_set_progress`. Add the step/status helpers after `_reset`:

```python
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
        self._run(job)

    def _label_incremental(self, messages: list[SampledMessage],
                           key: str) -> None:
        """Label `messages`, skipping any already in self.labeled (same
        schema), appending each result as it completes so a mid-run failure
        keeps finished work. Progress counts are over the FULL message list."""
        done_keys = {(r.chatlog_id, r.message_index) for r in self.labeled}
        todo = [m for m in messages
                if (m.chatlog_id, m.message_index) not in done_keys]
        offset = len(messages) - len(todo)
        progress = self._step_progress(key)
        progress(offset, len(messages))

        def on_result(m: SampledMessage, r: MessageLabels) -> None:
            with self._lock:
                self.labeled.append(r)
            self._note_recent(m, r)

        draft_labels(todo, self.schema, self.generate,
                     on_progress=lambda done, total:
                         progress(offset + done, len(messages)),
                     on_result=on_result)
```

Rewrite the three actions. Each job skips completed work so Task 6's retry can re-run it idempotently:

```python
    def start(self, intent: str, max_conversations: int = 200,
              sample_size: int = 25, seed: int = 0) -> None:
        with self._lock:
            self._require("idle")
            self._reset()
            self.seed = seed
            self.phase = "fetching"
        self._init_steps(("fetch", "Fetching conversations"),
                         ("schema", "Drafting schema"),
                         ("label", "Labeling review sample"))

        def job() -> None:
            self._begin_step("fetch")
            if not self.conversations:
                convs = self.fetch(self.ext_db_url, max_conversations,
                                   on_progress=self._step_progress("fetch"))
                total = self.count(self.ext_db_url)
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
            with self._lock:
                self.snapshot_path = path
                self.phase = "done"
        self._launch(job, "mass_labeling")
```

In `state()`, replace `"progress": self.progress,` with:

```python
                "status": {
                    "steps": [dict(s) for s in self.steps],
                    "retry": self.retry_info,
                    "recent": [dict(r) for r in self.recent],
                },
```

In `main()`, wire the retry banner (the lambda reads `session` late-bound, after it exists):

```python
    session: LoopSession | None = None
    generate = make_generate(
        settings.gemini_api_key,
        on_retry=lambda info: session.note_retry(info) if session else None)
    session = LoopSession(generate=generate,
                          ext_db_url=settings.ext_db_url,
                          data_dir=settings.data_dir,
                          repo_sha=_repo_sha(settings.repo_root))
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS. (`test_accept_emits_snapshot_and_saves_schema` and the API tests must still pass unchanged — if `test_api_happy_path` breaks, the `state()` payload shape regressed.)

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: structured step status, retry banner state, recent-labels feed, incremental labeling"
```

---

### Task 6: resumable errors — retry step + back to review

**Files:**
- Modify: `src/labeling/webapp.py` (`_run`, new `retry_step`/`back_to_review`, `state`, `create_app`)
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `self._retry_job` / `self._retry_phase` from Task 5's `_launch`.
- Produces:
  - `session.retry_step()` — valid only in `error`; clears `error`, restores `self._retry_phase`, re-runs the stored job (jobs skip completed work).
  - `session.back_to_review()` — valid only in `error` and only when `self.schema` and `self.sample` exist; returns to `review`.
  - `state()["recovery"]` — `None` unless `phase == "error"`, else `{"can_retry": bool, "can_review": bool, "labeled_count": int, "conversations": int}`.
  - Endpoints: `POST /api/retry`, `POST /api/back-to-review` (409 via `PhaseError` when invalid).

- [ ] **Step 1: Write failing tests** (append to `tests/test_webapp.py`)

```python
def make_flaky_generate(fail_at: int):
    """Delegates to make_fake_generate() but raises on the fail_at-th
    labeling call (schema calls never fail)."""
    inner = make_fake_generate()
    label_calls = {"n": 0}

    def gen(prompt, response_model):
        from src.labeling.draft import LabelVerdicts
        if response_model is LabelVerdicts:
            label_calls["n"] += 1
            if label_calls["n"] == fail_at:
                raise RuntimeError("boom")
        return inner(prompt, response_model)
    return gen


def test_error_keeps_partial_labels_and_retry_resumes(tmp_path):
    session = make_session(tmp_path)
    session.generate = make_flaky_generate(fail_at=3)  # 3rd sample msg dies
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    s = session.state()
    assert s["phase"] == "error"
    assert "boom" in s["error"]
    assert s["recovery"]["can_retry"] is True
    assert s["recovery"]["labeled_count"] == 2        # first two survived
    session.retry_step()                              # flaky gen now passes
    s = session.state()
    assert s["phase"] == "review"
    assert s["error"] is None
    # exactly 4 labels, none duplicated
    keys = [(r.chatlog_id, r.message_index) for r in session.labeled]
    assert len(keys) == len(set(keys)) == 4


def test_error_during_mass_label_retry_completes_snapshot(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    total_sample_labels = len(session.labeled)
    session.generate = make_flaky_generate(fail_at=1)  # 1st corpus call dies
    session.accept()
    assert session.state()["phase"] == "error"
    assert len(session.labeled) == total_sample_labels  # review work kept
    session.retry_step()
    s = session.state()
    assert s["phase"] == "done"
    assert s["snapshot_path"] is not None


def test_back_to_review_from_error(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.generate = make_flaky_generate(fail_at=1)
    session.accept()
    assert session.state()["phase"] == "error"
    assert session.state()["recovery"]["can_review"] is True
    session.back_to_review()
    s = session.state()
    assert s["phase"] == "review"
    assert s["error"] is None


def test_recovery_invalid_outside_error(tmp_path):
    session = make_session(tmp_path)
    with pytest.raises(PhaseError):
        session.retry_step()
    with pytest.raises(PhaseError):
        session.back_to_review()
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.retry_step()          # review is not error


def test_api_retry_and_back_to_review_endpoints(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    assert client.post("/api/retry").status_code == 409
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    session.generate = make_flaky_generate(fail_at=1)
    client.post("/api/accept")
    assert client.get("/api/state").json()["phase"] == "error"
    assert client.post("/api/back-to-review").status_code == 200
    assert client.get("/api/state").json()["phase"] == "review"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_webapp.py -q`
Expected: FAIL — `no attribute 'retry_step'`, `KeyError: 'recovery'`, 404 on `/api/retry`

- [ ] **Step 3: Implement**

Add to `LoopSession` (after `quit`):

```python
    def retry_step(self) -> None:
        with self._lock:
            self._require("error")
            if self._retry_job is None:
                raise PhaseError(self.phase)
            self.error = None
            self.phase = self._retry_phase
            job = self._retry_job
        self._run(job)

    def back_to_review(self) -> None:
        with self._lock:
            self._require("error")
            if self.schema is None or not self.sample:
                raise PhaseError(self.phase)
            self.error = None
            self.phase = "review"
```

In `state()`, add alongside `"status"`:

```python
                "recovery": ({
                    "can_retry": self._retry_job is not None,
                    "can_review": self.schema is not None and bool(self.sample),
                    "labeled_count": len(self.labeled),
                    "conversations": len(self.conversations),
                } if self.phase == "error" else None),
```

In `create_app`, add:

```python
    @app.post("/api/retry")
    def retry() -> dict:
        session.retry_step()
        return {"ok": True}

    @app.post("/api/back-to-review")
    def back_to_review() -> dict:
        session.back_to_review()
        return {"ok": True}
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: error screen is resumable — retry the failed step or return to review"
```

---

### Task 7: frontend — gate rail, action panel, ticker, ETA, recovery screen

**Files:**
- Modify: `src/labeling/static/index.html`

No JS test infra exists; verification is the existing `test_index_served` plus the manual checklist in Verification below. The reference design (colors, spacing, proportions) is the approved mockup at `.superpowers/brainstorm/51778-1785988010/content/full-page.html` — match it, but translate to this file's existing conventions.

**Interfaces:**
- Consumes: `state.status.steps` / `.retry` / `.recent`, `state.recovery`, endpoints `/api/retry`, `/api/back-to-review` (Tasks 5–6).

- [ ] **Step 1: Replace the CSS additions**

Keep all existing rules. Change the body rule and add rail/panel rules:

```css
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 52rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
  body.wide { max-width: 60rem; }
  .layout { display: flex; gap: 2.5rem; }
  @media (max-width: 44rem) { .layout { flex-direction: column; gap: 1.5rem; } }
  .rail { flex: 0 0 16rem; position: relative; padding-left: 1.5rem; }
  .rail-track, .rail-fill { position: absolute; left: .48rem; top: .6rem;
    width: 4px; border-radius: 2px; }
  .rail-track { bottom: .6rem; background: rgba(128,128,128,.2); }
  .rail-fill { background: linear-gradient(#3a9d5d, #4a7fd4); }
  .gate { position: relative; margin-bottom: 2rem; }
  .gate:last-child { margin-bottom: 0; }
  .gate .dot { position: absolute; left: -1.5rem; top: .15rem; width: 1rem;
    height: 1rem; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: .65rem; color: #fff; }
  .gate.done .dot { background: #3a9d5d; }
  .gate.active .dot { width: 1.2rem; height: 1.2rem; left: -1.6rem; top: .05rem;
    background: #4a7fd4; animation: pulse 1.6s ease-in-out infinite; }
  @keyframes pulse { 50% { box-shadow: 0 0 14px rgba(74,127,212,.9); } }
  .gate.pending .dot { border: 2px solid rgba(128,128,128,.4); }
  .gate .name { font-size: .95rem; font-weight: 600; }
  .gate.active .name { color: #4a7fd4; font-weight: 700; }
  .gate.pending .name { opacity: .45; font-weight: 400; }
  .gate .detail { font-size: .78rem; opacity: .6; }
  .action { flex: 1; min-width: 0; }
  .action-head { display: flex; justify-content: space-between;
    align-items: baseline; flex-wrap: wrap; gap: .25rem; margin-bottom: .5rem; }
  .action-head .stats { font-size: .82rem; opacity: .7; }
  .bar { background: rgba(128,128,128,.2); border-radius: 4px; height: 8px;
    overflow: hidden; margin-bottom: .7rem; }
  .bar > div { background: #4a7fd4; height: 100%; transition: width .8s; }
  .retry-banner { padding: .4rem .65rem; border-left: 3px solid #b8860b;
    background: rgba(184,134,11,.08); font-size: .82rem;
    margin-bottom: 1.1rem; border-radius: 0 4px 4px 0; }
  .feed-item { font-size: .88rem; padding: .45rem 0;
    border-bottom: 1px solid rgba(128,128,128,.18); }
  .feed-item:last-child { border-bottom: 0; }
  .feed-item .msg-text { font-style: italic; opacity: .85; }
  .feed-item.old { opacity: .65; }
  .feed-item.oldest { opacity: .4; }
```

- [ ] **Step 2: Replace the working and error screen markup**

```html
<section id="screen-working" class="hidden">
  <p class="provenance" id="working-provenance"></p>
  <div class="layout">
    <div class="rail">
      <div class="rail-track"></div>
      <div class="rail-fill" id="rail-fill"></div>
      <div id="gates"></div>
    </div>
    <div class="action">
      <div class="action-head">
        <span id="action-step"></span>
        <span class="stats" id="action-stats"></span>
      </div>
      <div class="bar"><div id="action-bar"></div></div>
      <div class="retry-banner hidden" id="retry-banner"></div>
      <div class="stratum">Recently labeled</div>
      <div id="feed"></div>
    </div>
  </div>
</section>
```

```html
<section id="screen-error" class="hidden">
  <h2 class="error">Error</h2>
  <p class="error" id="error-text"></p>
  <p class="provenance" id="error-survived"></p>
  <button id="btn-retry" class="hidden">Retry from where it stopped</button>
  <button id="btn-back-review" class="hidden">Back to review</button>
  <button id="btn-reset-error">Start over</button>
</section>
```

- [ ] **Step 3: Replace the working/error rendering JS**

Replace the `else { ... }` working-branch of `render(state)` and the error branch. Full replacement for `render` plus new helpers (everything below `renderReview`, above `refresh`):

```js
const PHASE_TITLES = {
  fetching: "Fetching from the raw-log DB",
  drafting: "Drafting and labeling the review sample",
  mass_labeling: "Labeling the full corpus",
};

// rolling (time, done) samples for rate/ETA; reset when the active step changes
let etaSamples = [];
let etaKey = null;

function renderStats(step) {
  const p = step.progress;
  if (!p || !p.total) return "";
  const now = Date.now() / 1000;
  const key = step.key + ":" + (step.started_at || 0);
  if (key !== etaKey) { etaKey = key; etaSamples = []; }
  etaSamples.push({ t: now, done: p.done });
  etaSamples = etaSamples.filter((s) => now - s.t < 60);
  let parts = [`${p.done} / ${p.total} (${Math.floor(p.done / p.total * 100)}%)`];
  const first = etaSamples[0];
  if (etaSamples.length > 1 && p.done > first.done) {
    const rate = (p.done - first.done) / (now - first.t);
    const left = (p.total - p.done) / rate;
    parts.push(`~${rate.toFixed(1)} msg/s`);
    parts.push(left > 90 ? `about ${Math.round(left / 60)} min left`
                         : `about ${Math.round(left)}s left`);
  }
  if (step.started_at) {
    const el = Math.max(0, Math.round(now - step.started_at));
    parts.push(`elapsed ${Math.floor(el / 60)}:${String(el % 60).padStart(2, "0")}`);
  }
  return parts.join(" · ");
}

function renderWorking(state) {
  const steps = (state.status && state.status.steps) || [];
  $("working-provenance").textContent = PHASE_TITLES[state.phase] || state.phase;

  const gates = $("gates");
  gates.replaceChildren();
  let doneCount = 0, activeFrac = 0, active = null;
  for (const s of steps) {
    if (s.state === "done") doneCount++;
    if (s.state === "active") {
      active = s;
      if (s.progress && s.progress.total)
        activeFrac = s.progress.done / s.progress.total;
    }
    const gate = document.createElement("div");
    gate.className = "gate " + s.state;
    const dot = document.createElement("div");
    dot.className = "dot";
    dot.textContent = s.state === "done" ? "✓" : s.state === "active" ? "◌" : "";
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = s.name;
    const detail = document.createElement("div");
    detail.className = "detail";
    detail.textContent = s.state === "active" && s.progress
      ? `${s.progress.done} / ${s.progress.total}` : s.detail;
    gate.append(dot, name, detail);
    gates.append(gate);
  }
  const frac = steps.length ? (doneCount + activeFrac) / steps.length : 0;
  $("rail-fill").style.height = (frac * 100).toFixed(1) + "%";

  $("action-step").textContent = active ? active.name : "Working…";
  $("action-stats").textContent = active ? renderStats(active) : "";
  $("action-bar").style.width = active && active.progress && active.progress.total
    ? (active.progress.done / active.progress.total * 100).toFixed(1) + "%" : "0%";

  const retry = state.status && state.status.retry;
  $("retry-banner").classList.toggle("hidden", !retry);
  if (retry)
    $("retry-banner").textContent = `⚠ Gemini call failed — retry ${retry.attempt} ` +
      `of ${retry.max}, waiting ${retry.wait_s}s`;

  const feed = $("feed");
  feed.replaceChildren();
  // student text: always textContent, never innerHTML
  (state.status && state.status.recent || []).forEach((r, i) => {
    const item = document.createElement("div");
    item.className = "feed-item" + (i === 1 ? " old" : i >= 2 ? " oldest" : "");
    const text = document.createElement("span");
    text.className = "msg-text";
    text.textContent = `“${r.text}”`;
    item.append(text);
    for (const name of r.labels) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = name;
      item.append(chip);
    }
    feed.append(item);
  });
}

function renderError(state) {
  $("error-text").textContent = state.error || "unknown error";
  const rec = state.recovery;
  $("error-survived").textContent = rec
    ? `Still in memory: ${rec.conversations} conversations, ` +
      `${rec.labeled_count} labeled messages. Retry continues from there; ` +
      `Start over discards everything.`
    : "";
  $("btn-retry").classList.toggle("hidden", !(rec && rec.can_retry));
  $("btn-back-review").classList.toggle("hidden", !(rec && rec.can_review));
}

function render(state) {
  const phase = state.phase;
  const working = ["fetching", "drafting", "mass_labeling"].includes(phase);
  document.body.classList.toggle("wide", working);
  if (phase === "idle") show("idle");
  else if (phase === "review") { renderReview(state); show("review"); }
  else if (phase === "done") {
    $("snapshot-path").textContent = state.snapshot_path || "";
    show("done");
  } else if (phase === "error") { renderError(state); show("error"); }
  else { renderWorking(state); show("working"); }
}
```

And register the new buttons next to the existing listeners:

```js
$("btn-retry").addEventListener("click", () => post("/api/retry"));
$("btn-back-review").addEventListener("click", () => post("/api/back-to-review"));
```

- [ ] **Step 4: Run the suite (serving + payload contract)**

Run: `python -m pytest tests/ -q`
Expected: PASS (`test_index_served` checks the page still serves)

- [ ] **Step 5: Manual smoke test against fakes**

Quick offline check that the page renders each screen: temporarily run the app with the test fakes:

```bash
python -c "
from pathlib import Path
import uvicorn
from src.labeling.webapp import LoopSession, create_app
from tests.test_webapp import make_session
import tempfile, threading, time

session = make_session(Path(tempfile.mkdtemp()))
# slow the fake generate down so working screens are observable
inner = session.generate
def slow(prompt, model):
    time.sleep(1.0)
    return inner(prompt, model)
session.generate = slow
session.runner = lambda job: threading.Thread(target=job, daemon=True).start()
uvicorn.run(create_app(session), host='127.0.0.1', port=8321)
"
```

Open http://127.0.0.1:8321, run a full start → review → tweak → accept → done loop. Check: gate rail fills and lights, ticker updates, action panel counts, error screen (kill the loop mid-run by editing the snippet's `slow` to raise once, or just verify via the automated tests), narrow-window stacking.

- [ ] **Step 6: Commit**

```bash
git add src/labeling/static/index.html
git commit -m "feat: gate-rail working screen with live ticker, ETA, retry banner, recoverable error screen"
```

---

### Task 8: end-to-end verification + ledger

**Files:**
- Modify: none expected (fixes only if verification finds problems)

- [ ] **Step 1: Full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS, no warnings introduced.

- [ ] **Step 2: Real end-to-end run (needs `bin/tunnel` + `GEMINI_API_KEY`)**

Run `label-loop-web`, do one small run (max_conversations ≈ 20, sample 10):
- fetching shows "Fetching conversation i / N" counting up;
- drafting shows the schema gate before the label counter appears;
- ticker shows real labeled messages (verify NOTHING is written under `data/` until the snapshot step);
- accept a schema, watch the four mass-labeling gates, confirm the snapshot gate is visibly active while writing;
- confirm `git status` shows no student data (rule 4) before any commit.

- [ ] **Step 3: Verification checklist against the design doc**

Walk `docs/2026-08-05-labeling-ui-progress-design.md` section by section (structured status, retry, ETA, all four safety items, layout) and confirm each is implemented or explicitly deferred. Fix gaps before declaring done.
