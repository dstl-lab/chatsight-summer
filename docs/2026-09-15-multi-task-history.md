# Preserve observed history beyond two tasks

The completed two-task run exposed a concrete continuity limit: creating Task 3
from Task 2 currently excludes Task 2's initialization, losing Task 1. Extend the
existing handoff and replay helpers within Minchan's standing direction to
continue simulator development independently of the delayed reviewer. No new
labeling, fidelity experiment, model request or learning claim is needed.

Keep `previous_encounter` for the immediate predecessor and add a flat
`earlier_encounters` list, oldest first. Reconstruct these observed records from
the linked saved sessions, checking every predecessor's manifest/state/history
hashes and generated terminal stop. Exclude arbitrary prior initialization,
private evaluators, runtime bindings and provenance from shared history. Both
agents receive this history through the existing initialization path. New work,
feedback, actions, branch identity and decision budget remain separate.

Reuse one read-only ancestry loader and observed-record projection in the
handoff and HTML replay tools. Reject missing, mismatched, busy or cyclic source
chains. Existing single-predecessor records keep their exact original prompts;
their replay must show only the history actually delivered at each task.
New handoffs retain all linked observed encounters without recursive nesting,
summarization or inferred traits. Apply the existing 64,000-byte UTF-8 ceiling to
the whole retained history and fail before publication when it is exceeded.
This is a bounded local history store, not a retrieval or reflection system.

Verify a three-/four-task continuation with offline adapters, including history
ordering, both agent inputs, feedback/privacy separation, unchanged ancestors,
lineage mismatch and size-limit rejection. Reuse the existing replay regression
for safe HTML and no-clobber behavior. Prepare a third task from the two completed
authored encounters and export its replay without generation. Preserve original
artifacts and source-pinned engines; document the resulting checks here.

## Use and verification

The existing command now retains all verified linked encounters. No new flag or
dependency is required:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_next_task data/finished-student data/next-student --task data/next-task.json --activity data/next-activity.json --evaluation-file data/next-evaluation.json --max-decisions 6
PYTHONPATH=. ../main/.venv/bin/python -m src.eval.notebook_replay data/next-student --output data/next-student-replay.html
```

The new four-task regression first failed because `earlier_encounters` was
missing, then passed. The related student/lesson/tutor-context/teaching-pair/replay
suite passes **32 tests**. Independent review also rejected cycles, missing/busy
ancestors and forged inherited records without output. No engine, model adapter,
runtime, action schema or recorded receipt changed.

The prepared third task is in ignored `data/episode-pilot/multi-task-history-v1/`.
It follows the completed blue-proportion and amber-count tasks, carrying both
records in 4,334 UTF-8 bytes. Their checked values of 0.5 and 2 remain historical;
the new amber-proportion task starts with no feedback and no recorded action.
Both agent inputs contain the same history. Its six-decision budget is unused.
There were **zero new model requests, container checks or human ratings**.

Eight earlier saved sessions replay exactly, 44 prior session files remain
unchanged, and 60 artifact hashes from historical reports match. The new HTML
shows all three tasks, the one record supplied at Task 2 and the two supplied at
Task 3. Browser inspection verified Task 3 navigation and its ungraded initial
state. Preparation inputs, source pins and verification receipts remain beside
the replay; earlier reports and HTML files were not regenerated.

## Limits

This establishes history retention and delivery, not retrieval quality, acquired
knowledge, a memory effect or fidelity to real students. No new student action
has been generated on Task 3. The third task and its initial dialogue are authored.
An older chain can be recovered from its actual saved encounters even if an
intermediate legacy task received only its immediate predecessor; replay preserves
that distinction instead of rewriting what the earlier model saw.

The entire source chain must remain available at its recorded local paths;
`--previous` overrides only the immediate predecessor when exporting. Overflow
fails before publishing a child and requires an explicit future context-selection
decision. Ancestry is checked by handoff and replay. The unchanged student engine
does not authenticate a manually edited fresh manifest before its first action;
this remains a local research tool, not an adversarial storage boundary. Historical
scripts pinning the old helper source must be run at their recorded version.
