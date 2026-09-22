# Recorded communication examples for an authored notebook task

**TL;DR:** Allow the public notebook setup to take an existing chat session as
an optional communication example. Copy its original visible conversation into
the existing initialization field, separately from the authored current task.
Preparation is offline. This is an input bridge, not a validated persona or an
adopted fidelity improvement.

The notebook engine already accepts initialization context and shares it with
both student and tutor. Reuse that path and the saved chat loader. Copy only the
source manifest's validated `query.prefix`, never its cached/generated replies,
later interventions, labels or target continuations. Keep identifier metadata
and source paths outside model context; retain source and prefix hashes in the
new session's researcher-facing provenance. Quoted text remains verbatim and
can itself contain personal content; this is not an anonymization tool.

Use a new destination outside the source session. Verify the source before
preparation and again before publication; reject changed or invalid records.
Keep the current exercise, work, authored opening dialogue, empty observations,
private expected value and six-decision budget unchanged. Limit the copied
prefix to 64 KB rather than silently truncating it. Reuse create-only publication
and the existing lesson/workspace/replay tools; no additional engine or UI.

The recorded conversation is an example from a different task, not evidence that
its participant attempted this exercise. Do not infer stable personality,
ability, emotion, notebook actions or outcomes. Sparse wording is a light guide,
not a requirement to copy code or answer a tutor question. Both model roles see
the example, so a later comparison cannot attribute changes solely to the student.
The existing next-task transfer omits arbitrary initialization; this scope covers
one fresh task, not a persistent persona across a sequence of tasks.

Acceptance is offline: verify unchanged current task/state, source preservation,
prompt exclusion of generated continuations and identifier metadata, private
evaluator isolation, existing-destination refusal and failure before publication
for invalid/changing sources. Prepare one separate local example from an existing
case, retaining its original receipts. No model calls, execution, new labels or
automatic follow-up experiment. Earlier closed studies and the fidelity gate
remain unchanged; no claim of improved student behavior follows from this bridge.

## Completed verification

The optional `--chat-source` path is implemented without changing student/tutor
engines or their prompts. Two new regression tests failed before implementation
and now pass. The full suite passes 441 tests, with three optional container skips
and one upstream warning; both Marimo checks and Node navigation pass. Independent
review found no issues. Authored test callbacks exercise both agent prompts and
saved replay, with no provider or container calls.

One private setup is saved at `data/notebook-communication-example/`, using the
first existing handoff case selected before generation. Its original prefix has
10 turns, including six student contributions; the cached simulated reply is
excluded. All six decisions remain unused. Source files and the previous public
walkthrough are unchanged, and `verification.json` records their hashes and the
new input checks. `initial.html` displays the prepared state. No live run or new
human review is queued. The notebook example creator's source hash changes, so
older all-source audits still require their recorded revisions; do not rewrite
their pins.
