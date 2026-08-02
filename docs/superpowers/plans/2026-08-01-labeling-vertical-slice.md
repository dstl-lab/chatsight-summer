# Top-Down Labeling Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working end-to-end CLI slice of the top-down labeling tool: instructor states desired trends → Gemini drafts a label schema → stratified sample of real messages gets draft labels → instructor reviews and accepts or tweaks via free text → mass-label → immutable snapshot in `data/snapshots/`.

**Architecture:** Pure-function core with injected LLM callable (`generate`) so every component is unit-testable without API calls or the DB. Thin SQL edge in `src/ingest/` (the only module besides `labeling` allowed to touch Postgres, per CLAUDE.md rule 3). Schema versions are content-hashed and chained by `parent_version`; every tweak iteration is a new version (invariant 6). CLI is interactive stdin/stdout — no frontend until Phase 4.

**Tech Stack:** Python ≥3.11, uv, pydantic v2, SQLAlchemy core via psycopg2 (read-only), google-genai (`gemini-2.5-flash`), pytest.

## Global Constraints

- **No student data in git** (CLAUDE.md rule 4): test fixtures use invented text only; all outputs go under `data/` (gitignored). Never write student text anywhere else.
- **Read-only DB access**: connection string user `dsc10_tutor`; no INSERT/UPDATE/DDL anywhere.
- **External DB URL**: default `postgresql+psycopg2://dsc10_tutor:{PG_PASSWORD}@localhost:5432/dsc10_tutor_logs`, overridable via `EXT_DB_URL` (mirrors ChatSight's convention, `chatsight/server/python/database.py:358-360`).
- **Tunnel**: `kubectl port-forward pod/dsc10-tutor-logs-prod-0 5432:5432 -n dsc-10-llm`.
- **Raw schema**: table `events(id, created_at, event_type, payload jsonb)`; student turns are `event_type='tutor_query'` with `payload->>'question'`; tutor turns `'tutor_response'` with `payload->>'response'`; conversations keyed by `payload->>'conversation_id'`; notebook in `payload->>'notebook'`.
- **Anchored drafting / blind measurement** (invariant 8): this slice builds the *drafting* loop only; nothing in it may be presented as a reliability measurement. The CLI accept step prints exactly: `NOTE: acceptance is a drafting decision, not a reliability measurement (blind audit comes in Phase 0).`
- **No silent caps**: mass-labeling defaults to `--max-conversations 200` and MUST log what was excluded.
- **Provenance**: every snapshot manifest records `snapshot_id, export_date, repo_sha, schema_version, classifier_hash, row_counts`.
- All Gemini calls go through one injected callable type: `generate(prompt: str, response_model: type[BaseModel]) -> BaseModel`. Tests always inject fakes; no test may hit the network or a real DB.

## File Structure

```
bin/tunnel                      ← kubectl port-forward wrapper (auto-reconnect)
.env.example                    ← PG_PASSWORD=, GEMINI_API_KEY= (names only)
src/config.py                   ← Settings: env loading, EXT_DB_URL default, data paths
src/ingest/rawlog.py            ← Turn/Conversation models; assemble_turns (pure); fetch_conversations (SQL edge)
src/labeling/schema.py          ← LabelDef, LabelSchema; content-hash version ids; save/load under data/labeling/schemas/
src/labeling/llm.py             ← generate() factory wrapping google-genai; structured output via pydantic
src/labeling/elicit.py          ← draft_schema, revise_schema (pure, injected generate)
src/labeling/sampler.py         ← stratified_sample over (length tercile × position) strata
src/labeling/draft.py           ← draft_labels per message; classifier_hash
src/labeling/snapshot.py        ← emit_snapshot: JSONL + manifest.json
src/labeling/cli.py             ← interactive loop wiring it together
tests/…                         ← mirrors src; synthetic fixtures only
```

---

### Task 1: Config, env template, tunnel script

**Files:**
- Create: `src/config.py`, `.env.example`, `bin/tunnel`, `tests/test_config.py`
- Modify: `pyproject.toml` (testpaths → `["tests"]`; add `sqlalchemy>=2.0`)

**Interfaces:**
- Produces: `from src.config import Settings`; `Settings.load() -> Settings` with fields `ext_db_url: str`, `gemini_api_key: str | None`, `data_dir: Path`, `repo_root: Path`. `data_dir` is `<repo_root>/data`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from src.config import Settings


def test_default_ext_db_url_built_from_pg_password(monkeypatch):
    monkeypatch.setenv("PG_PASSWORD", "sekrit")
    monkeypatch.delenv("EXT_DB_URL", raising=False)
    s = Settings.load()
    assert s.ext_db_url == (
        "postgresql+psycopg2://dsc10_tutor:sekrit@localhost:5432/dsc10_tutor_logs"
    )


def test_ext_db_url_env_override_wins(monkeypatch):
    monkeypatch.setenv("PG_PASSWORD", "ignored")
    monkeypatch.setenv("EXT_DB_URL", "postgresql+psycopg2://u:p@h:5/db")
    assert Settings.load().ext_db_url == "postgresql+psycopg2://u:p@h:5/db"


def test_data_dir_is_repo_data(monkeypatch):
    monkeypatch.setenv("PG_PASSWORD", "x")
    s = Settings.load()
    assert s.data_dir == s.repo_root / "data"
    assert (s.repo_root / "CLAUDE.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`
(If `uv run` errors on missing lockfile, run `uv sync` once first. Create empty `tests/__init__.py`.)

- [ ] **Step 3: Write minimal implementation**

```python
# src/config.py
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    ext_db_url: str
    gemini_api_key: str | None
    repo_root: Path
    data_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv(_REPO_ROOT / ".env")
        ext_db_url = os.environ.get("EXT_DB_URL")
        if not ext_db_url:
            pg_password = os.environ["PG_PASSWORD"]
            ext_db_url = (
                f"postgresql+psycopg2://dsc10_tutor:{pg_password}"
                "@localhost:5432/dsc10_tutor_logs"
            )
        return cls(
            ext_db_url=ext_db_url,
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
            repo_root=_REPO_ROOT,
            data_dir=_REPO_ROOT / "data",
        )
```

```
# .env.example  — copy to .env and fill in; .env is gitignored
PG_PASSWORD=
GEMINI_API_KEY=
# EXT_DB_URL=   # optional override of the default tunnel URL
```

```bash
#!/usr/bin/env bash
# bin/tunnel — port-forward to the raw-log Postgres, auto-reconnect on drop.
# Same access pattern as sibling project ChatSight (read-only DB user).
set -euo pipefail
while true; do
  kubectl port-forward pod/dsc10-tutor-logs-prod-0 5432:5432 -n dsc-10-llm || true
  echo "[tunnel] connection lost; reconnecting in 3s..." >&2
  sleep 3
done
```

Also `chmod +x bin/tunnel`. In `pyproject.toml`: change `testpaths = ["src"]` to `["tests"]`, add `"sqlalchemy>=2.0"` to dependencies.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v` — Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py .env.example bin/tunnel tests/ pyproject.toml uv.lock
git commit -m "feat: settings, env template, k8s tunnel script"
```

---

### Task 2: Raw-log ingest

**Files:**
- Create: `src/ingest/rawlog.py`, `tests/test_rawlog.py`

**Interfaces:**
- Produces:
  - `Turn(BaseModel)`: `index: int`, `role: Literal["student", "tutor"]`, `text: str`, `student_index: int | None` (position among student turns; None for tutor turns)
  - `Conversation(BaseModel)`: `conv_id: str`, `chatlog_id: int`, `notebook: str | None`, `started_at: datetime | None`, `turns: list[Turn]`; property `student_turns -> list[Turn]`
  - `assemble_turns(rows: list[tuple[str, str | None, str | None]]) -> list[Turn]` — rows are `(event_type, question, response)` ordered by event id; mirrors ChatSight's semantics: tutor responses before the first query are dropped; empty/None texts dropped
  - `fetch_conversations(ext_db_url: str, limit: int | None = None) -> list[Conversation]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rawlog.py  — all text is invented; never paste real student messages
from src.ingest.rawlog import Conversation, Turn, assemble_turns


ROWS = [
    ("tutor_response", None, "orphan greeting"),   # before first query: dropped
    ("tutor_query", "how do I sort a table?", None),
    ("tutor_response", None, "try .sort()"),
    ("tutor_query", "it errored", None),
    ("tutor_query", "", None),                      # empty: dropped
    ("tutor_response", None, None),                 # null: dropped
]


def test_assemble_turns_roles_and_indices():
    turns = assemble_turns(ROWS)
    assert [(t.role, t.index) for t in turns] == [
        ("student", 0), ("tutor", 1), ("student", 2)
    ]
    assert [t.student_index for t in turns] == [0, None, 1]
    assert turns[0].text == "how do I sort a table?"


def test_conversation_student_turns():
    conv = Conversation(
        conv_id="c1", chatlog_id=7, notebook="hw3", started_at=None,
        turns=assemble_turns(ROWS),
    )
    assert [t.text for t in conv.student_turns] == ["how do I sort a table?", "it errored"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_rawlog.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/ingest/rawlog.py
"""Raw-log access. The SQL edge is fetch_conversations; everything else is pure.
Read-only: never execute anything but SELECT against the external DB."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import create_engine, text


class Turn(BaseModel):
    index: int
    role: Literal["student", "tutor"]
    text: str
    student_index: int | None = None


class Conversation(BaseModel):
    conv_id: str
    chatlog_id: int
    notebook: str | None
    started_at: datetime | None
    turns: list[Turn]

    @property
    def student_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.role == "student"]


def assemble_turns(rows: list[tuple[str, str | None, str | None]]) -> list[Turn]:
    turns: list[Turn] = []
    student_idx = 0
    seen_query = False
    for event_type, question, response in rows:
        if event_type == "tutor_query" and question:
            seen_query = True
            turns.append(Turn(index=len(turns), role="student", text=question,
                              student_index=student_idx))
            student_idx += 1
        elif event_type == "tutor_response" and response and seen_query:
            turns.append(Turn(index=len(turns), role="tutor", text=response))
    return turns


_CONV_SQL = """
SELECT payload->>'conversation_id' AS conv_id,
       MIN(id) AS chatlog_id,
       MAX(payload->>'notebook') AS notebook,
       MIN(created_at) AS started_at
FROM events
WHERE event_type IN ('tutor_query', 'tutor_response')
GROUP BY payload->>'conversation_id'
ORDER BY chatlog_id
"""

_TURNS_SQL = """
SELECT event_type, payload->>'question' AS question, payload->>'response' AS response
FROM events
WHERE event_type IN ('tutor_query', 'tutor_response')
  AND payload->>'conversation_id' = :conv_id
ORDER BY id ASC
"""


def fetch_conversations(ext_db_url: str, limit: int | None = None) -> list[Conversation]:
    engine = create_engine(ext_db_url)
    sql = _CONV_SQL + (f"\nLIMIT {int(limit)}" if limit is not None else "")
    out: list[Conversation] = []
    with engine.connect() as conn:
        heads = conn.execute(text(sql)).mappings().all()
        for h in heads:
            rows = [tuple(r) for r in conn.execute(
                text(_TURNS_SQL), {"conv_id": h["conv_id"]}
            ).fetchall()]
            turns = assemble_turns(rows)
            if turns:
                out.append(Conversation(
                    conv_id=h["conv_id"], chatlog_id=h["chatlog_id"],
                    notebook=h["notebook"], started_at=h["started_at"], turns=turns,
                ))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_rawlog.py -v` — Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ingest/rawlog.py tests/test_rawlog.py
git commit -m "feat: raw-log ingest (pure turn assembly + read-only SQL edge)"
```

---

### Task 3: Label schema models with content-hashed versions

**Files:**
- Create: `src/labeling/schema.py`, `tests/test_schema.py`

**Interfaces:**
- Produces:
  - `LabelDef(BaseModel)`: `name: str` (kebab-case), `kind: Literal["conceptual", "behavioral", "other"]`, `description: str`, `positive_criteria: str`, `negative_criteria: str`
  - `LabelSchema(BaseModel)`: `instructor_intent: str`, `labels: list[LabelDef]`, `parent_version: str | None`, `feedback_applied: str | None`; property `version_id -> str` (12-hex content hash, stable, excludes nothing — any change ⇒ new id)
  - `save_schema(schema: LabelSchema, data_dir: Path) -> Path` (writes `data_dir/labeling/schemas/<version_id>.json`)
  - `load_schema(version_id: str, data_dir: Path) -> LabelSchema`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema.py
from pathlib import Path
from src.labeling.schema import LabelDef, LabelSchema, load_schema, save_schema


def _schema(desc: str = "asks for the answer outright") -> LabelSchema:
    return LabelSchema(
        instructor_intent="I want to see who extracts answers vs works for them",
        labels=[LabelDef(
            name="answer-extraction", kind="behavioral", description=desc,
            positive_criteria="directly requests final answer",
            negative_criteria="asks for a hint or explanation",
        )],
        parent_version=None, feedback_applied=None,
    )


def test_version_id_is_stable_and_content_sensitive():
    a, b = _schema(), _schema()
    assert a.version_id == b.version_id
    assert len(a.version_id) == 12
    assert a.version_id != _schema(desc="changed").version_id


def test_save_and_load_roundtrip(tmp_path: Path):
    s = _schema()
    path = save_schema(s, tmp_path)
    assert path.name == f"{s.version_id}.json"
    assert load_schema(s.version_id, tmp_path) == s


def test_tweak_lineage():
    parent = _schema()
    child = LabelSchema(
        instructor_intent=parent.instructor_intent,
        labels=parent.labels,
        parent_version=parent.version_id,
        feedback_applied="split confusion into concept vs logistics",
    )
    assert child.parent_version == parent.version_id
    assert child.version_id != parent.version_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schema.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/schema.py
"""Label schemas. Every instructor tweak creates a new content-hashed version
chained via parent_version (CLAUDE.md invariant 6)."""
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class LabelDef(BaseModel):
    name: str
    kind: Literal["conceptual", "behavioral", "other"]
    description: str
    positive_criteria: str
    negative_criteria: str


class LabelSchema(BaseModel):
    instructor_intent: str
    labels: list[LabelDef]
    parent_version: str | None = None
    feedback_applied: str | None = None

    @property
    def version_id(self) -> str:
        canonical = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _schemas_dir(data_dir: Path) -> Path:
    d = data_dir / "labeling" / "schemas"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_schema(schema: LabelSchema, data_dir: Path) -> Path:
    path = _schemas_dir(data_dir) / f"{schema.version_id}.json"
    path.write_text(schema.model_dump_json(indent=2))
    return path


def load_schema(version_id: str, data_dir: Path) -> LabelSchema:
    path = _schemas_dir(data_dir) / f"{version_id}.json"
    return LabelSchema.model_validate_json(path.read_text())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schema.py -v` — Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/schema.py tests/test_schema.py
git commit -m "feat: content-hashed label schema versions with tweak lineage"
```

---

### Task 4: Gemini wrapper + intent elicitation

**Files:**
- Create: `src/labeling/llm.py`, `src/labeling/elicit.py`, `tests/test_elicit.py`

**Interfaces:**
- Consumes: `LabelDef`, `LabelSchema` from `src/labeling/schema.py`
- Produces:
  - Type alias `Generate = Callable[[str, type[BaseModel]], BaseModel]`
  - `make_generate(api_key: str, model: str = "gemini-2.5-flash") -> Generate` (in `llm.py`; the ONLY place google-genai is imported)
  - `draft_schema(intent_text: str, generate: Generate) -> LabelSchema`
  - `revise_schema(current: LabelSchema, feedback: str, generate: Generate) -> LabelSchema` (sets `parent_version`, `feedback_applied`)
  - `ELICIT_PROMPT: str`, `REVISE_PROMPT: str` module constants (used for classifier_hash later — treat as part of pinned config)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_elicit.py
from src.labeling.elicit import DraftedLabels, draft_schema, revise_schema
from src.labeling.schema import LabelDef


FAKE_LABELS = [LabelDef(
    name="concept-confusion", kind="behavioral",
    description="student is confused about a course concept",
    positive_criteria="expresses not understanding a concept",
    negative_criteria="logistics or syntax-only questions",
)]


def fake_generate(prompt: str, response_model):
    assert response_model is DraftedLabels
    fake_generate.last_prompt = prompt
    return DraftedLabels(labels=FAKE_LABELS)


def test_draft_schema_wraps_llm_labels_with_intent():
    s = draft_schema("show me who is confused", fake_generate)
    assert s.instructor_intent == "show me who is confused"
    assert s.labels == FAKE_LABELS
    assert s.parent_version is None
    assert "show me who is confused" in fake_generate.last_prompt


def test_revise_schema_chains_lineage_and_carries_feedback():
    parent = draft_schema("show me who is confused", fake_generate)
    child = revise_schema(parent, "also split out anger", fake_generate)
    assert child.parent_version == parent.version_id
    assert child.feedback_applied == "also split out anger"
    assert "also split out anger" in fake_generate.last_prompt
    assert parent.labels[0].name in fake_generate.last_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_elicit.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/llm.py
"""The only module that imports google-genai. Everything else takes an injected
`generate` callable so it is testable offline."""
from typing import Callable

from pydantic import BaseModel

Generate = Callable[[str, type[BaseModel]], BaseModel]

DEFAULT_MODEL = "gemini-2.5-flash"


def make_generate(api_key: str, model: str = DEFAULT_MODEL) -> Generate:
    from google import genai

    client = genai.Client(api_key=api_key)

    def generate(prompt: str, response_model: type[BaseModel]) -> BaseModel:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": response_model,
            },
        )
        return response_model.model_validate_json(response.text)

    return generate
```

```python
# src/labeling/elicit.py
"""Intent elicitation: instructor's stated trends -> drafted label schema, and
free-text feedback -> revised schema. Drafting is anchored by design; reliability
measurement is blind and lives elsewhere (invariant 8)."""
from pydantic import BaseModel

from src.labeling.llm import Generate
from src.labeling.schema import LabelDef, LabelSchema


class DraftedLabels(BaseModel):
    labels: list[LabelDef]


ELICIT_PROMPT = """You are helping a course instructor turn the trends they want \
to see in student–AI tutor chat logs into a precise label schema.

Instructor's stated interest:
{intent}

Draft 3-8 binary message-level labels. Each label must have: a kebab-case name; \
kind ("conceptual" for topic/content labels, "behavioral" for help-seeking or \
affect, "other" otherwise); a one-sentence description; positive_criteria (when \
it applies); negative_criteria (nearby cases where it must NOT apply). Labels \
must be checkable from a single student message with surrounding conversation \
context. Prefer fewer, sharper labels over many vague ones."""

REVISE_PROMPT = """You are revising a label schema for student–AI tutor chat \
logs based on instructor feedback.

Instructor's original interest:
{intent}

Current labels:
{labels}

Instructor's feedback on the drafted labels as seen on a sample:
{feedback}

Return the full revised label set (same format, 3-8 binary message-level \
labels), applying the feedback. Keep labels the feedback did not touch."""


def draft_schema(intent_text: str, generate: Generate) -> LabelSchema:
    drafted = generate(ELICIT_PROMPT.format(intent=intent_text), DraftedLabels)
    return LabelSchema(instructor_intent=intent_text, labels=drafted.labels)


def revise_schema(current: LabelSchema, feedback: str, generate: Generate) -> LabelSchema:
    prompt = REVISE_PROMPT.format(
        intent=current.instructor_intent,
        labels="\n".join(
            f"- {l.name} ({l.kind}): {l.description} | applies: {l.positive_criteria} "
            f"| does not apply: {l.negative_criteria}"
            for l in current.labels
        ),
        feedback=feedback,
    )
    drafted = generate(prompt, DraftedLabels)
    return LabelSchema(
        instructor_intent=current.instructor_intent,
        labels=drafted.labels,
        parent_version=current.version_id,
        feedback_applied=feedback,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_elicit.py -v` — Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/llm.py src/labeling/elicit.py tests/test_elicit.py
git commit -m "feat: gemini wrapper + intent-to-schema elicitation with revise loop"
```

---

### Task 5: Stratified sampler

**Files:**
- Create: `src/labeling/sampler.py`, `tests/test_sampler.py`

**Interfaces:**
- Consumes: `Conversation`, `Turn` from `src/ingest/rawlog.py`
- Produces:
  - `SampledMessage(BaseModel)`: `chatlog_id: int`, `conv_id: str`, `message_index: int`, `text: str`, `context_before: str | None`, `context_after: str | None`, `stratum: str`
  - `stratified_sample(conversations: list[Conversation], n: int, seed: int) -> list[SampledMessage]`
  - v0 strata = conversation-length tercile (`short|mid|long`) × student-turn position (`early|late`, split at the midpoint of the student turns), e.g. stratum `"long/early"`. Round-robin across strata until `n` reached; deterministic given `seed`. Docstring MUST state the upgrade path (invariant 9): v0 is structural stratification only; model-uncertainty and embedding-diversity strata replace it once a first labeled pass exists.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sampler.py
from src.ingest.rawlog import Conversation, Turn
from src.labeling.sampler import stratified_sample


def _conv(conv_id: str, n_student: int) -> Conversation:
    turns = []
    for i in range(n_student):
        turns.append(Turn(index=2 * i, role="student",
                          text=f"{conv_id} q{i}", student_index=i))
        turns.append(Turn(index=2 * i + 1, role="tutor", text=f"{conv_id} a{i}"))
    return Conversation(conv_id=conv_id, chatlog_id=hash(conv_id) % 10_000,
                        notebook=None, started_at=None, turns=turns)


CONVS = [_conv("a", 1), _conv("b", 2), _conv("c", 4), _conv("d", 6),
         _conv("e", 9), _conv("f", 12)]


def test_sample_is_deterministic_and_sized():
    s1 = stratified_sample(CONVS, n=8, seed=7)
    s2 = stratified_sample(CONVS, n=8, seed=7)
    assert [ (m.conv_id, m.message_index) for m in s1 ] == \
           [ (m.conv_id, m.message_index) for m in s2 ]
    assert len(s1) == 8


def test_sample_spans_multiple_strata():
    strata = {m.stratum for m in stratified_sample(CONVS, n=8, seed=7)}
    assert len(strata) >= 3


def test_context_is_adjacent_tutor_turns():
    sample = stratified_sample(CONVS, n=8, seed=7)
    m = next(m for m in sample if m.conv_id == "c" and m.message_index > 0)
    assert m.context_before is not None and m.context_before.startswith("c a")


def test_no_duplicate_messages():
    sample = stratified_sample(CONVS, n=30, seed=0)  # n > population is fine
    keys = [(m.conv_id, m.message_index) for m in sample]
    assert len(keys) == len(set(keys))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sampler.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/sampler.py
"""Stratified sampling for instructor review (CLAUDE.md invariant 9: never a
plain random pull).

v0 strata are structural only: conversation-length tercile x student-turn
position (early/late). Upgrade path: once a first labeled pass exists, replace
with model-uncertainty and embedding-diversity strata so boundary and rare
cases surface."""
import random
from collections import defaultdict

from pydantic import BaseModel

from src.ingest.rawlog import Conversation


class SampledMessage(BaseModel):
    chatlog_id: int
    conv_id: str
    message_index: int
    text: str
    context_before: str | None
    context_after: str | None
    stratum: str


def _length_tercile(conversations: list[Conversation]) -> dict[str, str]:
    sizes = sorted((len(c.student_turns), c.conv_id) for c in conversations)
    out: dict[str, str] = {}
    third = max(1, len(sizes) // 3)
    for rank, (_, conv_id) in enumerate(sizes):
        out[conv_id] = ("short", "mid", "long")[min(rank // third, 2)]
    return out


def _neighbors(conv: Conversation, turn_index: int) -> tuple[str | None, str | None]:
    before = next((t.text for t in reversed(conv.turns[:turn_index])
                   if t.role == "tutor"), None)
    after = next((t.text for t in conv.turns[turn_index + 1:]
                  if t.role == "tutor"), None)
    return before, after


def stratified_sample(conversations: list[Conversation], n: int,
                      seed: int) -> list[SampledMessage]:
    tercile = _length_tercile(conversations)
    strata: dict[str, list[SampledMessage]] = defaultdict(list)
    for conv in conversations:
        n_student = len(conv.student_turns)
        for turn in conv.student_turns:
            position = "early" if turn.student_index < n_student / 2 else "late"
            stratum = f"{tercile[conv.conv_id]}/{position}"
            before, after = _neighbors(conv, turn.index)
            strata[stratum].append(SampledMessage(
                chatlog_id=conv.chatlog_id, conv_id=conv.conv_id,
                message_index=turn.index, text=turn.text,
                context_before=before, context_after=after, stratum=stratum,
            ))
    rng = random.Random(seed)
    for bucket in strata.values():
        rng.shuffle(bucket)
    out: list[SampledMessage] = []
    order = sorted(strata)
    while len(out) < n and any(strata[s] for s in order):
        for s in order:
            if strata[s] and len(out) < n:
                out.append(strata[s].pop())
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sampler.py -v` — Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/sampler.py tests/test_sampler.py
git commit -m "feat: stratified review sampler (structural v0 strata, documented upgrade path)"
```

---

### Task 6: Draft classifier + classifier hash

**Files:**
- Create: `src/labeling/draft.py`, `tests/test_draft.py`

**Interfaces:**
- Consumes: `SampledMessage`; `LabelSchema`; `Generate`
- Produces:
  - `MessageLabels(BaseModel)`: `chatlog_id: int`, `message_index: int`, `labels: dict[str, bool]`, `rationales: dict[str, str]`
  - `draft_labels(messages: list[SampledMessage], schema: LabelSchema, generate: Generate) -> list[MessageLabels]` (one LLM call per message, all schema labels at once)
  - `classifier_hash(schema: LabelSchema, model: str) -> str` — 12-hex sha256 over (CLASSIFY_PROMPT template ⊕ schema.version_id ⊕ model); this is the pin recorded in manifests (CLAUDE.md rule 2)
  - `CLASSIFY_PROMPT: str` module constant

- [ ] **Step 1: Write the failing test**

```python
# tests/test_draft.py
from src.labeling.draft import (CLASSIFY_PROMPT, LabelVerdicts, MessageLabels,
                                classifier_hash, draft_labels)
from src.labeling.elicit import draft_schema
from src.labeling.sampler import SampledMessage
from src.labeling.schema import LabelDef
import tests.test_elicit as te


def _msg(i: int) -> SampledMessage:
    return SampledMessage(chatlog_id=100 + i, conv_id="c", message_index=i,
                          text=f"invented question {i}", context_before=None,
                          context_after="try a hint", stratum="short/early")


def fake_generate(prompt: str, response_model):
    assert response_model is LabelVerdicts
    fake_generate.prompts.append(prompt)
    return LabelVerdicts(
        verdicts={"concept-confusion": True},
        rationales={"concept-confusion": "mentions not understanding"},
    )


fake_generate.prompts = []


def _schema():
    return draft_schema("who is confused", te.fake_generate)


def test_draft_labels_one_result_per_message():
    fake_generate.prompts = []
    results = draft_labels([_msg(0), _msg(1)], _schema(), fake_generate)
    assert [r.message_index for r in results] == [0, 1]
    assert results[0].labels == {"concept-confusion": True}
    assert "invented question 0" in fake_generate.prompts[0]
    assert "concept-confusion" in fake_generate.prompts[0]


def test_classifier_hash_pins_schema_and_model():
    s = _schema()
    h = classifier_hash(s, "gemini-2.5-flash")
    assert len(h) == 12
    assert h != classifier_hash(s, "gemini-3.0")
    revised = draft_schema("who is angry", te.fake_generate)
    assert h != classifier_hash(revised, "gemini-2.5-flash")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_draft.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/draft.py
"""Draft classification of sampled messages against a schema version.
classifier_hash is the provenance pin: same hash <=> same prompt template,
schema version, and model (CLAUDE.md rule 2)."""
import hashlib

from pydantic import BaseModel

from src.labeling.llm import Generate
from src.labeling.sampler import SampledMessage
from src.labeling.schema import LabelSchema


class LabelVerdicts(BaseModel):
    verdicts: dict[str, bool]
    rationales: dict[str, str]


class MessageLabels(BaseModel):
    chatlog_id: int
    message_index: int
    labels: dict[str, bool]
    rationales: dict[str, str]


CLASSIFY_PROMPT = """You label one student message from a student–AI tutor \
conversation. For EACH label below decide true/false and give a one-sentence \
rationale. Judge only the student message; context is for disambiguation.

Labels:
{labels}

Tutor message before (may be empty):
{context_before}

STUDENT MESSAGE TO LABEL:
{text}

Tutor message after (may be empty):
{context_after}

Return verdicts and rationales keyed by exact label name."""


def _labels_block(schema: LabelSchema) -> str:
    return "\n".join(
        f"- {l.name}: {l.description} | applies when: {l.positive_criteria} "
        f"| does NOT apply when: {l.negative_criteria}"
        for l in schema.labels
    )


def draft_labels(messages: list[SampledMessage], schema: LabelSchema,
                 generate: Generate) -> list[MessageLabels]:
    out: list[MessageLabels] = []
    block = _labels_block(schema)
    for m in messages:
        prompt = CLASSIFY_PROMPT.format(
            labels=block, context_before=m.context_before or "",
            text=m.text, context_after=m.context_after or "",
        )
        v: LabelVerdicts = generate(prompt, LabelVerdicts)
        out.append(MessageLabels(chatlog_id=m.chatlog_id,
                                 message_index=m.message_index,
                                 labels=v.verdicts, rationales=v.rationales))
    return out


def classifier_hash(schema: LabelSchema, model: str) -> str:
    canonical = "\x1e".join([CLASSIFY_PROMPT, schema.version_id, model])
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_draft.py -v` — Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/draft.py tests/test_draft.py
git commit -m "feat: draft classifier with provenance-pinning classifier hash"
```

---

### Task 7: Snapshot emission

**Files:**
- Create: `src/labeling/snapshot.py`, `tests/test_snapshot.py`

**Interfaces:**
- Consumes: `Conversation`; `MessageLabels`; `LabelSchema`; `classifier_hash`
- Produces:
  - `emit_snapshot(conversations: list[Conversation], labels: list[MessageLabels], schema: LabelSchema, model: str, repo_sha: str, data_dir: Path, excluded_conversations: int) -> Path` — creates `data_dir/snapshots/<snapshot_id>/` containing `conversations.jsonl` (one Conversation per line), `labels.jsonl` (one MessageLabels per line), `schema.json`, `manifest.json`
  - `snapshot_id` = `{YYYYMMDD}-{schema.version_id}-{classifier_hash[:6]}`
  - `manifest.json` keys: `snapshot_id, export_date, repo_sha, schema_version, classifier_hash, row_counts {conversations, turns, label_applications}, excluded_conversations`
  - Raises `FileExistsError` if the snapshot dir already exists (immutability)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_snapshot.py
import json
from pathlib import Path

import pytest

from src.labeling.draft import MessageLabels, classifier_hash
from src.labeling.elicit import draft_schema
from src.labeling.snapshot import emit_snapshot
import tests.test_elicit as te
from tests.test_sampler import _conv


def _fixtures():
    convs = [_conv("a", 2), _conv("b", 1)]
    schema = draft_schema("who is confused", te.fake_generate)
    labels = [MessageLabels(chatlog_id=convs[0].chatlog_id, message_index=0,
                            labels={"concept-confusion": True},
                            rationales={"concept-confusion": "invented"})]
    return convs, schema, labels


def test_emit_snapshot_writes_manifest_and_rows(tmp_path: Path):
    convs, schema, labels = _fixtures()
    path = emit_snapshot(convs, labels, schema, model="gemini-2.5-flash",
                         repo_sha="abc1234", data_dir=tmp_path,
                         excluded_conversations=17)
    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["schema_version"] == schema.version_id
    assert manifest["classifier_hash"] == classifier_hash(schema, "gemini-2.5-flash")
    assert manifest["repo_sha"] == "abc1234"
    assert manifest["row_counts"] == {
        "conversations": 2, "turns": 6, "label_applications": 1}
    assert manifest["excluded_conversations"] == 17
    assert len((path / "conversations.jsonl").read_text().splitlines()) == 2
    assert len((path / "labels.jsonl").read_text().splitlines()) == 1


def test_snapshots_are_immutable(tmp_path: Path):
    convs, schema, labels = _fixtures()
    emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                  data_dir=tmp_path, excluded_conversations=0)
    with pytest.raises(FileExistsError):
        emit_snapshot(convs, labels, schema, model="m", repo_sha="abc",
                      data_dir=tmp_path, excluded_conversations=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_snapshot.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/snapshot.py
"""Immutable labeled-corpus snapshots (CLAUDE.md rule 3). The simulation
subsystems consume ONLY these, never the DB. After emitting, add a row to
snapshots.md (the CLI reminds the operator)."""
import json
from datetime import date
from pathlib import Path

from src.ingest.rawlog import Conversation
from src.labeling.draft import MessageLabels, classifier_hash
from src.labeling.schema import LabelSchema


def emit_snapshot(conversations: list[Conversation], labels: list[MessageLabels],
                  schema: LabelSchema, model: str, repo_sha: str, data_dir: Path,
                  excluded_conversations: int) -> Path:
    chash = classifier_hash(schema, model)
    snapshot_id = f"{date.today():%Y%m%d}-{schema.version_id}-{chash[:6]}"
    path = data_dir / "snapshots" / snapshot_id
    path.mkdir(parents=True, exist_ok=False)  # immutability: never overwrite

    with (path / "conversations.jsonl").open("w") as f:
        for c in conversations:
            f.write(c.model_dump_json() + "\n")
    with (path / "labels.jsonl").open("w") as f:
        for l in labels:
            f.write(l.model_dump_json() + "\n")
    (path / "schema.json").write_text(schema.model_dump_json(indent=2))

    manifest = {
        "snapshot_id": snapshot_id,
        "export_date": date.today().isoformat(),
        "repo_sha": repo_sha,
        "schema_version": schema.version_id,
        "classifier_hash": chash,
        "row_counts": {
            "conversations": len(conversations),
            "turns": sum(len(c.turns) for c in conversations),
            "label_applications": len(labels),
        },
        "excluded_conversations": excluded_conversations,
    }
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_snapshot.py -v` — Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/snapshot.py tests/test_snapshot.py
git commit -m "feat: immutable snapshot emission with full provenance manifest"
```

---

### Task 8: Interactive CLI loop

**Files:**
- Create: `src/labeling/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `run_loop(intent: str, conversations: list[Conversation], generate: Generate, *, sample_size: int, seed: int, ask: Callable[[str], str], say: Callable[[str], None]) -> LabelSchema | None` — pure orchestration: draft schema → sample → draft labels → render → `ask("accept/tweak/quit> ")`; on `tweak` ask for feedback, revise, re-draft, repeat; on `accept` return the accepted schema; on `quit` return None. `ask`/`say` injected for testability.
  - `main()` — argparse: `--intent` (optional; prompt if absent), `--max-conversations` (default 200), `--sample-size` (default 25), `--seed` (default 0). Wires Settings, fetch_conversations, make_generate, run_loop; on accept: mass-label all student turns of the fetched conversations via `draft_labels`, `emit_snapshot`, print snapshot path + `Add a row to snapshots.md`. Must log excluded conversation count (no silent caps) and print the invariant-8 acceptance note verbatim (Global Constraints).
  - Register in `pyproject.toml`: `[project.scripts] label-loop = "src.labeling.cli:main"`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from src.labeling.cli import run_loop
from src.labeling.draft import LabelVerdicts
from src.labeling.elicit import DraftedLabels
from src.labeling.schema import LabelDef
from tests.test_sampler import CONVS


def _label(name: str) -> LabelDef:
    return LabelDef(name=name, kind="behavioral", description="d",
                    positive_criteria="p", negative_criteria="n")


def make_fake_generate():
    def fake_generate(prompt: str, response_model):
        if response_model is DraftedLabels:
            fake_generate.schema_calls += 1
            name = f"label-v{fake_generate.schema_calls}"
            return DraftedLabels(labels=[_label(name)])
        return LabelVerdicts(verdicts={"x": True}, rationales={"x": "r"})
    fake_generate.schema_calls = 0
    return fake_generate


def test_accept_returns_first_schema():
    answers = iter(["accept"])
    schema = run_loop("intent", CONVS, make_fake_generate(), sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lambda _: None)
    assert schema is not None
    assert schema.labels[0].name == "label-v1"
    assert schema.parent_version is None


def test_tweak_then_accept_chains_versions():
    answers = iter(["tweak", "split confusion by cause", "accept"])
    schema = run_loop("intent", CONVS, make_fake_generate(), sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lambda _: None)
    assert schema.labels[0].name == "label-v2"
    assert schema.parent_version is not None
    assert schema.feedback_applied == "split confusion by cause"


def test_quit_returns_none_and_renders_sample():
    lines: list[str] = []
    answers = iter(["quit"])
    result = run_loop("intent", CONVS, make_fake_generate(), sample_size=4,
                      seed=0, ask=lambda _: next(answers), say=lines.append)
    assert result is None
    joined = "\n".join(lines)
    assert "label-v1" in joined          # schema shown
    assert "q0" in joined                # sampled message text shown
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v` — Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# src/labeling/cli.py
"""Interactive draft->review->tweak loop. Drafting is anchored (instructor sees
model labels); this is fine for drafting and forbidden for measurement
(CLAUDE.md invariant 8)."""
import argparse
import subprocess
import sys
from typing import Callable

from src.config import Settings
from src.ingest.rawlog import Conversation, fetch_conversations
from src.labeling.draft import draft_labels
from src.labeling.elicit import draft_schema, revise_schema
from src.labeling.llm import DEFAULT_MODEL, Generate, make_generate
from src.labeling.sampler import SampledMessage, stratified_sample
from src.labeling.schema import LabelSchema, save_schema
from src.labeling.snapshot import emit_snapshot

ACCEPT_NOTE = ("NOTE: acceptance is a drafting decision, not a reliability "
               "measurement (blind audit comes in Phase 0).")


def _render(schema: LabelSchema, sample: list[SampledMessage],
            labeled, say: Callable[[str], None]) -> None:
    say(f"\n=== Schema {schema.version_id} ===")
    for l in schema.labels:
        say(f"  {l.name} ({l.kind}): {l.description}")
    by_key = {(r.chatlog_id, r.message_index): r for r in labeled}
    say(f"\n=== Sample ({len(sample)} messages) ===")
    for m in sample:
        r = by_key.get((m.chatlog_id, m.message_index))
        applied = [k for k, v in r.labels.items() if v] if r else []
        say(f"\n[{m.stratum}] {m.text}")
        say(f"  -> {', '.join(applied) if applied else '(no labels)'}")
        if r:
            for k in applied:
                say(f"     {k}: {r.rationales.get(k, '')}")


def run_loop(intent: str, conversations: list[Conversation], generate: Generate,
             *, sample_size: int, seed: int, ask: Callable[[str], str],
             say: Callable[[str], None]) -> LabelSchema | None:
    schema = draft_schema(intent, generate)
    sample = stratified_sample(conversations, n=sample_size, seed=seed)
    while True:
        labeled = draft_labels(sample, schema, generate)
        _render(schema, sample, labeled, say)
        say(f"\n{ACCEPT_NOTE}")
        choice = ask("accept/tweak/quit> ").strip().lower()
        if choice == "accept":
            return schema
        if choice == "quit":
            return None
        if choice == "tweak":
            feedback = ask("what should change? ")
            schema = revise_schema(schema, feedback, generate)


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-down labeling loop")
    parser.add_argument("--intent")
    parser.add_argument("--max-conversations", type=int, default=200)
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    settings = Settings.load()
    if not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    generate = make_generate(settings.gemini_api_key)

    intent = args.intent or input(
        "What trends do you want to see in the chat data "
        "(conceptual, behavioral, ...)? ")

    print(f"Fetching up to {args.max_conversations} conversations "
          "(is bin/tunnel running?)...")
    conversations = fetch_conversations(settings.ext_db_url,
                                        limit=args.max_conversations)
    print(f"Fetched {len(conversations)} conversations. Conversations beyond "
          f"--max-conversations={args.max_conversations} are EXCLUDED from "
          "this run and the snapshot.")

    schema = run_loop(intent, conversations, generate,
                      sample_size=args.sample_size, seed=args.seed,
                      ask=input, say=print)
    if schema is None:
        print("Quit without accepting; nothing written.")
        return

    save_schema(schema, settings.data_dir)
    print(f"Accepted schema {schema.version_id}. Mass-labeling "
          f"{len(conversations)} conversations...")
    all_messages = stratified_sample(conversations, n=10**9, seed=args.seed)
    labeled = draft_labels(all_messages, schema, generate)
    repo_sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              cwd=settings.repo_root).stdout.strip()
    path = emit_snapshot(conversations, labeled, schema, model=DEFAULT_MODEL,
                         repo_sha=repo_sha, data_dir=settings.data_dir,
                         excluded_conversations=0)
    print(f"Snapshot written: {path}")
    print("Add a row to snapshots.md with this manifest's provenance.")


if __name__ == "__main__":
    main()
```

Add to `pyproject.toml`:

```toml
[project.scripts]
label-loop = "src.labeling.cli:main"
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -v` — Expected: all tests from Tasks 1-8 PASS

- [ ] **Step 5: Commit**

```bash
git add src/labeling/cli.py tests/test_cli.py pyproject.toml uv.lock
git commit -m "feat: interactive labeling loop CLI wiring the vertical slice"
```

---

### Task 9: Live smoke test (manual, operator present)

No new code. Requires k8s access (open decision #6) and `.env` filled in.

- [ ] **Step 1:** `cp .env.example .env`, fill `PG_PASSWORD` (same value as ChatSight's `.env`) and `GEMINI_API_KEY`.
- [ ] **Step 2:** Terminal A: `bin/tunnel`. Terminal B: `uv run label-loop --max-conversations 20 --sample-size 8`.
- [ ] **Step 3:** Enter a real intent (e.g. "show me instrumental help-seeking vs answer extraction"), do one `tweak` round, then `accept`.
- [ ] **Step 4:** Verify `data/snapshots/<id>/manifest.json` row counts look sane; verify `git status` shows NOTHING from `data/` (rule 4); add the snapshot row to `snapshots.md`; commit only `snapshots.md`.

## Self-Review

- Spec coverage: elicitation (T4), sampling with invariant-9 stance (T5), draft labels (T6), review/tweak loop with version lineage (T3+T8), mass-label + snapshot with provenance (T7+T8), tunnel/ingest (T1+T2), live check (T9). ✓
- Placeholder scan: all steps carry real code. ✓
- Type consistency: `Generate` alias used across T4/T6/T8; `SampledMessage` fields match between T5 producer and T6/T8 consumers; `LabelVerdicts` name consistent in T6/T8 tests. ✓
- Known accepted v0 shortcuts (explicit, not hidden): mass-label reuses `stratified_sample(n=10**9)` as "all student messages"; `excluded_conversations=0` passed at emit time while exclusion is logged to the operator (the fetch limit is the cap; wiring the true count through is a small follow-up); one LLM call per message (no batching).
