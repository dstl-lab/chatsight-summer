# Simulated students: task list

**TL;DR:** Saved interactions and paired tutor-policy comparisons now work.
Next, choose one measurable student-fidelity improvement using the existing
evidence. Keep one bounded research question at a time, without restarting the
labeling queue or redesigning the workspace yet.

Updated: September 20, 2026. Unchecked items are proposed work, not completed results.

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

- [ ] **3. Choose one measurable student-fidelity improvement.** Use the existing
  reports and instructor feedback to identify a specific failure, such as excess
  explanation in otherwise terse student conversations. Establish whether existing
  evidence can measure it before changing the generator. Length and formatting
  diagnostics alone cannot establish appropriate behavior.
  **Done when:** one written decision specifies the target, baseline, measure,
  fixed cases and call budget, and adoption/stopping rule. If measurement cannot
  support the claim, narrow the claim instead of generating more examples.

- [ ] **4. Run only that declared comparison, if it is justified.** Preserve the
  original generator and frozen evidence; treat any changed prompt as a separate
  candidate. Reuse cached outputs where inputs match. Request human judgments only
  if a specific adoption decision cannot be resolved otherwise, using a small
  fixed sample and no rolling review queue.
  **Done when:** report improvement, no improvement, or inconclusive evidence and
  close the comparison. Do not reroll until an appealing difference appears.

- [ ] **5. Make the notebook and chat experience coherent.** Bring the existing
  authored notebook mode into the same scenario workflow, with notebook work and
  diffs on the left and conversation on the right. Keep historical chat scenarios
  explicit about unavailable work. Continue using Marimo and coordinate with the
  teammate's viewer work before duplicating it.
  **Done when:** an instructor can follow an existing notebook interaction and its
  work changes in one view. No historical notebook actions are invented.

- [ ] **6. Package the prototype for a teammate to run.** Document startup, local
  private-data setup, scenario selection, policy controls and saved results. Resolve
  the existing PR stack through its normal checks and review requirements.
  **Done when:** a teammate can reproduce a saved interaction without this chat,
  with no private student data committed to Git.

## Current difficulties

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
