# A short student sequence from known initial work

Move from isolated communications to linked actions using the existing notebook
action schema. Start one fresh synthetic branch at recovered case 1's initial
capture and first student/tutor exchange from `evaluation-context-v1`. The
student's only visible initial message names the question; the tutor offers a
stepwise hint. Instruction cell 59 contains the assignment and discount table;
editable code cell 60 contains the unfinished loan function and its example call.

This case has a self-contained function and known incomplete source. Case 3's
repair involves unverified kernel-state claims, while case 4's initial question
is already answered in its capture. Keep those cases unchanged. This is a
purposeful development example, not a representative sample or fidelity estimate.

Reuse `notebook_action.initial_task`, its unchanged `PROMPT` and `Action`, and
`apply_action`. The private runner carries the exact resulting work forward after
each quiet revision and appends history with model origin, work before/after and
no execution. Keep the original capture date explicit, fixed dialogue and null
observation. Generated revisions are synthetic work, not recovered later work.
The initial branch must not contain the later Chinese request, completed code,
human judgments or reference followups from the communication comparisons.

Allow at most three sequential Gemini 2.5 Pro choices under existing defaults.
Stop when the student sends a reply, sends a message with an edit, selects
no-reply, encounters a model error, or exhausts the cap. Chat awaits an externally
supplied tutor response; do not invent one. A cap stop remains `action-limit`,
not a model choice or evidence of completion. Do not require edits, a full
solution, partial progress or terse chat. One action has no assumed duration,
keystroke count or correspondence to a real attempt.

The action schema offers edits and messages, with no execution or grader action.
No code runs or pass/fail result is supplied. This example checks state continuity
and the relationship between doing work and communicating; it does not evaluate
correctness, mastery, realistic pacing or deployed-course outcomes. The existing
declared-runtime checker remains scoped to its authored count task.

New artifacts stay in ignored `data/episode-pilot/initial-work-sequence-v1/`.
Prepare the exact first request and disclose how subsequent requests are formed:
the same fixed source context plus only generated edits/history from this branch.
Record a maximum of three logical requests, each with the adapter's existing
four-attempt ceiling. Preserve standing authorization without claiming separate
exact disclosure approval. Record any actual automatic rejection separately.

Pin the recovered source manifest and selected initial capture, original schema,
prompt, adapter, new runner/reviewer/checks and input/disclosure. Save a pending
receipt before credentials or dispatch, retain errors/retries and refuse resends
or partial-batch resumes. Offline replay must reconstruct every prompt, revision,
history item and stop reason without model or source-code execution.

Use an invented check for quiet-edit carry-forward, chat/no-reply stops, cap/error
distinction, prompt/source drift and preservation of receipts. Show the resulting
trajectory in a compact step sequence: what changed in the notebook, what was
sent to the tutor and what remains unknown. Human review judges plausibility;
mechanical replay alone cannot establish it. Preserve all completed experiments
and leave production modules unchanged for this bounded probe.
