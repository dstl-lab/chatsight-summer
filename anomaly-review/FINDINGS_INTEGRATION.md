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

## Prepare a private historical export offline

Use the `events.jsonl.gz` from the private original-ChatSight export. No production
database access is needed. Run from `anomaly-review`:

```sh
uv run session-findings prepare /private/path/events.jsonl.gz \
  --count 20 --seed 15 --output private-data/pilot
uv run session-findings export private-data/pilot \
  --output private-data/pilot-not-analyzed.private.json
```

Open that JSON in the browser. Preparation streams the source, checks identifiers
and timezone-aware recorded timestamps, accounts for malformed/duplicate rows,
then selects up to twenty eligible conversations deterministically across notebook
strata. It includes exclusively `tutor`-mode conversations with student and tutor
text and a consistent account/notebook identity. Missing or conflicting identity,
missing dialogue, mixed/unknown modes and oversized conversations are excluded
with aggregate counts. Selection is frozen before model inference. This is a
convenience development sample, not a benchmark or a representative student cohort.

One conversation can supply notebook identity for another event in that same
conversation, but conflicting identities are excluded. Export event IDs are
export-local, not original production database IDs. Each selected record retains
the compressed input hash, source line, export ID, and normalized-record hash.
Raw messages and source paths remain private.

Nearby checks are attached only as account/notebook/time context within thirty
minutes of the conversation's observed logging span. They do not establish the
question the student asked about or a linked execution. Notebook captures are
shown as bounded code excerpts with an explicit notice, not as inferred edits or
executed revisions. Full snapshots remain in the original export.

## Analyze the fixed pilot, then reopen offline

Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in the process environment using your
normal credential workflow. The command does not search sibling repositories or
read a database password. Private course data requires appropriate authorization
for the established Gemini provider.

```sh
uv run session-findings analyze private-data/pilot \
  --model gemini-3.8-flash --send \
  --output private-data/pilot-analyzed.private.json
uv run session-findings check private-data/pilot-analyzed.private.json
```

The explicit `--send` command sends one request for each untouched selected
conversation, capped at twenty. The historical prompt includes student/tutor
messages, recorded timestamps/IDs, and missing-evidence warnings. Notebook
captures and nearby unlinked checks are not sent. Their UI presence does not mean
the model considered them. Model availability depends on the configured account;
choose and record another model explicitly if necessary.

Requests have create-only receipts written before dispatch. Completed, failed and
interrupted requests are preserved rather than automatically rerolled. The SDK
may retry transport requests independently; actual provider-attempt counts are
not claimed. Results bind the session evidence, prompt, response schema, model and
analyzer source hashes. Changed evidence/configuration refuses cache reuse. Use a
new output filename when exporting; existing files are not overwritten.

To reopen results without another request:

```sh
uv run session-findings export private-data/pilot \
  --model gemini-3.8-flash --output private-data/pilot-reopened.private.json
```

Results normally live in `private-data/pilot/analysis/`. `--analysis` selects a
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

Historical records use conversation scope with unknown question attribution and
unknown response-completion links. Database logging time is displayed with its
basis; it is not a verified client action clock. Equal-time records retain order
uncertainty. Missing notebook actions are not inactivity. Active-time percentiles,
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
The larger historical export is processed locally, not embedded in the UI.
