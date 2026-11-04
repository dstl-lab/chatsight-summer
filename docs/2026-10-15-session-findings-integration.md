# Integrate session findings with Steven’s frontend and recent PR100 data

Updated October 15, 2026 after Austin clarified the production data requirement.
This plan supersedes the historical-data milestone in the original draft. Current
commands and data semantics are in `anomaly-review/FINDINGS_INTEGRATION.md`.

## Objective and preserved branches

Use Austin’s finding algorithm in Steven’s review interface with **recent
production `dsc10-tutor-jlab` PR #100 notebook observations**. Preserve the original
algorithm and frontend branches. Historical original-ChatSight records are not
used for this test, and there is no automatic historical fallback.

- Repository: `dstl-lab/chatsight-summer`.
- Frontend base: `codex/anomaly-review-phase2c-phase3b`,
  `9dc2f2678ab5b3216bcedbdabd5237e175f3e49b`.
- Integration branch: `codex/session-findings-real-data`, separate checkout.
- Algorithm source: `dstl-lab/dsc10-tutor-jlab`,
  `codex/session-findings-prototype`, `25a146e10926108bbdfbcfd99438c955d122ac49`.
- Original copied-file hashes and subsequent port changes are recorded in
  `session_review/findings/PROVENANCE.json`.

## Fresh data audit

A read-only production audit confirmed the new PR100 observation stream starting
October 13, 2026. A fresh local export selected recent tutor-bearing page/notebook
scopes and included their available observations through its snapshot boundary.
It contains 21,702 events from October 15 Pacific: actual edit summaries,
execution requests/results, checks, request snapshots and tutor exchanges. Account
columns are pseudonymized; text, code and notebook content remain private.

This establishes that recent rich telemetry exists. It does not establish perfect
event coverage, verified question intent, complete kernel state or a valid
active-time baseline. Missing native identity, truncated windows and unmatched
requests/results are counted explicitly. No private data is committed here.

## Pipeline

```text
fresh private production PR100 events.jsonl.gz
  -> validate native identities and event-specific timestamps
  -> group account + page + notebook session
  -> fixed tutor-anchored observation windows, coverage/size accounting
  -> exact request links + source/execution/check links
  -> Austin’s assembler and adapted source-capture prompt
  -> bounded Gemini assessment with immutable request receipts
  -> factual/reference validator
  -> version-2 local review bundle
  -> Steven’s queue, timeline, findings, and instructor review UI
```

Keep observed facts, model interpretations, and instructor judgments separate.

## 1. Freeze the recent-data pilot

- Use `prepare-recent`; the legacy `prepare` adapter is retained independently.
- Group by account, `analytics_session_id`, and `notebook_session_id`, rather than
  a conversation ID that may be missing on the first request.
- Each window spans three minutes before and seven minutes after a tutor request.
  Do not extend windows or select cases based on model outcomes. Explicitly warn
  that later recovery outside a window is unobserved.
- Require tutor-mode dialogue, a completed request pair, verified request snapshot,
  edit summaries, bound execution results and bound checks for this first
  integration sample. This selects coverage and is not a representative benchmark.
- Reject mixed/unknown modes, conflicting IDs and oversized windows; fail if the
  requested count is unavailable. No truncation to fit a prompt or legacy fallback.
- Select deterministically by seeded hash, at most one window per notebook/page,
  and save source/context/input hashes before any model request.

Exit: five recent windows can export offline with no model calls and all source
references recoverable in the private source file.

## 2. Preserve the PR100 meanings

- Match query/response by exact request ID, unique terminal event and completed
  status; initial null conversation IDs do not prevent matching.
- Verify the SHA256 of the exact request notebook string. Use only the uniquely
  identified active code cell as captured context; keep full snapshots local.
- Actual edit-burst summaries have counts, lengths, revisions and intervals but no
  source text. Never derive a code diff from them.
- Bind submitted source and finished output by kernel/execution/native-cell IDs;
  reject source conflicts or reversed time. Source captures are not edit events.
- Bind checks to the exact accepted execution and checked source. Preserve the
  grader label separately from unknown question intent. A heuristic pass/fail is
  not proof of learning or complete kernel correctness; incomplete output is unknown.
- Preserve occurrence timestamps, page logging sequence, native cells, source line,
  file hash and record hash. Logging-call order and occurrence time have different
  semantics; missing events and equal times remain explicit.
- Do not fabricate question intent from task metadata, or timing/reference metrics
  from the length of an observed window.

Exit: authored regressions catch wrong request IDs, noncompleted responses,
conflicting UUID/sequence, bad snapshot hash, kernel/cell/source mismatches,
missing submissions and incomplete checks.

## 3. Integrate and validate the finding algorithm

- Port the pinned analyzer, six authored assessment fixtures, eleven casebook
  inputs, and original factual-validation tests without replacing Steven’s code.
- Extend records with request/cell/order metadata and explicitly typed edit
  observations versus source captures; version and hash the modified prompt.
- Send the prepared timeline, explicit links and coverage warnings to Gemini.
  Code, outputs and checks are part of this recent-data model input.
- Keep generation separate from local import/export. Save a create-only receipt
  before dispatch; preserve failed/interrupted/completed requests without rerolls.
- Validate every finding’s evidence references and factual assertions. Semantic
  correctness and causal interpretation still require human review.
- Model availability and permission to use the configured credential/provider are
  execution prerequisites; no model result is implied by offline validation.

Exit: the fixed pilot has saved validated results, or a clear failed/rejected state;
reopening results makes no model calls.

## 4. Keep the frontend reviewable

- Retain Steven’s queue, metrics, timeline and review panel, and both synthetic demos.
- Import a version-2 bundle locally; validate the Python-derived JSON Schema plus
  cross-reference, metric, origin, summary and state invariants in the browser.
- Display PR100 notebook observation scope, code captures, actual edit summaries,
  recorded outputs, request IDs, time basis and missing evidence.
- Findings jump to exact evidence, revealing events hidden by timeline filters.
  Show uncertainty and later observed recovery separately.
- Keep not analyzed, completed negative, surfaced, failed and rejected states
  distinct. Do not convert categorical findings into made-up priority scores.
- Store reviews separately by exact dataset identity, with offline review
  download/import and visible storage errors. Clear stale data on invalid imports.
- Keep private bundles out of source imports, public assets, builds and Git.

## 5. Verify and deliver

Run the Python suite, frontend suite and production build; inspect a local recent
bundle in the browser. Scan the staged diff against private source strings and
credentials, then push only implementation/docs/synthetic tests to the integration
branch. Neither source branch changes. No production deployment or public data
publication is part of this task.

## Current status

The recent PR100 adapter prepared five bounded windows with 10 matched tutor
exchanges, 302 actual edit summaries, 48 linked execution results and 8 linked
checks. These are coverage-selected development records, not detection results.
The historical pilot has been superseded. All real records, prepared evidence,
bundles and model receipts remain in ignored local storage.

After Austin explicitly authorized the credential source and recent-data transfer,
the five windows were analyzed with `gemini-3.8-flash`. All five responses completed
and passed the structural evidence validator; all returned `no_supported_finding`.
The analyzed bundle loaded in the frontend with 5/5 completed analyses. Offline
export reconstructed the exact same bundle from the saved receipts without another
model request. This verifies the integration path, not detection accuracy or the
semantic correctness of those assessments. No historical records were sent and
no private source, prompt, response or bundle was added to Git.


## Expanded recent-data experiment

A second read-only production export selected up to 60 recent notebook scopes,
excluding the pages used in the original five-window pilot. It contains 66,448
recent PR100 events. The next development run freezes two disjoint groups before
inference: ten standard windows (3 minutes before, 7 after) with rich observation
coverage, and ten longer windows (5 minutes before, 15 after) requiring matched
completed dialogue but allowing missing notebook/check evidence. Both use the
same analyzer, prompt, response schema, model and factual validator as the pilot.
No passing/failing check value or model outcome drives case selection.

The groups use seeds 16 and 17; the longer group also excludes the ten standard
pages. Preparations retain their selection/budget/exclusion manifests. Public CLI
options now support configurable bounded windows, rich/dialogue coverage, and
repeated `--exclude-prepared` arguments. Page identity excludes previous cases even
when account pseudonyms change across private exports. Oversized inputs still
fail eligibility rather than losing events to truncation.

The selected groups contain 63 matched tutor exchanges, 1,267 edit observations,
425 execution results, and 101 linked checks including 12 failed checks. Sixteen
windows contain multiple tutor requests. Although dialogue coverage allows absent
checks, the seeded longer sample happened to contain checks in all ten windows.
These are development cases, not a labeled evaluation or population estimate.


### Expanded run outcome, October 16

All twenty new windows completed and passed the structural evidence validator.
Nineteen returned `no_supported_finding`; one returned an
`advice_linked_obstacle` candidate. The original decisions, inputs and receipts
remain preserved. Offline export exactly reconstructed the twenty-window bundle
without another model request.

A source-level review of the candidate found later clarification and a
matching-grader pass beyond its ten-minute prompt boundary. A separate paired
25-minute window included that observed follow-up and returned
`no_supported_finding`. This is one additional model call on the same page, not
an independent 21st case or a reroll of the original input. Both assessments are
available side by side in a private comparison bundle. The original factual IDs,
source binding and time checks passed; those checks cannot verify the semantic
interpretation or tutor causality.

Evidence spot checks covered the candidate and three negative cases, including
recovery after clarification and an unfinished case that retained a failing
check. A negative decision is not completion or proof of correct tutoring. No
independent human labels, sensitivity, precision or false-positive rate are
claimed. Follow-up coverage should be reviewed before relying on short-window
flags. The window controls and exclusion regressions pass the 120-test Python
suite; private records and model outputs remain outside Git.
