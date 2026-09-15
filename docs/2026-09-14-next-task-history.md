# Carry one observed encounter into the next task

The later [multi-task extension](2026-09-15-multi-task-history.md) supersedes the
one-predecessor limit for new handoffs. This memo records the original design and
completed run; those saved inputs and results remain unchanged.

The bounded student now acts and stops within an encounter. A new task still
starts without that experience. Minchan directed continuation until input is
needed; the earlier coaching direction calls for retaining observed task,
interaction and feedback history. Add a small initializer using the existing
saved student and lesson APIs. Do not reopen the paused behavioral review or
history-ablation experiments.

Read a completed predecessor through its existing locked replay. Require a
generated terminal no-reply action, then create a fresh task session with the
previous encounter's visible task, activity, dialogue, work, actions and sanitized
feedback in its initialization. Keep the old stop terminal. The researcher
supplies the new task, work and tutor-ending dialogue; this does not imply that
the student independently chose another task or mastered the previous one.

Both the student and tutor receive initialization, so this is **shared observed
history**, not private student memory. Exclude the predecessor's initialization
to avoid recursively accumulating earlier encounters. Exclude private expected
answers, runtime bindings, provider receipts and model/identity provenance from
the shared packet. Keep predecessor session/state hashes, source path and helper
source hash in the new manifest's private provenance instead. Preserve the old
session byte for byte. The new task receives its own fresh work, evaluation,
empty current feedback/history, budget and inherited model.
Prepare initialization and provenance together before atomically publishing the
new manifest into an exclusively created directory. An interrupted preparation
must not leave a runnable child without its ancestry record. Give each new
session a distinct branch identifier, including destinations sharing a basename.

Retain one predecessor without summarization, reflection or inferred traits.
Reject a packet larger than 64,000 UTF-8 bytes before creating output, rather than
silently dropping events. More extensive memory should be motivated by an actual
context limit, not added preemptively. Use a new module so the source-pinned
student engine, prompts, tutor and runtime remain unchanged.

Verify history visibility to both agents, evaluator/provenance isolation, fresh
task state, predecessor immutability, terminal/budget distinctions, one-predecessor
scope and input boundaries with offline injected adapters. Then initialize one
new authored task from the existing completed proportion encounter and allow at
most six student decisions and two tutor replies through the existing lesson
command. No rerolls, prompt revision during the run, or human plausibility batch.
Report whatever happens; carrying context is not evidence that it caused a
behavior change or learning. The existing finite fidelity benchmark remains a
separate proposal needing team research decisions.

## Human input for the next research step

With bounded encounters and one-task continuity working, further authored runs
are not the next fidelity milestone. Prepare a small independent coding handoff
using only the eight recorded next messages from the completed communication
development set. Preserve their exact visible prefixes and existing v7 action
definitions. Omit generated candidates, prior labels, plausibility judgments and
task-relationship questions. This is a check of whether humans can apply the
measurement consistently, not another student-plausibility review or a benchmark.

Ask Minchan to assign two independent reviewers, preferably teammates who have
not seen the old assisted labels. Supply blank separate forms and record prior
exposure; do not generate or infer their answers. No messages are sent to them
without explicit authorization. Stop at the prepared handoff until reviewers
are available. Do not launch a new model batch, resume the history ablation or
turn this exposed eight-case set into a held-out fidelity score. After reviewing
coding uncertainty, the team still needs to agree on data/split, budget and
practical improvement criteria for the proposed baseline comparison.

## Initialize and run the next task

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_next_task data/finished-student data/next-student --task data/next-task.json --activity data/next-activity.json --evaluation-file data/next-evaluation.json --max-decisions 6
```

Initialization makes no model or container call. The new task JSON supplies its
own initialization, task statement, work and student/tutor dialogue ending with a
tutor reply. The activity and optional evaluation follow the existing formats;
omitting the evaluation retains legacy distinct counting. The predecessor must
have a recorded generated no-reply ending, not an active/budget pause, failure or
authored stop. The destination must be new. The model is inherited, while a fresh
branch identity and cumulative decision budget belong to the new encounter.

Use the existing `notebook_lesson` command to run the resulting session. Prior
work and feedback appear only under `initialization.previous_encounter`; current
`observation` is null and action `history` is empty at creation. The source path,
predecessor hashes and helper source hash stay in manifest provenance, outside
both agent prompts. Only one preceding encounter is retained; older initialization
is excluded without rewriting the predecessor's records.

## Completed verification and live continuation

The final related suite reports **56 passed, 2 skipped**. The optional container
integrations were not rerun for this initialization change. Tests cover shared
history in both prompts, old/new evaluator isolation, fresh state and budgets,
source provenance, predecessor immutability, terminal restrictions, UTF-8 bounds,
CLI validation and unique branch identities for matching directory names.

Independent review found that the first implementation published a runnable
child before adding provenance. A failing interruption regression reproduced that
gap. The corrected implementation stages the complete manifest and publishes it
atomically only after provenance is saved; the regression passes and follow-up
review found no remaining actionable issue. Existing engine/tutor/runtime modules
and prompts remain unchanged.

One authored successor used the completed proportion encounter as shared history
and a new table with a category-count task. Gemini 2.5 Pro generated three actions:
quiet revision, requested check returning integer `2` with passing feedback, and
chosen no-reply. Three of six decisions remained. No tutor message was requested,
so no generated tutor reply or reference delivery occurred. The earlier pass at
`0.5` stayed historical; the count received its own check under its own evaluator.

The new source used the row-count operation visible in earlier work, but this
single run has no comparison without history. It does not establish a memory
effect, acquired skill, behavioral fidelity or independent choice to continue.
The new task and initial dialogue were researcher supplied. Exact replay verifies
both sessions with unchanged files, and earlier source-pinned traces remain
intact. Plans, inputs, private ancestry, receipts, readable trajectory and verified
hashes are retained in `data/episode-pilot/next-task-history-v1/`.

## Prepared reviewer handoff

Minchan answered "2 reviewers." The prepared handoff is in ignored
`data/episode-pilot/fidelity-coding-readiness-v1/`: one `packet.md` shared by both
reviewers and separate `reviewer-1.json` / `reviewer-2.json` blank forms. All eight
recorded messages and prefixes match the saved source hashes. No generated
candidate or previous label is included in the packet. The source episodes
contain legacy label metadata, which is excluded from the handoff. Both forms contain all
eight case IDs and no suggested answers. No model or database calls were made
for this preparation, and no messages were sent to reviewers.

Each reviewer should choose the primary observable message action, retain
insufficient-evidence where needed, and note prior exposure. They should complete
their forms independently before discussing cases. The next input is those two
completed forms. Then report agreement, disagreements and uncertainty once;
do not automatically tune the simulator or extend the batch. This is readiness
for a measurement, not a fidelity score or a restart of the paused review loop.


## Portable review UI

Minchan requested a UI instead of the packet. `src/eval/coding_review.py` builds
one self-contained HTML page per reviewer from the same frozen source records,
seven action definitions and blank forms. It checks the source hashes, preserves
numbered-line gaps, escapes embedded data and includes no prior labels or model
candidates. All original handoff files remain unchanged.

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.eval.coding_review data/episode-pilot/fidelity-coding-readiness-v1
python3 -m http.server 8400 --bind 127.0.0.1 --directory data/episode-pilot/fidelity-coding-readiness-v1/ui
```

The builder uses a new output directory (`--output` overrides the default `ui`).
The server is only a local preview. Give each teammate their assigned
`reviewer-1.html` or `reviewer-2.html` file. The page contains everything it needs;
there are no external scripts, fonts, services or account setup.

The reviewer enters their name/initials and prior exposure, then sees one recorded
message with its context and seven choices. Notes are required for changed code,
other and insufficient evidence. Progress resumes from browser-local storage when
available; unreadable drafts, storage failures and changed-tab conflicts never
silently replace saved answers. Each reviewer has a separate storage key. One
active tab per reviewer is the intended scope; this is not synchronized storage.
The final screen lets reviewers copy or download the original response-form JSON.
Downloads do not submit anything, and downloaded drafts are copies, not a
cross-device resume mechanism. Original blank forms are never rewritten.

Validation: the builder regression and Node state check pass. They cover source
integrity, exact text, embedding safety, reviewer isolation, incomplete notes,
resume, failed saves, stale tabs and invalid saved metadata. Browser checks on a
separate test packet completed all eight cases, enforced a required note, resumed
partial and finished work after reload, and verified the copied eight-case JSON
and blank second reviewer. No human ratings were created by these checks.
Desktop layout was inspected and navigation kept visible beside long context.
The browser viewport override did not take effect, so mobile rendering is not
claimed verified. Direct file navigation was blocked by the browser testing
policy; the pages were tested through localhost. The in-app download observer
timed out without a console error; the copy-to-clipboard path and exact returned
JSON were verified as the usable alternative. No benchmark or model run occurred.
