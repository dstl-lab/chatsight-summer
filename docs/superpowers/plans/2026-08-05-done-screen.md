# Done-Screen First-Look Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare "Snapshot written" done screen with the v4 analysis screen: ink hero with the instructor's intent, per-label distribution with an evidence message under each bar, one annotated trend line, and a margin record column.

**Architecture:** A new pure module `src/labeling/summary.py` computes a JSON-ready summary from what `LoopSession` already holds (`conversations`, `labeled`, `schema`) — no DB, no snapshot reads, nothing written to disk. The accept job stores it on the session after the snapshot is written; `/api/state` exposes it only in `done`; a small `GET /api/examples` endpoint serves drill-in resampling. The frontend rebuilds only the done section of `index.html`.

**Tech Stack:** Python 3.12 (stdlib only — `random`, `collections`, `itertools`, `datetime`), FastAPI, pytest, vanilla JS/CSS.

**Spec:** `docs/2026-08-05-labeling-done-screen.md`. Visual reference: `.superpowers/brainstorm/11805-1785995509/content/done-screen-v4.html`.

## Global Constraints

- Student text rendered with `textContent` only, never `innerHTML` (CLAUDE.md rule 4).
- Everything computed in memory; nothing new written to disk; no DB access from summary code.
- All screen prose is template-assembled from computed fields — no generated sentences, no reliability or learning claims (invariants 5/8). The caveat block ships verbatim: "Drafted labels — descriptive counts, not audited measurements. Phase 0 owns reliability."
- No label-specific copy hardcoded (no special-casing "quiet exit" or any label name).
- Example sampling is seeded-random over a label's positives — never top-N / most-confident.
- Identity palette: exactly 6 fixed hues assigned in schema order; > 6 labels → all marks fall back to ink `#1b2530`, identity stays textual. Never cycle hues.
- Tests hermetic; run with `.venv/bin/python -m pytest tests/ -q` from repo root (`python` is not on PATH).
- Branch: work happens on `done-screen` (stacked on `ui-improvements`; do not touch `main` or reopen PR #2's commits).

---

### Task 1: summary core — lookup, totals, per-label distribution, seeded examples

**Files:**
- Create: `src/labeling/summary.py`
- Create: `tests/test_summary.py`

**Interfaces:**
- Produces (consumed by Tasks 2–3):
  - `_message_lookup(conversations) -> dict[tuple[int, int], tuple[str, Conversation]]` — `(chatlog_id, turn.index) -> (student text, conversation)`.
  - `conversation_week(conv, earliest) -> int | None` — `None` when either date is `None`.
  - `sample_examples(conversations, labeled, label, n, seed) -> list[dict]` — each `{"text": str, "rationale": str, "conv": int, "week": int | None}`, seeded-random over that label's positives.
  - `compute_summary(conversations, labeled, schema, seed) -> dict` — this task fills `"totals"` and `"per_label"`; Task 2 adds the rest (the function exists now, with the other keys set to `None`/empty).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_summary.py`:

```python
"""Hermetic tests for the done-screen summary. All text invented; no student
data. Conversations get synthetic started_at dates so week binning is testable
(the shared CONVS fixture is undated on purpose)."""
from datetime import datetime, timedelta

from src.ingest.rawlog import Conversation, Turn
from src.labeling.draft import MessageLabels
from src.labeling.summary import compute_summary, sample_examples


def _conv(conv_id: str, chatlog_id: int, n_student: int,
          started_at: datetime | None) -> Conversation:
    turns = []
    for i in range(n_student):
        turns.append(Turn(index=2 * i, role="student",
                          text=f"{conv_id} q{i}", student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"{conv_id} a{i}"))
    return Conversation(conv_id=conv_id, chatlog_id=chatlog_id, notebook=None,
                        started_at=started_at, turns=turns)


T0 = datetime(2026, 4, 6)
CONVS = [
    _conv("a", 1, 2, T0),                       # week 0
    _conv("b", 2, 3, T0 + timedelta(days=8)),   # week 1
    _conv("c", 3, 2, T0 + timedelta(days=22)),  # week 3
    _conv("d", 4, 1, None),                     # undated
]


def _ml(chatlog_id: int, message_index: int, **labels: bool) -> MessageLabels:
    names = ["confused", "frustrated"]
    full = {n: labels.get(n, False) for n in names}
    return MessageLabels(chatlog_id=chatlog_id, message_index=message_index,
                        labels=full,
                        rationales={n: f"r-{n}" for n in full})


LABELED = [
    _ml(1, 0, confused=True),
    _ml(1, 2, confused=True, frustrated=True),
    _ml(2, 0),
    _ml(2, 2, frustrated=True),
    _ml(2, 4),
    _ml(3, 0, confused=True),
    _ml(3, 2),
    _ml(4, 0),
]


class FakeLabel:
    def __init__(self, name): self.name = name


class FakeSchema:
    labels = [FakeLabel("confused"), FakeLabel("frustrated")]


def test_totals():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    assert s["totals"] == {
        "messages": 8, "conversations": 4, "with_label": 4,
        "labels_per_labeled": 1.2,   # 5 applications / 4 labeled messages
    }


def test_per_label_counts_shares_and_example_shape():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    assert [p["name"] for p in s["per_label"]] == ["confused", "frustrated"]
    confused = s["per_label"][0]
    assert confused["count"] == 3
    assert confused["share"] == 3 / 8
    ex = confused["example"]
    assert set(ex) == {"text", "rationale", "conv", "week"}
    assert ex["rationale"] == "r-confused"
    assert ex["text"].endswith(("q0", "q1", "q2"))  # a real student text


def test_per_label_example_none_when_label_never_applies():
    class S:
        labels = [FakeLabel("confused"), FakeLabel("never")]
    labeled = [MessageLabels(chatlog_id=1, message_index=0,
                             labels={"confused": True, "never": False},
                             rationales={"confused": "r", "never": "r"})]
    s = compute_summary(CONVS, labeled, S(), seed=0)
    never = s["per_label"][1]
    assert never["count"] == 0 and never["example"] is None


def test_sample_examples_seeded_and_random_not_topn():
    a = sample_examples(CONVS, LABELED, "confused", n=2, seed=7)
    b = sample_examples(CONVS, LABELED, "confused", n=2, seed=7)
    c = sample_examples(CONVS, LABELED, "confused", n=2, seed=8)
    assert a == b                      # same seed -> same sample
    assert len(a) == 2
    assert a != c or sample_examples(CONVS, LABELED, "confused", n=3, seed=8) \
        != sample_examples(CONVS, LABELED, "confused", n=3, seed=7)
    # n larger than the positive pool returns all positives, no repeats
    all_ex = sample_examples(CONVS, LABELED, "confused", n=99, seed=0)
    assert len(all_ex) == 3
    assert len({e["text"] for e in all_ex}) == 3


def test_sample_examples_week_from_conversation_date():
    ex = sample_examples(CONVS, LABELED, "frustrated", n=99, seed=0)
    weeks = {e["conv"]: e["week"] for e in ex}
    assert weeks[1] == 0 and weeks[2] == 1   # chatlog 1 wk0, chatlog 2 wk1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_summary.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.labeling.summary'`

- [ ] **Step 3: Implement `src/labeling/summary.py`**

```python
"""First-look descriptive summary of a mass-label run (2026-08-05 done-screen
memo). Pure functions over in-memory session data — no DB, no snapshot reads,
nothing written to disk. Every number here is a drafted-label count: the UI
must present them as descriptive only (invariants 5/8)."""
import random
from collections import Counter
from itertools import combinations

from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels


def _message_lookup(conversations: list[Conversation]
                    ) -> dict[tuple[int, int], tuple[str, Conversation]]:
    out: dict[tuple[int, int], tuple[str, Conversation]] = {}
    for conv in conversations:
        for turn in conv.student_turns:
            out[(conv.chatlog_id, turn.index)] = (turn.text, conv)
    return out


def _earliest_start(conversations: list[Conversation]):
    dates = [c.started_at for c in conversations if c.started_at is not None]
    return min(dates) if dates else None


def conversation_week(conv: Conversation, earliest) -> int | None:
    if conv.started_at is None or earliest is None:
        return None
    return (conv.started_at - earliest).days // 7


def _example_dict(text: str, conv: Conversation, rationale: str,
                  earliest) -> dict:
    return {"text": text, "rationale": rationale, "conv": conv.chatlog_id,
            "week": conversation_week(conv, earliest)}


def sample_examples(conversations: list[Conversation],
                    labeled: list[MessageLabels], label: str,
                    n: int, seed: int) -> list[dict]:
    """Seeded-random sample of a label's positives — deliberately never
    top-N/most-confident (typical evidence, not cherry-picked)."""
    lookup = _message_lookup(conversations)
    earliest = _earliest_start(conversations)
    positives = [r for r in labeled if r.labels.get(label)]
    rng = random.Random(seed)
    rng.shuffle(positives)
    out = []
    for r in positives[:n]:
        hit = lookup.get((r.chatlog_id, r.message_index))
        if hit is None:
            continue
        text, conv = hit
        out.append(_example_dict(text, conv, r.rationales.get(label, ""),
                                 earliest))
    return out


def compute_summary(conversations: list[Conversation],
                    labeled: list[MessageLabels], schema,
                    seed: int) -> dict:
    with_label = [r for r in labeled if any(r.labels.values())]
    applications = sum(sum(r.labels.values()) for r in labeled)
    totals = {
        "messages": len(labeled),
        "conversations": len(conversations),
        "with_label": len(with_label),
        "labels_per_labeled": (round(applications / len(with_label), 1)
                               if with_label else 0.0),
    }
    per_label = []
    for i, l in enumerate(schema.labels):
        count = sum(1 for r in labeled if r.labels.get(l.name))
        examples = sample_examples(conversations, labeled, l.name,
                                   n=1, seed=seed + i)
        per_label.append({
            "name": l.name,
            "count": count,
            "share": (count / len(labeled)) if labeled else 0.0,
            "example": examples[0] if examples else None,
        })
    return {
        "totals": totals,
        "per_label": per_label,
        "weekly": None,        # Task 2
        "top_pairs": [],       # Task 2
        "coverage": None,      # Task 2
        "largest_jump": None,  # Task 2
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_summary.py -q`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/labeling/summary.py tests/test_summary.py
git commit -m "feat: summary core — totals, per-label distribution, seeded evidence sampling"
```

---

### Task 2: summary figures — weekly shares, top pairs, coverage, largest jump

**Files:**
- Modify: `src/labeling/summary.py`
- Test: `tests/test_summary.py`

**Interfaces:**
- Consumes: Task 1's `_message_lookup`, `conversation_week`, `_earliest_start`, `compute_summary`.
- Produces (final summary shape, consumed by Tasks 3–4):
  - `"weekly"`: `{"weeks": [int, ...], "series": {label: [float, ...]}, "undated": int}` or `None` (omitted when the dated span is < 3 distinct weeks or fewer than 2 labels have any positives).
  - `"top_pairs"`: up to 3 of `{"a": str, "b": str, "share": float}` (share of all labeled messages carrying both), most frequent first; pairs with zero count never appear.
  - `"coverage"`: `{"bins": [int]*16, "zero_conversations": int, "zero_examples": [{"text", "conv"}]}` — bin index = min(labeled-message-with-≥1-label count, 15); `zero_examples` = up to 5 seeded-sampled first student messages of zero-label conversations.
  - `"largest_jump"`: `{"label": str, "week": int, "delta": float}` (largest absolute week-over-week share change, signed delta) or `None` when `"weekly"` is `None`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_summary.py`)

```python
def test_weekly_series_and_undated_count():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    w = s["weekly"]
    assert w is not None
    assert w["weeks"] == [0, 1, 3]
    assert w["undated"] == 1                      # conv d has no date
    # week 0 = conv a: 2 messages, confused on both -> share 1.0
    assert w["series"]["confused"] == [1.0, 0.0, 0.5]
    # week 1 = conv b: 3 messages, frustrated on one -> 1/3
    assert abs(w["series"]["frustrated"][1] - 1 / 3) < 1e-9


def test_weekly_none_when_span_too_short():
    convs = [_conv("a", 1, 2, T0), _conv("b", 2, 3, T0 + timedelta(days=8))]
    labeled = [r for r in LABELED if r.chatlog_id in (1, 2)]
    s = compute_summary(convs, labeled, FakeSchema(), seed=0)
    assert s["weekly"] is None and s["largest_jump"] is None


def test_top_pairs():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    assert s["top_pairs"] == [
        {"a": "confused", "b": "frustrated", "share": 1 / 8}]


def test_coverage_bins_zero_conversations_and_examples():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    cov = s["coverage"]
    # conv a: 2 labeled msgs, b: 1, c: 1, d: 0
    assert cov["bins"][0] == 1 and cov["bins"][1] == 2 and cov["bins"][2] == 1
    assert sum(cov["bins"]) == 4
    assert cov["zero_conversations"] == 1
    assert cov["zero_examples"] == [{"text": "d q0", "conv": 4}]


def test_coverage_binning_caps_at_15():
    conv = _conv("big", 9, 20, T0)
    labeled = [_ml(9, 2 * i, confused=True) for i in range(20)]
    s = compute_summary([conv], labeled, FakeSchema(), seed=0)
    assert s["coverage"]["bins"][15] == 1


def test_largest_jump():
    s = compute_summary(CONVS, LABELED, FakeSchema(), seed=0)
    # confused: [1.0, 0.0, 0.5] -> biggest |delta| is week 1, -1.0
    assert s["largest_jump"] == {"label": "confused", "week": 1, "delta": -1.0}
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `.venv/bin/python -m pytest tests/test_summary.py -q`
Expected: new tests FAIL (`weekly` is None / `top_pairs` empty / `coverage` is None); Task 1 tests still pass.

- [ ] **Step 3: Implement** — replace the `return` block of `compute_summary` and add helpers:

```python
def _weekly(conversations, labeled, label_names):
    earliest = _earliest_start(conversations)
    week_of = {c.chatlog_id: conversation_week(c, earliest)
               for c in conversations}
    undated = sum(1 for c in conversations if c.started_at is None)
    msgs_by_week: dict[int, list[MessageLabels]] = {}
    for r in labeled:
        w = week_of.get(r.chatlog_id)
        if w is not None:
            msgs_by_week.setdefault(w, []).append(r)
    weeks = sorted(msgs_by_week)
    labels_with_data = [n for n in label_names
                        if any(r.labels.get(n) for r in labeled)]
    if len(weeks) < 3 or len(labels_with_data) < 2:
        return None
    series = {}
    for name in label_names:
        series[name] = [
            sum(1 for r in msgs_by_week[w] if r.labels.get(name))
            / len(msgs_by_week[w])
            for w in weeks
        ]
    return {"weeks": weeks, "series": series, "undated": undated}


def _top_pairs(labeled, limit=3):
    counts: Counter = Counter()
    for r in labeled:
        on = sorted(k for k, v in r.labels.items() if v)
        counts.update(combinations(on, 2))
    return [{"a": a, "b": b, "share": c / len(labeled)}
            for (a, b), c in counts.most_common(limit) if c > 0]


def _coverage(conversations, labeled, seed):
    labeled_count = Counter()
    for r in labeled:
        if any(r.labels.values()):
            labeled_count[r.chatlog_id] += 1
    bins = [0] * 16
    zero_convs = []
    for c in conversations:
        n = labeled_count.get(c.chatlog_id, 0)
        bins[min(n, 15)] += 1
        if n == 0:
            zero_convs.append(c)
    rng = random.Random(seed)
    rng.shuffle(zero_convs)
    zero_examples = [{"text": c.student_turns[0].text, "conv": c.chatlog_id}
                     for c in zero_convs[:5] if c.student_turns]
    return {"bins": bins, "zero_conversations": len(zero_convs),
            "zero_examples": zero_examples}


def _largest_jump(weekly):
    if weekly is None:
        return None
    best = None
    for name, values in weekly["series"].items():
        for i in range(1, len(values)):
            delta = values[i] - values[i - 1]
            if best is None or abs(delta) > abs(best[2]):
                best = (name, weekly["weeks"][i], delta)
    if best is None:
        return None
    return {"label": best[0], "week": best[1], "delta": round(best[2], 4)}
```

and in `compute_summary`:

```python
    label_names = [l.name for l in schema.labels]
    weekly = _weekly(conversations, labeled, label_names)
    return {
        "totals": totals,
        "per_label": per_label,
        "weekly": weekly,
        "top_pairs": _top_pairs(labeled),
        "coverage": _coverage(conversations, labeled, seed),
        "largest_jump": _largest_jump(weekly),
    }
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/summary.py tests/test_summary.py
git commit -m "feat: summary figures — weekly shares, top pairs, coverage, largest jump"
```

---

### Task 3: session wiring — summary at done, /api/examples endpoint

**Files:**
- Modify: `src/labeling/webapp.py`
- Test: `tests/test_webapp.py`

**Interfaces:**
- Consumes: `compute_summary(conversations, labeled, schema, seed)` and `sample_examples(conversations, labeled, label, n, seed)` from Tasks 1–2.
- Produces: `state()["summary"]` — the summary dict in `done`, `None` in every other phase; `GET /api/examples?label=<name>&n=<int>&seed=<int>` → `{"examples": [...]}` (200 in `done`; 409 via `PhaseError` otherwise; 404 for a label not in the schema).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_webapp.py`)

```python
def test_summary_only_in_done(tmp_path):
    session = make_session(tmp_path)
    assert session.state()["summary"] is None
    session.start("intent", max_conversations=4, sample_size=4, seed=0)
    assert session.state()["summary"] is None          # review
    session.accept()
    s = session.state()
    assert s["phase"] == "done"
    summary = s["summary"]
    assert summary["totals"]["messages"] == 13         # corpus of CONVS[:4]
    assert [p["name"] for p in summary["per_label"]] == ["label-v1"]
    assert summary["coverage"] is not None
    session.quit()
    assert session.state()["summary"] is None          # reset clears it


def test_examples_endpoint(tmp_path):
    session = make_session(tmp_path)
    client = TestClient(create_app(session))
    assert client.get("/api/examples", params={"label": "x"}).status_code == 409
    client.post("/api/start", json={"intent": "i", "max_conversations": 4,
                                    "sample_size": 4})
    client.post("/api/accept")
    assert client.get("/api/state").json()["phase"] == "done"
    r = client.get("/api/examples",
                   params={"label": "label-v1", "n": 3, "seed": 1})
    assert r.status_code == 200
    ex = r.json()["examples"]
    assert 0 <= len(ex) <= 3
    assert all(set(e) == {"text", "rationale", "conv", "week"} for e in ex)
    assert client.get("/api/examples",
                      params={"label": "nope"}).status_code == 404
```

Note: the fake generate's verdicts apply label "x", which `_validated_verdicts`
drops — every `label-v1` value is False, so `examples` may be empty; the test
asserts shape, not count.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_webapp.py -q`
Expected: FAIL — `KeyError: 'summary'`, then 404 vs 409 mismatches.

- [ ] **Step 3: Implement in `src/labeling/webapp.py`**

Import at top: `from src.labeling.summary import compute_summary, sample_examples`.

In `_reset`, add:

```python
        self.summary: dict | None = None
```

In `accept()`'s job, after `self._end_step("snapshot", ...)` replace the final locked block with:

```python
            summary = compute_summary(self.conversations, self.labeled,
                                      self.schema, seed=self.seed)
            with self._lock:
                self.snapshot_path = path
                self.summary = summary
                self.phase = "done"
```

In `state()`'s return dict, add alongside `"snapshot_path"`:

```python
                "summary": self.summary if self.phase == "done" else None,
```

In `create_app`, add (with `from fastapi import HTTPException` in the import line):

```python
    @app.get("/api/examples")
    def examples(label: str, n: int = 5, seed: int = 0) -> dict:
        session._require("done")
        if label not in {l.name for l in session.schema.labels}:
            raise HTTPException(status_code=404,
                                detail=f"label {label!r} not in schema")
        return {"examples": sample_examples(session.conversations,
                                            session.labeled, label,
                                            n=n, seed=seed)}
```

(`_require` raises `PhaseError` → the existing handler returns 409.)

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/webapp.py tests/test_webapp.py
git commit -m "feat: expose run summary at done + /api/examples resampling endpoint"
```

---

### Task 4: frontend — the v4 done screen

**Files:**
- Modify: `src/labeling/static/index.html` (done section markup, CSS additions, `render` done-branch JS)

**Interfaces:**
- Consumes: `state.summary` (shape from Tasks 1–2), `state.schema.{version_id,intent,labels[]}`, `state.provenance.{fetched,total,excluded}`, `state.snapshot_path`, `GET /api/examples?label=&n=&seed=`.

The visual reference is `.superpowers/brainstorm/11805-1785995509/content/done-screen-v4.html` — match it. All student text via `textContent`. Numbers via `font-variant-numeric: tabular-nums`.

- [ ] **Step 1: Validate the identity palette**

Starting hues (from the approved mockup): `#3d64ad, #b25a3a, #7d549b, #2b7f6e, #5d6b7c, #8f7a2e`. Run the dataviz validator for both surfaces (repo root; node lives in nvm):

```bash
export PATH="$HOME/.nvm/versions/node/v22.21.1/bin:$PATH"
node /private/tmp/claude-501/bundled-skills/2.1.223/a7b68c780839b30351bc4ff458ab1b84/dataviz/scripts/validate_palette.js \
  "#3d64ad,#b25a3a,#7d549b,#2b7f6e,#5d6b7c,#8f7a2e" --mode light
node /private/tmp/claude-501/bundled-skills/2.1.223/a7b68c780839b30351bc4ff458ab1b84/dataviz/scripts/validate_palette.js \
  "#3d64ad,#b25a3a,#7d549b,#2b7f6e,#5d6b7c,#8f7a2e" --mode dark
```

If any check FAILs, adjust the failing hue minimally per the validator's output until both modes pass (keep hue families: blue, rust, plum, teal, slate, olive). Record the final six hexes in the commit message; use them in Step 3's `PALETTE`.

- [ ] **Step 2: Replace the done-section markup**

```html
<section id="screen-done" class="hidden">
  <div class="plate">
    <div class="plate-stamp" id="done-stamp"></div>
    <div class="plate-intent" id="done-intent"></div>
    <div class="plate-lede" id="done-lede"></div>
  </div>
  <div class="done-layout">
    <div class="answer">
      <p class="answer-intro">Where the labels landed — one sampled message
        under each. Click a label to read more; examples are drawn at random,
        never the most confident hits.</p>
      <div id="done-labels"></div>
      <div id="done-trend" class="trend hidden"></div>
    </div>
    <div class="marginrec">
      <div class="ledger" id="done-ledger"></div>
      <div class="note">Drafted labels — descriptive counts, not audited
        measurements. Phase 0 owns reliability.</div>
      <div id="done-pairs"></div>
      <div id="done-coverage"></div>
      <div class="next">Next: add this run to <code>snapshots.md</code>.</div>
      <button id="btn-reset-done">Start a new run</button>
    </div>
  </div>
</section>
```

(The old `#snapshot-path` element goes away; keep the `btn-reset-done` id so the existing listener still works.)

- [ ] **Step 3: Add CSS** (append to the existing `<style>`; keep every existing rule)

```css
  /* done screen */
  .plate { background: #1b2530; color: #e9edf2; border-radius: 8px;
    padding: 1.5rem 1.75rem 1.4rem; margin-bottom: 1.4rem; }
  .plate-stamp { font-family: ui-monospace, monospace; font-size: .7rem;
    letter-spacing: .08em; opacity: .6; text-transform: uppercase; }
  .plate-intent { font-size: 1.5rem; font-weight: 700; line-height: 1.2;
    max-width: 36rem; margin: .7rem 0 .55rem; }
  .plate-lede { font-size: .92rem; opacity: .75; max-width: 40rem; }
  .done-layout { display: grid; grid-template-columns: 1fr 15rem;
    gap: 2.5rem; font-variant-numeric: tabular-nums; }
  @media (max-width: 44rem) { .done-layout { grid-template-columns: 1fr; } }
  .answer-intro { font-size: .9rem; opacity: .75; max-width: 38rem;
    margin-bottom: 1.1rem; }
  .lbl-row { margin-bottom: 1.35rem; cursor: pointer; }
  .lbl-row:focus-visible { outline: 2px solid #4472c4; outline-offset: 3px;
    border-radius: 4px; }
  .lbl-head { display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: .2rem; }
  .lbl-name { font-size: .95rem; font-weight: 650; }
  .lbl-count { font-family: ui-monospace, monospace; font-size: .85rem;
    opacity: .75; }
  .lbl-bar { background: rgba(128,128,128,.11); border-radius: 3px;
    height: 16px; margin-bottom: .45rem; }
  .lbl-bar > div { height: 100%; border-radius: 3px 4px 4px 3px; width: 0; }
  .lbl-example { font-size: .84rem; padding-left: .9rem;
    border-left: 2px solid; }
  .lbl-example .quote { font-style: italic; opacity: .85; }
  .lbl-example .attr { font-size: .75rem; opacity: .65; }
  .lbl-more { margin: .4rem 0 0 .9rem; }
  .trend { border-top: 1px solid rgba(128,128,128,.22); padding-top: 1rem; }
  .trend-caption { font-size: .88rem; margin-bottom: .35rem; }
  .marginrec { font-size: .8rem;
    border-left: 1px solid rgba(128,128,128,.22); padding-left: 1.25rem; }
  @media (max-width: 44rem) { .marginrec { border-left: 0; padding-left: 0;
    border-top: 1px solid rgba(128,128,128,.22); padding-top: 1rem; } }
  .ledger { font-family: ui-monospace, monospace; font-size: .72rem;
    line-height: 1.7; opacity: .75; margin-bottom: 1.25rem;
    white-space: pre; }
  .marginrec .note { padding: .5rem .65rem; background: rgba(184,134,11,.08);
    border-left: 2px solid #b8860b; font-size: .76rem;
    margin-bottom: 1.25rem; }
  .pairs { font-family: ui-monospace, monospace; font-size: .74rem;
    line-height: 1.8; margin-bottom: 1.25rem; white-space: pre; }
  .mr-head { opacity: .8; margin-bottom: .35rem; }
  .cov-note { font-size: .74rem; opacity: .7; margin-bottom: 1.5rem; }
  .cov-note a { cursor: pointer; text-decoration: underline; }
  .next { opacity: .8; margin: 0 0 .5rem; }
  #btn-reset-done { background: #1b2530; color: #e9edf2; border: none;
    border-radius: 6px; }
  @media (prefers-reduced-motion: no-preference) {
    .lbl-bar > div { transition: width 220ms ease-out; }
  }
```

- [ ] **Step 4: Add the done-render JS** (replace the `done` branch of `render` and add helpers below `renderWorking`)

```js
const PALETTE = ["#3d64ad", "#b25a3a", "#7d549b", "#2b7f6e", "#5d6b7c",
                 "#8f7a2e"];  // final hexes from the validator run
const INK = "#1b2530";
const colorFor = (i, total) => total > PALETTE.length ? INK
                                                      : PALETTE[i];
const pct = (x) => Math.round(x * 100) + "%";
let doneRendered = null;   // schema version we last rendered (render once)

function exampleNode(ex, color) {
  const div = document.createElement("div");
  div.className = "lbl-example";
  div.style.borderLeftColor = color;
  const q = document.createElement("span");
  q.className = "quote";
  q.textContent = `“${ex.text}”`;   // student text: textContent only
  const attr = document.createElement("span");
  attr.className = "attr";
  attr.textContent = ` — conv #${ex.conv}` +
    (ex.week === null ? "" : `, week ${ex.week + 1}`);
  const rat = document.createElement("div");
  rat.className = "attr";
  rat.textContent = ex.rationale;
  div.append(q, attr, rat);
  return div;
}

async function expandLabel(row, name, color) {
  const seed = Math.floor(Math.random() * 1e6);
  const r = await fetch(`/api/examples?label=${encodeURIComponent(name)}` +
                        `&n=5&seed=${seed}`);
  if (!r.ok) return;
  const box = row.querySelector(".lbl-more");
  box.replaceChildren();
  for (const ex of (await r.json()).examples)
    box.append(exampleNode(ex, color));
  const re = document.createElement("a");
  re.className = "attr";
  re.style.cursor = "pointer";
  re.textContent = "resample";
  re.onclick = (e) => { e.stopPropagation(); expandLabel(row, name, color); };
  box.append(re);
}

function renderTrend(summary) {
  const el = $("done-trend");
  const w = summary.weekly, jump = summary.largest_jump;
  el.classList.toggle("hidden", !w || !jump);
  if (!w || !jump) return;
  el.replaceChildren();
  const total = summary.per_label.length;
  const idx = summary.per_label.findIndex((p) => p.name === jump.label);
  const color = colorFor(idx, total);
  const cap = document.createElement("div");
  cap.className = "trend-caption";
  const nm = document.createElement("span");
  nm.style.color = color; nm.style.fontWeight = "650";
  nm.textContent = jump.label;
  const rest = document.createElement("span");
  const sign = jump.delta >= 0 ? "+" : "−";
  rest.textContent = ` by course week — largest change: week ${jump.week + 1},`
    + ` ${sign}${Math.round(Math.abs(jump.delta) * 100)}pts`;
  rest.style.opacity = ".75";
  cap.append(nm, rest);
  el.append(cap);
  el.append(trendSvg(w, jump.label, color));
}

function trendSvg(w, label, color) {
  const W = 560, H = 90, PAD = 8, BASE = 74;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.style.width = "100%"; svg.style.height = "auto";
  const xs = w.weeks.map((_, i) =>
    PAD + i * (W - 2 * PAD) / Math.max(1, w.weeks.length - 1));
  const vals = w.series[label];
  const max = Math.max(...vals, 0.01);
  const ys = vals.map((v) => BASE - v / max * 60);
  const axis = document.createElementNS(svg.namespaceURI, "line");
  axis.setAttribute("x1", PAD); axis.setAttribute("x2", W - PAD);
  axis.setAttribute("y1", BASE); axis.setAttribute("y2", BASE);
  axis.setAttribute("stroke", "rgba(128,128,128,.25)");
  svg.append(axis);
  const line = document.createElementNS(svg.namespaceURI, "polyline");
  line.setAttribute("points", xs.map((x, i) => `${x},${ys[i]}`).join(" "));
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", color);
  line.setAttribute("stroke-width", "2.2");
  svg.append(line);
  const t0 = document.createElementNS(svg.namespaceURI, "text");
  t0.setAttribute("x", PAD); t0.setAttribute("y", H - 4);
  t0.setAttribute("font-size", "9"); t0.setAttribute("fill", "currentColor");
  t0.setAttribute("opacity", ".5");
  t0.textContent = `wk ${w.weeks[0] + 1}`;
  const t1 = document.createElementNS(svg.namespaceURI, "text");
  t1.setAttribute("x", W - 40); t1.setAttribute("y", H - 4);
  t1.setAttribute("font-size", "9"); t1.setAttribute("fill", "currentColor");
  t1.setAttribute("opacity", ".5");
  t1.textContent = `wk ${w.weeks[w.weeks.length - 1] + 1}`;
  svg.append(t0, t1);
  return svg;
}

function renderDone(state) {
  const s = state.summary;
  if (!s || doneRendered === state.schema.version_id) return;
  doneRendered = state.schema.version_id;

  const snap = (state.snapshot_path || "").split("/").slice(-1)[0];
  $("done-stamp").textContent =
    `run complete · snapshot ${snap} · schema ${state.schema.version_id}`;
  $("done-intent").textContent = `“${state.schema.intent}”`;
  const t = s.totals;
  const rare = [...s.per_label].sort((a, b) => a.count - b.count)[0];
  $("done-lede").textContent =
    `${t.messages.toLocaleString()} messages from ${t.conversations} ` +
    `conversations, labeled against schema ${state.schema.version_id}. ` +
    `${t.with_label.toLocaleString()} carry at least one label — ` +
    `${t.labels_per_labeled} each, on average. Rarest: ${rare.name}, ` +
    `${rare.count.toLocaleString()} messages.`;

  const total = s.per_label.length;
  const labels = $("done-labels");
  labels.replaceChildren();
  s.per_label.forEach((p, i) => {
    const color = colorFor(i, total);
    const row = document.createElement("div");
    row.className = "lbl-row";
    row.tabIndex = 0;
    const head = document.createElement("div");
    head.className = "lbl-head";
    const nm = document.createElement("span");
    nm.className = "lbl-name"; nm.style.color = color;
    nm.textContent = p.name;
    const ct = document.createElement("span");
    ct.className = "lbl-count";
    ct.textContent = `${p.count.toLocaleString()} · ${pct(p.share)}`;
    head.append(nm, ct);
    const bar = document.createElement("div");
    bar.className = "lbl-bar";
    const fill = document.createElement("div");
    fill.style.background = color;
    bar.append(fill);
    row.append(head, bar);
    if (p.example) row.append(exampleNode(p.example, color));
    const more = document.createElement("div");
    more.className = "lbl-more";
    row.append(more);
    const open = () => expandLabel(row, p.name, color);
    row.addEventListener("click", open);
    row.addEventListener("keydown",
      (e) => { if (e.key === "Enter" || e.key === " ") open(); });
    labels.append(row);
    const maxCount = Math.max(...s.per_label.map((q) => q.count), 1);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        fill.style.width = pct(p.count / maxCount);  // bars scale to the max
      }));
  });

  renderTrend(s);

  const prov = state.provenance || {};
  $("done-ledger").textContent =
    `schema     ${state.schema.version_id} · ${total} labels\n` +
    `corpus     ${t.conversations} conv · ${t.messages.toLocaleString()} msg\n` +
    `excluded   ${prov.excluded ?? "?"} conversations\n` +
    `snapshot   ${state.snapshot_path || ""}`;

  const pairs = $("done-pairs");
  pairs.replaceChildren();
  if (s.top_pairs.length) {
    const h = document.createElement("div");
    h.className = "mr-head";
    h.textContent = "Pairs that land together most:";
    const list = document.createElement("div");
    list.className = "pairs";
    list.textContent = s.top_pairs.map((p) =>
      `${p.a} × ${p.b}  ${pct(p.share)}`).join("\n");
    pairs.append(h, list);
  }

  const cov = $("done-coverage");
  cov.replaceChildren();
  const ch = document.createElement("div");
  ch.className = "mr-head";
  ch.textContent = "Coverage:";
  cov.append(ch, coverageSvg(s.coverage));
  const note = document.createElement("div");
  note.className = "cov-note";
  note.textContent = `Labels per conversation. ` +
    `${s.coverage.zero_conversations} conversations carry none`;
  if (s.coverage.zero_examples.length) {
    note.textContent += " — ";
    const read = document.createElement("a");
    read.textContent = "read them";
    read.onclick = () => {
      const box = document.createElement("div");
      for (const z of s.coverage.zero_examples)
        box.append(exampleNode(
          {text: z.text, rationale: "", conv: z.conv, week: null}, INK));
      note.after(box);
      read.remove();
    };
    note.append(read);
  }
  cov.append(note);
}

function coverageSvg(coverage) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 180 64");
  svg.style.width = "100%"; svg.style.height = "auto";
  const max = Math.max(...coverage.bins, 1);
  coverage.bins.forEach((n, i) => {
    if (!n && i > 0) return;
    const h = Math.max(2, n / max * 56);
    const r = document.createElementNS(svg.namespaceURI, "rect");
    r.setAttribute("x", 2 + i * 11); r.setAttribute("y", 60 - h);
    r.setAttribute("width", 9); r.setAttribute("height", h);
    r.setAttribute("rx", 2);
    r.setAttribute("fill", i === 0 ? "#5d6b7c" : "#8896a6");
    svg.append(r);
  });
  return svg;
}
```

And in `render(state)`, replace the done branch:

```js
  else if (phase === "done") { renderDone(state); show("done"); }
```

Also reset `doneRendered = null;` inside the `idle` branch (so a new run re-renders), and delete the old `$("snapshot-path").textContent = ...` line.

- [ ] **Step 5: Run the suite and smoke-test**

Run: `.venv/bin/python -m pytest tests/ -q` — expected PASS (`test_index_served` still green).

Smoke: restart the fake-backed smoke server (`scratchpad/smoke_server.py` from the previous feature; it needs no changes), run start→accept, and check the done screen renders: plate hero with intent, bars animating in with per-label colors, example under each bar (fake texts like "c q1"), ledger, coverage figure. The weekly trend will be absent (fixture conversations are undated) — that exercises the omission path.

- [ ] **Step 6: Commit**

```bash
git add src/labeling/static/index.html
git commit -m "feat: done screen v4 — intent hero, evidence-under-bar distribution, trend, margin record"
```

---

### Task 5: end-to-end verification

**Files:** none expected (fixes only if found).

- [ ] **Step 1: Full suite** — `.venv/bin/python -m pytest tests/ -q`, all green.
- [ ] **Step 2: Visual pass** on the smoke server via Chrome: done screen at full and narrow width (margin column stacks below), label expand + resample works, "read them" reveals zero-label conversations, reduced-motion honored (bars don't animate when the OS setting is on — verify by code inspection of the media query if the setting is awkward to toggle).
- [ ] **Step 3: Spec walk** — check every design-doc section (data fields, screen structure, identity colors incl. >6-label fallback, craft commitments, honest limits) is implemented or explicitly deferred; fix gaps.
- [ ] **Step 4: Rule-4 check** — `git status` before any commit: no `data/`, no student text in committed files.
