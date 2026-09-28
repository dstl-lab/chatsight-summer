# Simulated students: task list

**Completed (2026-09-28):** [the fixed-input full-adapter comparison](docs/2026-09-28-full-adapter-replies-status.md)
finished every request and passed exact input, identity, output-token and score
checks. Generated results are mixed: fewer repeats on fixed synthetic histories,
but a new recorded-context repeat and worse median character-count error. Keep
the candidate experimental; this does not establish improved conversation realism.
The comparison is closed, with no further tuning, generation or labeling queued.

**Completed (2026-09-28):** [the full recorded-reply training pass](docs/2026-09-28-training-coverage-status.md)
saved a separate adapter with lower prediction loss than both the base model and
the previous small-subset adapter on the unchanged development references. Most
cases improve; exact results stay in the private report. Full-pass, token, source
and score checks pass. No new labels or generated conversations; this run is closed
without automatic adoption or further training. Interactive realism and repetition
remain unvalidated.

**Completed (2026-09-28):** the [trained student now works through actual browser submissions](docs/2026-09-28-local-browser-check-status.md).
Initial and typed-tutor continuation both complete locally and reload read-only.
The saved model repeated its question despite receiving the new tutor text;
the result is retained without rerolling. Receipt/token audits and the JavaScript
check pass. Zero cloud calls or labels; the two-request browser check is closed.

**Implemented (2026-09-28):** [structured student replies now use the browser controls](docs/2026-09-28-structured-student-replies.md).
The trained-student callback receives exact selected-conversation history for
initial, typed-tutor and generated-tutor replies. The private launcher reuses the
saved workers; a fresh three-decision session is prepared read-only with zero
new calls. All 699 Python tests pass (three optional skips), including five new
routing/history/failure checks. Closed studies and their source files are unchanged.

**Completed (2026-09-28):** [student evidence and tutor integration are now separated](docs/2026-09-28-student-tutor-separation-status.md).
The offline summary uses recorded-tutor contexts and keeps prediction and
generation diagnostics separate. After exact-payload approval, one Gemini tutor
response and one new trained local student reply completed with no retries.
Exact histories and local tokens verify; the saved exchange opens read-only.
The fixed budget is exhausted. No further calls, training or labels are queued.

**Closed (2026-09-28):** the [local tutor-format comparison](docs/2026-09-28-local-tutor-role-status.md)
completed every fixed request and passed independent token/source verification.
Partial echo improvement did not resolve grounding and correctness problems;
the candidate is not adopted as a validated tutor. No student training or new
labels. Keep recorded-tutor student evaluation separate from interactive tests
with the intended tutor backend; no further formatting variant is queued.

**Completed (2026-09-27):** the [saved repetition diagnosis](docs/2026-09-27-local-repetition-diagnosis-status.md)
rules out stale histories and display duplication in the inspected repeats.
Mandatory student replies and tutor-role failures confound later turns. An
authored check and independent review pass; no new calls or labels. Next: isolate
tutor-role handling on saved requests before changing student training.

**Completed (2026-09-27):** the [fixed local conversation evaluation](docs/2026-09-27-local-conversation-cohort-status.md)
is closed. Starting and trained students completed every planned case using the
same tutor policy. The private report combines automatic coverage, repetition and
length diagnostics with per-case results; independent saved-token/history audits
pass. No further training or labels were needed. Next: diagnose the already-saved
repeated sequences before proposing a model change; no new run is queued.

**Completed (2026-09-27):** [recorded repetition now has an automatic baseline](docs/2026-09-27-recorded-repetition-status.md).
The same literal-text metric covers recorded response windows and the saved
local students, with independent canonical-source verification and six passing
tests. Private results distinguish descriptive evidence from plausibility
judgments. That check added no model calls or labeling. The subsequent fixed
conversation evaluation above is now complete; no automatic repetition penalty.

**Completed (2026-09-27):** the saved adapter now participates in a
[bounded conversation comparison](docs/2026-09-27-local-student-conversation-status.md)
through the existing chat engine. Starting and trained students each produced
three messages with the same unchanged tutor policy; both saved branches are
available in the read-only browser. Exact histories and source pins verify.
The private report records limitations; this pilot is closed with no new labels,
further training or default-generator replacement.

**Completed (2026-09-27):** the [fixed local training pilot](docs/2026-09-27-local-student-training-status.md)
saved a candidate adapter and completed the starting-versus-trained prediction
comparison. Private results and receipts are preserved; no new labels, Gemini
requests or simulator replacement. The subsequent bounded conversation above
uses the saved candidate with fixed settings and no further training.

**Preparation completed (2026-09-27):** [use recorded student replies as training targets](docs/2026-09-27-recorded-student-training.md).
The existing examples, separate development references and source pins now pass
the private readiness check; no new labels or extraction pipeline were needed.
The comparison above now uses these targets. Lower prediction loss alone does
not establish simulator realism.

**Closed (2026-09-27):** the [retrieved-example comparison](docs/2026-09-27-retrieved-student-example.md)
shows no measured improvement. Minchan reviewed all 14 unique messages from the
16-output run. Help/work flags match across conditions in all eight cases; both
conditions disagree with recorded work presence in four cases. The experimental
prompt is not adopted. No new labeling round or prompt variant is queued.
Pending PR #62 remains independent. Earlier status notes below are historical.

**Review integration (September 27):** PRs #47, #48, #57–#60 and #63 are merged.
The [completed communication review](docs/2026-09-27-standalone-communication-review.md)
now opens directly with its aggregate work-presence counts and existing examples.
Its 689 Python tests passed (three skips), along with all three Node and seven
Marimo checks. That integration added no labeling, generation or simulator change.

**Integration update (2026-09-23):** PRs #47, #48 and #57–#59 are merged;
#60 completes the browser workspace integration. Start from `main` using the
[teammate quickstart](docs/teammate-quickstart.md). The implementation and independent
reviews below are complete; pending-integration notes record earlier stages.
Closed studies remain closed; no new labeling or experiment is queued.

**Saved notebook comparison complete:** the existing
[teaching pair](docs/2026-09-15-teaching-pair.md#browser-comparison-september-22)
now opens in one browser workspace. Shared task/code, both supplied tutor replies,
saved actions, local results and stop reasons are visible together; one chat
sidebar switches between the shared start and either condition. Preparation and
current outcomes are verified separately. 686 Python tests, three Node and seven
Marimo checks pass; independent review and desktop checks complete. No new calls
or labels. Next: independent PR review and integration; no new experiment queued.

**Next-exercise workflow complete:** a completed notebook encounter can now
[preview and save one configured successor](docs/2026-09-22-browser-next-exercise.md)
from the browser. The same verified history and conversation example continue;
work, feedback and the supplied tutor policy start with the new task. Save is
offline; generation is separate. URL selection and read-only recovery preserve
the successor across reloads. 667 Python tests, three Node and seven Marimo checks
pass; the authored two-task browser walkthrough and independent review are complete.
No new provider calls, private demonstrations or labels. PR integration still
requires independent review; the closed fidelity studies remain closed.

The [Student fidelity view](docs/2026-09-22-browser-student-fidelity.md) now surfaces
the **completed** matched benchmark: eight conversations, four draws per condition,
64 saved replies and existing help/work judgments. Earlier dialogue had higher
mean Brier error (0.359375 versus 0.29296875). All reference messages request help
without showing work; this narrow, development-exposed sample cannot establish
overall fidelity or a random-student result. The benchmark is closed. No new
generation or labeling is queued; inspect this evidence before defining a distinct
improvement study. UI integration still needs independent PR review.

PR #47's reviewed issues are fixed, and the [browser policy comparison](docs/2026-09-22-browser-policy-comparison.md)
now opens saved pairs with shared context once, fixed policies, tutor responses
and distinct student outcomes. The [creation/run workflow](docs/2026-09-22-browser-policy-runs.md)
is also complete: choose an eligible conversation, save Policy A/B
instructions offline, then explicitly run untouched conditions. Reloads do not
resend requests; comparison drafts recover in their browser tab. 639 tests pass, with browser,
Marimo and independent checks. Port8431 has separate working copies of 29 saved
conversations (27 eligible). No new provider calls or labels were needed.
Next: independent PR review and integration; batch controls remain deferred.
This is workflow integration, not new fidelity evidence.
Navigation is now direct: policy workspaces open on Tutor policies, empty ones
show setup immediately, and conversations expose policy comparison, tutor
instructions and saved results. The single chat and explicit Save/Run steps remain.
All seven HCI audit findings are addressed: searchable question/policy excerpts,
tested-question entry, neutral A/B and one-exchange scope, exact-source setup reuse,
draft recovery/validation, fewer duplicate controls, and input contrast/focus.

The [replay usability pass](docs/2026-09-22-browser-replay-usability.md) is complete:
conversation-only runs use one chat with Previous/Next; the duplicate activity
list was removed. Notebook work and comparisons keep chat alongside. Details are
grouped and inspection keeps the scenario heading/playback visible. No new labels or runs.

**Current direction (September 22):** measure simulated-student fidelity against
real AI-tutor interactions, then test whether grounding improves it. The educator
decision walkthrough is paused. User selected a dedicated browser workspace and
requested a desktop HTML prototype: [preview and instructions](docs/prototypes/README.md).
The authored preview is accepted. A connected read-only browser workspace now
shows verified saved notebook sessions, linked tasks, chat, diffs and local check
results. Explicit state-bound tutor/student controls are now connected, with
read-only defaults, visible progress and no automatic resending. The
[live browser walkthrough](docs/2026-09-22-live-browser-workspace.md) is complete:
three student requests produced a quiet edit, a real passing local check and
no-reply. Saved replay and terminal controls verify; no tutor request or new label.
Matched baseline/grounded comparison remains separate from this engineering check.
The browser also opens [existing chat scenarios](docs/2026-09-22-browser-chat-scenarios.md)
through explicit `--chat`, with no invented notebook state. All 29 saved scenarios
reopen unchanged. The [scenario sidebar](docs/2026-09-22-browser-scenario-selection.md)
now browses all 29 via `--chat-sessions` on port 8428; switching resets drafts and
refresh retains selection. No new generation/labels.
Tutor replies now have [readable prose and code](docs/2026-09-22-browser-message-readability.md);
student text and original-source inspection remain literal. This display update
does not change the simulator or add fidelity evidence.
The [Compare tab](docs/2026-09-22-browser-saved-comparison.md) now opens the existing
eight-case review beside replay: recorded messages, both cached draws, supplied
context and completed help/work judgments. No new generation, labels or metrics;
that cached review is separate from the completed matched benchmark above.
The [chat sidebar](docs/2026-09-22-browser-chat-sidebar.md) now keeps conversation
beside notebook work or comparison cards; details and tutor controls use the
center. The separate Inspect tab is retired in the connected workspace.
**Saved results** now exposes the existing per-task/conversation receipt history
inside the browser, separating delivered instructions from current drafts and
unused configuration. Chat has clearer roles and first/last-message navigation.
This [inspection update](docs/2026-09-22-browser-saved-results.md) adds no generation
or labels and does not change the simulator.

**Earlier scope assessment (now paused):** PR #43 is merged; resolved branches are
cleaned up and the working simulator is on main. The
[research feasibility decision](docs/2026-09-22-educator-decision-feasibility.md)
is complete: saved evidence supports a formative keep/revise/inspect-more task,
not a policy-effectiveness comparison. Private first-case handouts and a blank
facilitator note sheet are prepared and verified; participant availability is
pending. No new labeling, model run, simulation-interface implementation or
participant study has started.

**TL;DR:** Saved interactions and paired tutor-policy comparisons now work.
The fidelity target is when work/evidence is presented in chat. A separate cached
review now covers five work-absent and three work-present references, but supplies
no matched improvement comparison. Generator-adoption experiments stay deferred.
The teammate quickstart and authored offline demo are on main via
[PR #30](https://github.com/dstl-lab/chatsight-summer/pull/30). Automated contributor
checks are also merged via [PR #40](https://github.com/dstl-lab/chatsight-summer/pull/40).
The six-case [joint evaluation](docs/2026-09-21-joint-fidelity-check.md) is closed:
four recorded-message preferences and two both-possible judgments. It supplies
qualitative feedback, not the missing binary labels. Keep bulk labeling paused;
workspace redesign is now authorized as the prototype above. The separate fixed
pass below is now closed too.
The automatic
[recorded-continuation selection comparison](docs/2026-09-21-recorded-continuation-selection.md)
is closed: with and without history both scored 8/16 complete pairs; word overlap
scored 7/16. Five of 38 requests remain missing after a schema failure; none were
resent. No manual labels or generator change. PR #42 merged the diagnostic.
The next engineering increment now coordinates three existing conversation
scenarios under the same two policies, with one new decision per condition.
The [cohort workflow](docs/2026-09-21-chat-cohort.md) is verified with scripted
responses. After specific payload approval, its
[one live round](docs/2026-09-21-live-cohort.md) completed all six conditions:
six tutor replies and six simulated student replies, 12 recorded requests and
no failures. All budgets are exhausted and the readable results are saved.
PR #44 merged into the results branch; combined PR #43 is now merged into main.
This verifies operation, not student realism or policy effects.
The [public notebook example](docs/2026-09-21-notebook-example.md) now makes the
existing task/work/execution path reproducible without private inputs. Its authored
container check passes; no new model calls or labels were needed.
Its [first generated walkthrough](docs/2026-09-21-live-notebook-example.md) then
quietly edited code, requested one real passing check and chose no further reply.
Three student requests, no additional tutor replies; that bounded run is closed.

The [Saved results repair](docs/2026-09-22-lesson-saved-results.md) also makes lesson
tutor receipts visible and separates configured policy from confirmed delivery.
The [optional conversation example](docs/2026-09-22-notebook-communication-context.md)
now connects an existing chat prefix to a fresh authored notebook task, with one
offline setup verified. PR #45 merged into #43; no new generations or labels.

The [cached-message inventory](docs/2026-09-22-cached-fidelity-scope.md) now verifies
eight references and 16 saved replies. One duplicate reduces any later common
coding pass to 23 distinct messages / 46 flags. No compatible labels overlap.
These are two draws of one condition, so this set cannot estimate a grounding
benefit. The subsequent [fixed review result](docs/2026-09-22-cached-communication-results.md)
is complete: generated work appears in 6/10 draws for work-absent references and
is absent in 2/6 draws for work-present references. No missing judgments, new
generations or further review rounds; preserve the existing simulator.

Updated: September 22, 2026. Unchecked items are proposed work, not completed results.

**Latest fidelity diagnostic:** a separate [work-presence forecast](docs/2026-09-22-work-presence-forecast-status.md)
is implemented and passes the 442-test suite. After specific approval, all eight
requests completed with no errors or adapter retries, reusing completed labels.
The screen **failed**: forecast error .80625 vs frequency .612245 and fixed 50/50
.5 (multiclass Brier; lower is better). Close this increment and retain the
simulator; no message-realization component, rerolls or new review form. The
screen measures a conditional message-feature forecast, not generated-message
fidelity. Earlier studies remain closed.

**Current increment complete:** [preserve the recorded communication example](docs/2026-09-22-communication-continuity.md)
when moving to later notebook tasks. Verified through Tasks 2 and 3 offline;
444 tests pass. A successor to the completed notebook demonstration retains its
10-turn example with fresh work and no actions/calls. This repairs context
continuity without claiming improved realism.

**Continuation complete:** after exact payload approval, the
[second exercise](docs/2026-09-22-live-notebook-continuity-status.md) produced a
quiet edit, passing local check (`0.25`) and no-reply. Three student requests,
zero tutor requests; all 59 pins and two-task replay verify. No new labels or
further run is queued. This demonstrates continuity, not learning or fidelity.

**Custom task setup complete:** a [supplied exercise](docs/2026-09-22-custom-notebook-exercise.md)
can now use the same verified conversation example without custom Python glue.
The public fruit-count bundle works offline; 446 tests pass. No engine change,
new live run or additional labeling.

**Policy handoff repaired:** the workspace can [load the prepared tutor policy](docs/2026-09-22-workspace-policy-file.md)
as its editable draft. Reload preserves edits; submitted requests retain the
actual draft. All 454 tests pass, without new model calls or labels.

**Exercise continuation ready:** the same setup command now accepts `--previous`
to [carry verified history into a supplied exercise](docs/2026-09-22-exercise-continuation-setup.md).
The new session and policy are prepared together offline; 457 tests pass.

## North Star

Build a tool where educators can try tutoring approaches with simulated students
grounded in observed interactions. Our research question is how poorly a generic
LLM reproduces observed DSC 10 AI usage, where it diverges, and whether grounding
reduces those gaps. A working interface and realistic student behavior are separate
milestones; the former does not establish the latter.

## Already working

- [x] Describe the existing corpus and preserve the completed comparisons and reviews.
- [x] Save and resume student conversations with fixed budgets and replayable receipts.
- [x] Open 29 scenarios in Marimo, reusing cached replies in separate workspace sessions.
- [x] Supply a tutor policy or manual reply and continue one student decision.
- [x] Distinguish recorded messages, simulated messages and tutor interventions; show missing notebook activity as unknown.
- [x] Support authored notebook tasks with work changes and isolated checks in the separate notebook mode.
- [x] Pause bulk labeling; keep the current generator because the tested candidate did not establish sufficient improvement.
- [x] Complete the requested six-case joint development evaluation, preserve the protocol amendment and instructor judgments, reveal origins, and close the pass without changing the generator.
- [x] Complete one fixed automatic recorded-continuation choice comparison, report the tie and five missing choices, and close without new labels, rerolls or generator adoption.
- [x] Coordinate three saved policy pairs as one bounded group, retain failures, and reopen all six outcomes without changing the student generator.

## Next, in order

- [x] **1. Make the saved result understandable inside the workspace.** Show the
  policy actually used for each exchange, its tutor reply, student response, and
  whether the run stopped, exhausted its budget, or failed. Read existing receipts.
  **Done when:** reopening a run explains what happened without inspecting JSON;
  viewing and reloading make no model calls.
  Completed in the [Saved results tab](docs/2026-09-20-workspace-saved-results.md),
  including failed/interrupted exchanges and notebook actions.

- [x] **2. Compare two policies from the same conversation starting point.** Use
  separate session identities, the same recorded prefix and cached first reply,
  and equal fixed budgets. Show both saved conversations together. Reuse the
  existing session machinery and lessons from notebook teaching pairs; those
  pairs already exist, but do not fork progressed chat sessions.
  Fix the selected cases and stopping rule before generation; retain failures and
  no-reply outcomes. Verify the mechanics with authored responses first.
  **Done when:** both conditions can continue and reopen independently, with
  visible policies and no overwrite of the original. One pair demonstrates the
  mechanism; it does not establish which policy helps real students.
  Completed in the [fixed-policy comparison](docs/2026-09-20-chat-policy-comparison.md),
  verified with authored responses. No live policy comparison was run.

- [x] **3. Choose one measurable student-fidelity improvement.** Use the existing
  reports and instructor feedback to identify a specific failure, such as excess
  explanation in otherwise terse student conversations. Establish whether existing
  evidence can measure it before changing the generator. Length and formatting
  diagnostics alone cannot establish appropriate behavior.
  **Done when:** one written decision specifies the target, baseline, measure,
  fixed cases and call budget, and adoption/stopping rule. If measurement cannot
  support the claim, narrow the claim instead of generating more examples.
  [Target and readiness decision](docs/2026-09-20-student-fidelity-target.md):
  work/evidence presentation. A constant help-only flag rule scores perfectly on
  the eight existing references. The proposed balanced work measure is unavailable
  because no reference contains work; retain the generator, zero new calls/labels.

- [ ] **4. Run only that declared comparison, if it is justified.** Preserve the
  original generator and frozen evidence; treat any changed prompt as a separate
  candidate. Reuse cached outputs where inputs match. Request human judgments only
  if a specific adoption decision cannot be resolved otherwise, using a small
  fixed sample and no rolling review queue.
  **Done when:** report improvement, no improvement, or inconclusive evidence and
  close the comparison. Do not reroll until an appealing difference appears.
  **Deferred:** the original measurement gate in item 3 failed. Item 14 now fills
  both work groups for a separate development slice, but supplies only one
  generator condition; an improvement comparison is still undeclared. No new
  generation or review batch is queued; simulator engineering can continue.

- [x] **5. Make the notebook and chat experience coherent.** Bring the existing
  authored notebook mode into the same scenario workflow, with notebook work and
  diffs on the left and conversation on the right. Keep historical chat scenarios
  explicit about unavailable work. The accepted dedicated browser replaces the
  earlier Marimo-only direction and reuses the existing Python operations.
  **Done when:** an instructor can follow an existing notebook interaction and its
  work changes in one view. No historical notebook actions are invented.
  **Complete:** the accepted browser layout supports notebook sessions and explicit
  chat mode, saved playback and bound controls. Historical chat has no reconstructed
  notebook work. The collection sidebar now selects saved chat scenarios without
  restarting. Matched comparisons remain separate; Marimo still works.

- [x] **6. Package the prototype for a teammate to run.** Document startup, local
  private-data setup, scenario selection, policy controls and saved results. Resolve
  the existing PR stack through its normal checks and review requirements.
  **Done when:** a teammate can reproduce a saved interaction without this chat,
  with no private student data committed to Git.
  **Packaging complete:** [teammate quickstart](docs/teammate-quickstart.md) and
  `src.agents.chat_demo` provide a create-only authored example using the existing
  runner and views. Setup was checked in a clean temporary checkout using locked
  dependencies; the demo needs no key, private files, database or Docker.
  **Integrated:** PR #30 merged to main at `2720455`. Its files match the reviewed
  version; 419 tests pass with two optional container skips. The manual audit
  stays paused; merging its preserved tooling does not resume labeling.

- [x] **7. Automate the existing contributor checks.** Run the Python suite,
  Marimo validation and existing review-navigation check on GitHub using authored
  fixtures and locked dependencies. No private data or provider credentials.
  **Done when:** a clean GitHub runner reports the checks passing on this PR.
  **Verified:** the [first GitHub run](https://github.com/dstl-lab/chatsight-summer/actions/runs/35516294840)
  passed all 419 tests (two optional skips), both Marimo checks and the Node check.
  PR #40 merged to main at `93904ef`.

- [x] **8. Run the existing comparison workflow across a small group.** Reuse three
  distinct frozen conversation sources and the same two policies, one new student
  decision per condition. Prepare and view offline, continue only untouched ready
  conditions, retain failures, and refuse resends or budget extensions.
  **Verified:** 430 tests pass with two optional skips; both Marimo apps and the
  Node check pass. The authored group exercised three replies, two no-replies and
  one failure with zero model calls. The approved historical group then completed
  six tutor/student exchanges in 12 requests, with no errors or missing conditions.
  Its fixed budgets are exhausted, source pins and exact prompt linkage verify,
  and a readable overview is saved. The [live round](docs/2026-09-21-live-cohort.md)
  is closed; no rerolls or further labeling are queued.
  See [workflow and limits](docs/2026-09-21-chat-cohort.md). This is simulator
  engineering, not a new fidelity experiment or evidence of tutor-policy effects.

- [x] **9. Make an explicit notebook task runnable from public files.** Package
  the existing four-row proportion exercise, initial cell and local evaluator
  through the existing notebook engine. Create a fresh session and editable tutor
  policy offline; keep historical chat work unknown and the UI redesign deferred.
  **Verified:** the [example command and guide](docs/2026-09-21-notebook-example.md)
  prepare/view without calls. An authored two-execution container check verifies
  wrong result, quiet edit, feedback clearing, correct result and exact replay.
  Full suite: 432 passed, three optional skips; the new container check also passed
  separately. No live generations or claims of improved student realism.

- [x] **10. Run the public notebook example once with generated actions.** Use
  the exact authored task/data and existing bounded lesson runner; allow checks
  only when requested. Preserve the model's chosen actions and stop reason.
  **Completed:** quiet revision → real local check (`0.5`, pass) → no-reply;
  three student requests, one container execution, no errors or generated tutor
  turns, three unused decisions. All 77 frozen files and exact saved replay verify.
  The policy/reference were configured but never delivered to a new tutor turn.
  See [walkthrough and limits](docs/2026-09-21-live-notebook-example.md). No new
  labels, forced errors, replacement draws or fidelity claims.

- [x] **11. Show lesson policies in Saved results.** Discover the lesson runner's
  tutor receipts, retain failures and show configured policies separately from
  confirmed delivery. Seven regression cases and the existing notebook/chat
  replays pass without calls or evidence changes. See the
  [repair note](docs/2026-09-22-lesson-saved-results.md).

- [x] **12. Connect an existing conversation example to a fresh notebook task.**
  The optional `--chat-source` setup copies only a verified source's original
  prefix into separate initialization context. Current task/work and the private
  evaluator stay unchanged; generated replies and identifier metadata are excluded.
  Both agents see the example. One private setup with 10 original turns is ready,
  with zero model calls or actions and six unused decisions. This is an optional
  input path, not a validated persona or generator-adoption result. The existing
  next-task path does not retain this initialization. See
  [scope and verification](docs/2026-09-22-notebook-communication-context.md).

- [x] **13. Establish the exact reusable evidence before requesting more review.**
  Eight original first-follow-up references match their independent review and
  all sixteen cached outputs. Preserve both weights for the one duplicate;
  a possible common-rubric pass has a fixed ceiling of 23 messages / 46 flags.
  No existing help/work judgments cover these messages. Original studies remain
  closed and this inventory creates no review queue, labels or generations.
  See [scope and stopping rule](docs/2026-09-22-cached-fidelity-scope.md).

- [x] **14. Complete one common-rubric pass over the cached messages.**
  All 23 messages/46 flags returned, with no uncertainty or missing values.
  Independent intake and arithmetic checks verify 50 pins and exact replay.
  Five reference cases lack work and three contain it. Generated replies include
  work in 6/10 draws in the first group and omit it in 2/6 in the second.
  Balanced work Brier is 5/12, descriptive only; there is no second condition.
  The [report](docs/2026-09-22-cached-communication-results.md) closes this pass;
  no replacement cases, second reviewer, additional labels or generator change.

- [x] **15. Test work-presentation forecasting once using existing labels.**
  Eight approved forecasts completed with no errors or adapter retries. The
  [declared screen failed](docs/2026-09-22-work-presence-forecast-status.md):
  error .80625 versus frequency .612245 and fixed 50/50 .5. Close without
  adding a message-realization component, tuning the prompt or requesting labels.

- [x] **16. Retain the recorded example across authored notebook tasks.**
  The root's explicitly sourced example now survives separately from simulated
  encounter history, with bounded context and verified provenance. New-session
  tampering is rejected; old omissions retain their actual saved inputs. The
  [offline successor and tests](docs/2026-09-22-communication-continuity.md) verify
  both agent inputs and replay, without new model calls or changing prior records.

- [x] **17. Run the prepared second notebook exercise once.**
  After specific approval, [the run completed](docs/2026-09-22-live-notebook-continuity-status.md):
  quiet edit → local check (`0.25`, pass) → no-reply. Three student requests,
  one execution, zero generated tutor/chat turns or failures. Original example
  and prior activity persist; both sessions replay and all 59 pins verify.
  Closed with three decisions unused, no rerolls, new labels or fidelity claim.

- [x] **18. Make conversation-conditioned setup work with a supplied exercise.**
  The existing command now accepts task, activity, evaluator and tutor policy in
  one [exercise file](examples/fruit-count.json), retaining its default example.
  Both agent inputs, next-task context, malformed inputs and source preservation
  are verified offline. The runtime still supports one selected cell, one string
  column and one scalar result; this does not establish broader student fidelity.

- [x] **19. Carry the prepared tutor policy into the workspace.**
  Explicit `--policy-file` loads the starting draft; missing/invalid/blank files
  stop instead of silently falling back. Defaults remain available when omitted.
  Real Marimo controls verify draft edits, reload/reset behavior and exact saved
  policy delivery with authored callbacks. The layout and sending rules are unchanged.

- [x] **20. Use supplied exercise files for subsequent notebook tasks.**
  Optional `--previous` reuses verified history and the original conversation
  example with the new task/policy, inherited model and six fresh decisions.
  Sources stay locked and unchanged through publication; unfinished, conflicting,
  nested or changed inputs cannot publish a successor. CLI and replay verified
  offline; no new live run or labels.

- [x] **21. Pass library guidance through the notebook workspace.**
  Optional `--reference-file` uses the existing tutor schema and exact
  library/version check. The reference reaches only generated tutor requests
  and their receipts; loading/reloading sends nothing. Authored control tests
  verify delivery, unchanged defaults and invalid-input refusal. No new live
  run, labels or generator change.

## Current difficulties

The second notebook exercise is complete and closed after specific approval.
Both linked exercises ended without generated chat, so they demonstrate operation
and preserved context but do not address the communication-fidelity gap.

The [single notebook run with conversation context](docs/2026-09-22-live-notebook-communication.md)
completed after explicit payload approval: three student requests produced a
quiet edit, one passing local check and no-reply. Zero tutor requests or generated
chat; three decisions unused. All 84 pins and saved replay verify. It matches the
earlier demonstration's actions/code, but does not measure a context effect or
improved communication. This run is closed, with no new labels or rerolls.

The live demonstration is complete. Different policy instructions did not always
produce different tutor behavior; single simulated outcomes cannot estimate policy
effects. Generated task details and notebook-like output in that chat-only run
remain synthetic chat; that run performed no execution or assignment verification.
The separate authored notebook walkthrough did execute its supplied task once,
but cannot validate historical student behavior. Combined PR #43 is now
merged into main. Item 14's human measurement input
has been received and its report is closed; no further labeling is queued.

The automatic selection comparison above is complete. Earlier history showed no
accuracy benefit on the 16 complete pairs; all-19 missing-outcome bounds range
from -15.8 to +10.5 percentage points. This separate recognition diagnostic does
not satisfy or reopen item 4's generator-adoption gate. No new labeling or
replacement fidelity experiment is queued; retain the existing simulator.

| Difficulty | What it means for the next work |
| --- | --- |
| Historical notebook actions are incomplete | Chat continuation is observable; silent edits, runs and grader outcomes often are not. Use authored notebook tasks for mechanism testing. |
| Conversations do not reliably identify individual learners | Call these conversation scenarios, not validated personalities or a random sample of students. |
| Existing cases have development exposure and limited prior context | They support development diagnostics, not pristine held-out evaluation or broad generalization claims. |
| Realistic behavior remains unvalidated | More polished UI or more generated conversations cannot substitute for a meaningful fidelity measure. |

## Keep out of the immediate scope

- An exhaustive label taxonomy or another bulk review pass.
- New-quarter data collection as a prerequisite for progress.
- A literal VS Code fork, game world, avatars or Animal Crossing styling.
- Claims of learning gains, realistic silence rates, or causal real-student policy effects.

Current implementation: [scenario workspace](docs/2026-09-20-chat-scenario-workspace.md).
Research evidence: [corpus](docs/2026-09-19-corpus-summary.md) and
[completed generator comparison](docs/2026-09-15-student-communication-result.md).
