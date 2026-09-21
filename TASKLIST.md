# Simulated students: task list

**TL;DR:** Saved interactions and paired tutor-policy comparisons now work.
The fidelity target is excess work/evidence presentation in chat, but the current
help-only reference set cannot validate a fix. Generator-adoption experiments stay deferred.
The teammate quickstart and authored offline demo are on main via
[PR #30](https://github.com/dstl-lab/chatsight-summer/pull/30). Automated contributor
checks are also merged via [PR #40](https://github.com/dstl-lab/chatsight-summer/pull/40).
The six-case [joint evaluation](docs/2026-09-21-joint-fidelity-check.md) is closed:
four recorded-message preferences and two both-possible judgments. It supplies
qualitative feedback, not the missing binary labels. Keep bulk labeling and
workspace redesign paused; no further review batch is queued. The automatic
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
PR #44 merged into the results branch; combined PR #43 awaits independent review
against main. This verifies operation, not student realism or policy effects.

Updated: September 21, 2026. Unchecked items are proposed work, not completed results.

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
  **Deferred:** the measurement gate in item 3 failed. No generation or review
  batch is queued; this does not block simulator engineering.

- [ ] **5. Make the notebook and chat experience coherent.** Bring the existing
  authored notebook mode into the same scenario workflow, with notebook work and
  diffs on the left and conversation on the right. Keep historical chat scenarios
  explicit about unavailable work. Continue using Marimo and coordinate with the
  teammate's viewer work before duplicating it.
  **Done when:** an instructor can follow an existing notebook interaction and its
  work changes in one view. No historical notebook actions are invented.
  **Deferred by Minchan:** leave the current layout for the later workspace redesign.

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

## Current difficulties

The live demonstration is complete. Different policy instructions did not always
produce different tutor behavior; single simulated outcomes cannot estimate policy
effects. Generated task details and notebook-like output remain synthetic chat.
No notebook execution or assignment verification occurred. Combined PR #43 still
needs independent review for main integration; no new labels are requested.

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
