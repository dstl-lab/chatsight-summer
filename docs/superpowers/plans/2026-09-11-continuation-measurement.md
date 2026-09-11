# Continuation Measurement Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement the bounded helper task; retain review evidence in commits.

**Goal:** Make the reviewed continuation prompt reusable and prepare comparable behavior reviews and valid synthetic branches.

**Architecture:** One pure-function evaluation module reuses the established source projection and v7 rubric. Frozen private experiments remain intact; the review UI fix and documentation cleanup are independent.

**Tech Stack:** Python >=3.11, existing Pydantic, stdlib, existing pytest.

**Spec:** `docs/2026-09-11-continuation-measurement.md`.

## Global constraints

- No new dependencies or student dialogue in Git; invented test dialogue only.
- Do not change existing pinned labeling modules or private frozen experiment files.
- Generated no-reply is not recorded absence, delay, or observed abandonment.
- No automatic historical-future replay, model judging, production agents or label admission.

## Task 1: Protect saved review work

Files: `src/eval/episode_review.py`, `src/eval/episode_review.html`, existing Python and JavaScript review tests.

- [x] Reproduce two clients overwriting a newer review and unchanged autosaves.
- [x] Require the revision loaded by the client; reject stale updates with HTTP 409 before writing. Preserve legacy review stores and unsaved browser edits.
- [x] Run `uv run python -m pytest tests/test_episode_review.py -q` and `node tests/episode_review_navigation.cjs`; review and commit the fix.

## Task 2: Reusable continuation and review helpers

Files: `src/eval/student_continuation.py`, `tests/test_student_continuation.py`, the dated spec and docs index.

Interfaces:

```python
class Continuation(BaseModel):  # exactly the existing experimental schema
    decision: Literal['reply', 'no-reply']
    text: str

def make_prompt(episode: dict) -> str: ...
def branch_episode(episode: dict, continuation: Continuation, tutor_bridge: str) -> dict: ...
def behavior_review(episode: dict, continuation: Continuation) -> dict: ...
```

- [x] Write invented-input regressions for future/metadata isolation, reply validation, branch provenance and termination, and unfilled behavior judgments with distinct absence provenance. Run before implementation.
- [x] Copy only the generic reviewed prompt/schema into the module. `make_prompt` reuses `tutor_moves.make_prompt(episode, 'v5')`'s `EPISODE JSON` projection exactly. `branch_episode` keeps the visible prefix as context and adds only the supplied generated student reply and scripted tutor bridge. `behavior_review` uses the same v7 action/task definitions for both origins without assigning model judgments.
- [x] Run `uv run python -m pytest tests/test_student_continuation.py -q`. Locally compare the module's prompt/schema and all eight rendered prefixes with the frozen interaction experiment, without publishing their text.
- [x] Add a short runnable Python usage example to the dated spec, then review and commit the module and documentation.

## Task 3: PR preparation

- [x] Make historical run commands portable and mark superseded review checkpoints.
- [x] Run `uv run python -m pytest -q`, `node tests/episode_review_navigation.cjs`, and `git diff --check`; scan new published files for private dialogue or credentials.
- [x] Replay commits onto current `origin/main` (the original base's tree is identical), preserving this separate worktree.
- [x] Push `codex/episode-pilot` and create or update a draft PR with scope, evidence limits, validation and commit history. Do not merge main in this step.

## Review checkpoint

The helper and UI fixes passed independent review, 282 Python tests and the Node
navigation check. Exact prompt/schema and eight-prefix parity passed; 319 parent
pins remain unchanged. Sixteen blank behavior-comparison packets are prepared.
The separate three-call continuity batch is prepared but unsent: automatic approval
review requires specific payload approval despite the logged standing grant. See
the spec for the exact experiment and saved request; no model outcomes are claimed.

All implementation/PR tasks above are complete. Draft PR: [#25](https://github.com/dstl-lab/chatsight-summer/pull/25).
The five implementation commits were replayed onto `origin/main` with an identical
final tree, then pushed from the separate `codex/episode-pilot` worktree. Main was
not merged. The outstanding action is the exact three-request model approval,
followed by generation and human continuity review.
