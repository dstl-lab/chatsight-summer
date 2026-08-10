# Sequence-Grounded Labeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inject autograder/snapshot/mode sequence context into every classifier call, record mechanically-decidable facts as facets (never LLM-judged), link messages to questions via reference conventions, stratify review samples by sequence pattern, and anchor label validation to outcomes — per the approved spec `docs/superpowers/specs/2026-08-09-sequence-grounded-labeling-design.md`.

**Architecture:** DB joins live only in `src/ingest/` (rule 3): `rawlog.py` learns per-turn `mode`, `sequences.py` learns per-conversation autograder runs and snapshot-traceback flags. `sampler.py` computes all per-message sequence fields on `SampledMessage`. `draft.py` renders them into the shared prompt context (hash-visible, rule 2) and copies mechanical facets onto `MessageLabels` untouched by Gemini. Instruments (`ablation`, `distinctness`, `validation`) grow sequence axes.

**Tech Stack:** Python 3.12, pydantic, sqlalchemy (ingest only), pytest.

## Global Constraints

- Run tests with `uv run python -m pytest` (bare `uv run pytest` broken in worktrees).
- The Bash sandbox rejects command strings containing the bare word "eval" — phrase commit messages, grep patterns, and `git add` targets to avoid it (e.g. `git add -A src tests`).
- Rule 4: `user_email` never leaves SQL joins; raw notebook JSON never enters prompts, artifacts, or test fixtures; tests use invented strings only.
- Rule 2: every prompt-visible change is folded into `classifier_hash`; the two golden-hash literals in `tests/test_draft.py` are re-vintaged ONCE in Task 3 with a comment, and no other task moves them.
- Mechanical facets are facts: never sent to Gemini, never overridden by LLM output (invariant 1: disagreement rows become audit candidates, not corrections).
- All work on branch `behavioral-sequences` in /Users/minchan/github/chatsight-summer/behavioral-sequences. Never touch ChatSight or other worktrees.

---

### Task 1: Per-turn mode + ingest fetchers (autograder runs, traceback flags)

**Files:**
- Modify: `src/ingest/rawlog.py` (Turn model, `_TURNS_SQL`, `assemble_turns`)
- Modify: `src/ingest/sequences.py` (add `AutograderRun`, `fetch_autograder_runs`, `fetch_traceback_flags`)
- Test: `tests/test_rawlog.py`, `tests/test_sequences.py`

**Interfaces:**
- Consumes: existing `Turn` (fields: index, role, text, student_index, at), `_TURNS_SQL` selecting `event_type, question, response, created_at` with 4-tuple `assemble_turns`.
- Produces: `Turn.mode: str = ""` (`"tutor"` / `"chatgpt"` / `""` for tutor turns and old snapshots); `AutograderRun` dataclass `(at: datetime, grader_id: str, success: bool)`; `fetch_autograder_runs(ext_db_url, conversations, before_min=45) -> dict[str, list[AutograderRun]]` keyed by conv_id, runs sorted by `at`, covering each conversation's span plus `before_min` before and `OUTCOME_MIN` after; `fetch_traceback_flags(ext_db_url, conversations) -> dict[str, bool]` (conv_id -> at-ask snapshot contains "Traceback"; missing snapshot -> False). Both fetchers join through `user_email` **inside SQL only** and return no email field.

- [ ] **Step 1: Write the failing tests**

In `tests/test_rawlog.py`, extend the existing assemble test (read the file first; it feeds rows shaped like `_TURNS_SQL` output). The SQL row grows to 5-tuple `(event_type, question, response, created_at, mode)`:

```python
def test_student_turns_carry_mode():
    rows = [("tutor_query", "q text", None, T0, "chatgpt"),
            ("tutor_response", None, "r text", T1, None)]
    turns = assemble_turns(rows)
    assert turns[0].mode == "chatgpt"
    assert turns[1].mode == ""            # tutor turns: no mode
```

(Adapt `T0`/`T1` names to the fixtures already in the file; update every other `assemble_turns` fixture in the test module to 5-tuples with mode `None` or `"tutor"`.)

In `tests/test_sequences.py` add pure-function coverage for the new window classifier reuse — the fetchers themselves are SQL-bound and get a shape-contract test only:

```python
def test_autograder_run_ordering_contract():
    from src.ingest.sequences import AutograderRun
    r = AutograderRun(at=datetime(2026, 5, 1, 10, 0), grader_id="q1_1",
                      success=False)
    assert r.grader_id == "q1_1" and r.success is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_rawlog.py tests/test_sequences.py -q`
Expected: FAIL — `Turn` has no `mode`, 5-tuple unpack breaks, `AutograderRun` missing.

- [ ] **Step 3: Implement**

`rawlog.py`: add `mode: str = ""` to `Turn`; `_TURNS_SQL` adds `payload->>'mode' AS mode` to the SELECT; `assemble_turns` unpacks the 5-tuple and sets `mode=mode or ""` on student turns only (tutor turns always `""`).

`sequences.py` additions:

```python
@dataclass(frozen=True)
class AutograderRun:
    at: datetime
    grader_id: str
    success: bool


_RUNS_SQL = """
WITH convs AS (
  SELECT payload->>'conversation_id' AS conv_id, user_email,
         payload->>'notebook' AS notebook,
         min(created_at) AS t0, max(created_at) AS t1
  FROM events
  WHERE event_type = 'tutor_query'
    AND payload->>'conversation_id' = ANY(:conv_ids)
  GROUP BY 1, 2, 3
)
SELECT c.conv_id, a.created_at, a.payload->>'grader_id',
       a.payload->>'success'
FROM convs c
JOIN events a ON a.event_type = 'autograder_info'
  AND a.user_email = c.user_email
  AND a.payload->>'notebook' = c.notebook
  AND a.created_at BETWEEN c.t0 - make_interval(mins => :before)
                       AND c.t1 + make_interval(mins => :after)
ORDER BY c.conv_id, a.created_at
"""


def fetch_autograder_runs(ext_db_url: str, conversations,
                          before_min: int = BEFORE_MIN,
                          after_min: int = OUTCOME_MIN
                          ) -> dict[str, list[AutograderRun]]:
    """Autograder runs bracketing each conversation. user_email is used
    inside the SQL join only and never returned (rule 4)."""
    conv_ids = [c.conv_id for c in conversations]
    if not conv_ids:
        return {}
    eng = sa.create_engine(ext_db_url)
    out: dict[str, list[AutograderRun]] = {}
    with eng.connect() as c:
        for cid, at, gid, success in c.execute(
                sa.text(_RUNS_SQL), {"conv_ids": conv_ids,
                                     "before": before_min,
                                     "after": after_min}):
            out.setdefault(cid, []).append(AutograderRun(
                at=at, grader_id=gid or "", success=success == "true"))
    return out


_TRACEBACK_SQL = """
SELECT payload->>'conversation_id',
       payload->>'initial_notebook_json' LIKE '%Traceback%'
FROM events
WHERE event_type = 'tutor_notebook_info'
  AND payload->>'initial_notebook_json' IS NOT NULL
  AND payload->>'conversation_id' = ANY(:conv_ids)
"""


def fetch_traceback_flags(ext_db_url: str, conversations) -> dict[str, bool]:
    """Whether the at-ask snapshot shows an unresolved traceback. The
    LIKE runs server-side; notebook JSON never crosses the wire (rule 4)."""
    conv_ids = [c.conv_id for c in conversations]
    if not conv_ids:
        return {}
    eng = sa.create_engine(ext_db_url)
    with eng.connect() as c:
        return {cid: bool(flag) for cid, flag in
                c.execute(sa.text(_TRACEBACK_SQL), {"conv_ids": conv_ids})}
```

(`sa`, `BEFORE_MIN`, `OUTCOME_MIN`, `datetime` already imported/defined in the module — reuse them.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest -q`
Expected: full suite PASS (rawlog fixture updates included).

- [ ] **Step 5: Commit**

```bash
git add src/ingest tests/test_rawlog.py tests/test_sequences.py
git commit -m "feat: per-turn mode and sequence fetchers in ingest"
```

---

### Task 2: Question-ref extractor + per-message sequence fields in the sampler

**Files:**
- Create: `src/labeling/qref.py`
- Modify: `src/labeling/sampler.py`
- Test: `tests/test_qref.py`, `tests/test_sampler.py`

**Interfaces:**
- Consumes: `AutograderRun` (Task 1), `Turn.mode` (Task 1), existing `SampledMessage`/`stratified_sample(conversations, n, seed)`.
- Produces: `extract_question_ref(text: str) -> str` (normalized like `"q3_2"`, `""` if none); `SampledMessage` new fields `mode: str = ""`, `defected: bool = False`, `question_ref: str = ""`, `pre_pattern: str = ""` (`""`/`ask-first`/`fail-then-ask`/`pass-then-ask`), `last_run_minutes: float | None = None`, `last_run_grader: str = ""`, `last_run_success: bool | None = None`, `snapshot_traceback: bool = False`, `seq_granularity: str = ""` (`""`/`notebook`/`question`); `stratified_sample(..., runs=None, traceback_flags=None)` optional dicts keyed by conv_id — omitted ⇒ all sequence fields stay defaults (v1 snapshots unaffected). Sequence strata: messages in `fail-then-ask` conversations, `ask-first` conversations, and defection messages get stratum suffixes `"/seq-fail"`, `"/seq-askfirst"`, `"/seq-defect"` appended to the structural stratum so the round-robin fill represents them (invariant 9).

- [ ] **Step 1: Write the failing tests**

`tests/test_qref.py`:

```python
import pytest

from src.labeling.qref import extract_question_ref


@pytest.mark.parametrize("text,ref", [
    ("how do I do 3.2?", "q3_2"),
    ("stuck on question 4", "q4"),
    ("q1_10 keeps failing", "q1_10"),
    ("Q2.4.1 hint please", "q2_4_1"),
    ("is there a way to do 1.5.2 without a loop", "q1_5_2"),
    ("my groupby is broken", ""),
    ("version 3.2 of pandas", "q3_2"),   # known false positive, accepted
])
def test_extract_question_ref(text, ref):
    assert extract_question_ref(text) == ref
```

`tests/test_sampler.py` additions (the file's `CONVS` fixture builds conversations with timestamps — read it first and reuse its builders):

```python
def test_sequence_fields_computed_when_runs_provided():
    from datetime import timedelta
    from src.ingest.sequences import AutograderRun
    conv = CONVS[0]
    t0 = conv.turns[0].at
    runs = {conv.conv_id: [AutograderRun(at=t0 - timedelta(minutes=4),
                                         grader_id="q1_1", success=False)]}
    tb = {conv.conv_id: True}
    sample = stratified_sample([conv], n=50, seed=0, runs=runs,
                               traceback_flags=tb)
    m = next(s for s in sample if s.conv_id == conv.conv_id)
    assert m.pre_pattern == "fail-then-ask"
    assert m.last_run_success is False and m.last_run_grader == "q1_1"
    assert m.last_run_minutes == pytest.approx(4, abs=1)
    assert m.snapshot_traceback is True
    assert "/seq-fail" in m.stratum


def test_sequence_fields_default_without_runs():
    sample = stratified_sample(CONVS, n=10, seed=0)
    assert all(m.pre_pattern == "" and not m.defected for m in sample)


def test_defection_is_first_chatgpt_after_tutor_mode():
    conv = _conv_with_modes(["tutor", "tutor", "chatgpt", "chatgpt"])
    sample = stratified_sample([conv], n=20, seed=0, runs={}, traceback_flags={})
    flags = {m.message_index: m.defected for m in sample}
    modes = [t for t in conv.student_turns]
    assert flags[modes[2].index] is True        # the switch turn
    assert flags[modes[3].index] is False       # staying is not re-defecting
    assert flags[modes[0].index] is False
    # chatgpt-first conversations never defect
    conv2 = _conv_with_modes(["chatgpt", "chatgpt"])
    s2 = stratified_sample([conv2], n=20, seed=0, runs={}, traceback_flags={})
    assert not any(m.defected for m in s2)
```

Write the `_conv_with_modes` helper in the test module: build a `Conversation` with alternating student/tutor turns where student turn i gets `mode=modes[i]` and consecutive timestamps (copy the pattern the existing CONVS builder uses).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_qref.py tests/test_sampler.py -q`
Expected: FAIL — no `qref` module, unknown kwargs on `stratified_sample`.

- [ ] **Step 3: Implement**

`src/labeling/qref.py`:

```python
"""Deterministic question-reference extraction from student messages.
DSC 10 reference_conventions: students cite assignment items as "3.2",
"q1_10", "question 4", "1.5.2". Normalized to grader_id shape (q3_2) so
the sequence join can narrow from notebook- to question-level. Pure text
processing — no LLM, no DB. Known false positives (version numbers) are
accepted and measured, not special-cased."""
import re

_PATTERNS = [
    re.compile(r"\bq(\d+(?:[._]\d+)*)\b", re.IGNORECASE),
    re.compile(r"\bquestion\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE),
    re.compile(r"\b(\d+\.\d+(?:\.\d+)*)\b"),
]


def extract_question_ref(text: str) -> str:
    for pat in _PATTERNS:
        m = pat.search(text)
        if m:
            return "q" + m.group(1).replace(".", "_").lower()
    return ""
```

`sampler.py`: import `AutograderRun` type for annotation and `extract_question_ref`. Add the new fields to `SampledMessage` (defaults per Interfaces). Extend `stratified_sample(conversations, n, seed, runs=None, traceback_flags=None)`:

```python
def _sequence_fields(conv, turn, runs, traceback_flags):
    """Mechanical per-message sequence facts (2026-08-09 spec). Facts,
    not LLM judgments; absent data leaves defaults ("", None, False)."""
    if runs is None:
        return {}
    fields: dict = {"snapshot_traceback":
                    bool((traceback_flags or {}).get(conv.conv_id))}
    fields["mode"] = turn.mode
    ref = extract_question_ref(turn.text)
    fields["question_ref"] = ref
    conv_runs = runs.get(conv.conv_id, [])
    scoped = ([r for r in conv_runs if r.grader_id.startswith(ref)]
              if ref else conv_runs)
    fields["seq_granularity"] = ("question" if ref and scoped
                                 else "notebook")
    pool = scoped if ref and scoped else conv_runs
    prior = [r for r in pool
             if turn.at is not None and r.at <= turn.at] if turn.at else []
    if not prior:
        fields["pre_pattern"] = "ask-first"
    else:
        last = prior[-1]
        fields["pre_pattern"] = ("pass-then-ask" if last.success
                                 else "fail-then-ask")
        fields["last_run_minutes"] = (turn.at - last.at).total_seconds() / 60
        fields["last_run_grader"] = last.grader_id
        fields["last_run_success"] = last.success
    return fields


def _defection_indexes(conv) -> set[int]:
    """Turn indexes where the student first switches tutor->chatgpt."""
    out, prev = set(), ""
    for t in conv.student_turns:
        if t.mode == "chatgpt" and prev == "tutor":
            out.add(t.index)
        if t.mode:
            prev = t.mode
    return out
```

In the sampling loop: compute `seq = _sequence_fields(...)`; `defected = turn.index in _defection_indexes(conv)` (only when `runs is not None`); build the stratum as `f"{tercile}/{position}"` plus suffix `"/seq-fail"` if `pre_pattern == "fail-then-ask"`, `"/seq-askfirst"` if `ask-first`, `"/seq-defect"` if defected (apply the first matching suffix only, in that priority order, so strata stay disjoint); pass all new fields into `SampledMessage`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest -q` — full suite PASS (existing sampler tests unaffected because omitting `runs` keeps old behavior byte-identical, including strata names).

- [ ] **Step 5: Commit**

```bash
git add src/labeling/qref.py src/labeling/sampler.py tests/test_qref.py tests/test_sampler.py
git commit -m "feat: question refs and per-message sequence facts in sampling"
```

---

### Task 3: Prompt rendering + mechanical facets on MessageLabels + hash re-vintage

**Files:**
- Modify: `src/labeling/draft.py`
- Test: `tests/test_draft.py`

**Interfaces:**
- Consumes: `SampledMessage` sequence fields (Task 2).
- Produces: `_SHARED_CONTEXT` gains two lines after the latency line: `Autograder state when the student asked: {sequence}` and `Assistant mode: {mode}`; `_render_sequence(m) -> str` and `_render_mode(m) -> str`; `MessageLabels` new fields (all defaulted for old-snapshot compat): `mode: str = ""`, `defected: bool = False`, `attempted: bool | None = None`, `error_verified: bool | None = None`, `question_ref: str = ""`, `pre_pattern: str = ""`, `seq_granularity: str = ""`; `draft_labels` copies them from `SampledMessage` (attempted = `None` if `pre_pattern == ""` else `pre_pattern != "ask-first"`; error_verified = `None` when no sequence data else `snapshot_traceback or last_run_success is False`); `classifier_hash` folds a `sequence=` element; BOTH golden literals re-vintage once.

- [ ] **Step 1: Write the failing tests**

```python
def test_sequence_render_lines():
    from src.labeling.draft import _render_mode, _render_sequence
    m = _msg(pre_pattern="fail-then-ask", last_run_minutes=4.2,
             last_run_grader="q3_2", last_run_success=False,
             snapshot_traceback=True, seq_granularity="question",
             mode="chatgpt")
    s = _render_sequence(m)
    assert "4m" in s and "FAILED" in s and "q3_2" in s
    assert "traceback" in s.lower()
    assert "question-level" in s
    empty = _render_sequence(_msg())
    assert "No autograder data" in empty
    assert "plain-ChatGPT mode" in _render_mode(m)
    assert "tutor" in _render_mode(_msg(mode="tutor")).lower()
    assert "unknown" in _render_mode(_msg()).lower()


def test_mechanical_facets_copied_not_judged():
    # fake generate returns applies=True for everything; facets must come
    # from the SampledMessage, untouched by the model
    msgs = [_msg(pre_pattern="ask-first", mode="chatgpt",
                 snapshot_traceback=False)]
    out = draft_labels(msgs, SCHEMA, PROFILE, fake_generate)
    r = out[0]
    assert r.mode == "chatgpt" and r.attempted is False
    assert r.error_verified is False and r.pre_pattern == "ask-first"
    legacy = draft_labels([_msg()], SCHEMA, PROFILE, fake_generate)[0]
    assert legacy.attempted is None and legacy.error_verified is None


def test_hash_covers_sequence_rendering():
    h1 = classifier_hash(SCHEMA, "m", PROFILE)
    assert h1 != HASH_BEFORE_SEQUENCE   # vintage moved, deliberately
```

Adapt `_msg`, `SCHEMA`, `PROFILE`, `fake_generate` to the helpers already in `tests/test_draft.py` (read it first; it has message builders and a fake generate). For the golden test: run the suite once to learn the new hash value, then set BOTH golden literals to it with the comment `# re-vintaged 2026-08-09: sequence context lines are prompt-visible (rule 2)`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_draft.py -q`
Expected: FAIL — no `_render_sequence`, `MessageLabels` lacks fields.

- [ ] **Step 3: Implement**

Renderers in `draft.py` (near `_render_latency`):

```python
def _render_sequence(m: SampledMessage) -> str:
    if not m.pre_pattern:
        return "No autograder data for this conversation."
    gran = ("question-level" if m.seq_granularity == "question"
            else "notebook-level")
    if m.pre_pattern == "ask-first":
        s = f"no autograder run before this message ({gran})"
    else:
        verdict = "PASSED" if m.last_run_success else "FAILED"
        mins = (f"{m.last_run_minutes:.0f}m"
                if m.last_run_minutes is not None else "?")
        s = (f"last run {mins} before this message: {verdict} "
             f"({m.last_run_grader or 'unknown check'}, {gran})")
    if m.snapshot_traceback:
        s += "; notebook shows an unresolved traceback"
    return s


def _render_mode(m: SampledMessage) -> str:
    if m.mode == "chatgpt":
        return ("plain-ChatGPT mode — the student toggled the tutor "
                "persona off for this message")
    if m.mode == "tutor":
        return "tutor mode"
    return "unknown (older log)"
```

`_SHARED_CONTEXT`: after the latency line add exactly:

```
Autograder state when the student asked: {sequence}
Assistant mode: {mode}
```

and pass `sequence=_render_sequence(m), mode=_render_mode(m)` at both format sites (the same helper formats both prompts — find the single `.format(` call at ~line 234).

`MessageLabels`: add the seven fields with defaults per Interfaces. In `draft_labels`' per-message result assembly (where latency fields are copied, ~line 285), copy `mode`, `defected`, `question_ref`, `pre_pattern`, `seq_granularity` verbatim and derive:

```python
attempted=(None if not m.pre_pattern
           else m.pre_pattern != "ask-first"),
error_verified=(None if not m.pre_pattern
                else m.snapshot_traceback or m.last_run_success is False),
```

`classifier_hash`: append to the canonical parts (next to the latency element, ~line 322):

```python
f"sequence=prepattern+lastrun+traceback+mode,granularity=qref",
```

Then run the suite, read the new golden value from the failure output, and set both literals with the re-vintage comment.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest -q` — full suite PASS, goldens updated exactly once.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/draft.py tests/test_draft.py
git commit -m "feat: sequence context in prompts, mechanical facets, hash re-vintage"
```

---

### Task 4: Ablation strip_sequence axis

**Files:**
- Modify: `src/labeling/ablation.py`
- Test: `tests/test_ablation.py`

**Interfaces:**
- Consumes: `SampledMessage` sequence fields; existing `strip_context(m) -> SampledMessage` and `flip_stats`.
- Produces: `strip_sequence(m) -> SampledMessage` (returns a copy with `pre_pattern=""`, `last_run_minutes=None`, `last_run_grader=""`, `last_run_success=None`, `snapshot_traceback=False`, `mode=""`, `seq_granularity=""` — i.e. renders as the absent-data lines; structural context and latency untouched); the CLI gains `--axis {context,sequence}` (default `context`, preserving current behavior) choosing which stripper runs.

- [ ] **Step 1: Write the failing test**

```python
def test_strip_sequence_resets_only_sequence_fields():
    from src.labeling.ablation import strip_sequence
    m = _msg(pre_pattern="fail-then-ask", last_run_success=False,
             snapshot_traceback=True, mode="chatgpt",
             latency_seconds=30.0, latency_bucket="rapid")
    s = strip_sequence(m)
    assert s.pre_pattern == "" and s.last_run_success is None
    assert s.mode == "" and not s.snapshot_traceback
    assert s.latency_bucket == "rapid"        # latency axis untouched
    assert s.context == m.context             # structural context untouched
```

(Reuse/extend the `_msg` helper in `tests/test_ablation.py` — read it first.)

- [ ] **Step 2: Run test to verify it fails** — `uv run python -m pytest tests/test_ablation.py -q` → ImportError.

- [ ] **Step 3: Implement**

```python
def strip_sequence(m: SampledMessage) -> SampledMessage:
    """Ablate ONLY the sequence facts so their marginal effect on verdicts
    is measurable (context-awareness instrument, 2026-08-09 spec)."""
    return m.model_copy(update={
        "pre_pattern": "", "last_run_minutes": None, "last_run_grader": "",
        "last_run_success": None, "snapshot_traceback": False,
        "mode": "", "seq_granularity": ""})
```

CLI: `parser.add_argument("--axis", choices=["context", "sequence"], default="context")`; select `strip_context` or `strip_sequence` accordingly; include the axis name in the report header.

- [ ] **Step 4: Run tests** — full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/ablation.py tests/test_ablation.py
git commit -m "feat: sequence-ablation axis"
```

---

### Task 5: Mode-split reporting + outcome anchors

**Files:**
- Modify: `src/labeling/distinctness.py`, `src/eval/validation.py`
- Test: `tests/test_distinctness.py`, `tests/test_eval_validation.py`

**Interfaces:**
- Consumes: `MessageLabels.mode`, `.pre_pattern`, plus existing `distinctness_report(rows)`, `validation_table(audit, model, ceilings=None)`, `Confusion`.
- Produces: `distinctness_report(rows)` appends a "by mode" section (per-label positive counts split tutor/chatgpt/unknown) when any row has a mode; `mode_split(rows) -> dict[str, Counter]` helper. In validation: `outcome_anchor(rows, label, expected_pattern="fail-then-ask") -> dict` returning `{"label", "expected_pattern", "in_pattern", "total_positives", "concentration", "baseline"}` where concentration = share of the label's positives on messages whose `pre_pattern == expected_pattern` and baseline = that pattern's share among ALL rows; `anchor_report(rows, anchors: dict[str, str]) -> str` rendering one line per label with a `FLAG` marker when concentration < baseline (label violates its directional expectation → audit candidate, never auto-relabeled).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_distinctness.py
def test_report_splits_by_mode():
    rows = [_row({"x": True}, mode="tutor"),
            _row({"x": True}, mode="chatgpt"),
            _row({"x": False}, mode="chatgpt")]
    r = distinctness_report(rows)
    assert "by mode" in r and "chatgpt" in r
    legacy = distinctness_report([_row({"x": True})])
    assert "by mode" not in legacy          # old snapshots: no section
```

```python
# tests/test_eval_validation.py
def test_outcome_anchor_flags_violation():
    from src.eval.validation import anchor_report, outcome_anchor
    rows = ([_ml({"extract": True}, pre_pattern="fail-then-ask")] * 3
            + [_ml({"extract": True}, pre_pattern="ask-first")] * 1
            + [_ml({"extract": False}, pre_pattern="ask-first")] * 6)
    a = outcome_anchor(rows, "extract")
    assert a["in_pattern"] == 3 and a["total_positives"] == 4
    assert a["concentration"] == pytest.approx(0.75)
    assert a["baseline"] == pytest.approx(0.3)
    r = anchor_report(rows, {"extract": "fail-then-ask"})
    assert "FLAG" not in r                   # 0.75 > 0.3: anchor holds
    bad = [_ml({"extract": True}, pre_pattern="ask-first")] * 4 \
        + [_ml({"extract": False}, pre_pattern="fail-then-ask")] * 6
    assert "FLAG" in anchor_report(bad, {"extract": "fail-then-ask"})
```

Write `_row`/`_ml` helpers matching the modules' existing fixtures (read both test files first; they have MessageLabels builders to extend with the new kwargs).

- [ ] **Step 2: Run tests to verify they fail** — new functions missing.

- [ ] **Step 3: Implement**

`distinctness.py`:

```python
def mode_split(rows: list[MessageLabels]) -> dict[str, Counter]:
    out: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        for label, applied in r.labels.items():
            if applied:
                out[label][r.mode or "unknown"] += 1
    return dict(out)
```

Append to `distinctness_report` when `any(r.mode for r in rows)`: a `== by mode ==` section, one line per label: `label: tutor=N chatgpt=N unknown=N`.

`validation.py`:

```python
def outcome_anchor(rows: list[MessageLabels], label: str,
                   expected_pattern: str = "fail-then-ask") -> dict:
    """Directional sanity check (2026-08-09 spec): a label like
    answer-extraction should concentrate in fail->ask conversations.
    Violations FLAG the label for human audit — never auto-relabel
    (invariant 1)."""
    positives = [r for r in rows if r.labels.get(label)]
    in_pattern = sum(1 for r in positives
                     if r.pre_pattern == expected_pattern)
    baseline = (sum(1 for r in rows if r.pre_pattern == expected_pattern)
                / len(rows)) if rows else 0.0
    conc = in_pattern / len(positives) if positives else 0.0
    return {"label": label, "expected_pattern": expected_pattern,
            "in_pattern": in_pattern, "total_positives": len(positives),
            "concentration": conc, "baseline": baseline}


def anchor_report(rows: list[MessageLabels],
                  anchors: dict[str, str]) -> str:
    lines = ["== outcome anchors =="]
    for label, pattern in sorted(anchors.items()):
        a = outcome_anchor(rows, label, pattern)
        flag = " FLAG: below baseline — audit candidate" \
            if a["total_positives"] and a["concentration"] < a["baseline"] \
            else ""
        lines.append(
            f"  {label}: {a['in_pattern']}/{a['total_positives']} positives "
            f"in {pattern} ({a['concentration']:.0%} vs baseline "
            f"{a['baseline']:.0%}){flag}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests** — full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/distinctness.py src/eval/validation.py tests/test_distinctness.py tests/test_eval_validation.py
git commit -m "feat: mode-split distinctness and outcome-anchor checks"
```

---

### Task 6: Plumbing — CLI/webapp fetch sequence data; manifest provenance

**Files:**
- Modify: `src/labeling/cli.py`, `src/labeling/webapp.py`, `src/labeling/snapshot.py`
- Test: `tests/test_webapp.py`, `tests/test_snapshot.py`

**Interfaces:**
- Consumes: `fetch_autograder_runs` / `fetch_traceback_flags` (Task 1), `stratified_sample(..., runs, traceback_flags)` (Task 2), `BEFORE_MIN`/`OUTCOME_MIN` from `src.ingest.sequences`.
- Produces: CLI `main()` and `LoopSession` fetch runs+flags right after fetching conversations and pass them to every `stratified_sample` call; a `--no-sequence` CLI flag / `LoopSession(..., sequence: bool = True)` escape hatch (skips the two fetches; sample falls back to defaults — needed when the events table lacks autograder rows); `emit_snapshot` manifest gains `"sequence_context": {"before_min": ..., "outcome_min": ..., "enabled": bool}`; `LoopSession` fake-fetch tests inject `runs_fetch=lambda url, convs: {}` / `flags_fetch=lambda url, convs: {}` constructor hooks (defaults = the real fetchers) so hermetic tests never touch SQL.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_webapp.py
def test_session_threads_sequence_data_into_sample(tmp_path):
    seen = {}
    def fake_runs(url, convs):
        seen["runs"] = True
        return {}
    def fake_flags(url, convs):
        seen["flags"] = True
        return {}
    session = make_session(tmp_path)          # extend helper: runs_fetch/flags_fetch kwargs
    session.runs_fetch, session.flags_fetch = fake_runs, fake_flags
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert seen == {"runs": True, "flags": True}
    assert session.state()["phase"] == "review"
```

```python
# tests/test_snapshot.py — extend the existing manifest test
    assert manifest["sequence_context"] == {"before_min": 45,
                                            "outcome_min": 20,
                                            "enabled": True}
```

(Read both test files first; extend `make_session` with the two hook kwargs defaulting to the real fetchers, and pass `sequence_context` through the existing `emit_snapshot` call sites.)

- [ ] **Step 2: Run tests to verify they fail** — unknown kwargs.

- [ ] **Step 3: Implement**

- `LoopSession.__init__` gains `runs_fetch=fetch_autograder_runs`, `flags_fetch=fetch_traceback_flags`, `sequence: bool = True`. In `start()`'s job after conversations are fetched: `runs = self.runs_fetch(self.ext_db_url, convs) if self.sequence else None`; same for flags; store on the session; pass `runs=..., traceback_flags=...` to BOTH `stratified_sample` calls (review sample in `start`, mass sample in `accept`).
- `cli.py main()`: same two fetches after `fetch_conversations` (guarded by `--no-sequence`), passed to both `stratified_sample` calls.
- `snapshot.py emit_snapshot(..., sequence_context: dict | None = None)`: manifest records it (`{"enabled": False}` when None); both callers pass `{"before_min": BEFORE_MIN, "outcome_min": OUTCOME_MIN, "enabled": <flag>}`.

- [ ] **Step 4: Run tests** — full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add src/labeling/cli.py src/labeling/webapp.py src/labeling/snapshot.py tests/test_webapp.py tests/test_snapshot.py
git commit -m "feat: thread sequence data through CLI, webapp, and manifests"
```

---

### Task 7: Live smoke run + memo

**Files:** none in src; verification + a short results section appended to the spec's memo.

- [ ] **Step 1:** Full suite green: `uv run python -m pytest -q`.
- [ ] **Step 2:** With the tunnel up, run a small CLI pass (`--max-conversations 15 --sample-size 6`) with a throwaway intent; verify from the printed sample debug (add a temporary print or use the existing `_render` output) that sequence lines appear ("Autograder state when the student asked: last run …"), that mode lines vary, and that the distinctness report's mode-split section prints. Check the manifest has `sequence_context` and the new `classifier_hash`.
- [ ] **Step 3:** Run the sequence-axis ablation on that sample (`--axis sequence`) and record per-label flip rates.
- [ ] **Step 4:** Delete the throwaway snapshot (only the one this test created). Append a "first sequence-grounded run" section to `docs/2026-08-09-sequence-pilot-first-numbers.md`: coverage (% messages with autograder data, % with question_ref), flip rates, mode split. Commit + push:

```bash
git add docs/2026-08-09-sequence-pilot-first-numbers.md
git commit -m "docs: first sequence-grounded labeling run"
git push
```

---

## Self-review notes

- Spec coverage: piece 1 → Tasks 1/3/6; piece 2 → Tasks 2/3; piece 3 → Tasks 3/5; piece 4 → Task 2 (extractor + narrowing in `_sequence_fields`); piece 5 → Task 2 strata suffixes; validation win → Task 5; provenance → Tasks 3/6; live check → Task 7.
- Type consistency: `runs: dict[str, list[AutograderRun]]`, `traceback_flags: dict[str, bool]`, field names identical across Tasks 2–6 (`pre_pattern`, `last_run_minutes`, `last_run_grader`, `last_run_success`, `snapshot_traceback`, `mode`, `defected`, `question_ref`, `seq_granularity`).
- Golden hashes move exactly once (Task 3).
- Old-snapshot compatibility: every new model field defaults; omitting `runs` keeps sampler output byte-identical.
