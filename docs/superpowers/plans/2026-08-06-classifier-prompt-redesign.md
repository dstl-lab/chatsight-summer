# Classifier Prompt Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Option A of `docs/2026-08-06-classifier-prompt-redesign.md`: context-faithful CLASSIFY_PROMPT with a turn-window, a CourseProfile that keeps the template course-agnostic, and an abstention/coverage channel — all folded into `classifier_hash` in one migration.

**Architecture:** A new `src/labeling/course.py` holds `CourseProfile` (pinned, hashed provenance input). `sampler.py` replaces the single-tutor-message `context_before` with a window of the last 6 turns (both roles). `draft.py` gets the rewritten prompt with `{course_context}`/`{context}` slots plus a `no_label_fits` abstention bool on the wire model and `MessageLabels`. `elicit.py`, `snapshot.py`, `summary.py`, `cli.py`, `webapp.py` thread the profile through and surface the abstention pile on the done screen.

**Tech Stack:** Python 3.11+, pydantic v2, pytest. Run everything with the worktree venv: `.venv/bin/pytest`, `.venv/bin/python`.

## Global Constraints

- **Rule 4:** no student text, no `.env`, nothing from `data/` may enter git. Test fixtures use invented text only.
- **Gemini wire models** (anything passed as `response_model` to `generate`) must stay free of `dict[...]` fields — lists of typed items and scalars only (Developer API rejects `additionalProperties`).
- **Provenance:** `classifier_hash` must cover prompt template, schema version, model, CourseProfile content, and window size. Any of these changing must change the hash.
- **Back-compat:** `MessageLabels` gains `no_label_fits: bool = False` with a default so existing snapshots' `labels.jsonl` still parse.
- **Register:** match existing docstring style — every module cites the CLAUDE.md rule it serves.
- Commit after each task; never `git add data/` or `.env`.

---

### Task 1: CourseProfile module

**Files:**
- Create: `src/labeling/course.py`
- Test: `tests/test_course.py`

**Interfaces:**
- Produces: `CourseProfile` (pydantic BaseModel; fields `course_name, domain_description, tooling, paste_conventions, reference_conventions, message_shape_notes`, all `str`), `CourseProfile.profile_id -> str` (12-hex content hash), `CourseProfile.render_context() -> str`, `CourseProfile.canonical() -> str`, module constant `DSC10_PROFILE: CourseProfile`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_course.py
"""CourseProfile: pinned course-context input to the classifier
(2026-08-06 memo, 'Generalization beyond DSC 10')."""
from src.labeling.course import DSC10_PROFILE, CourseProfile


def _profile(**overrides) -> CourseProfile:
    base = dict(
        course_name="CSE 99", domain_description="intro C++ course",
        tooling="g++, gradescope autograder",
        paste_conventions="students paste compiler errors and segfault output",
        reference_conventions="students reference problems as 'PA3 part 2'",
        message_shape_notes="most messages are short",
    )
    base.update(overrides)
    return CourseProfile(**base)


def test_profile_id_is_stable_and_content_sensitive():
    a, b = _profile(), _profile()
    assert a.profile_id == b.profile_id
    assert len(a.profile_id) == 12
    assert a.profile_id != _profile(tooling="clang").profile_id


def test_render_context_contains_every_field():
    p = _profile()
    text = p.render_context()
    for value in p.model_dump().values():
        assert value in text


def test_dsc10_profile_mentions_course_and_tooling():
    text = DSC10_PROFILE.render_context()
    assert "DSC 10" in text
    assert "babypandas" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_course.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.labeling.course'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/course.py
"""CourseProfile: the course-specific vocabulary the classifier prompt
operates over, kept out of the template so the template stays
course-agnostic (2026-08-06 memo). A profile is a pinned provenance input:
its content is hashed into classifier_hash, so two courses sharing a
template are still different classifiers."""
import hashlib
import json

from pydantic import BaseModel


class CourseProfile(BaseModel):
    course_name: str
    domain_description: str
    tooling: str
    paste_conventions: str
    reference_conventions: str
    message_shape_notes: str

    def canonical(self) -> str:
        return json.dumps(self.model_dump(), sort_keys=True)

    @property
    def profile_id(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()[:12]

    def render_context(self) -> str:
        return (
            f"{self.course_name}: {self.domain_description}\n"
            f"Tooling: {self.tooling}\n"
            f"Pasted material: {self.paste_conventions}\n"
            f"Assignment references: {self.reference_conventions}\n"
            f"Message shape: {self.message_shape_notes}"
        )


# Filled from the corpus-profiling pass behind the 2026-08-06 memo.
DSC10_PROFILE = CourseProfile(
    course_name="DSC 10",
    domain_description=(
        "an introductory data science course (UC San Diego) taught in "
        "Python with the babypandas library, inside Jupyter notebooks; "
        "an AI tutor is embedded in the notebook"),
    tooling="Python, babypandas, numpy, Jupyter notebooks",
    paste_conventions=(
        "students often paste assignment prompt text, code cells, or full "
        "error tracebacks as their message, sometimes with no words of "
        "their own"),
    reference_conventions=(
        "students reference assignment items by number (e.g. 'question "
        "1.6', 'help with 4.1', or a bare number like '3.2')"),
    message_shape_notes=(
        "most messages are under 40 characters; many are terse follow-ups "
        "that only make sense given the preceding turns; messages may be "
        "in languages other than English"),
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_course.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/labeling/course.py tests/test_course.py
git commit -m "feat: CourseProfile as pinned course-context input"
```

---

### Task 2: Turn-window context in the sampler

**Files:**
- Modify: `src/labeling/sampler.py` (replace `_neighbors` and `SampledMessage.context_before`)
- Test: `tests/test_sampler.py` (update existing + add window tests)

**Interfaces:**
- Consumes: `Turn`, `Conversation` from `src.ingest.rawlog` (unchanged).
- Produces: `WINDOW_TURNS = 6` module constant; `SampledMessage.context: list[Turn]` (the up-to-6 turns before the target, both roles, conversation order) REPLACING `context_before: str | None`; `SampledMessage.context_after: str | None` unchanged (next tutor reply).

- [ ] **Step 1: Read the existing tests, then add/adjust**

Read `tests/test_sampler.py` first; update any construction/assertion using `context_before`. Add:

```python
# append to tests/test_sampler.py
from src.ingest.rawlog import Conversation, Turn
from src.labeling.sampler import WINDOW_TURNS, stratified_sample


def _conv(texts_roles, conv_id="c1", chatlog_id=1) -> Conversation:
    turns, si = [], 0
    for i, (role, text) in enumerate(texts_roles):
        t = Turn(index=i, role=role, text=text,
                 student_index=si if role == "student" else None)
        if role == "student":
            si += 1
        turns.append(t)
    return Conversation(conv_id=conv_id, chatlog_id=chatlog_id,
                        notebook=None, started_at=None, turns=turns)


def test_context_is_prior_turns_both_roles_in_order():
    conv = _conv([("student", "s0"), ("tutor", "t0"),
                  ("student", "s1"), ("student", "s2")])
    sample = stratified_sample([conv], n=99, seed=0)
    target = next(m for m in sample if m.text == "s2")
    assert [(t.role, t.text) for t in target.context] == [
        ("student", "s0"), ("tutor", "t0"), ("student", "s1")]


def test_context_capped_at_window_turns():
    pairs = []
    for i in range(8):
        pairs += [("student", f"s{i}"), ("tutor", f"t{i}")]
    conv = _conv(pairs)
    sample = stratified_sample([conv], n=99, seed=0)
    target = next(m for m in sample if m.text == "s7")
    assert len(target.context) == WINDOW_TURNS
    assert target.context[-1].text == "t6"


def test_first_turn_has_empty_context():
    conv = _conv([("student", "s0"), ("tutor", "t0")])
    sample = stratified_sample([conv], n=99, seed=0)
    target = next(m for m in sample if m.text == "s0")
    assert target.context == []
    assert target.context_after == "t0"
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `.venv/bin/pytest tests/test_sampler.py -v`
Expected: FAIL with `ImportError: cannot import name 'WINDOW_TURNS'`

- [ ] **Step 3: Implement**

In `src/labeling/sampler.py`: import `Turn` alongside `Conversation`; add constant and replace `_neighbors`:

```python
from src.ingest.rawlog import Conversation, Turn

# Hash-visible context parameter (2026-08-06 memo): folded into
# classifier_hash via draft.classifier_hash. Changing it is a new classifier.
WINDOW_TURNS = 6


class SampledMessage(BaseModel):
    chatlog_id: int
    conv_id: str
    message_index: int
    text: str
    context: list[Turn]
    context_after: str | None
    stratum: str


def _context(conv: Conversation, turn_index: int) -> tuple[list[Turn], str | None]:
    """Last WINDOW_TURNS turns before the target (both roles: 71% of student
    turns are <40 chars and deictic — one adjacent tutor message is not
    enough; 2026-08-06 memo), plus the next tutor reply."""
    window = conv.turns[max(0, turn_index - WINDOW_TURNS):turn_index]
    after = next((t.text for t in conv.turns[turn_index + 1:]
                  if t.role == "tutor"), None)
    return list(window), after
```

and in `stratified_sample` replace the `_neighbors` call:

```python
            window, after = _context(conv, turn.index)
            strata[stratum].append(SampledMessage(
                chatlog_id=conv.chatlog_id, conv_id=conv.conv_id,
                message_index=turn.index, text=turn.text,
                context=window, context_after=after, stratum=stratum,
            ))
```

Delete `_neighbors`.

- [ ] **Step 4: Run the sampler tests**

Run: `.venv/bin/pytest tests/test_sampler.py -v`
Expected: PASS. (`tests/test_draft.py` and others may now fail on `context_before` — fixed in Task 3; do not commit broken main-suite state, so run only sampler tests here and commit together with Task 3 ONLY IF the full suite is red. If `pytest` whole-suite is green, commit now.)

- [ ] **Step 5: Commit (see caveat above)**

```bash
git add src/labeling/sampler.py tests/test_sampler.py
git commit -m "feat: turn-window context (WINDOW_TURNS=6) replaces single-tutor-message context"
```

---

### Task 3: Rewritten CLASSIFY_PROMPT, abstention field, profile-aware hash

**Files:**
- Modify: `src/labeling/draft.py`
- Test: `tests/test_draft.py`

**Interfaces:**
- Consumes: `CourseProfile`, `DSC10_PROFILE` (Task 1); `SampledMessage.context: list[Turn]`, `WINDOW_TURNS` (Task 2).
- Produces: `LabelVerdicts.no_label_fits: bool`; `MessageLabels.no_label_fits: bool = False`; `draft_labels(messages, schema, profile, generate, on_progress=None, on_result=None)`; `classifier_hash(schema, model, profile) -> str`; `CLASSIFY_PROMPT` with slots `{course_context} {labels} {context} {text} {context_after}`; helper `_render_window(turns: list[Turn]) -> str`.

- [ ] **Step 1: Update/extend tests**

Read `tests/test_draft.py`; update existing calls to the new signatures (add a `profile=` arg using a small fixture profile, switch `SampledMessage` construction to `context=[...]`). Add:

```python
# key new tests in tests/test_draft.py
from src.ingest.rawlog import Turn
from src.labeling.course import CourseProfile
from src.labeling.draft import (CLASSIFY_PROMPT, LabelVerdict, LabelVerdicts,
                                _render_window, classifier_hash, draft_labels)
from src.labeling.sampler import SampledMessage
from src.labeling.schema import LabelDef, LabelSchema

PROFILE = CourseProfile(
    course_name="Test 101", domain_description="a test course",
    tooling="pytest", paste_conventions="students paste tracebacks",
    reference_conventions="by number", message_shape_notes="short")

SCHEMA = LabelSchema(instructor_intent="i", labels=[
    LabelDef(name="asks-help", kind="behavioral", description="d",
             positive_criteria="p", negative_criteria="n")])


def _msg(**kw):
    base = dict(chatlog_id=1, conv_id="c", message_index=2, text="help 1.2",
                context=[Turn(index=0, role="student", text="earlier",
                              student_index=0),
                         Turn(index=1, role="tutor", text="reply")],
                context_after=None, stratum="s")
    base.update(kw)
    return SampledMessage(**base)


def test_prompt_carries_course_context_and_window():
    captured = {}

    def fake_generate(prompt, response_model):
        captured["prompt"] = prompt
        return LabelVerdicts(verdicts=[LabelVerdict(
            label="asks-help", applies=True, rationale="r")],
            no_label_fits=False)

    draft_labels([_msg()], SCHEMA, PROFILE, fake_generate)
    p = captured["prompt"]
    assert "Test 101" in p
    assert "student: earlier" in p and "tutor: reply" in p
    assert p.index("student: earlier") < p.index("STUDENT MESSAGE TO LABEL")


def test_abstention_flag_lands_on_message_labels():
    def fake_generate(prompt, response_model):
        return LabelVerdicts(verdicts=[], no_label_fits=True)

    out = draft_labels([_msg()], SCHEMA, PROFILE, fake_generate)
    assert out[0].no_label_fits is True
    assert out[0].labels == {"asks-help": False}


def test_render_window_empty():
    assert _render_window([]) == "(conversation start)"


def test_hash_covers_profile_and_window():
    h1 = classifier_hash(SCHEMA, "m", PROFILE)
    h2 = classifier_hash(SCHEMA, "m",
                         PROFILE.model_copy(update={"tooling": "other"}))
    assert h1 != h2
```

- [ ] **Step 2: Run to verify failures**

Run: `.venv/bin/pytest tests/test_draft.py -v`
Expected: FAIL (`no_label_fits` unknown field / signature mismatch).

- [ ] **Step 3: Implement in `src/labeling/draft.py`**

```python
class LabelVerdicts(BaseModel):
    verdicts: list[LabelVerdict]
    # Detection channel, not a labeling one (2026-08-06 memo): the model may
    # say "no label fits" but may never name a new label. Feeds the
    # instructor's coverage pile; round-trips through the tweak loop.
    no_label_fits: bool = False


class MessageLabels(BaseModel):
    chatlog_id: int
    message_index: int
    labels: dict[str, bool]
    rationales: dict[str, str]
    no_label_fits: bool = False   # default: old snapshots still parse


CLASSIFY_PROMPT = """You label one student message from a student–AI tutor \
conversation.

Course context:
{course_context}

For EACH label below decide true/false and give a one-sentence rationale. \
Judge the student's act in THIS message — what the student is doing at this \
point in the conversation — using the preceding turns to resolve short or \
deictic messages (a bare "?", a question number, a pasted error).

Rules:
- Distinguish student-authored words from pasted material. A pasted \
assignment prompt or bare error output expresses no affect by itself; label \
it by what the student is using it to do.
- Very short messages inherit their meaning from the immediately preceding \
turns, including the student's own previous message.
- If a label cannot be judged from this message even with context, mark it \
false and say why in the rationale.

Labels:
{labels}

Conversation so far (most recent last; may be empty):
{context}

STUDENT MESSAGE TO LABEL:
{text}

Tutor reply after (may be empty):
{context_after}

Return one verdict entry per label: label (exact name), applies \
(true/false), rationale (one sentence). Also set no_label_fits=true if this \
message shows a student act that none of the labels capture; otherwise \
false. Do not invent label names."""


def _render_window(turns: list[Turn]) -> str:
    if not turns:
        return "(conversation start)"
    return "\n".join(f"{t.role}: {t.text}" for t in turns)
```

`draft_labels` gains `profile: CourseProfile` as third positional parameter (before `generate`); prompt formatting becomes:

```python
        prompt = CLASSIFY_PROMPT.format(
            course_context=profile.render_context(), labels=block,
            context=_render_window(m.context), text=m.text,
            context_after=m.context_after or "",
        )
        v: LabelVerdicts = generate(prompt, LabelVerdicts)
        labels, rationales = _validated_verdicts(v, schema)
        out.append(MessageLabels(chatlog_id=m.chatlog_id,
                                 message_index=m.message_index,
                                 labels=labels, rationales=rationales,
                                 no_label_fits=v.no_label_fits))
```

`classifier_hash` becomes:

```python
def classifier_hash(schema: LabelSchema, model: str,
                    profile: CourseProfile) -> str:
    canonical = "\x1e".join([CLASSIFY_PROMPT, schema.version_id, model,
                             profile.canonical(), f"window={WINDOW_TURNS}"])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
```

Imports: `from src.ingest.rawlog import Turn`, `from src.labeling.course import CourseProfile`, `from src.labeling.sampler import SampledMessage, WINDOW_TURNS`. Update the module docstring: hash now pins template + schema + model + profile + window.

- [ ] **Step 4: Run draft + sampler tests**

Run: `.venv/bin/pytest tests/test_draft.py tests/test_sampler.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/draft.py tests/test_draft.py src/labeling/sampler.py tests/test_sampler.py
git commit -m "feat: context-faithful classifier prompt, abstention channel, profile-aware classifier_hash"
```

---

### Task 4: Course context in elicitation

**Files:**
- Modify: `src/labeling/elicit.py`
- Test: `tests/test_elicit.py`

**Interfaces:**
- Consumes: `CourseProfile` (Task 1).
- Produces: `draft_schema(intent_text, profile, generate)`; `revise_schema(current, feedback, profile, generate)` — `profile` inserted before `generate` in both.

- [ ] **Step 1: Update tests** — adapt existing calls; add:

```python
def test_elicit_prompt_carries_course_context_and_judgeability():
    captured = {}

    def fake_generate(prompt, response_model):
        captured["prompt"] = prompt
        return DraftedLabels(labels=[LabelDef(
            name="x", kind="other", description="d",
            positive_criteria="p", negative_criteria="n")])

    draft_schema("intent", PROFILE, fake_generate)   # PROFILE as in test_draft
    assert "Test 101" in captured["prompt"]
    assert "judgeable on messages as they actually occur" in captured["prompt"]
```

- [ ] **Step 2: Run to verify failure** — `.venv/bin/pytest tests/test_elicit.py -v` → FAIL (signature).

- [ ] **Step 3: Implement** — both templates gain a block after their first paragraph:

```
Course context:
{course_context}
```

and `ELICIT_PROMPT` gains, at the end of the drafting-instructions paragraph:
`Labels must be judgeable on messages as they actually occur in this course's logs (see message shape above), not only on articulate prose.`
Both functions pass `course_context=profile.render_context()` into `.format(...)`.

- [ ] **Step 4: Run** — `.venv/bin/pytest tests/test_elicit.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/elicit.py tests/test_elicit.py
git commit -m "feat: elicitation prompts take course context + judgeability constraint"
```

---

### Task 5: Profile in snapshot manifest

**Files:**
- Modify: `src/labeling/snapshot.py`
- Test: `tests/test_snapshot.py`

**Interfaces:**
- Consumes: `classifier_hash(schema, model, profile)` (Task 3), `CourseProfile` (Task 1).
- Produces: `emit_snapshot(conversations, labels, schema, model, repo_sha, data_dir, excluded_conversations, profile)` — `profile: CourseProfile` appended as keyword arg; manifest gains `"course_profile": profile.model_dump()` and `"profile_id": profile.profile_id`.

- [ ] **Step 1: Update tests** — adapt `emit_snapshot` calls; add assertion:

```python
manifest = json.loads((path / "manifest.json").read_text())
assert manifest["profile_id"] == PROFILE.profile_id
assert manifest["course_profile"]["course_name"] == "Test 101"
```

- [ ] **Step 2: Run to verify failure** — `.venv/bin/pytest tests/test_snapshot.py -v` → FAIL.
- [ ] **Step 3: Implement** — thread `profile` through; `chash = classifier_hash(schema, model, profile)`; add the two manifest keys after `"classifier_hash"`.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit**

```bash
git add src/labeling/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot manifest records course profile + profile_id"
```

---

### Task 6: Abstention pile in the summary

**Files:**
- Modify: `src/labeling/summary.py` (extend `_coverage`)
- Test: `tests/test_summary.py`

**Interfaces:**
- Consumes: `MessageLabels.no_label_fits` (Task 3).
- Produces: `_coverage(...)` return dict gains `"abstained": int` (count of `no_label_fits`) and `"abstained_examples": list[dict]` (up to 5, seeded shuffle, `{"text", "conv"}` — same shape as `zero_examples`).

- [ ] **Step 1: Add test**

```python
def test_coverage_reports_abstained_pile():
    # build conversations + labeled where exactly one MessageLabels has
    # no_label_fits=True; call compute_summary(...)
    assert summary["coverage"]["abstained"] == 1
    assert summary["coverage"]["abstained_examples"][0]["conv"] == 1
```

(Reuse the fixture builders already in `tests/test_summary.py` — read them first and construct `MessageLabels(..., no_label_fits=True)` for one message.)

- [ ] **Step 2: Run to verify failure** → KeyError `abstained`.
- [ ] **Step 3: Implement** in `_coverage`, mirroring the `zero_examples` pattern:

```python
    lookup = _message_lookup(conversations)
    abstained = [r for r in labeled if r.no_label_fits]
    rng.shuffle(abstained)
    abstained_examples = []
    for r in abstained[:5]:
        hit = lookup.get((r.chatlog_id, r.message_index))
        if hit:
            abstained_examples.append({"text": hit[0], "conv": r.chatlog_id})
```

Add `"abstained": len(abstained), "abstained_examples": abstained_examples` to the return dict. Note in the docstring: the pile feeds the instructor, not the schema (2026-08-06 memo).

- [ ] **Step 4: Run** — `.venv/bin/pytest tests/test_summary.py -v` → PASS.
- [ ] **Step 5: Commit**

```bash
git add src/labeling/summary.py tests/test_summary.py
git commit -m "feat: abstained (no-label-fits) pile in coverage summary"
```

---

### Task 7: Thread the profile through cli.py and webapp.py

**Files:**
- Modify: `src/labeling/cli.py`, `src/labeling/webapp.py`
- Test: `tests/test_cli.py`, `tests/test_webapp.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `run_loop(intent, conversations, generate, *, profile, sample_size, seed, ask, say)`; `LoopSession(..., profile: CourseProfile = DSC10_PROFILE)`; webapp summary `classifier` dict gains `"profile_id": profile.profile_id`; state dict provenance unchanged otherwise.

- [ ] **Step 1: Update tests** — read both test files; update every `run_loop`/`LoopSession`/`draft_labels`/`draft_schema`/`revise_schema`/`emit_snapshot` call for the new signatures (pass a fixture profile or rely on the `DSC10_PROFILE` default). Add to `tests/test_webapp.py`:

```python
def test_done_summary_carries_profile_id():
    # drive session start->accept with fake generate/fetch (existing pattern)
    assert session.state()["summary"]["classifier"]["profile_id"] == \
        session.profile.profile_id
```

- [ ] **Step 2: Run to verify failures** — `.venv/bin/pytest tests/test_cli.py tests/test_webapp.py -v`.
- [ ] **Step 3: Implement**
  - `cli.py`: import `DSC10_PROFILE`; `run_loop` gains keyword-only `profile`; pass to `draft_schema(intent, profile, generate)`, `revise_schema(schema, feedback, profile, generate)`, `draft_labels(sample, schema, profile, generate)`; `main()` uses `DSC10_PROFILE` and passes `profile=DSC10_PROFILE` to `run_loop`, mass-label `draft_labels`, and `emit_snapshot(..., profile=DSC10_PROFILE)`.
  - `webapp.py`: `LoopSession.__init__` gains `profile: CourseProfile = DSC10_PROFILE`, stored as `self.profile`; `_label_incremental` calls `draft_labels(todo, self.schema, self.profile, self.generate, ...)`; `start()` job uses `draft_schema(intent, self.profile, self.generate)`; `tweak()` uses `revise_schema(self.schema, feedback, self.profile, self.generate)`; `accept()` uses `emit_snapshot(..., profile=self.profile)` and

```python
            summary["classifier"] = {
                "hash": classifier_hash(self.schema, DEFAULT_MODEL,
                                        self.profile),
                "model": DEFAULT_MODEL,
                "profile_id": self.profile.profile_id,
            }
```

- [ ] **Step 4: Run the FULL suite** — `.venv/bin/pytest -v` → all PASS.
- [ ] **Step 5: Commit**

```bash
git add src/labeling/cli.py src/labeling/webapp.py tests/test_cli.py tests/test_webapp.py
git commit -m "feat: thread CourseProfile through CLI and webapp; profile_id in done summary"
```

---

### Task 8: Done-screen surfaces the abstention pile

**Files:**
- Modify: `src/labeling/static/index.html` (done-screen coverage section, near the `zero_examples` rendering around the `renderDone`/`done-coverage` code, and the ledger lines around `addLedgerLine(ledger, ...)`)

**Interfaces:**
- Consumes: `summary.coverage.abstained`, `summary.coverage.abstained_examples`, `summary.classifier.profile_id` (Tasks 6–7).

- [ ] **Step 1: Locate the rendering code** — in `index.html`, find where `s.coverage.zero_conversations` and `s.coverage.zero_examples` are rendered (~line 800) and where `classifier`/`model` ledger lines are added (~line 770).

- [ ] **Step 2: Implement** — after the zero-conversations block, add a parallel block (match surrounding style/idiom exactly):

```javascript
  if (s.coverage.abstained > 0) {
    const ab = document.createElement("p");
    ab.textContent =
      `${s.coverage.abstained} messages the classifier could not fit to ` +
      `any label — review candidates for a schema tweak`;
    cov.append(ab);
    if (s.coverage.abstained_examples.length) {
      const ul = document.createElement("ul");
      for (const z of s.coverage.abstained_examples) {
        const li = document.createElement("li");
        li.textContent = z.text;
        ul.append(li);
      }
      cov.append(ul);
    }
  }
```

and one ledger line after the model line: `addLedgerLine(ledger, \`profile    ${s.classifier.profile_id}\`);`

- [ ] **Step 3: Verify** — `.venv/bin/pytest -v` still green (static file has no unit tests); then a syntax sanity check: `node --check` is unavailable for inline HTML, so instead load-test via the webapp test that fetches `/` if present, and eyeball the diff.

- [ ] **Step 4: Commit**

```bash
git add src/labeling/static/index.html
git commit -m "feat: done screen shows abstention pile + profile id"
```

---

### Task 9: Memo status + full-suite gate

**Files:**
- Modify: `docs/2026-08-06-classifier-prompt-redesign.md` (status line only)

- [ ] **Step 1: Full suite** — `.venv/bin/pytest -v` → all PASS. Also `git status` — confirm nothing from `data/` or `.env` is staged (Rule 4).
- [ ] **Step 2: Update memo status line** to:

```
Status: **adopted (A + CourseProfile + abstention channel) — implemented on
branch `classifier-prompt`, 2026-08-06. B (message-form facet) and C
(few-shot exemplars) remain open.**
```

- [ ] **Step 3: Commit**

```bash
git add docs/2026-08-06-classifier-prompt-redesign.md
git commit -m "docs: memo status — option A + profile + abstention implemented"
```

---

## Verification checklist (post-plan)

- `classifier_hash` changes when: template text, schema, model, any profile field, or `WINDOW_TURNS` changes.
- Old snapshots' `labels.jsonl` rows (no `no_label_fits` key) still validate as `MessageLabels`.
- No `dict[...]` field on `LabelVerdicts`/`LabelVerdict` (wire models).
- The abstention channel never adds label names anywhere — grep `no_label_fits` uses to confirm it is only counted/displayed.
- `git log --stat` shows no `data/` or `.env` files in any commit.
