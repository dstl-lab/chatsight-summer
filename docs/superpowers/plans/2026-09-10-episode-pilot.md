# Episode Pilot Implementation Plan

> Execute in this task using subagent-driven development for independent components.

**Goal:** Deliver a runnable, snapshot-grounded episode pilot with a development sample and an untouched episode holdout.
**Architecture:** One preparation/annotation module, one localhost review server and static page; reuse existing conversation models and Gemini adapter.
**Tech Stack:** Python, Pydantic, FastAPI, vanilla HTML/CSS/JS; no new dependencies.
**Spec:** ../../2026-09-10-episode-pilot.md

## Constraints

Student text stays under ignored data/. No DB needed. No simulated ground truth. No automatic formal admission. Existing snapshots are immutable. Human and model share the same evidence. Future information is never represented as prior state.

## Tasks

- [x] Fix shared sequence lookup: regress future-run scoping, stale prior runs and unordered inputs; pin the changed derivation in the classifier hash.
- [x] Add `src/labeling/episodes.py`: validate snapshot keys/counts, extract request-response-follow-up windows, sample one per conversation, freeze source/rubric hashes, annotate with phase-specific evidence validation, and expose prepare/annotate CLI commands. Tests use invented dialogues only.
- [x] Add `src/eval/episode_review.py` and `src/eval/episode_review.html`: validated reviewer names, split/task selection, counterbalanced condition payloads, blind coding, evidence selection, atomic save/resume, saved timing and optional instructor action. Test payload blindness, invalid evidence, save/resume and immutable source behavior.
- [x] Prepare 12 development and 35 reserved episodes from the August 11 snapshot (47 eligible conversations; 5 have no tutor response).
- [x] Generate development drafts with Gemini: Minchan explicitly authorized disclosure of the 12 development episodes, including student and tutor dialogue. All 12 drafts in `data/episode-pilot/pilot-v3/bundle.json` pass evidence validation; all 35 reserved episodes and manifest pins remained unchanged during generation. Gemini selects source lines and the application copies exact quotes, preserving the stored annotation format. The provenance pin includes the selection schema and line-rendering version. Source files, episode content and development IDs are unchanged; versions 1 and 2 remain archived and incompatible with the current protocol. See the runbook for commands.
- [x] Run full tests, inspect the page in a browser, perform a synthetic save/resume smoke check, review the diff and document exact run commands and limitations.
- [x] Simplify development review with Accept all, individual Accept/Change/Cannot assess, and preselected evidence in the correction drawer. Add separate workflow/assessment metadata; cannot assess records reviewer inability rather than a student label. Keep coding/comparison manual, legacy records valid and untouched on viewing, and the model rubric/bundle unchanged.

Each code task uses a failing behavioral test before implementation. Final review checks the spec and data boundary, with no extra framework or broad refactor.

Verification of the simplified UI: all 236 Python tests pass, with one pre-existing Starlette deprecation warning. The Node navigation/decision regression and invented-dialogue browser checks pass; accepted, corrected, and unassessable reviews save and restore. The five existing label decisions and notes are preserved, and the real bundle bytes are unchanged. Historical timing from the old UI includes passive viewing and must not support speed comparisons; passive viewing in the new UI creates no writes. The held-out split remains unannotated and outside the current disclosure authorization.

## V4 calibration continuation

- [x] Separate five developmental judgments and document inclusion, exclusion, and evidence rules after seven reviews.
- [x] Add version dispatch while preserving the v3 prompt/schema hash and saved bundles; add paired evidence and context-line validation. All 240 Python tests and the navigation checks pass.
- [x] Prepare the same sample and regenerate only its 12 development episodes under explicit Gemini disclosure approval. Two invalid selections were rejected and retried with the unchanged protocol; all 12 saved outputs pass structural checks.
- [x] Produce an actual before/after preview with a separate semantic audit. Preserve v3 and all seven reviews byte-for-byte; leave all 35 reserved episodes unannotated and unchanged.

The calibration pass is complete. The audit identifies remaining hindsight, task-link, tutor-response, and citation problems; the machine drafts are not validated labels or simulation state. No v4 UI migration or further human annotation was added. See the v4 codebook memo and ignored preview for the proposed next changes.

## V5 input isolation

- [x] Document the observed hindsight cause and isolate pre-help fields in a stateless context/request-only call, keeping v4 category definitions unchanged.
- [x] Pin stage schemas, prompts, input contract, and strict local validation. Preserve v3/v4 hashes and reject cross-stage overwrite. Handle Gemini's unsupported wire keyword without relaxing local validation.
- [x] Verify future-input invariance, merged output, failure/resume, and compatibility. All 246 Python tests pass.
- [x] Generate the same 12 authorized development episodes; retry three blank-line selections with unchanged prompts. Verify live before-help input hashes and preserve the 35 reserved episodes and earlier artifacts.
- [x] Write v4/v5 comparison and semantic audit under ignored data/. Episode 5 no longer invokes future information; context-based intent inference remains unresolved in episodes 7 and 10. No UI migration or additional human annotation was added.

## Approved checking-work distinction and observed absence

- [x] Add v6 checks-work with the approved checking/solution/mixed boundary and earlier request anchors; filter model-visible blank lines after numbering. Preserve prior protocols and artifacts. All 251 tests pass.
- [x] Generate the same authorized sample. Preserve nine valid v6 drafts and three repeated rejections for invented follow-ups; document the separate semantic audit.
- [x] Correct the root cause in v7: derive absent followup from recorded turns with a strict tutor-only stage; preserve observed blank turns and failure/retry behavior. Clarify existing hint/status/task-link rules without changing old definitions. All 257 tests pass.
- [x] Generate 12 valid v7 development drafts on the first pass, verify all 24 actual prompt hashes, and preserve 15 earlier artifacts, seven human reviews, and all 35 reserved episodes. Document remaining mixed/task-link errors without relabeling records or requesting repeated reviews.

## Fixed-codebook model comparison

- [x] Predeclare development checks with human, approved-example, and assistant-audit provenance kept separate. Verify Pro availability, freeze v7 source/prompt hashes, and identify the candidate run separately from its sample/protocol bundle ID.
- [x] Generate the same 12 authorized episodes with Gemini 2.5 Pro. Verify all 24 actual prompt hashes match Flash and all prior source/artifact hashes remain unchanged. Two flagged tutor categories changed; task-link errors remain.
- [x] Prepare six metadata-selected reserved cases for a prediction-hidden two-field pilot review, without model calls or source mutation. Split into three-case packets, verify complete source rendering and empty separate answer records, and leave the active v3 UI untouched.
- [ ] Collect the user's explicit blind-packet answers before comparing new cases with model judgments. No formal reliability or admission inference from the development comparison.
