# Profile-Setup Webapp Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The label-loop webapp gains the explore → skim-and-accept course-profile flow (spec: `docs/superpowers/specs/2026-08-08-profile-setup-webapp-design.md`) and runs labeling with the accepted CourseProfile v2, like the CLI already does.

**Architecture:** `LoopSession` (src/labeling/webapp.py) gains two idle-adjacent phases (`exploring`, `profile_review`), an `explore_course` job reusing `src/labeling/explore.explore`, and a synchronous no-LLM `accept_profile` that applies delete/promote surgery via `model_copy`, lints, and writes `profiles/<slug>.json`. Labeling runs mirror the CLI's v2 path: review loop on the instructor schema with `profile2` passed to `draft_labels` (concepts facet), composition via `compose_schema` at accept before the mass pass.

**Tech Stack:** Python 3.12, FastAPI + vanilla-JS static page (existing pattern), pydantic, pytest.

## Global Constraints

- Server binds 127.0.0.1 only (CLAUDE.md rule 4); student text and uploaded materials never leave the machine.
- Materials text lives in session memory for the exploration call only — never written to disk, never echoed in any API response.
- Every profile write goes through `lint_profile` (rule 4: no 8-word verbatim run of student text).
- `accept_profile` makes no LLM calls — deterministic `model_copy` surgery only.
- Run tests with `uv run python -m pytest` (bare `uv run pytest` is broken in worktrees).
- Branch: `profile-setup-webapp`. Do NOT touch ChatSight (`~/github/chatsight`) or the `admission-threshold` worktree.
- The Bash sandbox rejects command strings containing the bare word "eval" — write commit messages and paths accordingly.

---

### Task 1: Merge the distinctness-elicitation branch

The layer-aware `draft_schema(intent, profile, generate, profile2=None)` (with its ALREADY-COVERED block) lives on the pushed `distinctness-elicitation` branch. Without it, an instructor schema drafted alongside an accepted profile can duplicate the profile's affect/intent labels and `compose_schema` raises a name-collision ValueError at accept time.

**Files:** none created — a git merge.

**Interfaces:**
- Produces: `src.labeling.elicit.draft_schema(intent_text, profile, generate, profile2=None)`; `src.labeling.distinctness` and `src.labeling.ablation` modules; tightened `profiles/dsc10.json` (profile_id `a5241abd5c25`).

- [ ] **Step 1: Merge and verify**

```bash
git merge origin/distinctness-elicitation -m "merge: layer-aware elicitation + distinctness instruments"
uv run python -m pytest -q
```

Expected: merge is clean or trivially resolvable (both branches cut from the same main); full suite passes. Confirm the signature:

```bash
grep -n "def draft_schema" src/labeling/elicit.py
```

Expected: `def draft_schema(intent_text: str, profile: CourseProfile, generate: Generate, profile2=None) -> LabelSchema:` (arg name may differ slightly — read the actual signature and use it in Task 4).

---

### Task 2: Session explore flow (`exploring` / `profile_review` phases)

**Files:**
- Modify: `src/labeling/webapp.py` (LoopSession: `__init__`, `_reset`, new `explore_course`, `state`)
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `src.labeling.explore.explore(conversations, materials_texts, generate, *, sample_meta, repo_sha, explored_on) -> CourseProfileV2`; `src.labeling.explore.write_draft(v2, conversations, path) -> Path`.
- Produces: `LoopSession.explore_course(slug: str, materials: list[dict]) -> None` (materials items are `{"name": str, "text": str}`); session fields `profile2: CourseProfileV2 | None`, `profile2_draft: CourseProfileV2 | None`, `course_slug: str`, `profiles_dir: Path`, `_explore_convs: list[Conversation]`; `state()["profile"]` block. Constant `EXPLORE_SAMPLE = 150`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp.py` (the file already imports `LoopSession`, `PhaseError`, `make_fake_generate`, `CONVS`). `make_session` needs `profiles_dir=tmp_path / "profiles"` added to the `LoopSession(...)` call, and the fake generate must learn `ExplorationDraft`:

```python
# In tests/test_cli.py, extend make_fake_generate's fake_generate with:
        from src.labeling.explore import ExplorationDraft
        if response_model is ExplorationDraft:
            from src.labeling.course import DSC10_PROFILE
            from src.labeling.profile2 import ConceptDef
            from src.labeling.schema import LabelDef
            base = DSC10_PROFILE.model_dump()
            return ExplorationDraft(
                **{k: base[k] for k in ("course_name", "domain_description",
                                        "tooling", "paste_conventions",
                                        "reference_conventions",
                                        "message_shape_notes")},
                concepts=[ConceptDef(name="groupby", description="d"),
                          ConceptDef(name="loops", description="d")],
                affect_labels=[LabelDef(name="frustrated", kind="behavioral",
                                        description="d", positive_criteria="p",
                                        negative_criteria="n")],
                intent_labels=[LabelDef(name="wants-hint", kind="behavioral",
                                        description="d", positive_criteria="p",
                                        negative_criteria="n")])
```

```python
# tests/test_webapp.py
def test_explore_reaches_profile_review_with_draft(tmp_path):
    session = make_session(tmp_path)
    session.explore_course("dsc10", [{"name": "syllabus.md", "text": "babypandas"}])
    s = session.state()
    assert s["phase"] == "profile_review"
    draft = s["profile"]["draft"]
    assert [c["name"] for c in draft["concepts"]] == ["groupby", "loops"]
    assert draft["affect"][0]["name"] == "frustrated"
    assert draft["intent"][0]["name"] == "wants-hint"
    assert (tmp_path / "profiles" / "dsc10-draft.json").exists()
    # materials text never appears in any state payload (rule 4)
    import json as j
    assert "babypandas" not in j.dumps(s)


def test_explore_phase_guards(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    with pytest.raises(PhaseError):
        session.explore_course("dsc10", [])   # review: no explore
    session.quit()
    session.explore_course("dsc10", [])
    with pytest.raises(PhaseError):
        session.start("intent")               # profile_review: no labeling run
    with pytest.raises(PhaseError):
        session.explore_course("dsc10", [])   # no double-explore
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_webapp.py -q`
Expected: FAIL — `TypeError: LoopSession.__init__() got an unexpected keyword argument 'profiles_dir'` (and/or `AttributeError: explore_course`).

- [ ] **Step 3: Implement**

In `src/labeling/webapp.py`:

```python
# imports
from datetime import date
from src.labeling.explore import EXCERPTS_PER_CONV  # noqa: F401 (unused ok)
from src.labeling.explore import explore, write_draft
from src.labeling.profile2 import CourseProfileV2

EXPLORE_SAMPLE = 150   # conversations read by the exploration pass (explore CLI default)
```

`__init__` gains `profiles_dir: Path` and `course_slug: str = "dsc10"` keyword args (store both). `_reset` must NOT clear `profile2`/`course_slug` (they survive quit); it clears only the draft state:

```python
        # in _reset():
        self.profile2_draft: CourseProfileV2 | None = None
        self._explore_convs: list[Conversation] = []
```

Add `self.profile2: CourseProfileV2 | None = None` in `__init__` (before `_reset()` so reset never wipes it).

```python
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
```

In `state()`, add a `profile` key to the returned dict:

```python
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
```

and include `"profile": profile` in the returned dict. In `start()`, the existing `self._require("idle")` already blocks labeling from `exploring`/`profile_review` since those are distinct phases — verify `quit()`'s `_require` gains `"profile_review"` in Task 3, not here.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_webapp.py tests/test_cli.py -q`
Expected: PASS (all — the `make_session` change requires updating every existing call in `tests/test_webapp.py` only via the shared helper).

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py tests/test_cli.py
git commit -m "feat: exploration phase in the label-loop session"
```

---

### Task 3: Accept surgery, persistence, re-explore

**Files:**
- Modify: `src/labeling/webapp.py`
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `lint_profile(v2, conversations) -> list[str]`, `save_profile(v2, path)`, `ConceptDef` (validator: promoted needs both criteria), session fields from Task 2.
- Produces: `LoopSession.accept_profile(deleted: dict[str, list[str]], promoted: list[str]) -> None` (raises `ValueError` with a readable reason on lint/collision; phase stays `profile_review`); `LoopSession.discard_profile() -> None` (from `profile_review` or idle-with-accepted-profile; returns session to the no-profile idle state — the frontend's "Re-explore" is discard + a fresh `explore_course`).

- [ ] **Step 1: Write the failing tests**

```python
def _explored(tmp_path):
    session = make_session(tmp_path)
    session.explore_course("dsc10", [])
    return session


def test_accept_profile_applies_surgery_and_persists(tmp_path):
    session = _explored(tmp_path)
    session.accept_profile(deleted={"concepts": ["loops"], "affect": [],
                                    "intent": []},
                           promoted=["groupby"])
    s = session.state()
    assert s["phase"] == "idle"
    acc = s["profile"]["accepted"]
    assert acc["concepts"] == 1 and acc["promoted"] == 1
    from src.labeling.profile2 import load_profile
    v2 = load_profile(tmp_path / "profiles" / "dsc10.json")
    assert v2.accepted
    assert [c.name for c in v2.concepts] == ["groupby"]
    assert v2.concepts[0].promoted
    assert v2.concepts[0].positive_criteria      # template criteria filled
    assert v2.concepts[0].negative_criteria


def test_accept_profile_is_deterministic_no_llm(tmp_path):
    session = _explored(tmp_path)
    calls_before = session.generate.schema_calls
    session.accept_profile(deleted={}, promoted=[])
    assert session.generate.schema_calls == calls_before


def test_accept_profile_rejects_internal_collision(tmp_path):
    session = _explored(tmp_path)
    # sabotage: duplicate name across layers
    dup = session.profile2_draft.affect_labels[0].model_copy(
        update={"name": "wants-hint"})
    session.profile2_draft = session.profile2_draft.model_copy(
        update={"affect_labels": [dup]})
    with pytest.raises(ValueError, match="wants-hint"):
        session.accept_profile(deleted={}, promoted=[])
    assert session.state()["phase"] == "profile_review"


def test_discard_returns_to_setup_state(tmp_path):
    session = _explored(tmp_path)
    session.discard_profile()
    s = session.state()
    assert s["phase"] == "idle"
    assert s["profile"]["draft"] is None
    session.explore_course("dsc10", [])
    session.accept_profile(deleted={}, promoted=[])
    session.discard_profile()                    # from idle-with-profile
    assert session.state()["profile"]["accepted"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_webapp.py -q`
Expected: FAIL with `AttributeError: 'LoopSession' object has no attribute 'accept_profile'`.

- [ ] **Step 3: Implement**

```python
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
```

Imports: add `lint_profile, save_profile` to the existing `from src.labeling.profile2 import ...` line. Also extend `quit()`'s `_require` with `"profile_review"` so an erroring exploration can be abandoned (`self._require("review", "error", "done", "profile_review")`).

Note: `accept_profile` reads `generate.schema_calls` in the no-LLM test — that attribute exists on `make_fake_generate`'s fake; no production change needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_webapp.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: skim-and-accept profile surgery in the session"
```

---

### Task 4: Profile2-grounded labeling runs + startup loading

**Files:**
- Modify: `src/labeling/webapp.py` (`start`, `tweak`, `accept`, `main`)
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `draft_schema(intent, profile, generate, profile2=None)` (Task 1 — use the exact merged signature), `compose_schema(v2, instructor_schema) -> LabelSchema`, `draft_labels(..., profile2=...)`, `classifier_hash(schema, model, profile, profile2=...)`, `emit_snapshot(..., profile2=...)`, `load_accepted_profile(path)` from `src.labeling.cli`.
- Produces: labeling runs grounded in `self.profile2` end-to-end; `main()` gains `--course <slug>` (default `dsc10`) and loads `profiles/<slug>.json` when present and accepted.

- [ ] **Step 1: Write the failing tests**

```python
def _accepted_session(tmp_path):
    session = _explored(tmp_path)
    session.accept_profile(deleted={}, promoted=["groupby"])
    return session


def test_run_with_profile_composes_at_accept(tmp_path):
    session = _accepted_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    review_names = [l["name"] for l in session.state()["schema"]["labels"]]
    assert review_names == ["label-v1"]          # review: instructor-only
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    names = [l["name"] for l in s["schema"]["labels"]]
    assert "groupby" in names and "frustrated" in names \
        and "wants-hint" in names                 # composed for the mass pass
    import json as j
    manifest = j.loads(
        (Path(s["snapshot_path"]) / "manifest.json").read_text())
    assert manifest["classifier"]["profile2_id"] \
        == session.profile2.profile_id
    assert s["summary"]["classifier"]["profile_id"] \
        == session.profile.profile_id


def test_run_without_profile_unchanged(tmp_path):
    session = make_session(tmp_path)
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    session.accept()
    import json as j
    manifest = j.loads((Path(session.state()["snapshot_path"])
                        / "manifest.json").read_text())
    assert manifest["classifier"]["profile2_id"] is None
```

Check the manifest's actual key path first (`grep -n profile2_id src/labeling/snapshot.py`) — if `profile2_id` sits at the top level rather than under `"classifier"`, assert accordingly.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_webapp.py -q`
Expected: `test_run_with_profile_composes_at_accept` FAILS — composed labels absent.

- [ ] **Step 3: Implement**

Mirror the CLI ordering (cli.py `main`): review loop on the instructor schema with `profile2` in `draft_labels`; compose at accept.

- In `start()`'s job: `draft_schema(intent, self.profile, self.generate, profile2=self.profile2)` (exact kwarg from Task 1).
- In `_label_incremental`: pass `profile2=self.profile2` to `draft_labels`.
- In `accept()`'s job, after `save_schema(self.schema, self.data_dir)`:

```python
            if self.profile2 is not None:
                composed = compose_schema(self.profile2, self.schema)
                save_schema(composed, self.data_dir)
                with self._lock:
                    self.schema = composed
```

(The existing `_label_incremental` schema-vintage guard then clears the review-sample labels — correct: the mass pass must be scored under the composed schema, rule 2.) Guard the retry path: wrap in `if not composed_flag["done"]` like `tweak`'s `revised` guard so a retry never composes twice.

- `emit_snapshot(...)` and the `summary["classifier"]` block gain `profile2=self.profile2` / `"profile2_id": self.profile2.profile_id if self.profile2 else None`.
- `main()`: add `argparse` with `--course` (default `"dsc10"`); `profiles_dir = settings.repo_root / "profiles"`; if `(profiles_dir / f"{slug}.json").exists()`, load via `load_accepted_profile` and set `session.profile2` after constructing the session; pass `profiles_dir=profiles_dir, course_slug=args.course` to `LoopSession`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest -q`
Expected: full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: profile2-grounded labeling runs in the webapp"
```

---

### Task 5: API endpoints

**Files:**
- Modify: `src/labeling/webapp.py` (FastAPI layer)
- Test: `tests/test_webapp.py` (API section)

**Interfaces:**
- Consumes: Task 2–4 session methods.
- Produces: `POST /api/explore` body `{"slug": str, "materials": [{"name": str, "text": str}]}` (JSON, not multipart — files are read client-side with FileReader; avoids the python-multipart dependency); `POST /api/profile/accept` body `{"deleted": {"concepts": [...], "affect": [...], "intent": [...]}, "promoted": [...]}` → 400 with `detail` on ValueError; `POST /api/profile/reexplore` (calls `discard_profile`).

- [ ] **Step 1: Write the failing tests**

```python
def test_api_profile_flow(tmp_path):
    client = TestClient(create_app(make_session(tmp_path)))
    r = client.post("/api/explore", json={
        "slug": "dsc10",
        "materials": [{"name": "syllabus.md", "text": "babypandas"}]})
    assert r.status_code == 200
    s = client.get("/api/state").json()
    assert s["phase"] == "profile_review"
    assert "babypandas" not in r.text and "babypandas" not in str(s)
    r = client.post("/api/profile/accept", json={
        "deleted": {"concepts": ["loops"], "affect": [], "intent": []},
        "promoted": []})
    assert r.status_code == 200
    assert client.get("/api/state").json()["profile"]["accepted"]["concepts"] == 1
    assert client.post("/api/profile/reexplore").json() == {"ok": True}
    assert client.get("/api/state").json()["profile"]["accepted"] is None


def test_api_accept_error_returns_400(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    client.post("/api/explore", json={"slug": "dsc10", "materials": []})
    dup = session.profile2_draft.affect_labels[0].model_copy(
        update={"name": "wants-hint"})
    session.profile2_draft = session.profile2_draft.model_copy(
        update={"affect_labels": [dup]})
    r = client.post("/api/profile/accept",
                    json={"deleted": {}, "promoted": []})
    assert r.status_code == 400 and "wants-hint" in r.json()["detail"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_webapp.py -q`
Expected: FAIL with 404 on `/api/explore`.

- [ ] **Step 3: Implement**

```python
class MaterialFile(BaseModel):
    name: str
    text: str


class ExploreRequest(BaseModel):
    slug: str = "dsc10"
    materials: list[MaterialFile] = []


class ProfileAcceptRequest(BaseModel):
    deleted: dict[str, list[str]] = {}
    promoted: list[str] = []
```

In `create_app`:

```python
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
```

Also update the spec (`docs/superpowers/specs/2026-08-08-profile-setup-webapp-design.md`): change the `/api/explore` line from "multipart form" to "JSON body with client-side-read file text (avoids the python-multipart dependency)".

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_webapp.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py docs/superpowers/specs/2026-08-08-profile-setup-webapp-design.md
git commit -m "feat: profile setup API endpoints"
```

---

### Task 6: Frontend — idle panel and review screen

**Files:**
- Modify: `src/labeling/static/index.html` (single-file vanilla JS page, ~974 lines — read it first and follow its existing render-from-`/api/state` pattern and CSS variables)

**Interfaces:**
- Consumes: `state.profile` block, `POST /api/explore`, `/api/profile/accept`, `/api/profile/reexplore`; phases `exploring` (render the existing steps/progress UI, which is phase-generic) and `profile_review`.
- Produces: three idle-panel states per the spec.

No unit tests (the page has none today); verified by Task 7's live pass. Still TDD-adjacent: implement in small commits, checking each state renders via a hand-run of the server with a stubbed state if convenient.

- [ ] **Step 1: Setup panel (idle, no accepted profile)**

Above the existing intent form, add a `#profile-panel` div. Render logic in the state poller:

- `state.profile.accepted == null && state.profile.draft == null && phase == "idle"` → show setup: slug text input (default `state.profile.slug`), `<input type="file" id="materials" multiple accept=".txt,.md">`, Explore button. On click, read files client-side and POST:

```javascript
async function startExplore() {
  const files = [...document.getElementById('materials').files];
  const materials = await Promise.all(files.map(async f => (
    {name: f.name, text: await f.text()})));
  await fetch('/api/explore', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({slug: slugInput.value, materials})});
}
```

Gray out the intent form while no accepted profile exists? No — labeling without a profile stays allowed (v1 path); show the setup panel as an optional card labeled "Ground this course (optional)".

- [ ] **Step 2: Review screen (phase == "profile_review")**

Render the three layers with the layer colors already used by the audit server (concept green `#dcfce7`-family, affect rose, intent blue — pick the page's existing palette variables if any). Per entry: name, description, criteria (collapsed under `<details>`), a Delete button (moves the entry into a local `deleted` set, row renders struck-through with an Undo), and for concepts a "Promote to label" checkbox (local `promoted` set; disabled+checked implies criteria will be templated — add the hint text "criteria auto-drafted; refine later in the tweak loop"). Accept button POSTs `/api/profile/accept` with the sets; on 400, show `detail` in the page's existing error style and keep the screen. Re-explore button POSTs `/api/profile/reexplore` then re-renders (back to setup).

- [ ] **Step 3: Accepted banner**

`state.profile.accepted != null` → collapse the panel to one line: `Course: <course_name> · profile <profile_id> · N concepts (M promoted) · A affect · I intent` plus a small Re-explore link (confirm()-free — it only discards in-session state).

- [ ] **Step 4: Sanity-run the server**

Run: `uv run python -m pytest -q` (nothing broken), then start the app and eyeball the three states with the real DB tunnel down (setup panel must render even when `/api/peek` fails — check the existing error handling).

- [ ] **Step 5: Commit**

```bash
git add src/labeling/static/index.html
git commit -m "feat: course-profile setup and review UI"
```

---

### Task 7: Live end-to-end pass

**Files:** none — verification.

- [ ] **Step 1:** Full suite: `uv run python -m pytest -q` → all green.
- [ ] **Step 2:** With `bin/tunnel` running and `GEMINI_API_KEY` set, start the webapp (`uv run python -m src.labeling.webapp`), then drive Chrome through: setup panel → Explore (attach a small .md) → review screen renders three colored layers → delete one entry, promote one concept → Accept → banner shows → run a small labeling pass (max_conversations 20, sample 6) → accept → snapshot manifest records `profile2_id`. Screenshot each screen.
- [ ] **Step 3:** `rm` any snapshot produced by throwaway test runs only if it was created by this test (check the manifest timestamp); otherwise leave and add a ledger row in `snapshots.md` if the snapshot is kept.
- [ ] **Step 4:** Final commit + push branch:

```bash
git push -u origin profile-setup-webapp
```

---

## Self-review notes

- Spec coverage: flow states (Tasks 2/3/6), accept semantics incl. deterministic surgery + lint + collision (Task 3), server/session changes incl. `--course` startup (Tasks 4/5), rule-4 handling (Tasks 2/5 assertions), testing list (Tasks 2–5, 7). Deviations from spec, both deliberate: JSON-not-multipart upload (Task 5 updates the spec) and re-explore = discard-then-explore (two clicks; materials can't be re-sent otherwise).
- Promotion criteria templating is an addition the spec didn't cover (ConceptDef validator requires criteria when promoted) — surfaced to Minchan in chat before planning.
- Type consistency: `explore_course(slug, materials: list[dict])`, `accept_profile(deleted, promoted)`, `discard_profile()` used identically across Tasks 2–5.
