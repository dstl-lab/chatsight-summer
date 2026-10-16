# Integrate session findings with Steven's review frontend

Prepared October 15, 2026 before implementation. The design below records the
agreed integration plan. Implementation now lives on
`codex/session-findings-real-data`; see `anomaly-review/FINDINGS_INTEGRATION.md`
for current commands and limitations.

## Objective

Use Austin's evidence-based session-finding algorithm inside Steven's existing
session-review interface, with a reproducible local path from recorded course
events to reviewable findings and their exact source evidence. Preserve both
original branches and the private historical export.

## Source revisions and branch strategy

- Destination repository: `dstl-lab/chatsight-summer`.
- Base: Steven's `codex/anomaly-review-phase2c-phase3b`, inspected at
  `9dc2f2678ab5b3216bcedbdabd5237e175f3e49b`.
- New integration branch: `codex/session-findings-real-data`.
- Algorithm source: `dstl-lab/dsc10-tutor-jlab`,
  `codex/session-findings-prototype`, commit `25a146e`.
- Record the full source SHA and copied-file hashes when implementation begins.
- Use a separate checkout. Make no commits or history changes on either original
  branch; do not merge either prototype into main as part of this work.
- Port the selected analyzer, fixtures, and tests into `anomaly-review`; do not
  merge the unrelated Jupyter extension history across repositories.
- Before code, add the dated integration design memo required by this repo's
  working style. Update it as concrete source decisions become known.
- Push the integration branch after verification. Any later PR should describe
  its dependency on Steven's branch; initially compare against that branch so
  the integration changes can be reviewed separately.

## Findings from inspection

1. Steven's React interface imports a static synthetic JSON dataset. It has no
   model adapter, backend, or real-data loader. Its types require `synthetic: true`.
2. The frontend's displayed priorities, reasons, and timing reference bands are
   currently authored demo metadata. Python metric-based ranking exists separately
   but is not wired into that frontend.
3. His canonical normalizer, source provenance, explicit unknowns, metric models,
   and evidence references are reusable. His question-episode constructor requires
   learner/course/cohort/assignment/version/notebook scope and an explicit or
   verified question link; historical records missing these must remain unassigned
   under that constructor.
4. Austin's analyzer already accepts unknown question IDs and missing notebook
   activity. It has three finding categories and a separate factual/evidence
   validator. Its output is not a priority score or proof of semantic correctness.
5. The private export contains 484,652 events and 9,443 conversation IDs from
   February through September 18, 2026. It is gzipped JSONL, not the JSON-array
   document Steven's configurable adapter currently expects.
6. Historical notebook captures and checks do not provide continuous, explicitly
   linked edit/execution traces. No present-day deployment claim will be based on
   this historical export; current-quarter telemetry needs a separate fresh audit.

## Proposed architecture

```text
private historical events.jsonl.gz
  -> streaming source adapter + quality accounting
  -> canonical records + provenance index
  -> conversation-scoped evidence (legacy records)
     OR existing question episodes (explicitly linked records)
  -> Austin's assembler and evidence validation
  -> bounded Gemini assessments, saved once per exact input/configuration
  -> validated findings + recorded timeline + available metrics
  -> versioned review bundle
  -> Steven's frontend, loaded locally
```

Keep three outputs distinct: source facts, model interpretations, and instructor
review decisions. Metric-based ranking remains a separate optional signal.

## Phase 1 — Preserve and port the algorithm

- Establish the isolated branch at the pinned Steven revision.
- Put the reusable analyzer under `anomaly-review/session_review/findings/`.
- Port the three categories, assembly, response schema, validator, and existing
  tests without changing detection behavior during the first port.
- Preserve the original six input-pinned offline assessments. Include the eleven
  authored casebook inputs as additional synthetic examples, with separate origins.
- Add `google-genai` only to the Python analysis path; keep keys out of the browser.
- Record prompt/schema/model/source versions. Any prompt/schema adaptation gets
  its own version rather than silently changing a saved assessment's meaning.

Exit: existing twenty prototype tests pass in the new package, and offline fixture
replay gives the same decisions and validation results. An LLM is unnecessary to
prove that the port preserved behavior.

## Phase 2 — Define one review contract

Create a versioned contract shared by the Python exporter and frontend. Include:

- Dataset ID, input hash, real/synthetic origin, analysis version, model, prompt hash.
- Stable session ID and scope (`conversation` or `question_episode`).
- Known/unknown assignment/question identity, including the attribution basis.
- Timeline source IDs, timestamps and clock basis, provenance references, text,
  observed notebook state, explicit links, and ambiguity/missingness notices.
- Analysis state: not analyzed, completed, failed, or validation rejected.
- Decision: surface, no supported finding, or insufficient evidence.
- Findings with category, explanation, interpretation evidence, checked facts,
  recovery evidence, uncertainties, and validation outcome.
- Metrics with known/unknown values and their evidence; optional ranking metadata.

Validate generated bundles in Python and at the browser import boundary. A failed
analysis must not look like a completed 'no issue' assessment. Keep raw rejected
model output in private diagnostics, not in the accepted-findings display.

Exit: the same contract can represent Steven's synthetic demo, Austin's casebook,
and a historical conversation with unknown question/activity/outcome.

## Phase 3 — Implement the historical-data adapter

Read the existing private export; no new production export or database credentials
are necessary for the first integration.

| Historical source | Treatment |
| --- | --- |
| tutor_query | Recorded student message; retain conversation, mode, notebook, timestamp basis |
| tutor_response | Recorded tutor message; preserve unknown request/completion linkage |
| tutor_notebook_info | Captured notebook-state context, not a code edit or executed revision |
| autograder_info | Recorded check with grader and pass/fail/unknown; execution binding unknown |
| session_start | Observation context, not proof of active work or a complete session boundary |
| experiment/UI/other events | Preserve source access and account for exclusions; not automatically model evidence |

- Stream the gzipped JSONL; do not load 484,652 full records or notebook snapshots
  into the browser or one model prompt.
- Maintain file hash, line/event locator, original export-local ID, and stable
  canonical reference so every displayed excerpt can be traced to its exact source.
- Preserve server logging time as server logging time. Use client time only when
  its format/timezone and clock basis are documented. Ties and uncertain order
  remain explicit; a display sort does not prove causal order.
- Group historical chat by conversation plus consistent account/notebook identity.
  Conflicting identities are quarantined or explicitly split with recorded reasons.
- Do not fill in missing course, quarter, assignment versions, or question IDs with
  invented constants to satisfy the strict question-session builder.
- Keep grader question identity separate from the question a message concerns.
  Nearby same-account/notebook checks are contextual unless a documented mapping
  establishes applicability. Do not infer an execution link from proximity.
- Keep notebook snapshots in a separate observed-state record/sidecar. If included
  in model context, declare the capture-time uncertainty and which portion was sent.
  A snapshot must not be converted to an invented edit or execution event.
- Define fixed scope/size limits. Oversized or malformed cases receive explicit
  exclusions; no silent truncation, deduplication, or deletion of recovery evidence.
- Export a privacy-safe quality summary: counts, accepted/rejected/context-only
  rows, missing question/request/execution links, timestamp issues and usable cases.

Exit: mechanically reconcile all input rows with accepted/context-only/excluded
accounting, then inspect representative bounded joins locally. Real legacy
conversations can appear in the UI even when question metrics are unavailable.

## Phase 4 — Add bounded, reproducible analysis

- Provide separate offline preparation/check, live analyze, and offline export
  commands. Opening the frontend must never trigger a model request.
- First run the synthetic examples through the full UI export path offline.
- Prepare a fixed twenty-conversation development pilot from eligible real
  conversations, stratified by available mode/notebook/context coverage where
  practical, with selection rule and seed recorded before analysis. Do not select
  cases because they yield convincing findings.
- Inspect prompt previews and counts locally before sending. For the first real
  run, send selected dialogue and supported minimal context, not whole captured
  notebooks, embedded images, or the entire historical corpus.
- Use the established Gemini provider/configuration, checking model availability
  during implementation. One application-level request per selected session;
  record transport attempts where possible and avoid automatic rerolling.
- Save assessments against exact input, source/prompt/schema/model pins; reuse only
  matching results. Preserve provider failure, rejection and incomplete states.
- Run the evidence validator before accepting any surfaced finding. Keep later
  recovery and conflicting checks visible. Semantic correctness remains a human
  review question, not something the structural validator proves.

Exit: saved real-session results reopen offline, every accepted citation resolves,
and failed/rejected runs are explicit. The twenty cases are development material,
not a validated detection benchmark or population estimate.

## Phase 5 — Connect Steven's frontend

- Keep his layout, session queue, timeline, evidence navigation and review panel.
- Add local import of a validated review bundle; retain synthetic demo as an
  explicit selectable dataset. No private data is added to source imports,
  `frontend/public/`, JavaScript build assets, or Git.
- Replace synthetic-only labels/types with actual dataset/session provenance.
- Populate the findings panel from the validated model output: explanation,
  category, precise highlighted events, recovery and uncertainty.
- Separate filters for surfaced findings, no supported finding, insufficient
  evidence and not analyzed. Do not fabricate high/medium priority from the
  algorithm's three categorical decisions.
- Keep metric-based rankings separately labeled and eligible only where the
  required question scope and observation coverage exist. Unknown timing/check
  metrics remain unknown; no historical 'typical time' range is manufactured.
- Display notebook captures as snapshots with their limitations. Missing notebook
  actions are not an empty sequence proving no activity.
- Retain timestamp/date/timezone visibility and exact-source access. When an
  evidence link targets an event hidden by a timeline filter, reveal it before
  scrolling and highlighting.
- Namespace local review storage by dataset and session identity, provide review
  JSON download/import, and count reviews for the current dataset only. Explain
  browser storage behavior and keep it separate from model assessments.
- Clear stale session/review state on dataset changes or failed imports; validate
  schemas at runtime rather than relying on a TypeScript cast.

Exit: a reviewer can open a real conversation, understand why it was surfaced,
inspect the supporting/recovery evidence, record a judgment and reopen it without
a model call. The unchanged synthetic demo still works.

## Phase 6 — Validate and deliver

Tests should cover actual integration failure modes:

- Source mapping, ID stability, record accounting, dates/timezones, tied times,
  mixed/missing identity, duplicate events, malformed records and oversized inputs.
- Snapshot-versus-edit separation, unknown question links, grader context without
  execution links, and no fake request completion or active-time measurement.
- Analyzer regressions: false checks, fabricated IDs, wrong-question recovery,
  omitted recovery, unavailable models, rejected evidence and cache invalidation.
- Python-export/TypeScript-import contract, findings-to-timeline navigation,
  invalid-file/stale-state handling, dataset-specific reviews and literal rendering
  of untrusted message/code content.
- Existing anomaly-review Python tests, frontend tests and production build.
- A desktop walkthrough with synthetic cases and a bounded private real bundle.
- Inspect the final staged diff and built assets for private records/credentials.

Deliver the new branch and a concise README with setup, offline demo, local import,
analysis commands, exact data scope, provider behavior, and known limitations.
Keep private inputs, prompts, responses, bundles and reviews in ignored local
storage. Do not deploy or publish real-data pages as part of this integration.

## Suggested commit sequence

1. Dated integration design memo and source provenance.
2. Preserve and package the analyzer with its fixtures/tests.
3. Versioned review contract and private historical-event adapter.
4. Conversation evidence assembly, accounting and offline export.
5. Bounded model runner and saved-result handling.
6. Frontend import, findings display and dataset-specific reviews.
7. End-to-end verification, usage documentation and branch push.

## First milestone and practical boundary

The first milestone is Steven's UI displaying Austin's validated synthetic
findings plus genuine historical conversations, followed by a fixed small real
analysis run. It is not an all-quarter batch, a newly deployed logger, a detector
accuracy study, or proof that a tutor caused a student's difficulty.

New fully linked student telemetry, when available, can later use the existing
strict question-episode route through the same review contract. That is an
extension of this integration, not a prerequisite for the first real-data view.

## Implementation status, October 15

The isolated branch now contains the pinned analyzer, original evidence regressions,
synthetic fixtures, JSON Schema-validated version-2 review bundles, streaming
historical adapter, fixed pilot preparation, durable model receipts, offline
exports and local frontend imports. Findings and instructor reviews remain separate.
Unknown question/activity metrics are preserved. Notebook captures are display-only
bounded excerpts; nearby checks are contextual. Private records remain outside Git.
The legacy synthetic frontend dataset was absent from the source branch because its
`src/data/` location matched the root data ignore rule; it has been regenerated
from the existing fictional fixture as `demo-data.synthetic.json`.

Local tests cover input accounting, conflicting/missing identity, oversized content,
immutable preparation, failed/interrupted request preservation, contract parity,
unknown metrics, invalid imports, evidence navigation and review isolation. Browser
checks verified the authored findings and local import of a bounded real pilot.
No result here establishes detection accuracy or tutor causality. A live private
model pilot remains a separate execution step, and opening the app is offline.
