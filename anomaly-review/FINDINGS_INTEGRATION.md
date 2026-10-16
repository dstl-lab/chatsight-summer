# Session findings in the review frontend

This branch connects Austin's standalone evidence-based analyzer to Steven's
React review interface. It branches from Steven's `codex/anomaly-review-phase2c-phase3b`
(`9dc2f2678ab5b3216bcedbdabd5237e175f3e49b`). The original analyzer comes from
`dstl-lab/dsc10-tutor-jlab`, `codex/session-findings-prototype`, commit
`25a146e10926108bbdfbcfd99438c955d122ac49`; copied-file hashes are recorded in
`session_review/findings/PROVENANCE.json`. Neither source branch is changed.

## Start the interface

```sh
cd anomaly-review
uv sync --locked
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:4173. **Steven’s demo** opens his original synthetic metrics
and authored priorities. **Findings demo** opens Austin's six input-pinned authored
assessments, with accepted evidence and recovery links. It makes no model calls;
those assessments are authored examples, not measured detection performance.
The additional eleven-scenario casebook inputs remain in `fixtures/findings/`.

**Open local review bundle** reads a version-2 JSON file in browser memory. It
makes no upload or model call. The import validates JSON Schema, IDs, references,
origins, analysis states, metrics and summary counts. It clears the prior dataset
on an invalid import. The app does not automatically restore an imported private
dataset after a refresh; reopen the same bundle. Instructor judgments are stored
separately under a dataset-specific localStorage key. **Download reviews** and
**Import reviews** provide an offline backup for this exact dataset. Browser
storage can contain private notes; failures are reported rather than claiming a
review was saved. No shared review server is provided.

## Prepare recent production PR100 observations offline

The current workflow uses recent production notebook observations from
`dsc10-tutor-jlab` PR #100. The old original-ChatSight export is **not** an input
or fallback for this pilot. A read-only fresh export is prepared locally; database
credentials and private source files are not part of this branch.

Run from `anomaly-review` against that recent `events.jsonl.gz`:

```sh
uv run session-findings prepare-recent /private/path/events.jsonl.gz \
  --count 5 --seed 15 --output private-data/recent-pr100
uv run session-findings export private-data/recent-pr100 \
  --output private-data/recent-not-analyzed.private.json
```

Preparation groups by pseudonymous account, page `analytics_session_id`, and
`notebook_session_id`. Each candidate has a fixed window from three minutes before
a tutor request to seven minutes after it. All available PR100 observations in
that scope/window are considered; malformed identities and invalid bindings are
accounted for. It keeps at most one window per page/notebook scope, chooses by a
fixed seeded hash, and freezes the input/context hashes before analysis.

The initial development sample requires a completed tutor exchange, verified
request snapshot, actual edit summaries, source-bound execution results, and
execution-bound checks. Mixed/unknown tutor modes and oversized windows are
excluded. Coverage selection biases the sample; it is not a representative
cohort or an accuracy benchmark. Later recovery outside the fixed window is
unobserved, not absent. The requested count must be available or preparation
fails; it never substitutes historical records.

| Recent production observation | Model/UI treatment |
| --- | --- |
| Tutor query and completed response | Match exact request ID, even when the first query has no conversation ID; preserve occurrence timestamps, page sequence, and native cell IDs |
| Request notebook JSON | Verify SHA256 of the exact serialized request snapshot; include only uniquely identified active code-cell source as context, not the full notebook |
| Cell source changed | Actual edit-burst summary, revision/count/length and interval; it contains no edited source text |
| Execution requested/finished | Exact submitted source and output, bound by kernel/execution/cell IDs, checked for matching source and consistent time |
| Autograder info | Exact execution and checked-source binding; pass/fail remains a text heuristic; incomplete output/result stays unknown |
| Cell creation/deletion/movement/selection | Observed structural activity, not proof of a change in the student’s question |
| Failed/cancelled tutor request | Explicit failure observation; partial text is not a completed tutor answer |

Source captures are labeled separately from edits. Every evidence record has
source-file hash, source line, export ID, and normalized-record hash. Client event
time is distinguished from database logging time. Logging sequence is retained,
but equal occurrence timestamps remain uncertain unless an explicit link provides
order. Task metadata is notebook structure; it does not establish the subject of
typed student questions. Grader labels do not silently become question intent.
The full exported snapshots remain private and local.

The older `prepare` command remains a separate legacy adapter for reproducibility.
It is not used by `prepare-recent` or by the current recent-data pilot.

## Analyze the fixed pilot, then reopen offline

Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in the process environment using your
normal credential workflow. The command does not search sibling repositories or
read a database password. Private course data requires appropriate authorization
for the established Gemini provider.

```sh
uv run session-findings analyze private-data/recent-pr100 \
  --model gemini-3.8-flash --send \
  --output private-data/recent-pr100-analyzed.private.json
uv run session-findings check private-data/recent-pr100-analyzed.private.json
```

The explicit `--send` command sends one request for each untouched selected
observation window, capped at twenty. The recent prompt includes student/tutor
messages, timestamps/IDs, request links, actual edit summaries, captured source,
execution output, checks, explicit bindings and missing-evidence warnings.
Only the prepared evidence is sent; full request snapshots remain local.
Model availability depends on the configured account;
choose and record another model explicitly if necessary.

Requests have create-only receipts written before dispatch. Completed, failed and
interrupted requests are preserved rather than automatically rerolled. The SDK
may retry transport requests independently; actual provider-attempt counts are
not claimed. Results bind the session evidence, prompt, response schema, model and
analyzer source hashes. Changed evidence/configuration refuses cache reuse. Use a
new output filename when exporting; existing files are not overwritten.

To reopen results without another request:

```sh
uv run session-findings export private-data/recent-pr100 \
  --model gemini-3.8-flash --output private-data/recent-pr100-reopened.private.json
```

Results normally live in `private-data/recent-pr100/analysis/`. `--analysis` selects a
different receipt folder, with the same configuration checks. Loading a bundle in
the browser never calls Gemini. If generation or factual/evidence validation
fails, the UI shows insufficient evidence and exposes no accepted finding.

## Interpretation

The analyzer looks for persistent difficulty, request mismatch, and obstacles
associated with trying tutor advice. Accepted findings contain explanatory source
references, recovery, uncertainty and machine-checked factual claims. Those checks
do not establish semantic correctness, causality, learning, or tutor quality.
**No supported finding** means no qualifying finding under this analysis, not that
the tutor was proven correct. Completed-analysis counts distinguish unevaluated
sessions from negative results.

Recent records use bounded page/notebook scope with explicit request and
execution links. Question intent can still be unknown. Event-specific client time
is displayed with its basis. Equal-time records retain order uncertainty.
Missing notebook actions are not inactivity. Active-time percentiles,
post-help failure counts and question completion stay unknown when the necessary
links/coverage are absent. No high/medium priority is inferred from model decisions.
Steven's existing canonical question reconstruction and ranking remain available
as separate CLI workflows for records that meet their explicit linkage contracts.

## Tests and private-data boundary

```sh
uv run pytest -q
cd frontend
npm test
npm run build
```

The public fixtures are entirely synthetic. Do not place a real bundle in source
imports, `frontend/public/`, built assets, or Git. Keep private inputs, receipts,
outputs and reviews in ignored storage such as `anomaly-review/private-data/`.
Recent production exports are processed locally, never embedded in public assets.
