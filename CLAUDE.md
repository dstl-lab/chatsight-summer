# CLAUDE.md — Top-Down Labeling + Learner-Agent Simulation (one repo, temporary name)

## Saved student fidelity comparison (2026-09-22)

`browser_workspace --fidelity-comparison <help-work-benchmark-v1>` opens the closed
eight-conversation, two-condition, four-draw study without a replay folder. Both
conditions share the current request and recorded tutor reply; history additionally
receives earlier student AND tutor messages. Fixed-file pins, prompt reconstruction,
existing scorer reproduction and message joins verify read-only display. No model
calls, new labels or simulator changes. Mean Brier: history 0.359375, current-only
0.29296875. All references help=yes/work=no; one reviewer and development exposure
preclude general fidelity/adoption claims. This experiment already reached its
stopping rule; do not rerun/relabel it. No untouched learner-separated holdout has
been identified, and conversation IDs are not learner IDs. Memo:
docs/2026-09-22-browser-student-fidelity.md.

## Browser policy creation and explicit runs (2026-09-22)

UI direction: apply shadcn's code-ownership/composition philosophy through shared
native components and semantic tokens. Reuse button variants, fields, neutral
status badges and focus states; no frontend framework migration is required.
Design contract: docs/prototypes/README.md.

HCI audit fixes: literal question excerpts and policy text identify/search starts
and pairs; the single chat opens at the tested question. Neutral Policy A/B and
one-exchange scope clarify the evidence. Use this setup copies only an exact
eligible source and its policies. Unsaved comparison drafts recover per browser
tab/workspace, with resume/discard, inline validation and save/error focus.
Duplicate action controls are reduced and input outlines strengthened. 639 Python
tests pass (three optional skips), seven Marimo and three Node checks pass;
independent review and authored desktop checks complete. No new provider calls.

Wayfinding follow-up: configured policy workspaces land on Tutor policies (empty
ones show setup). Explicit view/legacy conversation URLs preserve replay. Direct
comparison, instructions and saved-results controls replace nested access; ready
policies expand and saved comparison statuses are visible. Drafts and ineligible
sources stay explicit. UI-only change; three Node checks and desktop/independent
review pass. No new calls, labels or comparison data.

Compare now creates frozen policy pairs from eligible saved chat starts through
--policy-workspace, then runs untouched arms only with --send and an explicit
button. Reuses freeze_next/run_both; shared context appears once. Source/run pins,
serialized mutations and GET-only lost-response recovery preserve evidence and
drafts. Failed/interrupted/completed arms are never resent. One serving process;
external additions require reopening. 637 Python tests (three optional skips),
seven Marimo and three Node checks pass; independent and authored browser review
complete. Port8431 uses working copies of 29 conversations (27 eligible), sending
enabled for user actions. All 105 original files unchanged; no new provider calls,
labels or fidelity evidence. Memo: docs/2026-09-22-browser-policy-runs.md. PR #57.

## Policy labs integrated as saved browser comparisons (2026-09-22)

PR #47 corrections verify saved/derived results, use structured receipt lifecycle,
keep observation reads read-only and fix cached-start/context/request attribution.
Browser --policy-comparison opens one saved one-decision pair in Compare; shared
context appears once, fixed instructions and tutor/student outcomes in two columns.
Original --comparison review format remains distinct. No generation or new labels.
618 Python tests (three optional skips), seven Marimo and three Node checks pass;
independent and desktop browser review complete. Authored read-only preview:8429.
Memos: docs/2026-09-22-policy-lab-corrections.md and
docs/2026-09-22-browser-policy-comparison.md. Next: explicit browser pair creation
and generation; larger batches deferred. Main still requires independent review.

## Browser replay usability (2026-09-22)

Conversation-only runs now have ONE chat view with Previous/Next attached. The
duplicate activity list was removed after user feedback. Notebook work and Compare
keep chat beside their distinct content; details reuse the same chat element.
Run details groups research views; source focus and read-only boundaries remain.
No API/engine/evidence changes or new requests/labels. 544 Python tests pass (three
optional skips), three Node checks and both Marimo checks pass; desktop browser
and independent JS review complete. Scope: docs/2026-09-22-browser-replay-usability.md.
Included in browser PR #48; main still requires independent review.
Follow-up clarification: Conversation replaces Scenario; starting context and
student decisions are labeled separately. Pending replies distinguish earlier
playback from the latest saved result, and missing replies within supplied history
are marked as recorded gaps. 27 of 29 current starts have one imported decision;
all 29 end awaiting a tutor. No new generation; 34 browser tests and the controller
check pass. Details in the same usability memo.

## Browser Saved results and chat reading (2026-09-22)

Each verified encounter now includes saved_results_html from workspace_history,
under existing shared locks. Browser hides raw diagnostics and refuses symlinks
in newly read receipt paths; default Marimo rendering is unchanged. Saved results
opens the entire selected encounter's history in center details, explicitly
including later exchanges while chat stays at the selected playback state.
Policy attribution still uses the existing exact delivery matcher, independent
of current drafts. Chat adds compact source headers, clearer role styling, count
and First/Last navigation. 544 Python tests (three optional skips), Marimo/Node
checks pass. All 29 scenarios load, two have confirmed policies, zero receipt
warnings; all 130 evidence files unchanged. No calls/execution/labels. Memo:
docs/2026-09-22-browser-saved-results.md.

## Conversation stays beside the work (2026-09-22)

Connected browser chat now lives in a persistent right sidebar. Replay follows
the selected state; Compare uses only the selected review's shared prefix, never
an unrelated replay or a concatenation of alternatives. Inspect tab is retired;
source/details and tutor controls use the center. Hide/show retains drafts and
selection. Failed/loading reads clear stale chat. Reuse restricted tutor display
formatting and exact source; no engine change. 534 Python tests (three optional
skips), Marimo and Node checks pass; desktop browser and independent review pass.
All 130 evidence files unchanged; no calls/execution/labels. Both previews remain
read-only. Memo: docs/2026-09-22-browser-chat-sidebar.md.

## Existing communication review is visible in Compare (2026-09-22)

browser_workspace --comparison points to the completed cached communication
bundle alongside a notebook/chat launch. Fixed files, closure/provenance hashes,
exact joins and one declared condition are checked before projection; saved
scripts/path metadata are never executed/followed. Closure is pinned at startup.
Compare has separate eight-case navigation, recorded reference + both draws,
existing help/work flags, supplied context and review details. Preserve duplicate
draws/shared judgments and distinguish missing/unclear from no. No generation or
new coding in Compare; replay selection/drafts survive switching. 534 tests,
Marimo/Node checks and independent review pass. Browser cases 1/3/8 verified;
20 review, 105 chat and five notebook files unchanged. Port8428 now serves the
combined read-only workspace. No new scores/calls/labels or fidelity claims.
Memo: docs/2026-09-22-browser-saved-comparison.md.

## Saved tutor replies have readable formatting (2026-09-22)

The connected browser renders restricted Markdown only for tutor display, with
original text retained in Inspect source and literal student messages. Raw HTML,
links/images and fence attributes remain inert. Existing Markdown dependency is
now direct/locked; no engine, prompt, binding or receipt changes. 509 tests pass
(three optional skips), plus Marimo/Node checks and independent security review.
Browser checks verified formatted code/lists, raw source and keyboard code focus;
all 29 scenarios load and 105 chat/five notebook files remain unchanged. Both
8428/8427 previews remain read-only. No calls/execution/labels. Memo:
docs/2026-09-22-browser-message-readability.md.

## Saved scenarios can be selected in the browser (2026-09-22)

browser_workspace --chat-sessions freezes direct-child chat folders at startup,
serves a path-free catalog, and verifies one selected scenario per GET/POST.
Selection is explicit and per-tab; bound submissions and operation messages stay
with that scenario. Symlink/unknown/duplicate selectors fail closed. Switching
resets drafts and clears old content; URL retains selection on refresh. Busy work
disables switching, failed cases retain the catalog, and keyboard focus recovers.
508 tests, Marimo and Node checks pass; independent review found no remaining
blocker. All29selected HTTP views and browser cases1/2/3/29 verified,105files
unchanged. No calls/execution/labels. localhost:8428 serves the readonly collection;
8427 remains the completed notebook, now readonly too. No engine changes or
closed-study reruns. Memo: docs/2026-09-22-browser-scenario-selection.md.
This supersedes the single-session browser limitation below; comparisons remain
separate work. Local audit: data/browser-scenario-selection-verification/.

## Existing chat scenarios now open in the browser (2026-09-22)

Explicit browser_workspace --chat opens one saved chat session, projects initial
and receipt states after existing-loader verification under a shared readonly
lock, and routes bound controls through chat_workspace. Ready status is preserved;
notebook work/changes/activity/checks stay null. Source labels are neutral and
raw origins inspectable. Chat cannot execute checks or load a library reference.
Missing lock/incomplete/tampered records fail closed. No engine/prompt changes.
497 tests, Marimo and Node checks pass; independent review found no blocker.
All29historical workspace scenarios reopen with105filesunchanged. localhost:8428
shows case01read-only; notebook result remains at8427. No calls/labels or migration.
Scope/result: docs/2026-09-22-browser-chat-scenarios.md. Task5complete; collection
selection and matched comparisons are separate work. Closed studies stay closed.

## Live browser walkthrough complete and closed (2026-09-22)

The fresh public authored browser example was continued through three actual UI
submissions: quiet revision -> requested container check (float0.5/pass) -> no-reply.
Three Gemini student requests, one real execution, zero tutor requests/errors;
three decisions unused. Exact offline replay, saved refresh, terminal disabled
control and all18pre-result pins verified. Original protocol is preserved locally;
remaining17input/source pins stay unchanged. No code/prompt/labels changed. The
prepared policy was never delivered; this does not test live tutor generation,
communication realism or grounding benefit. Scope/audit/replay are in ignored
data/browser-workspace-example/live-run; public result is
docs/2026-09-22-live-browser-workspace.md. Do not reroll this closed example.
localhost:8427 displays the saved terminal outcome. This supersedes the fresh
zero-action status below; fidelity comparison remains separate research work.

## Browser workspace supports explicit tutor/student submissions (2026-09-22)

User continued after the saved viewer. browser_workspace now exposes strict bound
POST /api/continue behind --send (default off), reusing student_workspace advance/
respond for one decision. Policy/reference files load once. A single-process lock
blocks parallel submissions; pending reads return202 and UI polls reads only.
Durable pending/failed receipts block restart bypass, including manual replies
against an existing tutor exchange. Drafts survive Reload saved run; completion
closes the editor and displays saved results. No runner/prompt/schema changes.
491 tests, Marimo/Node checks and authored browser flow pass. Exactly3 scripted
student decisions and1 scripted tutor response in a temporary test session; no
Gemini/runtime calls. localhost:8427 now opens data/browser-workspace-example/session
with --send and its policy file: fresh authored task, zero generated actions, key
configuration present. Do not confuse the temporary UI test with a model result.
The old completed examples are unchanged. Docs: docs/prototypes/README.md.

## Browser workspace reads verified saved notebook sessions (2026-09-22)

User approved the simplified desktop layout and continuing. The new local server
src.agents.browser_workspace serves that shell with apps/browser_workspace.js,
using lineage validation/read-only locks to project initial and saved receipt
states, including prior tasks. Notebook/chat, pending replies, net diffs, local
feedback and source context are inspectable. Missing origins stay unspecified;
structured task cells render as text. Unverified reloads clear previous content.
No new provider/runtime calls, writes, labels or fidelity claims. Live controls
and matched comparisons are not implemented here. Existing Marimo controls remain
available. The public notebook example is open at localhost:8427; the disconnected
preview remains at8426. 470 tests pass (three optional container skips), Marimo
and Node checks pass. See docs/prototypes/README.md for launch and limits.

## Browser workspace prototype; simulator fidelity remains the goal (2026-09-22)

User accepted: how accurately can an LLM simulate DSC10 AI-tutor interactions,
and can grounding in real interactions improve accuracy? Instructor tutor-policy
testing is the eventual application. The educator-decision walkthrough was paused
before any judgment; do not resume it or infer answers. User selected a dedicated
browser workspace over the existing Python backend and requested a simple HTML
preview. docs/prototypes/student-workspace.html is standalone, entirely authored,
with Inspect/Simulate/Compare, evidence inspection, step playback and temporary
tutor drafts. No backend, model call, private data or measured fidelity result.
Desktop is the target; user explicitly said mobile support is unnecessary.
The declutter pass removes duplicate navigation, keeps the inspector closed until
requested, and shows playback only in Simulate. Guidance: cognitive-load and
Impeccable distill skills, verified with browser MCP and the Node smoke check.
Keep this prototype separate from the research-scope PR46. See its README for
launch and verification. Backend integration is a subsequent scoped change.

## Workspace carries the tutor library reference (2026-09-22)

Optional notebook-only --reference-file now loads through the existing
LibraryReference schema once at launch. Malformed files/chat use stop; exact
activity library/version mismatch is rejected before generated tutor dispatch.
student_workspace.respond forwards the optional reference to notebook_tutor;
the existing request/receipt records delivery, and the raw reference is not
injected into student input. Manual/quiet steps and reload retain their existing
behavior. No generator/runtime change or new live calls/labels. Authored Marimo
controls and backend regressions reproduce and verify the handoff; 466 tests,
both Marimo checks and Node navigation pass. See
docs/2026-09-22-workspace-library-reference.md. Task21 complete.

## Supplied exercises connect to notebook history (2026-09-22)

notebook_example --previous/API previous reuses notebook_next_task for a completed
encounter, publishing its new session and policy together. Mutually exclusive with
--chat-source; original context/model carry forward, new work/feedback/budget are
fresh. Source locks span publication; all ancestor nesting and changed snapshots
are rejected. No engine/prompt change. See docs/2026-09-22-exercise-continuation-setup.md.
457 tests, Marimo checks and Node navigation pass; independent review found no
issue. Real CLI/replay verified offline at data/custom-notebook-continuation-example
from the authored closed notebook example; previous files and continuity59pins
unchanged. No new model/runtime calls, labels or live run. Task20 complete.

## Workspace loads the prepared policy (2026-09-22)

Fixed a handoff gap: custom exercise setup saved policy.txt but the documented
workspace opened with generic text. Optional --policy-file now reads UTF-8 once
into the editable draft; malformed/missing/blank files stop without fallback.
Omission keeps old defaults. Draft edits survive reload; scenario selection resets
to the initial file content, and restart rereads disk. Existing explicit sending
and saved policy receipts are unchanged. Both notebook and chat modes use it.
The real Marimo-cell regression reproduced the gap before the fix and now checks
edited-draft delivery, reload, disk changes, reset and invalid-file handling with
authored callbacks. 454 tests, both Marimo checks and Node navigation pass;
independent review found no issue. See docs/2026-09-22-workspace-policy-file.md and
updated launch examples. No live calls, labeling, engine or prompt change.
Task19 complete; combined PR43 still requires independent GitHub review.

## Custom notebook exercise setup complete (2026-09-22)

notebook_example now accepts an optional exercise mapping / --exercise-file with
the existing task/activity/evaluation/policy structures, while retaining the
default example and verified --chat-source bridge. The immutable image is a
separate argument; malformed/unknown inputs fail without publishing, and supplied
objects/sources remain unchanged. No engine, prompt, runtime or budget changes.
See docs/2026-09-22-custom-notebook-exercise.md and examples/fruit-count.json.
446 tests, both Marimo checks and Node navigation pass; independent review found
no code blocker and corrected a stale continuity claim in the teammate guide.
The actual public CLI/replay also verified offline at
data/custom-notebook-exercise-example: expected2, no feedback/actions, six unused
decisions. No provider/container calls, labels or new live run. The completed
continuity run's59pins remain unchanged; older snapshots pinning the setup helper
must use their recorded revision. Task18 complete; PR43 still needs GitHub review.

## Second notebook exercise completed and closed (2026-09-22)

Minchan explicitly answered Yes to the exact blocked private-payload Gemini scope.
Saved approval precedes the one dispatch, 03:02:02–03:02:24 UTC. Quiet edit → real
local check (float0.25/pass, revision1) → no-reply; three student requests, zero
tutor requests/generated chat, one container execution, no recorded failures,
three decisions unused. All59pins and exact two-task replay verify; prior0.5
feedback stays in history and current feedback starts null. Both recorded example
and prior simulated activity reach every actual student prompt. Follow-up tutor
policy/reference were configured but never delivered. Private closure/replay are
in data/notebook-communication-continuity/live-run; public result is
docs/2026-09-22-live-notebook-continuity-status.md. No code/prompt change, resends,
labels, automatic third exercise or fidelity/learning claim. This supersedes the
blocked state below. Actual retries unmeasured; at most12adapter attempts.

## Second notebook exercise prepared; dispatch blocked (2026-09-22)

Latest Continue prepares one bounded live continuation using the unchanged lesson
runner and copied create-only dispatcher. The advance protocol is frozen in
docs/2026-09-22-live-notebook-continuity.md; private scope/preflight/approval-block
are in data/notebook-communication-continuity/live-run. All 59 pins and both role
payloads independently verify. The original 10-turn example and previous simulated
activity persist; current work is fresh and current feedback null. Runtime image
availability is verified. Six student decisions / two tutor replies, at most eight
logical requests / 32 adapter attempts and six requested local checks.
Automatic approval review rejected process creation because the new private
payload needs specific Gemini approval despite the standing grant. Nothing was
sent or executed; no dispatch, lesson or steps exist, and all predecessor files
remain unchanged. Scope SHA aaf358850e9f3d63ae09d92b3b4ab1cbace36c8a70c30ff145a1b3163ad74c3c.
Await exact approval, preserve it before one dispatch, then verify replay and close
regardless of outcome. No bypass, automatic retries, new labels or fidelity claim.
This supersedes the earlier no-live-run status; production code is unchanged.

## Recorded example persists across notebook tasks (2026-09-22)

notebook_next_task now carries only the root's explicitly sourced conversation
example and scope, separately from simulated encounter history. Query validation,
the saved prefix hash and predecessor manifest chain bind the source; a carried
content hash rejects altered/missing examples in new successors. The prechange
writer hash ccaa59b9…7476c21b alone permits historical omission. Replay shows the
example only where actually delivered. Arbitrary initialization stays excluded;
one copy counts toward the existing 64KB shared-context ceiling. Engines/prompts
are unchanged. See docs/2026-09-22-communication-continuity.md.
444 tests, both Marimo checks and Node navigation pass; independent review caught
and verified the fix for complete-example deletion masquerading as legacy input.
An offline green-proportion successor is saved at data/notebook-communication-continuity:
exact 10-turn example, previous simulated activity, fresh task/work/evaluator,
zero calls/executions/actions and six unused decisions. All34setup pins verify;
source sessions remain unchanged. The failed forecast's69pins still verify.
No live run, labeling or persona/fidelity claim is queued. Old audits pinning
the changed next-task/replay sources require their historical revisions.

## Work-presence forecast completed; failed screen closed (2026-09-22)

Minchan answered Yes to the exact eight-prefix Gemini scope after the automatic
approval block. payload-approval.json binds that approval to scope/jobs/rejection
before dispatch. All eight forecasts completed 02:23:57–02:25:18 UTC, with no
errors, missing results or adapter retry events (SDK transport retries unmeasured).
Mean multiclass Brier .80625 vs LOCO .612245, constant-half .5, no-work .75;
work-absent group1.081, work-present .348333, equal-group mean .714667.
Four of five work-absent references received work probabilities .70–.90. The
declared development screen fails: no wording component, prompt tuning/rerolls,
new labels or default generator change. The run is complete and closed.
Read-only replay/independent arithmetic verify all69pins and the result; preserve
the exact advance protocol and all original review/source artifacts. See
docs/2026-09-22-work-presence-forecast-status.md and private result/closure/events.
This supersedes the blocked status below. It is a negative forecast result on
eight exposed development cases, not generated-message fidelity, calibration,
reply probability, grounding effect or real-student validation.

## Work-presence forecast implemented; dispatch blocked (2026-09-22)

Latest Continue adds only src/eval/work_presence_forecast.py, a strict probability
schema and future-excluding, ID-free prefix projection. No default simulator or
saved-engine change. Dated advance protocol and subsequent status are in
docs/2026-09-22-work-presence-forecast{,-status}.md. Reuse the eight just-coded
references for one exposed-development forecast screen, conditional on a next
message being recorded; no new labels or message generation. Existing scorer
supplies leave-one-conversation-out frequency baseline .612245 (multiclass Brier
0–2); fixed .5 forecast scores .5, no-work scores .75. No model result yet.
69 pins, 36 visible turns and all eight source/label joins independently verify;
442 tests, both Marimo checks, Node navigation and authored arithmetic pass.
The exact 8-request/32-attempt Gemini scope is saved in ignored
data/episode-pilot/work-presence-forecast-v1. Automatic approval review rejected
process creation: it requires specific approval for this private payload and
destination despite the standing grant. Zero requests, no dispatch/event ledger.
Preserve approval-block.json and scope SHA
80573690b3e7e834fc132f233fe2ab8fae94fa7050e5f8628a9ccb8f6cfd7e16.
Do not bypass/retry without required approval. After approval, run once, retain
failures, score and close; no rerolls, automatic adoption or new review queue.
The prior cached-review pass remains closed and its original pins unchanged.

## Cached-message coding and report complete; pass closed (2026-09-22)

The returned 23-message/46-flag form is complete with no missing/unclear values.
Literal chat text and normalized JSON are both preserved; only HTML indentation,
escaped key underscores and the Done heading were removed. Exposure=no remains
a self-report; these are still previously exposed development cases. Independent
transcription and arithmetic audits pass, including all 50 preparation pins.
Recorded help 8/8 and work 3/8; generated help 13/16 and work 10/16. In five
work-absent cases, 6/10 generated draws present work; in three work-present cases,
2/6 omit it. Both groups now support the descriptive balanced work Brier, 5/12
(constant-no-work rule .5); this is no adoption threshold or grounding benefit.
See docs/2026-09-22-cached-communication-results.md and the matching private
result/intake/closure artifacts. Preserve the frozen page, rules, mapping and
received answers. Close item 14; no further review, new generation, prompt change
or second-reviewer request. Original studies remain closed. This set has only
one historical chat condition and does not validate the notebook agent.

## Fixed cached-message review prepared; human export needed (2026-09-22)

Minchan's Continue advances the inventoried scope to one help-work-v1 review.
Eight cases, 23 distinct messages/46 flags, unchanged original prefixes and
definitions; case 5's shared draw judgment retains both occurrence weights.
The existing page is served only from cached-communication-review-v1/ui on
127.0.0.1:8425. Opaque case/candidate IDs and order are frozen; origins, old labels
and private mappings stay outside the page. All answers/reviewer details blank.
50 pins, source joins, exact HTML/HTTP access and authored draft/report checks
pass. Browser automation blocked a temporary authored file test; no bypass or
live browser walkthrough. User opens the provided localhost link themselves.
The private report helper supports missing/unclear flags and independent per-flag
case exclusion; balanced work Brier needs both comparable reference groups.
See docs/2026-09-22-cached-communication-review.md and ignored matching folder.
Next input: one returned JSON export. Preserve its exact bytes and verify frozen
files before scoring. If review stops early, preserve the partial form and close
as incomplete; no forced adjudication. No model calls, source label conversion,
second-reviewer dependency, replacement cases or automatic generator adoption.
All old studies stay closed; this pass cannot estimate a grounding benefit.

## Cached communication scope inventoried, no review launched (2026-09-22)

The accepted step verified eight old recorded references and 16 cached replies:
two identical-input draws from one historical chat generator, not two conditions.
Case 5's draws have identical text/context, so a possible common help-work-v1 pass
needs at most 23 distinct messages/46 flags, retaining both occurrence weights.
Zero compatible prior judgments overlap; old v7 categories must not be converted.
Case 1 retains only the first of eleven follow-up messages, per the original unit.
Coverage of work-absent/work-present references remains unknown under this rubric;
help is a separate flag, with help-only coverage reported separately.
See docs/2026-09-22-cached-fidelity-scope.md and ignored cached-fidelity-scope-v1
inventory/replay. This is a separate development-readiness diagnostic; earlier
studies stay closed. No packet, review handoff, model calls or labels were created.
The possible one-pass ceiling is specified, not launched. It cannot establish a
grounding benefit, validate the notebook student or support generator adoption.

## Conversation-conditioned notebook run completed and closed (2026-09-22)

Minchan explicitly answered “Approve this single run” to the exact private prefix,
derived-context and Gemini destination question. payload-approval.json binds it to
the frozen scope and earlier rejection. One dispatch ran 00:26:14–00:26:50 UTC:
quiet edit → real local check (float0.5/pass, revision1) → no-reply. Three student
requests, one execution, zero tutor requests/chat/errors, three unused decisions;
at most 12 adapter attempts, actual retries unknown. No rerolls or queued runs.
Actions/code match the earlier separate unconditioned demonstration; this is not
a controlled effect estimate. No generated communication exercised the claimed
benefit of the historical example. Policy/reference configured but undelivered.
All 84 pins and read-only replay verify. Preserve initial artifacts, source chat,
older walkthrough and rejection/approval chronology. See
docs/2026-09-22-live-notebook-communication.md and ignored matching live-run
overview/replay/closure. This supersedes the blocked status below; the fidelity
gate and paused labeling are unchanged. PR #43 still requires GitHub review.

## Conversation-conditioned notebook run prepared, not sent (2026-09-22)

The current Continue prepared one run of data/notebook-communication-example/session:
six student decisions, at most two tutor replies, eight logical requests/32 adapter
attempts, existing Gemini 2.5 Pro and local runtime. Both roles would receive the
private original 10-turn prefix plus authored task/current work and later feedback.
Independent preflight passed all 84 pins, exact inputs and mocked dispatch guards.
Automatic approval review rejected process creation because this specific private
payload/destination needs explicit authorization. No dispatch, model/check call or
student step exists; initial session and source artifacts are unchanged. Preserve
scope/protocol/preflight/approval-block files under live-run. Do not retry or
bypass the rejection; await explicit user approval for this saved scope. See
docs/2026-09-22-live-notebook-communication.md. No labels or rerolls are queued.

## Conversation example for an authored notebook task (2026-09-22)

On codex/notebook-communication-context, notebook_example accepts --chat-source.
PR #45 merged into parent PR #43 at 1680abd with the tested tree unchanged;
it is not yet on main. Continue from codex/selection-results.
Reuse chat._load and the existing initialization path; copy only the original
query.prefix, separately from current authored task/work/dialogue. Exclude
simulated continuations and identifier metadata from model context; keep source
path and hashes in private provenance. Both student and tutor see the example.
See docs/2026-09-22-notebook-communication-context.md. This is an opt-in input
bridge, not a validated persona or adopted fidelity fix; later next-task transfer
does not preserve arbitrary initialization. Engines/prompts remain unchanged.
441 tests pass (three optional container skips), Marimo/Node checks and independent
review pass. Ignored data/notebook-communication-example contains one offline
setup from existing case 1: 10 original turns, six student contributions, cached
simulated reply excluded, six unused decisions, zero model or execution calls.
Original sources/public walkthrough remain unchanged; preserve their old pins
and use historical revisions for all-source audits. Task 12 complete. No labels,
rerolls or live experiment queued. Parent PR #43 still requires GitHub review.

## Lesson policy visibility repaired (2026-09-22)

Saved results now discovers notebook lesson/tutor-* records as well as workspace
tutor-exchanges/*, using the same context/reply/continuation validation. The lesson
policy is shown as configured, separately from confirmed delivery. Failed,
interrupted and malformed records remain visible. See
docs/2026-09-22-lesson-saved-results.md. Full suite: 439 passed, three optional
container skips; Marimo/Node checks and independent review pass. Existing notebook
replay and all six saved chat cohort views verify without changing evidence.
Only the display renderer's source hash changes among the public walkthrough's
77 pins; use the recorded historical revision for that all-source audit. Student
engines, prompts and old pins remain unchanged. No new model calls, execution or
labels. Task 11 complete; PR #43 still requires independent GitHub review for main.

## Public notebook live walkthrough closed (2026-09-21)

After the next Continue, ran the prepared data/notebook-example/session once
through the existing notebook_lesson runner. All initial task/table/work/dialogue
were public authored content; no private historical student payload. The frozen
live-run/scope.json records standing authorization, initial prompt/state, policy,
reference, 77 source/setup pins and a six-student/two-tutor ceiling (eight logical
requests, 32 adapter attempts).

Actual sequence: quiet revision → requested container check → generated no-reply.
Three Gemini 2.5 Pro student requests, one real check returning float 0.5/pass on
revision 1, zero generated tutor replies or errors. Three decisions remain unused;
no-reply closed the encounter. Actual retries are unknown, with at most 12 adapter
attempts for the three recorded requests. No rerolls or new labels.

The configured policy/reference were not delivered to a generated tutor; only the
authored initial hint was present. No generated chat was emitted, and no initial
failing check occurred in this live run. Do not claim tutor-policy effects or a
fixed chat hallucination problem. audit.json and replay.html verify actual saved
prompts, actions, bound check feedback, all 77 pins and unchanged read-only replay.
Repeating the lesson is rejected. See docs/2026-09-21-live-notebook-example.md.
Keep the old preparation verification and initial.html intact. Task 10 complete;
all older studies and source pins remain unchanged, generator/UI work stays as
previously scoped, and combined PR #43 still needs independent review for main.

## Public notebook setup (2026-09-21)

The existing notebook engine is now reachable without private experiment inputs:
src.agents.notebook_example creates an explicitly authored four-row proportion
task, initial count-as-proportion code, private expected float and concise hint
policy. Require an immutable runtime image ID; creation validates and publishes
session plus policy together, with no execution or model calls. Existing paths and
dangling symlinks are refused. See docs/2026-09-21-notebook-example.md and the
teammate quickstart section 2b for viewing, optional live lesson and HTML replay.

The session has six student decisions; the documented lesson caps tutor replies
at two, at most eight logical requests/32 adapter attempts if explicitly run.
No such live run occurred in this packaging step. A fresh local example is saved
at ignored data/notebook-example/session with initial.html for offline inspection.
Keep it separate from all frozen historical and authored proof artifacts.

432 tests pass (three optional container skips, one upstream warning), both Marimo
checks and Node navigation pass. The new integration test separately passed two
actual local container checks: wrong2 → quiet edit/feedback cleared → correct0.5,
then unchanged saved replay. Actions were scripted test callbacks; legacy origin
tags do not turn those into provider-generated behavior. Independent review found
no substantive issue. Student/tutor engines, prompts, schemas and existing source
pins stay unchanged; this does not repair or validate chat-only hallucinations.
Task9 is complete; labeling and UI redesign remain paused. This setup joins the
existing isolated branch and PR #43, still requiring independent main review.

## Live cohort completed and closed (2026-09-21)

PR #44 merged into codex/selection-results as 0ba649b. Combined PR #43 now includes
the closed selection result and three-scenario coordinator; independent review
against main is still required. Do not treat its old docs-only description or
the older branch notes below as current scope.

The bounded demonstration is frozen in ignored chat-cohort-live-v1:
three existing historical-group cases, hint/direct policies, one new decision
each, Gemini 2.5 Pro both roles, at most 12 logical requests / 48 adapter attempts.
See docs/2026-09-21-live-cohort.md. Exact six tutor prompts, dynamic student-prompt
templates, schemas and 106 file pins are saved; independent audit and 25 focused
workflow tests pass. run.py reuses the coordinator with an exclusive dispatch
receipt, preserving every outcome and stopping after one invocation.

After automatic approval review blocked process creation, Minchan explicitly
answered “Yes, approved” to this exact disclosed Gemini payload. The new
payload-approval.json binds that reply to scope/disclosure/prior rejection before
dispatch; preserve the earlier authorization and rejection records. One invocation
completed: six tutor replies, six student replies, zero no-replies/errors/missing
conditions; 12 logical requests, at most 48 adapter attempts (actual retries unknown).
All child budgets are exhausted; no resends or further generation are queued.

audit.json verifies all 106 source/startup pins, exact tutor and dynamic student
prompts, receipt linkage and unchanged read-only replay. OVERVIEW.md shows all six
actual exchanges. Distinct policy text did not consistently yield distinct tutor
interventions; generated task details/output/error claims are not recovered
notebook evidence. This confirms operation only, not fidelity or policy effects.
Original sources, authored proof artifacts, closed studies, live workspace and
paused labeling remain unchanged. Keep this demonstration closed; no new review
batch or generator changes. PR #43 still needs independent review against main.

## Three-scenario policy workflow (2026-09-21)

codex/chat-cohort adds a thin coordinator around chat_policy_pair: exactly three
distinct frozen source conversations, the same model and two policies, one new
student decision per condition. Existing pairs keep their budgets, identities,
bindings and receipts; there is no new generator, scheduler ledger or UI. Create
and show are offline. Run requires explicit send, preserves failures and advances
only untouched ready peers; completed or interrupted arms cannot resend. A changed
group plan aborts; unrecorded errors propagate; comparison symlinks are rejected.
See docs/2026-09-21-chat-cohort.md. Eight new tests pass; full suite 430 passed,
two optional skips, one upstream warning. Marimo and Node checks pass.

Ignored chat-cohort-v1 holds the historical-group prepared from frozen handoff
cases 1–3, all six conditions untouched. Original source hashes still match.
Its separate authored-group has three scripted replies, two no-replies and one
saved provider failure; twelve injected callbacks, zero model calls. Reopen and
completed rerun change no files or dispatches. OVERVIEW.md shows both groups.
Independent review confirmed the source/containment and failure protections.
Existing interactive model schemas already omit the field that broke the recent
selection evaluation; no shared engine or provider repair was needed. Leave old
source pins, live workspace, closed studies and paused labeling unchanged.
PR #43 remains the separate results review; this feature branches from its commit
0599523. No live cohort comparison or new labels ran, and no fidelity claim follows
from this engineering check. Before later research use, fix its scope and stopping rule.

## Automatic continuation selection closed (2026-09-21)

PR #42 merged the offline diagnostic as b179876. Results follow-up is on
codex/selection-results in the existing isolated episode-pilot worktree. Minchan
explicitly approved sending the frozen private dialogue/options to Gemini after
the initial automatic-review block; payload-approval.json binds that approval.
The first dispatch failed on unsupported additional_properties: four errors and
one interruption, no choices. Preserve original run.py/results.json/source pins.
A frozen transport amendment removed only that wire-schema field, kept strict
local validation, and sent only the 33 untouched jobs. All succeeded, zero resends;
at most 53 adapter attempts across both phases, below the 152 ceiling. The original
five missing choices remain missing in the combined report, not replaced.

Result: history 8/16 and current 8/16 on the same complete pairs, zero accuracy
difference and 16 ties (8 both-correct, 8 both-wrong). Actual choices agree 15/16.
Paired lexical 7/16, shortest 4/16, longest 6/16; coverage history 16/19, current 17/19.
All-19 missing-outcome delta bounds: -15.8 to +10.5 percentage points, not a CI.
See docs/2026-09-21-recorded-continuation-selection.md and the ignored matching v1
folder for protocol, amendment, sources and receipts. This is recognition of logged
continuations, not generation fidelity; the cases have prior development exposure.
Close the comparison and retain the generator. No labels, failed-case rerolls,
option/prompt tuning, generator adoption or new comparison is queued. Keep the
bulk audit, UI redesign and closed six-case pass unchanged. Public engines and
dependencies did not change; private transport checks cover the compatibility fix.

## Joint instructor evaluation closed (2026-09-21)

Minchan completed six cached recorded/generated continuation comparisons. After
case 1, the announced question changed from help/work coding to comparative
likelihood. Recorded messages were preferred in four cases; both were possible
in two, without a stated ranking. All 24 help/work flags remain unassigned.
See docs/2026-09-21-joint-fidelity-check.md and ignored joint-fidelity-check-v1
for the amendment, exact replies and source mapping. Prior exposure, one draw,
assistant facilitation and changed questions limit this to development feedback.
The working hypothesis concerns answering tutor prompts versus observed student
communication patterns; no stable trait or improvement is established. Retain the
generator; the binary measurement gate remains unmet. The six-case pass is closed,
with zero new calls and no further review or generation queued. Keep the bulk
audit and UI redesign paused. PR #40 is now merged to main at 93904ef.

## Main integration and contributor checks (2026-09-20)

Minchan completed PR #30's merge; GitHub records squash commit 2720455 on main.
Its file tree matches the reviewed 87baed6 exactly. The merged suite passes 419
tests with two optional container skips, and both Marimo apps validate. Packaging
task 6 is complete. The quickstart now clones main; private sessions still need
their matching source revision. The old review-pending notes below are historical.

PR #40 adds .github/workflows/tests.yml for the existing
offline tests, Marimo checks and authored Node navigation check on pull requests
and main. Use locked dependencies, Python 3.13 and Node 22, read-only repository
permissions and pinned official actions. Do not supply private data or credentials,
or change branch protection. The optional container tests stay opt-in. No student
engine, prompt, live session, labeling or deferred UI work changes in this step.
The first GitHub run, 35516294840, passed 419 tests with the expected two optional
container skips; Marimo and Node checks passed too. Task 7's clean-run acceptance
is complete. PR #40 subsequently merged at 93904ef. All 195
frozen source pins and 87 workspace startup files continue to verify locally.

## Consolidated simulator review (2026-09-20)

PRs #31–#39 are merged into their parent branches, leaving one combined PR #30
against main on codex/corpus-summary. Each consolidation preserved the tested
tree exactly. Main is unchanged and GitHub still requires one independent
approving review; the final merge must use squash. No protections were bypassed.
The full suite passes 419 tests with two optional container skips; both Marimo
apps validate. The only integration-review defect was the receipt fallback below,
fixed in ef531a3. All 195 frozen source pins and 87 workspace startup files verify.
The audit and UI redesign remain paused. No new labels, model calls or data exports.

## Integration review fix (2026-09-20)

The workspace now catches structural receipt-read errors during initialization,
Reload and saved-history loading. A missing result field previously raised an
uncaught KeyError before the fallback could render. The authored regression uses
the actual Marimo cells and standalone cleanup, keeping readable prior records,
the damaged-record warning and Reload available without generation or file repair.
No source-pinned engine changed. All three review scopes are complete; this small
workspace defect was the only actionable finding before stack consolidation.

## Teammate setup (2026-09-20)

The teammate quickstart is docs/teammate-quickstart.md. The create-only
src.agents.chat_demo command saves entirely invented, scripted source dialogue
and tutor/student responses through the existing chat runner and policy pair.
Both branches finish after one new decision: A exhausts its budget and B has an
authored no-reply. The model identifier is authored-offline-demo; no provider is
constructed. Visible policies and seeded context identify the fixture as authored.
This demonstrates setup, replay and saved results, not student fidelity or policy
effects. Existing engines, prompts, private sessions and the live workspace remain
unchanged. No new labels or model calls. Task-list item 6 packaging is ready;
integration remains pending the independent GitHub review of combined PR #30.
Do not bypass review or resume the paused audit to integrate this work.
Verification: 418 tests passed, two optional container checks skipped; both Marimo
apps validate. A clean temporary checkout installed the locked workspace packages
from the local cache, created the demo and passed the new offline/copy/no-overwrite
check. Standalone browser checks covered both apps, saved results, reload and
scenario switching. Existing 195 source pins and 87 workspace startup files verify.

## Fidelity target and measurement limit (2026-09-20)

Task-list item 3 selected excess work/evidence presentation in student chat.
The eight-case help/work report replays exactly: recorded work0/8, grounded26/32,
current-exchange23/32. A new constant-flag diagnostic gives always-help/no-work a
zero combined Brier error on those homogeneous references, showing why that score
cannot validate preserving appropriate work submissions. Balanced work-flag error
would require both reference groups and is currently unavailable. Retain the
generator; no new model/judge requests or labels. Item4 is deferred, not a queued
experiment or a reason to resume the paused audit. No coding procedures are pooled.
See docs/2026-09-20-student-fidelity-target.md and the ignored aggregate diagnostic.
UI redesign also remains deferred; packaging current tools for teammates can proceed.

## Fixed chat-policy comparison (2026-09-20)

TASKLIST.md item 2 is implemented by chat_policy_pair and the separate Marimo
comparison app. Prepare only from a frozen first-reply session; import its cached
response into fresh independent identities, freeze both policies and equal new
decision budgets, and preserve terminal/error outcomes. Default acceptance is one
new decision per arm with authored responses; no live policy comparison was run.
The original workspace and source-pinned student engines are unchanged. Minchan
confirmed generation works and deferred layout redesign to the later VS Code-style
workspace. Next is selecting one measurable fidelity improvement from existing
evidence, not more bulk labels or repeated plausibility checks. See
docs/2026-09-20-chat-policy-comparison.md.

## Saved-result inspection (2026-09-20)

TASKLIST.md item 1 is complete: the Marimo Saved results tab reads existing chat
and notebook receipts, linking policies only through matching pre-step bindings,
tutor text and saved continuation results. Failed/interrupted records remain
inspectable when session replay fails; no repair, retry or new generation occurs.
Student engines/prompts are unchanged. See docs/2026-09-20-workspace-saved-results.md.
The next proposed item is two-policy comparison from the same starting chat context.

## Existing chat scenarios in the workspace (2026-09-20)

Minchan approved connecting the 29 cached chat scenarios to the Marimo workspace:
select a scenario, set a tutor policy, continue a bounded interaction, reopen the
saved result. Use separate new session identities under ignored
data/episode-pilot/chat-workspace-v1/sessions; never continue the frozen handoff
sources directly or regenerate their first replies. The original student generator
and source-pinned engines stay unchanged. A chat-specific workspace adapter supplies
visible dialogue to the tutor and binds delivery to the displayed state. Recorded,
simulated and intervention messages are distinct; notebook activity is unknown.
No new labeling queue, benchmark or one-off plausibility check. See
docs/2026-09-20-chat-scenario-workspace.md for operation and limitations.

## Workspace direction and tutor-policy continuation (2026-09-20)

Minchan's intended interface is a notebook-focused VS Code/Cursor-style workspace:
notebooks on the left, student–tutor chat on the right. Defer the larger redesign
as requested; Marimo is the current prototype, not the final layout. Continue
with optional policy-generated tutor replies so the researcher need not manually
write every tutor message. Reuse the existing tutor/runner, explicit one-exchange
controls, displayed-state bindings and saved receipts. No manual labeling queue.
See docs/2026-09-20-workspace-tutor-policy.md.

## Marimo intervention workspace (2026-09-19)

Minchan approved continuing to saved-session controls. The notebook workspace in
apps/student_workspace.py uses tutor_context.snapshot and a small bound-step
helper in src/agents/student_workspace.py. Viewing/reloading is offline. Only
explicit UI callbacks can dispatch, only with --send=true, one student decision
at a time. Both displayed hashes go to the existing runner; no changed prompts,
engine, receipt format or bypass of terminal/budget/pending-operation protections.
The tutor form appears only for a pending student message. No new labeling queue.
Marimo is an optional workspace dependency; see
docs/2026-09-19-saved-student-workspace.md for use and verification.

The separate authored example in data/episode-pilot/student-workspace-v1/session
starts with six unused decisions. Browser checks use a separate invented fixture
and injected adapters, not new Gemini samples. Do not reopen old closed demos.
This is an operational interface, not new evidence of persona fidelity or learning.

## Standing preference: minimize manual labeling (2026-09-19)

Minchan explicitly instructed: "yes, do that. minimize manual labeling unless
absolutely necessary." The 86-message audit below is PAUSED. It does not block
simulator development. This supersedes older instructions to await more coding.
Preserve all frozen evidence and browser drafts; do not silently assign missing
labels. Use existing judgments and automatic diagnostics, with their limits.
Request human labeling only for a specific consequential decision that existing
evidence cannot resolve, stating the smallest useful sample and stopping rule.
No standing queue, replacement bulk batch or repeated plausibility checks.
See docs/2026-09-19-minimize-manual-labeling.md.

Expose the existing three-task saved replay without generating another demo.
Then prioritize researcher intervention using the existing saved-session commands,
coordinating with the Marimo viewer work. Keep the current generator; unresolved
semantic fidelity does not prevent mechanism/UI development. The local review
address now serves a pause page with optional access to the unchanged old form.

## Recorded behavior audit (2026-09-19; paused)

Minchan approved proceeding from the corpus summary to a conversation-level
behavioral benchmark. The bounded next step reuses the existing 29 query cases and
cached original/candidate outputs: 29 references +29 original replies +28 candidate
replies =86 messages /172 help-work flags. Candidate's one no-reply is retained
outside the reviewer UI. No new model/DB calls or changes to old experiments.
See docs/2026-09-19-recorded-behavior-audit.md and ignored
data/episode-pilot/recorded-behavior-audit-v1/ for the protocol, private mapping,
coverage, preparation and portable UI. This is a new secondary analysis of exposed
saved messages, not a replacement length comparison or probability calibration.

The original plan was ONE human coding pass; Minchan subsequently paused it.
The following scoring instructions apply only if that audit is explicitly resumed.
Preserve returned JSON, verify the frozen preparation, and use
src/eval/cached_communication_scoring.py for the fixed report. Primary is signed
original-generator work-incidence gap, accompanied by its 2x2 disagreement table;
help and same-case candidate comparisons are secondary. Each flag has its own
complete-pair denominator. Do not assign labels, treat no-reply as no/no, request
another plausibility round, generate replacements or adopt a changed simulator.
26/29 cases start in February; ten have no earlier student context. Target is the
first next message, including the one case with a five-message follow-up block.

## Corpus description (2026-09-19)

Minchan approved step 1 of the simulation-fidelity study: describe the existing
corpus before selecting another comparison. The offline corpus report is complete;
see docs/2026-09-19-corpus-summary.md and src/eval/corpus_summary.py. Eight canonical
exports contain 455 memberships / 252 distinct conversations. Fresh message
analysis uses only the existing 156-conversation development library (1,400 student
messages), preserving the old split. Median message length is 34 characters; the
largest 16 conversations supply 36.1% of messages. Equal-conversation statistics
are reported separately. About 60% of the full corpus starts in February; most
development student timestamps/modes are missing. Known modes include tutor and
chatgpt. These selected exports are not a representative or untouched student
sample. The canonical chat snapshots and saved notebook-pair metadata provide no
usable learner mapping for this corpus; conversation IDs are not student IDs.

The create-only private aggregate report is at
data/episode-pilot/corpus-summary-v1/report.json. Source hashes and independent
arithmetic verify; old experiments remain unchanged. No model/DB calls, labels,
reviewer tasks, generator changes or replacement benchmark. This descriptive step
is closed. The next study must separately freeze its observable endpoint, sampling,
comparison and stopping rule; do not resume one-off plausibility checks.

## Current implementation focus (2026-09-15)

The grounded local-task continuation is COMPLETE and CLOSED in
data/episode-pilot/grounded-chat-v1/. Minchan explicitly approved case 6 with
"Yes" after the initial automatic-review rejection. exact-scope-approval.json
records that reply and six hashes before dispatch; preserve both records.
One Gemini 2.5 Pro request completed in one adapter attempt, zero retries.
The student prepended the exact already-visible name assignment to its three
cached code lines. It stayed within the locally described task; no code ran.
The full assignment, data values, grading, learning and fidelity remain unknown.
One reused plus one new decision exhaust the fixed budget. Exact prompt/binding/
replay, all 224 preparation pins and prior evidence verify; independent audit
passed. No production source, prompt or frozen protocol changed. Private
REPORT.md/report.json preserve the exchange; see docs/2026-09-15-grounded-chat-result.md.

The initial saved-chat demonstration is now closed: 29 handoffs plus the
missing-context and grounded-task continuations. Do not start another one-off
sample to recheck the same mechanism or ask for more plausibility ratings.
Use the saved sessions as fixtures for researcher interaction, coordinating with
the existing Marimo viewer work rather than duplicating it. A further fidelity
study needs a separate behavioral question and stopping rule.

The one saved-chat continuation is COMPLETE and CLOSED under
data/episode-pilot/chat-clarification-v1/. After the initial automatic-review
rejection, Minchan explicitly replied "Yes, I approve" to the exact private
payload/Gemini scope. exact-scope-approval.json preserves that reply and five
scope hashes before dispatch; the earlier rejection/standing approval remain.
One new Gemini 2.5 Pro request completed in one adapter attempt, zero retries.
The separate session has one reused reply plus one new decision, zero remaining.
Offline replay matches the receipt; all 207 preparation pins and both earlier
sets of 29 sessions remain intact. Independent audit passed. No generator source,
prompt or frozen protocol changed. No further request or plausibility rating.

The student supplied assignment-like text after the tutor asked for missing
question text. That content was absent from the input: preserve it as generated
scenario content, not recovered question 1.6 or historical assignment evidence.
The run demonstrates saved-chat continuation, not student fidelity, learning or
a tutoring-policy effect. Budget exhaustion is not student silence. Private
REPORT.md/report.json retain the exchange and receipts; see
docs/2026-09-15-chat-clarification-result.md. Keep the preparation memo unchanged.
A subsequent grounded interaction needs task text in its starting context or an
explicitly authored task before generation; repeated calls cannot recover missing
assignment state. Do not automatically extend or reroll this closed run.

The conversation handoff is COMPLETE on `codex/chat-continuation-handoff`.
PR #28 merged as `9ac3e45` INTO PR #27's branch, not main; PR #27 still awaits
the required human review. Its tree is identical to the completed saved-chat
branch. This increment changes no simulator source or generator prompt.

All 29 already-generated original-control replies are imported locally into
separate sessions under data/episode-pilot/chat-continuation-handoff-v1/.
Every import matches the original query, prompt, schema, model and response.
All reopen awaiting-tutor with one reused decision and five remaining. There
were zero new provider requests, new samples or labels. INDEX.md links one
readable tutor handoff percase; contexts/ contains current state exports.
handoff.json preserves original call indices/generation times and local import
times with source/output hashes. New step timestamps describe cache imports,
not fresh model calls. The earlier initial29 sessions and closed comparison
are unchanged. See docs/2026-09-15-chat-continuation-handoff.md.

Use the imported sessions for later interactions instead of regenerating their
first replies. A next tutor reply is supplied intervention; no recorded future
can be appended after divergence. Later generation needs its exact private-data
send scope handled separately. This is a usable conversation handoff, not an
additional benchmark, persona-fidelity result or another plausibility-review loop.

The saved-chat workflow is COMPLETE in PR #28
https://github.com/dstl-lab/chatsight-summer/pull/28 on `codex/saved-chat-student`,
stacked on PR #27 while its required human review is outstanding. `src/agents/chat_student.py`
reuses the strict historical Query, unchanged continuation prompt/schema/branch
helper and existing atomic-save/lock helpers. Create/show are offline. One step
generates one reply or no-reply; later steps require a supplied tutor response
and the exact inspected session/state binding. Unique session IDs isolate even
identical seeds. Fixed budget, terminal error/no-reply, pending-before-dispatch
and exact replay prevent accidental resends. No notebook runtime or label state
is invented. Code in chat is text only. See docs/2026-09-15-saved-chat-student.md.

All 381 tests pass, two optional container checks skip. The private preparation
under data/episode-pilot/saved-chat-student-v1/ initializes all 29 existing query
prefixes as separate ready scenarios, each with zero decisions and a six-decision
budget. All first prompts exactly match the frozen original-control prompts;
earlier comparison files and pins remain unchanged. No model calls, new labels,
historical notebook demonstration, UI or new fidelity result. These are dialogue
scenarios, not reconstructed people or calibrated student personas. `prepare.py
verify` checks the untouched preparation; do not rerun create-only preparation.
Later private-data sends need their exact scope handled separately. The 58-request
approval and completed comparison below do not authorize a replacement benchmark.

PR #26 is MERGED as `0f1a586`. Continue in the same isolated worktree on
`codex/student-communication-candidate`. A separate 19-line candidate helper,
`src/eval/student_communication.py`, adds an explicit student-only communication
history field from the already visible prefix. Old instructions, schema and
`student_continuation.py` stay unchanged. Chat-only wording was tested before;
the new variable is prominence of observed student messages, not another rule.
See the frozen docs/2026-09-15-student-communication-candidate.md.

The fixed comparison is COMPLETE under
data/episode-pilot/student-communication-candidate-v1/. After the initial
zero-send rejection, Minchan explicitly approved the exact private-prefix/Gemini
scope; exact-scope-approval.json and dispatch-start.json preserve that sequence.
All 58 requests returned valid outcomes, using 61 adapter attempts (case 8 candidate
needed three retries). Original: 29 replies. Candidate: 28 replies, one no-reply.
On 28 paired replies, length MAE was 127.357 original versus 126.107 candidate;
primary paired difference −1.25 characters. The same-case constant 35-character
baseline was better on length (75.679); retrieval was 393.357. Candidate median
length/error fell, but neither that nor literal formatting flags establish less
extra work, relevance, persona fidelity or realistic silence. Case 4 no-reply is
excluded from paired scores and retained as a separate disposition.

Decision: RETAIN THE CURRENT GENERATOR; no automatic adoption or further prompt
experiment. See docs/2026-09-15-student-communication-result.md and private
REPORT.md/report.json. One fixed report closes this run. Replay verifies 58 slots
and all 59 preparation/source pins. The source commit passed 376 tests, with two
optional container tests skipped. Source generator/schema and older experiments
remain unchanged. Do not rerun create-only send/score or tune this frozen batch.
PR #27 records the separate candidate and completed development result.

The first existing-data baseline is COMPLETE. `src/eval/retrieval_baseline.py`
retrieves the recorded next message from a train-only TF-IDF prefix library;
query targets are excluded, conversation/known-learner overlaps rejected, and
blank messages/no lexical match kept distinct. Run with
`python -m src.eval.retrieval_baseline INPUT.json OUTPUT.json` (create-only output).
The frozen protocol is docs/2026-09-15-historical-response-baseline.md; leave that
file unchanged because the private run pins it. Results/inputs/references and
verification are in ignored data/episode-pilot/historical-response-baseline-v1/.
1179 examples from156 conversations supplied29 responses for29 separate query
conversations, excluding all55 minimum known continuation-exposed conversations
from queries. All source windows and joins independently reproduce. Length MAE
381.586 versus74.172 for the constant train-median35-character baseline; one7594
error contributes68.6% of total retrieval error. This is a narrow mechanical
diagnostic, not help/work coding, contextual appropriateness or improved fidelity.
374 tests pass, two optional container tests skip; a full authored-harness future
mutation leaves split, inputs and predictions unchanged. No model/DB calls,
labels, prompt tuning or changes to old benchmark evidence. Stop this fixed run;
the next model candidate/comparison requires its own frozen decision, not automatic
rerolls. A baseline now exists; repeating its construction is not a new milestone.

Minchan corrected the main priority: the next quarter is not imminent, so build
and evaluate simulated students with the data already available. Future logging,
deployment and new collection are NOT prerequisites for the main research flow.
The completed logging PR is a separate supporting improvement. This supersedes
older statements below that put collector verification before all further
simulator work; that verification gates claims about newly logged data only.

Reuse the existing historical chat prefixes, captured-work initialization,
continuation/action helpers and saved-session machinery. Do not repeat the
already completed three-action historical notebook demonstration or build another
importer. The next development priority is the known excess-work/narration
communication mismatch, with a simple baseline and a fixed comparison on what
historical records actually observe. Prior exposed examples may inform development
but are not a fresh holdout. Keep completed help/work and notebook forecast batches,
labels, prompts and results intact; any changed model is a separate candidate.
No exhaustive label taxonomy, repeated plausibility review, or invented execution/
stop/learning ground truth. New private-data model sends still need their exact
scope handled separately; this priority correction itself sends nothing.
See the current-direction note in docs/2026-09-15-simulation-progress-summary.md.

### Completed logging work (separate from the main simulation flow)

Minchan approved the future logging implementation with "Let's do it" after the
coding-assistant tracking comparison. Implemented in generalized tutor PR #11
https://github.com/dstl-lab/jupyterlab-ai-tutor/pull/11 at `adff528` (initial `3843d12`), separate persistent
worktree ../tutor-request-logging on codex/request-work-logging. See
docs/2026-09-15-request-work-logging.md. Streamed requests retain exact work/context,
request IDs, source hashes and native cell IDs; responses/failures join by request
ID. Execution records bind submitted code to kernel message IDs and reply+idle,
with bounded text, qualified grader heuristics and explicit incomplete outcomes.
20 frontend unit tests, two browser tests, TS/extension build, changed-file
lint/format and independent reviews pass. The browser test uses invented work and
a real local Python kernel with scripted tutor/intercepted collector; source-bound
output and two distinct request snapshots verified. Private receipts/logs are in
data/episode-pilot/tutor-logging-integration-v1. Logging remains best effort; no
deployed retention claim. No model/DB calls, new ratings, historical reruns or
deployment. Main/initial PR startup failure traced to Tornado6.5.9 versus Jupyter
Server2.21.0; CI-only bound restores local startup, runtime requirements unchanged.
All six PR checks now pass; PR #11 is ready for required human review, unmerged and
undeployed. User asked about latency: serialization/copy/hash precede
dispatch, logging uploads asynchronous; latency remains unmeasured and needs a
representative deployment check. One approving GitHub review is required.
Implementation/PR approval does not authorize starting real collection.
For use of future logging: review the concrete PR, then verify an invented example
through an approved installation/collector. Existing-data simulation proceeds
independently. The
earlier source-audit-only/proposed status immediately below is historical.

Main-flow source audit located the actual lab tutor/logger repositories; see
`docs/2026-09-15-logged-work-boundary.md`. Old DSC10 client at3eab46cd and pre-April
8f8957f0 send sanitized notebook each request but persist source only on the first
completed turn, re-reading it after streaming. New generalized client7ffe89e has
the same limits. Sanitization omits native cell IDs; grader events lack request/
execution/source bindings. Collector078e54cd stores arbitrary payload unchanged.
No durable per-turn notebook archive found in the inspected old backend; deployed
versions/external traces remain unverified. Historical captures are response-time
work, not verified exact tutor-request inputs. Preserve all old results and pins.
A minimal future change would capture exact request-time work per turn with shared
request IDs, schema/client version and retained cell IDs; it is proposed only.
No upstream/DB/model/UI change. Minchan says assume the two teammate tasks handed
off: new runner exercises and a read-only Marimo viewer. Do not duplicate them;
continue core work independently. Scope for future-session logging needs a decision.

PR#25 is MERGED at 35ae189; continuation branch is codex/observation-contract
in the same isolated worktree. Preserve its ignored historical research evidence.
Minchan explicitly selected MARIMO for the eventual educator/researcher simulation
workspace, motivated by Python source and readable diffs. See
`docs/2026-09-15-marimo-and-observation-contract.md` and the two open-ended teammate
briefs in `docs/2026-09-15-teammate-explorations.md`. No UI implementation or new
Marimo dependency yet. Keep explicit student/check actions distinct from reactive
UI reruns. A bounded local source search found consumers/parsers but no deployed
tutor emitter/version; real task/revision/check bindings remain unverified.
The next evidence needed is one replayable recorded example bound to that logger
version, or a precise account of the missing fields. No new models or labels.
The new-branch baseline passed371 tests, two optional container tests skipped.
The older PR#25 merge/review status below is historical and superseded.

The offline observation-window audit is COMPLETE; see
`docs/2026-09-15-observation-window-readiness.md`. Same-notebook capture comparisons
are possible, but same-question identity and next-action endpoints are unverified.
Pair3 includes three later tutor replies outside the forecast prompt; pair2 has
at least one later linked student query. Net-state forecast results remain valid
within their stated conditional scope and unchanged; do not tune or rerun them.
No new DB/model calls, human labels or simulator changes. Next engineering work
should verify a common real/simulated observation contract before a fidelity study.
Minchan explicitly authorized merging PR#25 if ready; this supersedes all older
keep-draft/unmerged instructions below. Full suite: 371 passed, two optional
container tests skipped; three Node checks pass; independent code reviews found
no blockers. Main's organization rule requires one approving GitHub review and
squash merge; do not bypass it. Preserve this worktree's private evidence.
All older preparation/approval/merge-status entries below are historical.

The fixed V2 next-capture work run is now COMPLETE; see
`docs/2026-09-15-next-visit-work-v2-results.md`. Minchan explicitly approved the new
two-request/eight-attempt cap. The separate explicit-approval-response.json binds
seven unchanged artifacts and precedes both requests; prior inferred authorization
and rejection remain preserved. Two logical requests/two adapter attempts yielded
two valid forecasts. Pair2: observed1 changed cell, predicted7, TP1/FP6/FN0/exact0.
Pair3: observed4, predicted1, TP1/FP0/FN3/exact1. Unchanged baseline misses1/4 with
no extra edits. All58/54 code positions were forecastable. No correctness tests,
chat, execution, labels, replacements or exclusions. Independent raw-cell counts,
approval/source pins and exact score replay pass; V1 failures and earlier notebook/
help-work artifacts remain unchanged. These two exposed positional comparisons
show uneven work-extent/location forecasts, not action-policy fidelity, learning
or a general baseline ranking. Close the batch with its report: no further review,
rerolls, prompt tuning or automatic model runs. A future fidelity study must fix
its observation boundary, sampling and baseline before generation. Keep PR#25
draft/unmerged. The older pending V2 entries below are historical.

The corrected next-capture schema now passes a live authored smoke check:
one logical Gemini request/one adapter attempt, expected edit received and locally
validated, no code execution. See `docs/2026-09-15-next-visit-work-v2.md` and ignored
`data/episode-pilot/next-visit-work-v2/`. V2 is separately prepared with unchanged
initial contexts/inputs/targets/disclosure/runner/scorer; only the two unsupported
provider schema fields were removed. Independent audit and offline checks pass.
However, automatic approval review rejected the V2 private-data resend before
process creation because prior permission covered only the exhausted V1 batch.
Zero V2 real-data requests/attempts and no run.json. Preparation inferred renewed
authorization from the latest continuation; that inference was not accepted.
Preserve its approval-response.json and send-blocked.json. Obtain explicit consent
for two NEW requests/eight adapter attempts with the SAME private excerpts to
Gemini, record a separate bound approval before dispatch, then run once. No
workaround, replacement of V1 failures, more samples, labels or human fit review.
The specific live schema issue is resolved; student forecast results remain absent.
V1 and earlier benchmark artifacts remain unchanged. Keep PR#25 draft/unmerged.

The two next-eligible-capture requests have now run after Minchan explicitly
approved the exact payloads and requested the project recap first. The recap was
created and linked before dispatch; see `docs/2026-09-15-simulation-progress-summary.md`.
The run exhausted two logical requests/eight adapter attempts, with zero forecasts:
Gemini rejected root/nested additional_properties fields (HTTP400). Both errors and
the earlier automatic-review rejection remain preserved. No behavioral score or
replacement request exists. See `docs/2026-09-15-next-visit-work-results.md`.
The root cause was new forecast configs omitting the existing Gemini-compatible
BeforeHelpSelection config. The failed helper is preserved byte-for-byte privately
and at Gitf9c44f5. Both classes now reuse the compatible config with strict local
validation; the new regression failed first and all17relatedtests then passed.
No prompt/scoring/runtime change. Current helper/test pins intentionally differ
from the failed experiment; use preserved originals for its source audit. Exact
failure scoring still reproduces. Live acceptance of the correction remains
untested; first perform an authored schema smoke check before any separately
bounded real-data run. Do not rerun or replace this exhausted fixed batch.
The former pending preparation below is historical and superseded by this result.
Keep PR#25 draft/unmerged; no new human labels or plausibility review are needed.

The next-eligible-capture work forecast is prepared but NOT RUN; see
`docs/2026-09-15-next-visit-work-forecast.md` and ignored
`data/episode-pilot/next-visit-work-v1/`. This is an explicit net-state forecast,
not a next-action score or a change to the production student. The pure helper
`src/eval/notebook_forecast.py` projects initial source + matched first exchange,
applies in-scope net edits and compares changed positions against unchanged source.
Pairs 2/3 from the prior exposed check recover uniquely; all 58/54 initial code
positions are supplied, with 1/4 changed positions in separately stored targets.
Two Gemini 2.5 Pro logical requests maximum (eight adapter attempts), one per case.
Exact prompts are 35,900/25,765 characters; no future work, timing, outputs or
identifying metadata. Private identifying text may remain within source excerpts.
17 related tests, the private future/no-resend control and independent preparation
review pass. Automatic approval review rejected dispatch before process creation:
standing approval did not specifically authorize these private sources/exchanges
to Gemini. Zero requests/attempts and no run.json. Preserve send-blocked.json;
obtain exact authorization for the unchanged disclosure, record its bound receipt
before dispatch, then run the two fixed requests once. No replacements, new labels,
rerolls or automatic adoption. Prior notebook-pair/help-work pins remain unchanged.
Keep PR #25 draft/unmerged. The prior availability check below remains closed.

Minchan asked to continue after the fixed help/work benchmark closed. The bounded
notebook-pair availability check is complete; see
`docs/2026-09-15-notebook-snapshot-pairs.md` and ignored
`data/episode-pilot/notebook-snapshot-pairs-v1/`. One read-only historical metadata
inventory found 5,921 eligible adjacent capture pairs across 222 learner identities.
These are candidates, not validated transitions. Three pairs were fixed by metadata
hash order, at most one per learner, before content fetch; no replacements.
All six captures parse and pass endpoint attribution/window checks. Two pairs
have equal cell layouts and exact non-code source, with one/four changed code
positions. The third has three more code cells overall and unresolved alignment.
None has stable cell IDs. These are net changes between captures, not recovered
intermediate actions, grader-to-source bindings, tutoring effects or learning.
The three exposed pairs are development evidence, not a holdout. The next possible
benchmark must align notebook observation boundaries and the simulator's single-cell
scope before scoring. The availability check stops here; no models, labels, prompt
changes or further plausibility review. Existing help/work results remain closed
and unchanged. Keep PR #25 draft/unmerged.

The fixed help/work benchmark is now COMPLETE; see
`docs/2026-09-15-help-work-results.md`. Minchan returned all 72 messages/144 flags
in one JSON form, preserved byte-for-byte under
`data/episode-pilot/help-work-benchmark-v1/received/review.json`; prior exposure is
self-reported unsure. No missing/unclear flags, no notes, all eight cases included.
The frozen scorer produced `coding-result.json` once; independent arithmetic agrees.
All eight references are help=yes/work=no. Earlier-dialogue draws are help32/32,
work26/32; current-exchange-only help30/32, work23/32. Mean two-flag Brier is
0.359375 versus 0.29296875; paired difference +0.06640625 (higher error with earlier
dialogue in this sample). The mismatch is frequent additional work/evidence, while
help requests largely remain. Homogeneous reference flags, four draws/condition,
one reviewer and uncertain exposure limit the conclusion. No positive-work or
negative-help reference coverage, reliability, general history effect, notebook
action fidelity or learning claim. All original generation/review artifacts remain
unchanged; the generation-only reports retain their historical pending-coding status.
No new model calls, relabeling, adjudication or prompt changes. The prescribed
stopping point has been reached: no further coding input is required; do not rerun,
extend or auto-tune this benchmark. Retain production behavior and keep PR #25
draft/unmerged. Further research needs a new decision, not an automatic next batch.

Minchan approved one finite recorded-behavior comparison and selected help-seeking
versus work submission with one fixed blind coding pass. The protocol is frozen
in `docs/2026-09-15-help-work-benchmark.md` and ignored
`data/episode-pilot/help-work-benchmark-v1/`: eight distinct conversations selected
without target-text criteria from 29 eligible windows/14 conversations, excluding
47 known continuation conversations across 252 deduplicated conversations. Four
draws each for full available dialogue and current-exchange-only: 64 logical Gemini
2.5 Pro requests, at most 256 adapter attempts. The only input difference is earlier
context. No recorded next messages or source identities enter prompts. The two
observable help/work flags are independent, including both yes and explicit
unclear; one blind pass, then complete-case paired binary Brier plus all coverage
and exclusions. No tuning, replacement draws, automatic adoption or second batch.
The portable grouped-message UI and strict offline scorer are implemented; 12
related tests and the private future-exclusion/no-resend/package canary check pass.
Independent pre-freeze audit passed. After the initial automatic-review rejection,
Minchan explicitly answered Yes to sending the exact frozen excerpts to Gemini.
The separate `approval-response.json` binds the unchanged disclosure/inputs and
predates dispatch; preserve both the original rejection and preparation grant.
The fixed run is complete: 64 valid replies, zero final errors/no-reply, one adapter
retry and 65 adapter attempts. Physical HTTP attempts below the SDK are unmeasured.
No replacements or prompt changes. Exact offline replay and independent final
audit pass: 38 preparation, four approval, three review and 12 completion-file
hashes match. The 72 blind review messages (64 generated plus eight recorded) and
34 shared prefix turns map exactly to source; origins/conditions stay outside HTML.
`run-summary.json` and `RUN_REPORT.md` record generation only. At that stage, no
human judgments or behavior score existed; the completed intake above supersedes
that pending state. The requested input was one completed coding form from
`ui/index.html`, served on loopback at http://127.0.0.1:8422/ with only the UI folder
exposed. The page begins blank and provides browser-local drafts and JSON export.
Do not resend, repackage or begin another batch. The frozen scorer has now run once
and the fixed report closes the benchmark. This supersedes older pending-
benchmark statements below; the incomplete six-case history ablation remains paused. These
audited same-course exports cannot establish a student-separated/pristine holdout,
notebook action fidelity, learning or transfer. The existing notebook engine and
all prior artifacts remain unchanged. Keep draft PR #25 open and unmerged.

The prepared third task has now run once under `multi-task-history-v1/run-plan.json`:
quiet code edit -> requested passing check at float 0.4 -> chosen no-reply. Three
student requests, zero generated tutor replies and one container check; three of
six decisions remain. Both previous records appear unchanged in all three student
prompts. The optional tutor API note was not delivered. All three linked tasks
replay exactly; six distinct prior sessions/35 files and eight preparation
artifacts remain unchanged. The earlier preparation-only report/replay is retained;
new `RUN_REPORT.md`, `run-summary.json` and `completed-replay.html` record execution.
Automatic review initially rejected dispatch; exact payload/source inspection
proved all content authored/generated with no real-student data. The same command
was accepted on reconsideration with that evidence; preserve rejection and audit.
No rerolls, labels or human ratings. This closes the authored continuity checkpoint.
Minchan asked whether progress is concrete: distinguish the functioning simulation
prototype from unvalidated behavioral fidelity. The recommended next milestone is
a fixed recorded-behavior comparison against a generic baseline. Its then-pending
recommendation is superseded by the completed fixed comparison and human coding
report above.

The multi-task history extension is complete. New `notebook_next_task` handoffs
retain a flat oldest-first `earlier_encounters` list plus the immediate
`previous_encounter`, reconstructed from a verified saved chain and bounded at
64,000 UTF-8 bytes. Shared ancestry loading in handoff/replay checks each edge;
old source-pinned engines and receipts remain unchanged. Replay shows every task
and only the historical records actually delivered at each initialization.
Related suite: 32 passed; independent ancestry audit passed. Six distinct earlier sessions
replay exactly, 35 distinct prior files remain unchanged and 60 historical report hashes
match. The original preparation under `data/episode-pilot/multi-task-history-v1/`
retained both completed encounters (4,334 bytes) and made no new model requests.
The subsequent third-task execution is recorded above; both stages remain saved.
This proves retention and delivery, not learning or fidelity. No new labeling or
history-ablation run. See `docs/2026-09-15-multi-task-history.md` for use,
scope and the unchanged local-manifest trust boundary. This supersedes the older
one-predecessor limit below for new handoffs.
The original verification counted eight session paths/44 file paths; relative and
absolute aliases duplicated two sessions/nine files. Corrected counts above use
resolved paths. Original verification artifacts remain unchanged.

The prepared teaching pair has now run once per condition under the frozen
`teaching-pair-v1/run-plan.json`: six student decisions/two follow-up tutor replies
maximum per condition, same policy/reference, A then B, no rerolls. Both used three
student decisions: identical quiet source edit -> requested pass at float 0.5 ->
chosen no-reply. Six logical model requests and two actual container checks total;
physical provider attempts are unknown. Neither condition chatted, so no tutor
reply was generated and no API reference was delivered. Three decisions remained
per student. Reports and static replays preserve both outcomes. Exact offline
replay and 49 earlier artifact hashes verify; no labels or production code changed.
This is an end-to-end authored comparison mechanism, not evidence of teaching
equivalence, learning or behavioral fidelity. Stop at this fixed report; do not
rerun to obtain a difference. See `docs/2026-09-15-teaching-pair.md` for results.

The next bounded engineering increment is complete: `notebook_teaching_pair`
prepares two alternative initial tutor replies using the unchanged saved-student
engine. Shared task/work/prior dialogue/evaluation/budget remain identical; only
the final tutor text differs in the student prompts. Private branch identities
and staged publication isolate checks and prevent a partially prepared pair.
This does not fork a progressed learner. Existing student/tutor/lesson APIs can
continue each child. See `docs/2026-09-15-teaching-pair.md` for commands and limits.
An authored hint-versus-worked-answer pair was prepared under ignored
`data/episode-pilot/teaching-pair-v1/`; its later execution is recorded above.
Related suite: 31 passed. Independent review found no concrete issue. No new
labeling, production engine edits, or old trace changes occurred during setup.

Minchan explicitly directed continuation with one completed review because the
second will be delayed. This supersedes the two-form waiting condition below and
in earlier handoff documents. The single-review pass is complete in ignored
`data/episode-pilot/fidelity-coding-readiness-v1/single-review-v1/`; reviewer 2 is
optional later evidence, not a simulator-development blocker. Reviewer 1 supplied
5 help / 2 code / 1 work labels. Cases 2 and 8 differ from historical assisted
coding at revision and code-plus-help boundaries; preserve both coding sets.
No inter-rater agreement, fidelity score, adjudication or new model batch. The
older chat generator differs from the current notebook student; no routing defect
or production behavior change is justified. Two existing scripted continuation/
lesson checks pass. See `docs/2026-09-15-single-review-decision.md`. Keep repeated
plausibility review and history ablation paused; continue engineering independently
of the delayed form. Benchmark design and coding reliability remain unvalidated.

Reviewer 1's returned form is saved byte-for-byte in ignored
`data/episode-pilot/fidelity-coding-readiness-v1/received/reviewer-1/`, alongside
an intake receipt. All eight case IDs, allowed labels and required-note rules
pass validation; independent intake review agrees. Prior exposure is self-reported
false. The export lacks a packet ID, so association follows the handoff context.
All four original packet artifacts, including blank forms, remain unchanged.
The original two-form comparison is deferred by the newer direction above.
No labels were assigned or changed by the assistant; no model calls or tuning.

The approved work while reviewers code is complete: `src/eval/behavior_scoring.py`
scores supplied probabilities against training frequencies, checks declared
conversation/student separation (even excluded records), and reports paired
encounter/group means with coverage, failures and exclusions. Its committed
`tests/fixtures/behavior_scoring_toy.json` is invented: paired Brier .3 vs 11/24;
group means .35 vs .375. No real benchmark or output labeling was run.
`src/eval/notebook_replay.py` exports a static read-only view of the existing
two-task simulation after ancestry checks. The completed toy report and replay
are in `data/episode-pilot/offline-evaluation-tools-v1/`; original sessions and
reviewer artifacts remain unchanged. Related suite: 27 passed. Scoring review
and browser replay inspection completed. See
`docs/2026-09-14-offline-scoring-and-replay.md` for commands and limits.
Stop at these artifacts: no new model batch, no scoring the exposed eight-case
readiness set, no automatic history-ablation restart. The later single-review
decision above removes the reviewer wait; real benchmark protocol/budget is pending.

Minchan requested a UI instead of the eight-case packet. The portable builder
`src/eval/coding_review.py` and HTML template produce one self-contained page per
reviewer, plus a local handoff index. Generated pages are in
`data/episode-pilot/fidelity-coding-readiness-v1/ui/`; original forms and packet
remain unchanged. Reviewers see one case, frozen context, seven existing options,
required notes where appropriate, browser-local drafts, and copy/download answers.
No accounts, external requests, shared response store or model calls. Give each
reviewer only their assigned HTML; copied/exported answers retain the original
form shape. Browser drafts do not sync across computers. Mechanical browser tests
used a separate packet identity; they are not human judgments. Completed human
answers remain the next input. See the UI section of the next-task-history memo.

The new `src/agents/notebook_next_task.py` initializes a fresh task with shared
observed history from one completed, generated no-reply encounter. It preserves
the old terminal session, excludes its private evaluator/provenance and does not
recursively carry earlier initialization. Both agents see the shared record.
Fresh work, feedback, history, budget and branch identity belong to the new task.
Initialization and ancestry are staged before atomic publication. The related
suite passes 56 tests with two optional container integrations skipped.
In data/episode-pilot/next-task-history-v1, the generated follow-on student quietly
edited, requested a passing check at 2, and chose no-reply in three decisions.
No tutor reply was generated. Both encounters and older traces replay unchanged.
This demonstrates history delivery and task continuity, not a measured history
effect or learning. See docs/2026-09-14-next-task-history.md.
Minchan specified "2 reviewers" for a fixed independent coding readiness pass.
The handoff in data/episode-pilot/fidelity-coding-readiness-v1 contains only the
eight recorded next messages from the exposed communication development set,
their exact prefixes, existing v7 action definitions and two blank separate forms.
Prior labels and generated candidates are omitted. No reviewer messages were
sent and no model benchmark launched. No ratings were received at preparation;
reviewer 1's later return is recorded above. Do not fill forms with model labels,
restart plausibility review/history ablation or claim this set is a holdout.

The new `src/agents/notebook_lesson.py` runs one bounded encounter by alternating
the existing student and tutor transactions automatically. It preserves cumulative
student usage, separately caps tutor replies and records one create-only `lesson/`
directory per session; interruptions cannot automatically resend through a fresh
output path. Existing student/tutor commands provide explicit continuation after
inspection. See docs/2026-09-14-notebook-lesson.md. No prior engine module changed.
The related suite passes 50 tests with two optional container integrations skipped.
One authored proportion run in data/episode-pilot/notebook-lesson-v1 completed five
generated student decisions: quiet edit, requested TypeError, quiet revision,
requested pass at 0.5, chosen no-reply. One decision remained. No student chat was
generated, so there were zero generated tutor replies and the optional tutor API
note was not delivered. Two-tutor alternation is tested offline, not by this live
trace. Exact replay, source/input pins and unchanged earlier sessions verify.
This is a working bounded mechanism, not learner fidelity or learning evidence.
No reroll or human plausibility review is pending; the review loop remains paused.

Minchan asked how the tool generalizes. The current increment separates a private
scalar evaluation from the visible task, using the existing notebook action loop
for distinct counting and category proportion. See
docs/2026-09-14-task-portability.md. `create --evaluation-file` accepts an expected
scalar; neither model prompt nor worker input receives it. Feedback binds its
hash, and edits clear current feedback. Omission retains legacy distinct counting.
This deliberately revises runtime/session/wrapper source pins: exact original V1
and V2 sessions replay unchanged; new operations use V3 receipts with current
source hashes. Other source/schema changes remain unsupported. Completed older
experiments retain their recorded commits and must not be regraded.
The final related suite passes 44 tests with two optional integrations skipped;
the new two-task container integration separately passes. Authored action controls
in data/episode-pilot/task-portability-v1 show failed and passing checks for both
operations. The original proportion formula returned 0.0 because Python iteration
over the Babypandas Series yielded no values; the Series.sum correction returns
0.5. Preserve all five session checks and two diagnostics. No model requests or
human review occurred in this increment. This establishes narrow software task
portability, not behavior fidelity, persona validity or transfer across courses.

Minchan set presentation work aside and directed continuation of simulated-student
implementation. A saved notebook student can receive a supplied tutor reply and
continue with the same work and history; see docs/2026-09-14-continuing-student.md
and src/agents/notebook_student.py. The tutor can now inspect its current selected
cell, pending message, net changes since the previous supplied tutor exchange,
and revision-bound feedback with src/agents/tutor_context.py. Exported context can
bind the next reply to the saved session/state; stale replies fail before dispatch.
See docs/2026-09-14-tutor-context.md for commands and completed offline validation.
The new src/agents/notebook_tutor.py generates one reply under a supplied teaching
policy and continues the bound student through the existing transaction. The
authored live integration in data/episode-pilot/notebook-tutor-v1 completed six
student decisions and one tutor hint. Two requested checks raised actual library
errors; the final third revision is unchecked and the student remains active at
its fixed budget. The tutor suggested an unavailable Babypandas method, so this
is evidence of connected interaction and a tutor limitation, not successful teaching.
See docs/2026-09-14-notebook-tutor.md. Exact replay and 36 related offline tests pass
(one container integration test skipped); no human plausibility review is pending.
The tutor now supports an optional library/version-matched API reference through
--reference-file; see docs/2026-09-14-tutor-library-reference.md. The shipped
Babypandas note is verified against the existing image with an authored check,
separate from student observations. The default tutor prompt and earlier trace
remain unchanged. The final related suite passes 38 tests with one skipped. No
new student trajectory or completed model generation was made; an initial failed
test adapter connection and its correction are documented in the memo. Reference
delivery is verified; model compliance and tutor correctness remain unmeasured.
Original b2a417b sessions remain replayable without rewriting saved receipts;
new operations record their actual engine. Other source/schema changes still fail.
Existing prompts and completed experiments remain unchanged; the task-evaluation
increment above explicitly revises the runtime/session boundary. The saved session
wrapper has a per-step cap and cumulative model budget;
chosen no-reply remains terminal, while a budget pause is not student silence.
The earlier history ablation and repeated plausibility-review loop remain paused.
The reassessment below remains research context, not a block on this implementation.

## Research reassessment (2026-09-14)

Minchan requested a project-level reassessment of the repeated plausibility-review
loop and a decision-focused update for the research team they lead. The proposed
history ablation is paused before preparation or dispatch; its private scripts
are incomplete and no results exist. Do not automatically resume it or start
another review batch. See docs/2026-09-14-research-reassessment.md for the evidence,
architecture explanation, data limits and proposed finite benchmark/stopping rules.
The benchmark and two-week time box are proposals for team agreement, not a run
or an established success threshold. Completed experiments remain frozen.
Standing authorization persists, but is not an instruction to resume experiments
that the latest research direction has paused. Presentation preparation is deferred.

## Current North Star (2026-09-11 clarification)

Minchan's primary inspiration is Generative Agents: an interactive world of
simulated students, engaging to explore as part of the broader goal of improving
learning amid technological and societal change. The first audience is
educators/researchers experimenting with student support. Minchan selected the
coaching direction (NBA2K/FIFA inspiration), deferred adventure and support placement,
and requested Animal Crossing stylistically, using original characters and assets.
Minchan then explicitly prioritized making the simulated students work before
designing the end product. Pause interface development; the exploratory storyboard
is preserved, not a current deliverable or a functioning student model.
The research context is in docs/2026-09-11-learning-expedition.md.
One invented worksheet/action loop with computed feedback is implemented in
src/eval/student_task.py; two live traces and their limits are recorded in
docs/2026-09-11-student-task-loop.md. It tests mechanics; human-audited real-data
fidelity remains a separate, incomplete requirement.
Four new-to-continuation development comparisons are complete in
data/episode-pilot/real-student-comparison-v1/ (docs/2026-09-11-real-student-comparison.md).
Specific send approval is recorded; all four generated replies and A/B review
pairs are preserved. Human review is complete; qualitative judgments and their
conditions are recorded separately without changing the original blank packets.
The bounded notebook audit in docs/2026-09-11-notebook-context-recovery.md found
omitted initial assignment context and first queries, plus reference-only grader
events. Later work changes remain unknown. Recover work context before tuning
communication; preserve the completed prompts and keep future observations out
of generator inputs. No additional model batch was run for that audit.
Recovery now has a supplemental snapshot and a one-cell edit/optional-chat path
(docs/2026-09-11-work-context-snapshot.md). Four initial exchanges are restored
without renumbering old turns; current work at the later cutoffs remains unknown.
Two initial-encounter draws are complete in data/episode-pilot/notebook-action-v1/.
Minchan specifically approved the exact disclosed payload after automatic review
initially rejected it; both approval and rejection are preserved. Both draws made
the same source revision without chat. Neither executed code or obtained feedback.
The private review.md presents that action once; Minchan accepted it as plausible.
The separate human-review-response.json preserves that judgment without implying
correctness or execution. All 16 pins still verify.
The new src/eval/notebook_check.py connects edits, requested computed fixture
feedback and optional chat (docs/2026-09-11-notebook-check-loop.md). It recognizes
two count-expression forms on authored data without executing candidate source;
unsupported code stays ungraded. An edit clears current feedback. The accepted
revision passed the limited scripted control. After Minchan's specific approval,
the bounded live trajectory in data/episode-pilot/notebook-check-v1/ completed:
request-check -> computed fixture pass -> no-reply, across two logical requests.
No new edit or message occurred. Exact offline replay and all 31 pins verify;
approval precedes both calls. Preserve the original automatic rejection,
approval and receipts. No candidate code or course grader ran; Minchan accepted
the new check/stop sequence as plausible, with that answer recorded separately.
This is one exposed development trajectory, not calibrated behavior.
The two authored controls in docs/2026-09-11-failed-check-continuation.md are
complete. notebook-failure-v1 reached an unsupported method and the action limit;
its final code is ungraded and no no-reply was generated. student-task-failure-v1
uses the existing structured worksheet: scripted failure -> generated correction
-> requested computed pass -> generated answer summary; stopped awaiting tutor.
All 17/14 pins and exact replays verify. These test mechanics, not learner fidelity.
Before another notebook behavior run, declare its runtime and checker capabilities;
do not conflate unsupported checks with student mistakes or patch spellings merely
to turn a retained run into success. The completed modules and traces stay frozen.
The new standalone src/eval/notebook_runtime.py now evaluates one cell inside an
explicit local Docker image (docs/2026-09-11-declared-notebook-runtime.md).
It separates checked answers, runtime errors, execution limits and environment
errors; only checked answers have Boolean success. Actual runtime, source,
revision, branch, activity, image, checker and timeout bind the observation.
Under newly declared environments, both retained authored revisions pass in
pandas 2.3.3 and raise AttributeError in Babypandas 1.0.0. The original unspecified
activity remains ungraded. All 13 new pins verify; no model requests were made.
The full suite passes 319 tests including isolated-container controls. The older
behavior loops are unchanged; the next new notebook trajectory must declare its
library before code selection and keep environment faults separate from learner
errors. The runtime checks cooperative code, not adversarial grading integrity.
The new src/eval/notebook_session.py connects that runtime to individual actions
without modifying the completed loops. Requested checks install verified feedback;
edits clear it, runtime errors stay ungraded, and environment/limit failures stop
the session. docs/2026-09-11-runtime-student-trajectory.md records the authored
three-decision probe, completed 2026-09-12. Its failed Docker setup attempt is
preserved; after recovery, a separately recorded actual runtime error preceded
three model choices: quiet revision -> requested actual pass -> no-reply. The
error was scripted, the correction/check/stop were generated. All 25 preparation
pins and six execution-file hashes verify; exact replay makes no Gemini or Docker
calls. The full suite passes 321 tests. This establishes one execution-backed
action/state example, not real-student recovery rates or learning. Human behavior
review remains separate; realistic work-context fidelity is the next bottleneck.
Minchan approved the three-case developmental review in
docs/2026-09-12-initial-action-review.md. It uses the remaining recovered initial
encounters (1/2/3), the frozen notebook_action prompt/schema, and one proposal per
case. Relevant captured supporting code is read-only; no code execution or later
state reconstruction is part of this pass. Keep all human fields blank until
review and all private payloads/results outside Git. Existing experiments stay frozen.
The three-case batch is complete in data/episode-pilot/initial-action-review-v1/.
Automatic review first blocked dispatch; Minchan then approved the exact disclosure,
recorded separately in approval-response.json before all three calls. Preserve the
original rejection and standing grant. All proposals revise the selected cell
without chat; no code ran and no grader outcome exists. Exact replay, 20 preparation
pins and nine completion-file hashes verify. Human review is complete in the separate
human-review-response.json: cases 1/2 plausible, case 3 plausible but leaning toward
implausible because finishing both functions after one tutor response seems doubtful.
Do not count the third judgment as an unqualified acceptance or binary rejection.
The original packet and its blank fields remain unchanged. An invented offline
check confirms partial edits already fit the schema; a source revision has no
defined duration or silent-attempt count. The next bounded probe should compare
original versus neutral partial-work wording with fresh draws, keeping cases 1/2
as controls, without forcing mistakes or inventing ability. This is a wording
diagnostic, not pacing calibration. The Markdown review is cumbersome but usable;
show future cases individually and defer a new review UI. No new calls were made
while recording feedback or checking the action contract.
Minchan approved that comparison; docs/2026-09-12-progress-wording.md defines six
fresh requests, original/clarified per case, in data/episode-pilot/progress-wording-v1/.
Tasks and state JSON stay identical; the sole prompt addition neutrally permits
unfinished work. Do not feed earlier generated actions or human verdicts into it.
No execution, pacing calibration or fidelity claim is part of this probe. Present
one case per Markdown file, retain both candidate receipts even when identical,
and preserve all completed sources and earlier reviews.
That comparison completed after Minchan's separate exact-prompt approval, which
precedes all six calls. Preserve approval-response.json and the earlier rejection.
Six silent revisions completed without retries; cases 1/2 are identical pairs,
and both case-3 draws fill one function while leaving the other unfinished. Since
the original wording also produced partial work, this batch does not establish
an added benefit from clarification; do not adopt a prompt change on this evidence.
Exact replay/31 preparation pins and 12 completion hashes verify. No code executed.
Case 1 repeats the previously accepted action with identical context; case 2 only
adds a final display expression to its earlier proposal. Keep new judgment fields
blank and earlier reviews separate. Minchan accepted both case-3 partial edits as
plausible and noted only variable-name differences; human-review-response.json
records the exact reply and both judgments. No condition preference or new case1/2
judgment is inferred. Close this diagnostic and retain the original prompt; no
further wording batch is needed. The next useful check is continuity from accepted
partial work using existing actions and explicit generated-state provenance, with
no invented intervening tutor reply, execution or outcome. This is not evidence
of calibrated action frequency, learning or a need for a new memory framework.
Minchan approved that continuation. docs/2026-09-12-partial-work-continuity.md
defines one next action in data/episode-pilot/partial-continuity-v1/, seeded from
progress-wording-v1 case3 original/call4. Current work is exact generated revision1;
the single model history event retains revision0, with no new tutor/feedback/run.
Original prompt/schema/settings remain fixed, and human acceptance stays outside
the input. Keep captured_at explicitly tied to the original capture, not generated
work or inferred time. All previous experiments and human reviews remain frozen.
That request completed after Minchan's separate exact-payload approval. Preserve
approval-response.json, the prior rejection and the standing grant. One quiet
edit fills the remaining function while preserving the earlier function and all
calling code; work advances 1→2. No tutor turn, chat, execution or outcome occurs.
Exact replay/50 preparation pins and nine completion hashes verify. The private
review.md retains its original blank human fields. Minchan accepted quietly
finishing the remaining function as plausible after an inline clarification of
the available guidance, earlier formula and exact change. The separate private
human-review-response.json records that answer and six evidence hashes. Close
this example; retain the earlier qualified judgment of the one-proposal solution.
Two model calls do not establish two real attempts, elapsed time or frequencies.
The next step in docs/2026-09-12-student-evaluation-readiness.md is an offline
inventory of existing snapshots and a fixed four-conversation context-recovery
candidate list. Reuse the extractor and existing exposure ledgers; do not send
models, query the DB, assign semantic labels or alter generators for this check.
Prior label audits and source searches preclude a pristine-holdout claim. An
observed next message cannot measure silent edits; historical initial code is
not current work at a later cutoff. Keep private metadata outside Git.
That inventory is complete in data/episode-pilot/evaluation-readiness-v1/.
Eight snapshots contain 252 distinct conversations; the primary source has 55
eligible windows across 24 conversations after known exposure and prefix filters.
Four distinct candidates are fixed using the existing raw-string digest; an
earlier JSON-ranking preparation is preserved as superseded, without target
review or model dispatch. All four have complete timestamps but no recovered
initial work. Exact regeneration, future-text isolation and 32 hashes verify;
an independent check matches the saved candidate metadata. No model/DB calls.
Next recover context for those fixed candidates via the existing read-only
ingestion path; preserve missing cases and distinguish initial captures from
unknown later work before constructing any generator payload. No user review is
needed for this inventory. Do not extend the count-only runtime to grade the
accepted two-function exercise merely to continue a closed development example.
Context recovery is complete in data/episode-pilot/evaluation-context-v1/;
docs/2026-09-12-evaluation-context-recovery.md records the bounded read-only queries.
Cases1/3/4 align; case2 has two matching unlinked initial queries and remains
ambiguous. Preserve it rather than selecting the nearer query or substituting a
case. Nineteen sources/three outputs verify; failed tunnel/query attempts remain
separate. All later work is still unknown and reference checks stay excluded.
Continue with docs/2026-09-12-context-grounded-communication.md: one fresh
communication proposal for each recovered case, original continuation prompt and
schema, explicit historical selected cells, null current work/observation, no
invented intermediate execution. This is conditional development comparison,
not reply-rate calibration or simulated notebook actions. User explicitly
reiterated continuing until a concrete human review is needed; do not stop after
routine preparation/verification milestones or request routine run permission.
The three requests are fully prepared in data/episode-pilot/evaluation-communication-v1/.
All 35 pins and both private checks pass; independent payload audit found no
material issue. Automatic approval review rejected the actual send before
process launch, requiring this exact private dialogue/code disclosure to Gemini
to be approved separately. send-blocked.json preserves the rejection/question
and five hashes. Minchan then approved the exact requests; the separate
approval-response.json binds that reply to the unchanged preparation and prior
rejection. All three calls completed in order without retry notifications and
selected reply. No student code ran and no current observation was supplied.
Exact replay, 35 preparation pins and 14 completion hashes verify; all three
review pages reproduce identically. An independent audit checked source text,
hidden origin mappings and five approval links; approval precedes every call.
Minchan tentatively prefers case1 A over B because the tutor already supplied
the complete function, making sending it back unnecessary. The separate private
human-review-case-1.json preserves the exact reply and six evidence hashes;
neither candidate receives an absolute verdict. Case3 B is preferred conditional
on prior evidence of student awareness that the tutor sees the notebook; the
separate human-review-case-3.json preserves this qualification and seven hashes.
The visible short notebook references are consistent with shared context, but
explicit awareness and a broader trend remain unknown. Minchan judged case4's
messages equivalent, without a preference or absolute plausibility verdict.
human-review-case-4.json and human-review-summary.json close this review while
preserving the original blank fields. Recorded messages were preferred with
qualifications in cases1/3; case4 was equivalent. No accuracy score follows.
Next, docs/2026-09-13-communication-channel.md defines six fresh paired requests
with the same three inputs and one neutral chat-channel clarification. Preserve
the original prompt; neither force terse/no-code replies nor assert the student's
knowledge of tutor notebook visibility. All six exact requests are now prepared
in data/episode-pilot/communication-channel-v1/. The only insertion is 220
characters; paired JSON is byte-identical. All43 pins and both invented checks
pass, including the runner/reviewer seam, with independent audit confirmation.
Automatic approval review initially rejected dispatch before process launch;
send-blocked.json preserves the actual rejection/question and six hashes.
Minchan then approved all six exact requests; approval-response.json binds that
reply to the unchanged preparation and prior rejection before every call.
All six calls completed with no retries and selected reply. Exact replay/43 pins
and14 completion hashes verify; the three review pages reproduce identically.
Independent audit confirms five approval/six rejection links, approval timing,
all candidate mappings and blank human fields.
Case1 pairs an acknowledgment with a function; case3's functions differ only in
formatting; case4's messages both ask about choice2. No code ran or work changed.
Minchan accepted the shown case1A acknowledgment as plausible because the student
asked in Chinese. human-review-case-1.json records only that verdict and six
evidence hashes; B remains unjudged and no prompt benefit is inferred. Original
blank fields stay intact and no prompt change is adopted. Minchan accepted
case3's shared function-sending behavior as plausible in one grouped judgment;
human-review-case-3.json preserves the raw reply and six hashes. No spacing or
condition preference is inferred, and the preceding conditional short-check
preference remains intact. Both case4 messages are now judged plausible, with a
tentative terser alternative described as a minor issue. human-review-case-4.json
and human-review-summary.json close this focused review; case1B stays unjudged.
No condition preference or mandatory brevity rule follows. Retain the original
communication prompt; another wording iteration is not justified by this batch.
Next follow docs/2026-09-13-initial-work-sequence.md: one fresh branch from
evaluation-context-v1 case1's initial capture/first exchange, instruction59 and
work60, at most three existing notebook actions. Carry generated work/history
forward, stop on chat/no-reply/error/cap, keep observation null and run no code.
Do not inject its later Chinese request or communication reviews into this
initial branch. Production modules and completed experiments remain frozen.
That sequence is fully prepared in data/episode-pilot/initial-work-sequence-v1/.
All 38 preparation pins and both invented checks pass; the independent audit
confirms exact initial context and the bounded generated-state procedure.
Automatic approval review rejected dispatch before launch because the private
payload and Gemini destination need specific approval. send-blocked.json records
the actual rejection and six hashes; that rejected attempt made no model request
and created no results or execution receipt. The disclosure contains the exact
first prompt and explains up to two dependent followups from generated work/history. Preserve the standing
grant, frozen preparation and rejection; do not describe all three prompts as
already known or infer behavior review from eventual send approval.
Minchan then explicitly continued in response to that disclosure question;
approval-response.json preserves the reply and six hashes before every call.
All three requests completed without retries: quiet fraction edit, quiet discount
conditions, then quiet principal calculation/return. Work advances 0→3 with no
chat, execution, new tutor or observation. The runner stops at action-limit;
no model-selected no-reply or subsequent action is known. Exact replay/38 pins
and 13 completion hashes verify; the review renders identically with blank human
fields. Present the progression once with initial context for plausibility review.
Do not infer pacing, attempt counts, correctness or an added prompt benefit.
Minchan accepted this quiet progression as plausible. The separate
human-review-response.json records the actual chat question, exact reply and
eight evidence hashes; no reason or broader behavior claim is inferred.
Close this example. Minchan then questioned the purpose of the repeated checks:
consolidate mechanics versus behavior evidence before another experiment, and
avoid more one-off wording/plausibility loops without a defined research question.
The evidence checkpoint at the end of docs/2026-09-13-initial-work-sequence.md
distinguishes plausible examples from representative student behavior. Next freeze
a varied evaluation set, generator and observable behavior criteria before any
batch; review failures/uncertainty together without tuning between cases. Existing
data is exposed and does not establish silent-work truth or reply frequencies.
Do not create an acceptance rate from the qualified and relative reviews so far.
Minchan approved that fixed evaluation. Follow
docs/2026-09-13-fixed-communication-evaluation.md: eight distinct conversations,
two independent original-prompt draws each, one concealed-origin review batch.
The updated 39-key exclusion leaves 43 windows/20 conversations; select 2 code/error,
3 earlier-context and 3 concise cases using the saved rank. Selection/protocol
are frozen before reference text is extracted. Use the first later student
message as reference, existing v7 followup/task_relation and human context fit.
All 16 dispositions stay in the report; preserve missing/uncertain judgments,
and report per-case outcomes rather than treating draws as independent students.
No tuning, case replacement, notebook reconstruction or acceptance threshold.
Private preparation/runner/reviewer live in fixed-communication-eval-v1; production
and completed experiments remain frozen. The next human review is the whole
batch, after any actual external-send approval requirement has been resolved.
The fixed batch is fully prepared: 50 pins and three invented checks pass,
including pending-summary refusal, reference/generated fit counts and first-only
reference selection. All selected future replacements preserve the 16 inputs.
An independent source audit found no material issues. Automatic approval review
rejected the actual send before launch, requiring specific approval of the eight
private prefixes sent twice to Gemini. send-blocked.json preserves the rejection
and seven hashes; that rejected attempt made no model request or execution receipt.
Minchan subsequently approved the exact disclosure. approval-response.json binds
the reply and seven evidence links before all16 calls; keep the standing grant
and original rejection unchanged. All16 requests completed and selected reply
with no errors or retry notifications. No student code ran. Exact offline replay,
50 preparation pins and twice-identical review rendering verify. An independent
completion audit passes; completion-verification.json binds 18 artifact hashes.
The audit's judgments.json hash describes only its initial blank snapshot, not
an immutability requirement on the separate human judgment file.
The original review.json remains blank; judgments.json is its separate editable
copy. Initially all24 messages/72 ratings awaited human review; the pending summary
writes no final report. Present REVIEW_START.md and the whole review.md packet; accept
plain-English chat judgments in parts without tuning or replacing cases. Do not
resume the old per-example tuning loop. Keep origin-key.json concealed until all
judgments are recorded; request-send approval is not a behavior verdict. Preserve
the earlier recovery case2's ambiguity and all completed evidence. Generation is
finished; the next milestone is the report after the complete human review.
Minchan's first whole-batch feedback is recorded separately in
human-review-response-1.json with seven evidence hashes. Cases2/4/5/6/7/8 allow
all candidates as possible: 18 plausible fits with qualifications retained.
Cases1/3 express relative A/C preferences only; six absolute fits remain missing.
Keep case7's ambiguous responding-trend explanation verbatim. All48 action/task
fields remain null; 24 rows/54 ratings are incomplete and no final summary exists.
Use review-remaining.md for grouped missing judgments without repeating prior
comments. Do not assign model labels as human judgments, reveal origins, infer
rejection from preference, tune prompts or turn these fits into a success rate.
Minchan then requested continuation. The separate private label-suggestions.md
offers grouped assistant-only action/task suggestions for confirmation. No fit
or human judgment is filled by this step. Later confirmed suggestions must be
marked human-reviewed assistant labels: assistance can anchor decisions and is
not independent annotation. Keep the frozen packet/protocol/generator unchanged,
origins concealed and the formal report pending until actual judgments arrive.
Minchan's “looks good” now confirms all48 proposed action/task labels, recorded
as assistant-suggested, human-approved in human-review-response-2.json with eight
evidence hashes. Keep the primary3C/7B asked-for-help choices and their documented
ambiguities. Original fit comments/preferences remain intact; six case1/3 fits
remain null pending the separate explicit question. The pending summary has six
incomplete rows/six missing ratings and creates no final report. No further label
approval is needed; do not infer the remaining fits or reveal origins yet.
Minchan then explicitly answered “yes, plausible” to the case1/3 fit question.
human-review-response-3.json preserves that grouped confirmation and eight hashes;
only six fits changed. All72 fields are filled, and summary.json/md plus REPORT.md
close this fixed batch. All16 generated/eight references are plausible, with
preferences/qualifications retained. Primary help labels are4/8 references versus
0/16 generated; the two documented alternative readings would leave2/8 versus0/16.
Action equality is6/16, not accuracy. Task relationships are uncertain for3/8
references and12/16 generated; only2/16 pairs are known on both sides. Origins may
now be revealed. Independent audit verifies preservation,50prep/18completion/eight
new receipt links and exact summary rendering after the final fit receipt.
Keep this batch closed and preserve assisted-label/grouped-fit provenance; no
new generation, prompt change, fidelity score or classifier admission follows.
The next proposed diagnostic tests available history with/without earlier dialogue
while holding the current exchange fixed; no-history cases cannot supply a history
treatment. Do not infer that another style instruction or new planner is a fix.
Labeling and continuation diagnostics
support this goal. Behavioral fidelity, educator usefulness and real learning
outcomes remain separate questions; the invariants below still apply.

## What this project is

Research codebase with two subsystems (decision memo:
`docs/2026-08-01-topdown-labeling-same-repo.md`):

1. **Labeling — top-down, instructor-facing.** The instructor states what trends they want
   to see from the data — conceptual ("which topics are students struggling with"),
   behavioral/affective ("confused, satisfied, angry"), or other. The tool pulls a
   *stratified* sample of real messages, drafts labels against that intent, and shows the
   labeled sample. Instructor accepts the direction → mass-label the corpus; or tweaks by
   describing what they want differently → new prompt, new draft, review again. Every tweak
   iteration is a new schema version.
2. **Simulation.** LLM agents grounded in real students' logged behavior with an AI tutor,
   used to screen tutor-policy changes ("never give direct answers," "answer-then-probe")
   against a synthetic cohort **before any real student is exposed**. Consumes the labeling
   subsystem's output as the **state space of the simulation**.

Raw data: DSC 10 tutor chat logs in an external PostgreSQL database (`dsc10_tutor_logs`),
reached read-only via `kubectl port-forward` into the Kubernetes cluster — the same access
pattern ChatSight uses (see its README for tunnel setup; replicate the pattern, not the code).

An agent is a thing that moves through label-space ("instrumental ask" → "got hint" →
"re-engaged" vs. → "extracted answer" vs. → went silent). The classifiers are the projection
that maps any transcript — real or synthetic — into that space. A "policy effect" is a shift
in the distribution of trajectories through it.

## The relationship to ChatSight — READ THIS FIRST

**ChatSight (`github.com/minchan/chatsight`, local: `~/github/chatsight`) is a sibling, not
an upstream.** It does bottom-up labeling (instructor labels first, classifier generalizes)
for its fall instructor pilots; this repo does top-down intent-compiled labeling. Both read
the same raw-log database. This repo was deliberately created outside ChatSight so research
cadence never destabilizes those pilots.

**Rule 1 — Never modify ChatSight from here, never import or vendor its code.**
Reference its conventions freely (kubectl tunnel pattern, backend stack, .env layout). This
repo's classifier is a deliberate independent reimplementation — not a fork claiming
equivalence. Corollary: **labels produced here and labels produced by ChatSight are never
compared or mixed in any claim** unless a dedicated calibration study earns it.

**Rule 2 — Classifier parity is the load-bearing wall (now internal).**
Every fidelity and policy claim depends on synthetic transcripts being scored by *the same
classifier that labeled the real corpus* — same prompt/config hash, same schema version.
Every results artifact records: schema version ID, classifier prompt/config hash, corpus
snapshot ID, model IDs. No orphan numbers.

**Rule 3 — The live-DB boundary runs inside this repo.**
`src/labeling/` and `src/ingest/` may open the raw-log Postgres (read-only, through the
tunnel). The labeling subsystem's output is an immutable labeled-corpus snapshot in
`data/snapshots/<id>/` (JSONL: conversations, turns, label applications, schema version)
with a manifest (export date, schema version, classifier hash, row counts). The simulation
subsystems (`eval/`, `trajectories/`, `agents/`, `replay/`) consume **only snapshots, never
the DB**. If labels change, that is a *new snapshot*; old experiments still reproduce
against the old one.

**Rule 4 — Student data never enters git.**
Snapshots contain real students' conversations (IRB-covered, DSC 10). `data/` is gitignored
from the first commit. Same for `.env`, API keys, and anything derived that quotes verbatim
student text. Check `git status` before every commit; if a student utterance appears in a
committed file (including notebooks and test fixtures), treat it as an incident: purge
history, tell Minchan.

## Non-negotiable research invariants

1. **Evaluation ground truth is human-labeled real data. Always.** Synthetic/generated data
   may train, densify few-shot pools, or probe boundaries — it never sits in an eval set and
   never judges anything. The whole chain is Gemini four layers deep (drafts labels → mass-
   labels → plays the student → scores the result); the human-audited sets are the only
   contact with ground truth. Guard them.
2. **Judge classifiers against the human-agreement ceiling, not 100%.** If two instructors
   agree 80% on a label, a classifier at 78% is near-perfect and an agent at 75% agreement
   with real students may be near the achievable maximum. Every reported agreement number
   carries its ceiling next to it.
3. **A label enters the simulation state space only if its classifier clears the admission
   threshold** (Phase 0 defines it; human decision #1 below). Unreliable labels stay
   analytics-only in ChatSight; here they are poison.
4. **Personas are cluster-level archetypes, not per-student agents.** Grounded in label-
   trajectory profiles and behavioral summaries, not verbatim reproductions of one student's
   turns. This is both an IRB position and an honesty position about the method's resolution.
5. **Claim discipline.** Allowed: "policy X changed simulated help-seeking behavior (fidelity:
   …)"; "agents reproduce the labeled behavioral/transition distribution of the real cohort."
   Never allowed, not even hedged: "policy X improves learning"; "policy X would work with
   real students." The contribution is a *screening instrument* — it narrows twenty candidate
   policies to the three worth a real quarter.
6. **Experiments pin a schema version.** Label schemas evolve upstream (merge/split/rename).
   An experiment binds to one schema version + one snapshot; cross-version comparison is its
   own explicit analysis, never an accident.
7. **Agents must be able to not respond.** Quiet exit (student silently defects to ChatGPT /
   gives up) is the most important negative signal in the framing. An agent that always
   replies cannot reproduce it; model non-response as a first-class action from day one.
8. **Blind measurement, anchored drafting.** The review-and-tweak loop shows model-drafted
   labels — anchored, fine for *drafting*. Reliability numbers for the admission threshold
   come only from instructor labels produced blind (messages without model labels), on a
   held-out sample never used in the tweak loop. Approval of a shown label is not ground
   truth; anchoring inflates agreement.
9. **Stratified review samples.** Samples shown to the instructor are deliberately composed
   (model-uncertain, embedding-diverse, boundary cases), never the first N or a uniform
   random pull — rare behaviors (quiet exit, answer-extraction) are the point and won't
   surface in a quick random sample.

## Phase plan (full details in the pipeline memo)

Each phase has a publishable fallback; never let a phase's success become a bet the next one
must win.

- **Phase 0 — classifier eval harness. START HERE; blocks everything.** Per-label
  precision/recall vs. human-audited held-out real messages; human-agreement ceiling from
  double-labeled samples; admission threshold proposal. Runnable on the first DSC 10 snapshot.
- **Phase 1 — intent-compiled schema.** Elicit the instructor's *what-if question* / desired
  trends, backward-chain to required constructs, run the draft→review→tweak loop
  (invariants 8–9), verification gate = boundary cases + negative-space coverage + per-label
  reliability (invariant 3). Lives in this repo's `src/labeling/` — the first
  instructor-facing surface.
- **Phase 2 — trajectories.** Mass-labeled corpus → label trajectories per conversation →
  empirical transition matrix (grounding data, fidelity target, and screening baseline all at
  once) → 4–7 clustered archetypes. *Standalone paper fallback: descriptive dynamics of
  help-seeking in a real AI-tutored course.*
- **Phase 3 — agents + fidelity.** Held-out turn prediction (agent generates turn k+1; real
  and synthetic both classified; agreement measured **on labels**, against the ceiling);
  distributional fidelity (does the cohort reproduce the spread, or collapse to a modal
  agent?); transition fidelity (dynamics, not marginals); fidelity-vs-depth decay curve
  (report the usable horizon). All on historical data, no live students. *Fallback: a
  rigorous failure characterization of LLM learner simulation is itself a contribution.*
- **Phase 4 — replay + policy screening.** Multi-turn replay of variant tutor policies ×
  archetype cohort → scored → diffed against the Phase 2 baseline. Instructor study (3–5
  instructors) observing what they *decide*. Interface contract: policy in → inspectable
  cohort out; aggregate numbers click through to individual synthetic trajectories;
  per-construct confidence shown as ranges; flag policies whose gains concentrate in
  low-confidence label regions (a policy can game the classifier, not the learning).

## Suggested layout

```
CLAUDE.md                  ← this file
docs/                      ← memos, dated `YYYY-MM-DD-topic.md`, discussion-memo register
data/                      ← gitignored; snapshots/<snapshot_id>/ with manifest.json
snapshots.md               ← human-readable ledger of known snapshots + provenance
src/
  ingest/                  ← raw-log DB access (tunnel) + snapshot loader/manifest validation
  labeling/                ← Phase 1: intent elicitation, stratified sampling, draft
                             classifier, review/tweak loop, mass-label → snapshot emission
  eval/                    ← Phase 0 harness (first real code)
  trajectories/            ← Phase 2 extraction, transition matrices, archetype clustering
  agents/                  ← Phase 3 persona construction + generation (incl. non-response)
  replay/                  ← Phase 4 engine + policy variants
  scoring/                 ← thin wrapper pinning this repo's classifier config — no logic here
experiments/               ← one dir per experiment: config (pins), results, notebook
```

Python-first; match ChatSight's backend conventions where sensible so context transfers.
Frontend work is paused by Minchan's latest instruction. Build and evaluate the
student behavior loop before returning to the selected coaching presentation.

## Decisions already made (don't relitigate without new information)

- Separate repo from ChatSight, as a *sibling* sharing only the raw-log data source
  (2026-08-01 memo). Chosen so pilot-facing ChatSight stays stable through fall. Price:
  independent classifier with no label-continuity to ChatSight's corpus.
- Labeling is top-down intent compilation with an instructor review/tweak loop; drafting may
  be anchored, measurement must be blind (invariants 8–9).
- Archetype-level personas, not per-student (invariant 4).
- Intent-first (top-down) schema drafting is *compilation of instructor intent*, arbitrated
  on real data — not a return to upfront rubrics. The instructor's arbitration sample is the
  metrological foundation of everything downstream.
- Synthetic data: amplifier, never substitute; human labels define, synthetic multiplies,
  real data judges.

## Open decisions — need Minchan (and usually Sam). Do not decide unilaterally.

1. Admission threshold for the state space (blocks Phase 1 gate design).
2. Archetype granularity the data actually supports.
3. Schema freeze/migration policy across quarters.
4. IRB: confirm archetype personas from label profiles are within the existing protocol /
   amendment scope **before Phase 3 code exists**.
5. Who owns the DSC 10 tutor's prompt/policy surface (prerequisite for any replay; open
   since the July memo — it's an email, chase it).
6. Kubernetes credentials/namespace for this repo's own read-only tunnel to
   `dsc10_tutor_logs` (replaces the dissolved ChatSight-export question).
7. Permanent name for this repo/tool — current name is explicitly temporary.

## Related work you must know before writing anything

Park et al., *Generative Agents* (arXiv 2304.03442) and *LLM Agents Grounded in Self-Reports*
(arXiv 2411.10109) — method provenance; we transpose grounding from self-reports to
behavioral logs. **PromptDecipher** (arXiv 2605.16605) — closest neighbor and the clock
pressure: validates tutors on pre-defined scenarios, not real course logs; our differentiator
is grounding + instructor-authored metrics. TutorGym (arXiv 2505.01563) — replay for agent
benchmarking, researcher-facing. EvalGen / "Who Validates the Validators" (UIST 2024) —
criteria drift supports the bottom-up gate. AIED/EDM simulated-student literature simulates
*generic* novices from knowledge models; we instantiate from one real course's labeled
behavior. Re-run the novelty search before each paper; this area moves monthly.

## Working style

- **Standing model-run approval (2026-09-11).** Minchan explicitly said: "Yes, you
  always have the approval. Make sure to log this." This authorizes continued model
  runs for this project's student-simulation and labeling work, including new batches
  and prompt iterations with the established provider, Gemini. Do not ask again for
  routine batch approval. Record each experiment's scope and results; human judgments
  of generated behavior remain separate. The exact response and the immediately
  approved batch are recorded in
  `data/episode-pilot/student-continuation-check-v1/interaction-comparison/approval-response.json`.
- Every substantive direction change gets a dated memo in `docs/` *before* the code — that is
  how this project thinks. Match the register of the existing memos: claims carried with
  their limits, "honest limit" sections, must-cite tables.
- When results look good, the next task is attacking them (circularity? register cue? ceiling
  effect? snapshot leakage into eval?). When they look bad, characterize precisely — that is
  the Phase 3 fallback paper.
- Context: Minchan is applying to PhD programs (HCI/CS-ed, fall 2027 entry) with this work as
  the centerpiece; Sam Lau (UCSD HDSI) advises. Evidence that exists by **December 2026**
  matters more than elegance. Paper 2 drafting starts mid-October (CSCW rolling / L@S
  ~mid-Jan / LAK); Phase 0 + a Phase 2 descriptive result are the December targets.
