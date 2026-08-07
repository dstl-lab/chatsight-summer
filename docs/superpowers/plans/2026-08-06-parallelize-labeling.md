# Single-Label Parallel Labeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the sequential all-labels-in-one-call classifier with single-label calls + a per-message coverage call, fanned out on a bounded thread pool, with the abstention pile surfaced live in the webapp and CLI.

**Architecture:** `draft_labels` becomes a call-level fan-out — (message × label) verdict calls plus one (message) coverage call — on a `ThreadPoolExecutor`; a message's record assembles when all its calls land, so the per-message `on_result`/resume contract is unchanged. `classifier_hash` re-pins over both new templates. Webapp/CLI gain a `workers` knob and an abstention feed.

**Tech Stack:** Python 3.12, pydantic, `concurrent.futures`, FastAPI webapp (vanilla-JS static page), pytest. Gemini via the injected `Generate` callable — tests never touch the network.

**Spec:** `docs/superpowers/specs/2026-08-06-parallelize-labeling-design.md`. Memo: `docs/2026-08-06-parallel-labeling-live-schema-growth.md`.

## Global Constraints

- `MessageLabels` stays snapshot-compatible: new fields must default (`coverage_note: str = ""`) so old snapshots parse.
- Wire models for Gemini structured output must stay free of `dict[...]` fields (Gemini rejects additionalProperties).
- The coverage call runs for EVERY message, never conditionally.
- Coverage `note` describes the uncaptured act; the classifier never names/creates labels.
- Callbacks (`on_result`, `on_progress`) fire under `draft_labels`' internal lock: serialized, progress strictly increasing, per completed MESSAGE.
- `workers=1` must execute strictly sequentially (parity baseline).
- No embeddings anywhere; no snapshot manifest format change beyond the new hash value.
- Student data never enters git — test fixtures use invented text only.
- Run tests with `uv run pytest`.

---

### Task 1: Single-label + coverage prompts, sequential fan-out, new hash

**Files:**
- Modify: `src/labeling/draft.py` (full rewrite of prompts/wire models/loop; keep module docstring's provenance framing, updated)
- Modify: `tests/test_draft.py`
- Modify: `tests/test_cli.py` (shared `make_fake_generate`)
- Test: `tests/test_draft.py`

**Interfaces:**
- Consumes: `LabelSchema`/`LabelDef` (schema.py), `CourseProfile.render_context()` (course.py), `SampledMessage`, `WINDOW_TURNS` (sampler.py), `Generate` (llm.py).
- Produces (later tasks rely on these exact names):
  - `SingleLabelVerdict(BaseModel)`: `applies: bool`, `rationale: str`
  - `CoverageVerdict(BaseModel)`: `no_label_fits: bool`, `note: str = ""`
  - `MessageLabels`: existing fields + `coverage_note: str = ""`
  - `SINGLE_LABEL_PROMPT`, `COVERAGE_PROMPT` module constants
  - `draft_labels(messages, schema, profile, generate, on_progress=None, on_result=None)` — same signature as today (workers added in Task 2), same return type `list[MessageLabels]` in input order
  - `classifier_hash(schema, model, profile) -> str` — same signature, new canonical string

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_draft.py` wholesale (the old `LabelVerdicts` block architecture is gone). Keep `PROFILE`, `SCHEMA`, `_msg`, `_msg_i` helpers as they are today, then:

```python
from src.labeling.draft import (COVERAGE_PROMPT, SINGLE_LABEL_PROMPT,
                                CoverageVerdict, MessageLabels,
                                SingleLabelVerdict, _render_window,
                                classifier_hash, draft_labels)

TWO_LABEL_SCHEMA = LabelSchema(instructor_intent="i", labels=[
    LabelDef(name="asks-help", kind="behavioral", description="asks for help",
             positive_criteria="p", negative_criteria="n"),
    LabelDef(name="frustrated", kind="behavioral", description="is frustrated",
             positive_criteria="p2", negative_criteria="n2")])


def make_fake(applies=True, no_label_fits=False, note=""):
    def gen(prompt, response_model):
        gen.calls.append((response_model.__name__, prompt))
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=applies, rationale="because")
        assert response_model is CoverageVerdict
        return CoverageVerdict(no_label_fits=no_label_fits, note=note)
    gen.calls = []
    return gen


def test_fanout_shape_one_call_per_label_plus_coverage():
    gen = make_fake()
    out = draft_labels([_msg_i(0), _msg_i(1)], TWO_LABEL_SCHEMA, PROFILE, gen)
    # (2 labels + 1 coverage) x 2 messages
    assert len(gen.calls) == 6
    single = [p for kind, p in gen.calls if kind == "SingleLabelVerdict"]
    coverage = [p for kind, p in gen.calls if kind == "CoverageVerdict"]
    assert len(single) == 4 and len(coverage) == 2
    # each single-label prompt carries exactly one label's criteria
    assert sum("p2" in p for p in single) == 2
    for p in single:
        assert ("asks-help" in p) != ("frustrated" in p)
    # coverage prompt sees every label name but no positive/negative criteria
    for p in coverage:
        assert "asks-help" in p and "frustrated" in p
    assert len(out) == 2
    assert out[0].labels == {"asks-help": True, "frustrated": True}
    assert out[0].rationales["asks-help"] == "because"


def test_coverage_note_lands_on_message_labels():
    gen = make_fake(applies=False, no_label_fits=True, note="asks about grades")
    out = draft_labels([_msg()], SCHEMA, PROFILE, gen)
    assert out[0].no_label_fits is True
    assert out[0].coverage_note == "asks about grades"
    assert out[0].labels == {"asks-help": False}


def test_coverage_call_runs_even_when_labels_apply():
    gen = make_fake(applies=True)
    draft_labels([_msg()], SCHEMA, PROFILE, gen)
    assert any(k == "CoverageVerdict" for k, _ in gen.calls)


def test_prompt_carries_course_context_and_window():
    gen = make_fake()
    draft_labels([_msg()], SCHEMA, PROFILE, gen)
    for _, p in gen.calls:
        assert "Test 101" in p
        assert "student: earlier" in p and "tutor: reply" in p
        assert p.index("student: earlier") < p.index("STUDENT MESSAGE TO LABEL")


def test_empty_rationale_defaults():
    def gen(prompt, response_model):
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="")
        return CoverageVerdict(no_label_fits=False)
    out = draft_labels([_msg()], SCHEMA, PROFILE, gen)
    assert out[0].rationales == {"asks-help": "(no rationale returned)"}


def test_message_labels_defaults_parse_old_snapshots():
    r = MessageLabels(chatlog_id=1, message_index=0, labels={},
                      rationales={})
    assert r.coverage_note == "" and r.no_label_fits is False


def test_on_result_fires_per_message_in_order():
    gen = make_fake()
    seen = []
    msgs = [_msg_i(0), _msg_i(1)]
    draft_labels(msgs, SCHEMA, PROFILE, gen,
                 on_result=lambda m, r: seen.append(m.message_index))
    assert seen == [0, 1]


def test_progress_counts_messages():
    gen = make_fake()
    ticks = []
    draft_labels([_msg_i(0), _msg_i(1)], SCHEMA, PROFILE, gen,
                 on_progress=lambda d, t: ticks.append((d, t)))
    assert ticks == [(1, 2), (2, 2)]


def test_render_window_empty():
    assert _render_window([]) == "(conversation start)"


def test_hash_covers_profile_window_schema_model():
    h = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert len(h) == 12
    assert h != classifier_hash(SCHEMA, "gemini-3.0", PROFILE)
    assert h != classifier_hash(TWO_LABEL_SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h != classifier_hash(
        SCHEMA, "gemini-2.5-flash",
        PROFILE.model_copy(update={"tooling": "other"}))


def test_classifier_hash_golden_regression():
    # Golden literal pins BOTH templates, the profile rendering, and the
    # window rendering. Any intentional change to those must update this
    # literal — that update, and only that update, is the point of the test.
    h = classifier_hash(SCHEMA, "gemini-2.5-flash", PROFILE)
    assert h == "REPLACE_AFTER_IMPLEMENTATION"
```

Delete the old `fake_generate`, `fake_generate_stray_and_missing`, and the tests
`test_draft_labels_one_result_per_message`, `test_draft_labels_filters_stray_keys_and_defaults_missing`, `test_classifier_hash_pins_schema_and_model`, `test_draft_labels_calls_on_result_per_message`, `test_abstention_flag_lands_on_message_labels` (their behaviors are covered by the new tests; stray-label filtering is structurally impossible now — single-label calls can't hallucinate names).

In `tests/test_cli.py`, update `make_fake_generate` so its labeling branch dispatches on the new wire models (keep its schema-drafting branch exactly as is):

```python
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        if response_model is CoverageVerdict:
            return CoverageVerdict(no_label_fits=False, note="")
```

(with `from src.labeling.draft import CoverageVerdict, SingleLabelVerdict` added; remove the old `LabelVerdicts` construction and import.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_draft.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'SINGLE_LABEL_PROMPT'`.

- [ ] **Step 3: Rewrite draft.py**

Replace the wire models, prompt, and loop (module docstring: update the provenance sentence to name both templates). Keep `_render_window` as is; delete `LabelVerdict`, `LabelVerdicts`, `_labels_block`, `_validated_verdicts`, `CLASSIFY_PROMPT`.

```python
class SingleLabelVerdict(BaseModel):
    applies: bool
    rationale: str


class CoverageVerdict(BaseModel):
    # Detection channel, not a labeling one (2026-08-06 memos): the model may
    # flag "no label fits" and describe the act, but never name a label.
    no_label_fits: bool
    note: str = ""


class MessageLabels(BaseModel):
    chatlog_id: int
    message_index: int
    labels: dict[str, bool]
    rationales: dict[str, str]
    no_label_fits: bool = False   # default: old snapshots still parse
    coverage_note: str = ""       # ditto


_SHARED_RULES = """\
Rules:
- Distinguish student-authored words from pasted material. A pasted \
assignment prompt or bare error output expresses no affect by itself; label \
it by what the student is using it to do.
- Very short messages inherit their meaning from the immediately preceding \
turns, including the student's own previous message.
- Judge the student's act in THIS message — what the student is doing at \
this point in the conversation — using the preceding turns to resolve short \
or deictic messages (a bare "?", a question number, a pasted error)."""

_SHARED_CONTEXT = """\
Conversation so far (most recent last; may be empty):
{context}

STUDENT MESSAGE TO LABEL:
{text}

Tutor reply after (may be empty):
{context_after}"""

SINGLE_LABEL_PROMPT = f"""You judge ONE label against one student message \
from a student–AI tutor conversation.

Course context:
{{course_context}}

{_SHARED_RULES}
- If the label cannot be judged from this message even with context, answer \
false and say why in the rationale.

Label:
- {{label_name}}: {{label_description}} | applies when: {{positive_criteria}} \
| does NOT apply when: {{negative_criteria}}

{_SHARED_CONTEXT}

Does the label apply to the student message? Return applies (true/false) \
and a one-sentence rationale."""

COVERAGE_PROMPT = f"""You check label coverage for one student message from \
a student–AI tutor conversation.

Course context:
{{course_context}}

{_SHARED_RULES}

The label set:
{{labels}}

{_SHARED_CONTEXT}

Set no_label_fits=true only if this message shows a student act that NONE \
of the labels capture (a message can be partially captured: some act \
labeled, another not — that still counts). If true, describe the uncaptured \
act in one sentence in note; do not propose or name any label. Otherwise \
no_label_fits=false and note empty."""


def _coverage_labels_block(schema: LabelSchema) -> str:
    return "\n".join(f"- {l.name}: {l.description}" for l in schema.labels)


def _classify_message(m: SampledMessage, schema: LabelSchema,
                      profile: CourseProfile,
                      generate: Generate) -> MessageLabels:
    common = dict(course_context=profile.render_context(),
                  context=_render_window(m.context), text=m.text,
                  context_after=m.context_after or "")
    labels: dict[str, bool] = {}
    rationales: dict[str, str] = {}
    for l in schema.labels:
        v: SingleLabelVerdict = generate(
            SINGLE_LABEL_PROMPT.format(
                label_name=l.name, label_description=l.description,
                positive_criteria=l.positive_criteria,
                negative_criteria=l.negative_criteria, **common),
            SingleLabelVerdict)
        labels[l.name] = v.applies
        rationales[l.name] = v.rationale or "(no rationale returned)"
    c: CoverageVerdict = generate(
        COVERAGE_PROMPT.format(labels=_coverage_labels_block(schema),
                               **common),
        CoverageVerdict)
    return MessageLabels(chatlog_id=m.chatlog_id,
                         message_index=m.message_index, labels=labels,
                         rationales=rationales,
                         no_label_fits=c.no_label_fits,
                         coverage_note=c.note if c.no_label_fits else "")


def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 profile: CourseProfile, generate: Generate,
                 on_progress: Callable[[int, int], None] | None = None,
                 on_result: Callable[[SampledMessage, MessageLabels], None]
                 | None = None) -> list[MessageLabels]:
    out: list[MessageLabels] = []
    for i, m in enumerate(messages):
        out.append(_classify_message(m, schema, profile, generate))
        if on_result:
            on_result(m, out[-1])
        if on_progress:
            on_progress(i + 1, len(messages))
    return out


def classifier_hash(schema: LabelSchema, model: str,
                    profile: CourseProfile) -> str:
    # \x1e-joined provenance components: none of them may themselves contain
    # \x1e, or the join stops being unambiguous.
    canonical = "\x1e".join([
        SINGLE_LABEL_PROMPT, COVERAGE_PROMPT, schema.version_id, model,
        profile.canonical(), profile.render_context(),
        f"window={WINDOW_TURNS}",
        _render_window([]),
        _render_window([Turn(index=0, role="student", text="x",
                             student_index=0)]),
    ])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
```

Note `coverage_note` is blanked when `no_label_fits` is false — a stray note without an abstention is noise.

- [ ] **Step 4: Run tests; fix the golden literal**

Run: `uv run pytest tests/test_draft.py -q`
Expected: all pass except `test_classifier_hash_golden_regression`. Print the real hash (`uv run python -c "from tests.test_draft import *; print(classifier_hash(SCHEMA, 'gemini-2.5-flash', PROFILE))"`) and replace `REPLACE_AFTER_IMPLEMENTATION` with it. Re-run: all pass.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS. `tests/test_webapp.py` and `tests/test_cli.py` route through `make_fake_generate`, already updated. If any other test constructs `LabelVerdicts`, update it to the new models the same way.

- [ ] **Step 6: Commit**

```bash
git add src/labeling/draft.py tests/test_draft.py tests/test_cli.py
git commit -m "feat: single-label + coverage call architecture for draft labeling (#1)"
```

---

### Task 2: Parallel executor in draft_labels

**Files:**
- Modify: `src/labeling/draft.py` (`draft_labels` only)
- Test: `tests/test_draft.py`

**Interfaces:**
- Consumes: Task 1's `_classify_message` internals get inlined into call-level tasks; `SingleLabelVerdict`, `CoverageVerdict` unchanged.
- Produces: `draft_labels(messages, schema, profile, generate, on_progress=None, on_result=None, workers: int = 8)` — the only signature change is the keyword-only-style trailing `workers` param. Callbacks fire under the internal lock (serialized); returned list in input order.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_draft.py`)

```python
import threading
import time


def test_calls_run_concurrently():
    barrier = threading.Barrier(3, timeout=5)

    def gen(prompt, response_model):
        barrier.wait()   # only passable with 3 calls truly in flight
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=False, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    # 3 messages x (1 label + coverage) = 6 calls; barrier trips twice
    out = draft_labels([_msg_i(i) for i in range(3)], SCHEMA, PROFILE, gen,
                       workers=3)
    assert len(out) == 3


def test_output_order_despite_scrambled_completion():
    def gen(prompt, response_model):
        # later messages finish first
        for i in range(4):
            if f"invented question {i}" in prompt:
                time.sleep(0.05 * (3 - i))
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    msgs = [_msg_i(i) for i in range(4)]
    seen = []
    ticks = []
    out = draft_labels(msgs, SCHEMA, PROFILE, gen, workers=4,
                       on_result=lambda m, r: seen.append(m.message_index),
                       on_progress=lambda d, t: ticks.append(d))
    assert [r.message_index for r in out] == [0, 1, 2, 3]
    assert sorted(seen) == [0, 1, 2, 3]        # any completion order
    assert ticks == [1, 2, 3, 4]               # strictly increasing


def test_failure_aborts_but_keeps_finished_messages():
    def gen(prompt, response_model):
        if "invented question 2" in prompt:
            raise RuntimeError("boom")
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    msgs = [_msg_i(i) for i in range(3)]
    delivered = []
    try:
        draft_labels(msgs, SCHEMA, PROFILE, gen, workers=1,
                     on_result=lambda m, r: delivered.append(m.message_index))
        raise AssertionError("should have raised")
    except RuntimeError as e:
        assert str(e) == "boom"
    # workers=1 is sequential: messages 0 and 1 completed and were delivered,
    # message 2 failed, nothing after it ran
    assert delivered == [0, 1]


def test_workers_one_is_strictly_sequential():
    active = {"now": 0, "max": 0}
    lock = threading.Lock()

    def gen(prompt, response_model):
        with lock:
            active["now"] += 1
            active["max"] = max(active["max"], active["now"])
        time.sleep(0.005)
        with lock:
            active["now"] -= 1
        if response_model is SingleLabelVerdict:
            return SingleLabelVerdict(applies=True, rationale="r")
        return CoverageVerdict(no_label_fits=False)

    out = draft_labels([_msg_i(i) for i in range(3)], SCHEMA, PROFILE, gen,
                       workers=1)
    assert active["max"] == 1
    assert [r.message_index for r in out] == [0, 1, 2]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_draft.py -q -k "concurrently or scrambled or aborts or sequential"`
Expected: `test_calls_run_concurrently` FAILS (BrokenBarrierError after 5s — sequential code can't have 3 calls in flight) and the others fail on the unknown `workers` kwarg.

- [ ] **Step 3: Implement the executor**

Replace `draft_labels` (keep `_classify_message` for reference or inline it away — the call-level version below supersedes it; delete `_classify_message` if no longer used):

```python
def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 profile: CourseProfile, generate: Generate,
                 on_progress: Callable[[int, int], None] | None = None,
                 on_result: Callable[[SampledMessage, MessageLabels], None]
                 | None = None, workers: int = 8) -> list[MessageLabels]:
    """Call-level fan-out: (message x label) verdict calls plus one coverage
    call per message on a bounded pool. A message's record assembles when all
    its calls land; callbacks fire under the internal lock (serialized,
    progress strictly increasing, per completed message). First failure stops
    further work; already-completed messages were delivered via on_result, so
    a resuming caller (webapp done-set) re-runs only the rest. Concurrency is
    not a provenance input (classifier_hash unchanged by `workers`)."""
    n = len(messages)
    results: list[MessageLabels | None] = [None] * n
    calls_per_msg = len(schema.labels) + 1
    slots = [{"labels": {}, "rationales": {}, "coverage": None,
              "remaining": calls_per_msg} for _ in messages]
    lock = threading.Lock()
    state = {"done": 0, "failure": None}

    def run_call(idx: int, label) -> None:
        with lock:
            if state["failure"] is not None:
                return
        m = messages[idx]
        common = dict(course_context=profile.render_context(),
                      context=_render_window(m.context), text=m.text,
                      context_after=m.context_after or "")
        try:
            if label is None:
                verdict = generate(
                    COVERAGE_PROMPT.format(
                        labels=_coverage_labels_block(schema), **common),
                    CoverageVerdict)
            else:
                verdict = generate(
                    SINGLE_LABEL_PROMPT.format(
                        label_name=label.name,
                        label_description=label.description,
                        positive_criteria=label.positive_criteria,
                        negative_criteria=label.negative_criteria, **common),
                    SingleLabelVerdict)
        except BaseException as e:
            with lock:
                if state["failure"] is None:
                    state["failure"] = e
            return
        with lock:
            if state["failure"] is not None:
                return
            slot = slots[idx]
            if label is None:
                slot["coverage"] = verdict
            else:
                slot["labels"][label.name] = verdict.applies
                slot["rationales"][label.name] = (verdict.rationale
                                                  or "(no rationale returned)")
            slot["remaining"] -= 1
            if slot["remaining"] == 0:
                cov = slot["coverage"]
                r = MessageLabels(
                    chatlog_id=m.chatlog_id, message_index=m.message_index,
                    labels=slot["labels"], rationales=slot["rationales"],
                    no_label_fits=cov.no_label_fits,
                    coverage_note=cov.note if cov.no_label_fits else "")
                results[idx] = r
                state["done"] += 1
                if on_result:
                    on_result(m, r)
                if on_progress:
                    on_progress(state["done"], n)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for idx in range(n):
            for label in [*schema.labels, None]:
                pool.submit(run_call, idx, label)
    if state["failure"] is not None:
        raise state["failure"]
    return [r for r in results if r is not None]
```

Add imports at top: `import threading` and `from concurrent.futures import ThreadPoolExecutor`.

Design notes the implementer should not "fix": callbacks intentionally run inside the lock (serialization + monotonic progress; the webapp's own lock is a different lock and never calls back into draft_labels, so no deadlock). After a failure, pending submitted calls become no-ops via the failure check; the pool context manager waits them out. Partially-called messages stay `None` and are filtered from the return — their calls re-run on resume.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, including all Task 1 tests (sequential semantics under `workers=8` still satisfy them: order, per-message callbacks, fan-out shape).

- [ ] **Step 5: Commit**

```bash
git add src/labeling/draft.py tests/test_draft.py
git commit -m "feat: bounded thread-pool fan-out for draft labeling (#1)"
```

---

### Task 3: workers config + CLI flag + coverage summary line

**Files:**
- Modify: `src/config.py`
- Modify: `src/labeling/cli.py`
- Modify: `src/labeling/webapp.py` (`LoopSession.__init__`, `_label_incremental`, `main`)
- Test: `tests/test_config.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 2's `draft_labels(..., workers=...)`.
- Produces: `Settings.labeling_workers: int` (env `LABELING_WORKERS`, default 8); `run_loop(..., workers: int = 8)`; `LoopSession(..., workers: int = 8)` storing `self.workers`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config.py` (match its existing env-patching style):

```python
def test_labeling_workers_default_and_env(monkeypatch):
    monkeypatch.setenv("EXT_DB_URL", "postgresql://x/y")
    monkeypatch.delenv("LABELING_WORKERS", raising=False)
    assert Settings.load(dotenv=False).labeling_workers == 8
    monkeypatch.setenv("LABELING_WORKERS", "2")
    assert Settings.load(dotenv=False).labeling_workers == 2
```

Append to `tests/test_cli.py` (reuse its existing fake/run harness; adapt names to how the file drives `main`/`run_loop` today):

```python
def test_mass_label_prints_coverage_summary(capsys):
    # drive the existing CLI test harness but with a fake generate whose
    # CoverageVerdict returns no_label_fits=True, note="uncaptured act"
    # for every message; assert the printed summary line:
    #   "Coverage: N of M messages (P%) showed acts no label captures."
    ...
```

Write this test concretely against the harness found in `tests/test_cli.py` (it already fakes `fetch_conversations`/`input`; copy its pattern, swap the coverage branch of the fake to `CoverageVerdict(no_label_fits=True, note="x")`, run the accept path, and assert `"showed acts no label captures" in capsys.readouterr().out`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py tests/test_cli.py -q`
Expected: FAIL — `labeling_workers` attribute missing; coverage line absent.

- [ ] **Step 3: Implement**

`src/config.py` — add field and load line:

```python
    labeling_workers: int
```
```python
            labeling_workers=int(os.environ.get("LABELING_WORKERS", "8")),
```

`src/labeling/cli.py`:
- `argparse`: `parser.add_argument("--workers", type=int, default=None, help="parallel Gemini calls (default: LABELING_WORKERS or 8)")`
- after `settings = Settings.load()`: `workers = args.workers or settings.labeling_workers`
- `run_loop(...)` gains `workers: int = 8` keyword; its internal `draft_labels(sample, schema, profile, generate)` becomes `draft_labels(sample, schema, profile, generate, workers=workers)`; `main` passes `workers=workers`.
- mass-label call becomes `draft_labels(all_messages, schema, DSC10_PROFILE, generate, workers=workers)`, followed by:

```python
    abstained = sum(1 for r in labeled if r.no_label_fits)
    if labeled:
        print(f"Coverage: {abstained} of {len(labeled)} messages "
              f"({abstained / len(labeled):.0%}) showed acts no label "
              f"captures.")
```

`src/labeling/webapp.py`:
- `LoopSession.__init__` signature gains `workers: int = 8`; store `self.workers = workers`.
- `_label_incremental`'s `draft_labels(...)` call gains `workers=self.workers`.
- `main()` passes `workers=settings.labeling_workers` to `LoopSession`.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/config.py src/labeling/cli.py src/labeling/webapp.py tests/test_config.py tests/test_cli.py
git commit -m "feat: LABELING_WORKERS config, --workers flag, CLI coverage summary (#1)"
```

---

### Task 4: Live abstention feed (webapp state + static UI + summary notes)

**Files:**
- Modify: `src/labeling/webapp.py` (`_reset`, `_label_incremental`, `tweak`, `state`)
- Modify: `src/labeling/summary.py` (`_coverage`)
- Modify: `src/labeling/static/index.html`
- Test: `tests/test_webapp.py`, `tests/test_summary.py`

**Interfaces:**
- Consumes: `MessageLabels.no_label_fits` / `.coverage_note` (Task 1).
- Produces: `state()["status"]["abstention"] = {"count": int, "recent": [{"text": str, "note": str}, ...]}` (recent = latest 3, newest first; present in every state, count 0 when none). `summary["coverage"]["abstained_examples"]` entries gain `"note": str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp.py` (reuse its existing session fixture pattern — synchronous runner, fake generate; give the fake's coverage branch `CoverageVerdict(no_label_fits=True, note="asks about grades")` for every message):

```python
def test_state_carries_abstention_feed():
    # build session via the file's existing helper, with an all-abstaining
    # fake generate; drive start() through review
    state = session.state()
    ab = state["status"]["abstention"]
    assert ab["count"] == len(session.labeled)
    assert ab["recent"][0]["note"] == "asks about grades"
    assert all(set(r) == {"text", "note"} for r in ab["recent"])
    assert len(ab["recent"]) <= 3


def test_tweak_clears_abstention_feed():
    # after driving a tweak (new schema version), the feed resets
    assert session.state()["status"]["abstention"] == {"count": 0,
                                                       "recent": []}
```

Adapt fixture/driver names to what `tests/test_webapp.py` already uses (it drives `LoopSession` with a synchronous `runner=lambda job: job()`).

Append to `tests/test_summary.py`, alongside its existing abstention test (which builds `MessageLabels(..., no_label_fits=True)` around line 158): give that record `coverage_note="asks about grades"` and assert:

```python
    ex = summary["coverage"]["abstained_examples"][0]
    assert ex["note"] == "asks about grades"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_webapp.py tests/test_summary.py -q`
Expected: FAIL — no `abstention` key; no `note` key.

- [ ] **Step 3: Implement session + summary**

`src/labeling/webapp.py`:
- `_reset`: add `self.abstained_count = 0` and `self.abstained_recent: list[dict] = []`.
- `_label_incremental`: in the schema-mismatch clear block and where `self.labeled`/`self.recent` are cleared, also clear both new fields. Same in `tweak()`'s clear block. Rebuild them from reused labels when resuming is unnecessary — they are display-only; but for correctness after a schema-version clear they must be zeroed.
- `_note_recent` stays; extend `on_result` inside `_label_incremental`:

```python
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
```

- `state()`: inside the `"status"` dict add

```python
                    "abstention": {"count": self.abstained_count,
                                   "recent": [dict(a) for a in
                                              self.abstained_recent]},
```

`src/labeling/summary.py` — in `_coverage`, the abstained-examples loop gains the note:

```python
            abstained_examples.append({"text": hit[0], "conv": r.chatlog_id,
                                       "note": r.coverage_note})
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_webapp.py tests/test_summary.py -q`
Expected: PASS.

- [ ] **Step 5: Static UI**

`src/labeling/static/index.html` (student text: always `textContent`, never `innerHTML` — house rule at the feed renderer):

1. Locate the working-screen feed container (`id="feed"` in the HTML body). Add a sibling immediately after it: `<div id="abstention" class="abstention hidden"></div>`. Add CSS next to the `.feed-item` rules: `.abstention { margin-top: 12px; } .abstention .head { font-weight: 600; margin-bottom: 4px; } .abstention .note { opacity: .7; font-style: italic; }`.
2. At the end of `renderWorking(state)` append:

```javascript
  const ab = state.status && state.status.abstention;
  const abEl = $("abstention");
  abEl.classList.toggle("hidden", !ab || !ab.count);
  if (ab && ab.count) {
    abEl.replaceChildren();
    const head = document.createElement("div");
    head.className = "head";
    head.textContent =
      `${ab.count} abstention${ab.count === 1 ? "" : "s"} — acts no label captures`;
    abEl.append(head);
    for (const a of ab.recent) {
      const row = document.createElement("div");
      row.className = "feed-item";
      const t = document.createElement("span");
      t.className = "msg-text";
      t.textContent = `“${a.text}”`;
      row.append(t);
      if (a.note) {
        const note = document.createElement("span");
        note.className = "note";
        note.textContent = a.note;
        row.append(note);
      }
      abEl.append(row);
    }
  }
```

3. Done screen: find the renderer that consumes `state.summary` (search `index.html` for `summary`). Where it renders `summary.coverage` (or, if it does not yet render coverage, immediately after the per-label section) add a coverage block with the same DOM style as the surrounding sections:

```javascript
  const cov = summary.coverage;
  if (cov && cov.abstained) {
    // heading: `${cov.abstained} messages (${pct}%) showed acts no label captures`
    // where pct = (cov.abstained / summary.totals.messages * 100).toFixed(0)
    // then one row per cov.abstained_examples entry: “text” + italic note,
    // built with the same textContent-only pattern as step 2.
  }
```

Follow the existing done-screen section markup exactly (this is the only place the plan defers to the file — the done screen's DOM helpers are local to it; reuse them rather than inventing parallel ones).

- [ ] **Step 6: Manual smoke test**

Run: `uv run pytest -q` (all green), then `uv run python -c "from src.labeling.webapp import create_app, LoopSession"` (imports clean). Full UI smoke happens on the next real labeling run — no student data in tests.

- [ ] **Step 7: Commit**

```bash
git add src/labeling/webapp.py src/labeling/summary.py src/labeling/static/index.html tests/test_webapp.py tests/test_summary.py
git commit -m "feat: live abstention feed and coverage report in labeling UI (#1)"
```

---

## Self-review notes

- Spec §1 prompts → Task 1; §2 hash → Task 1; §3 executor → Task 2; §4 config → Task 3; §5 abstention surfacing → Tasks 3 (CLI) + 4 (webapp); §6 tests 1–8 → Tasks 1 (1), 2 (2–6), 1 (7), 3+4 (8).
- Spec's "strictly sequential under workers=1" and "callbacks under lock" are encoded as tests, not prose.
- The golden-hash literal is intentionally a fill-in-after-implementation step — that is how the existing golden test was built (test_draft.py comment).
- Type consistency: `SingleLabelVerdict`/`CoverageVerdict`/`coverage_note`/`labeling_workers`/`workers` names match across all four tasks.
