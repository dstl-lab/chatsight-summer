# Give the tutor the student's current work

The saved student can continue after a supplied tutor reply. The tutor previously
had to interpret raw session JSON to see what changed. The new readable local
handoff includes the pending message, preceding dialogue, selected cell and
current feedback. It shows a net source diff from the work at the most recent
supplied tutor exchange, or the initial work when no such exchange exists.
That comparison describes two saved endpoints, not every intervening action or
what a historical tutor necessarily saw.

This handoff explicitly gives access to the selected cell and current local
feedback. It does not imply access to an entire notebook or a student's beliefs,
knowledge or unobserved activity. Cleared checks stay cleared: an old passing
result must not become feedback on a new revision. Pending student text appears
once, and internal runtime bindings and source hashes stay outside visible content.
Environment failures show that execution was unavailable and the work is ungraded;
their full diagnostic remains in the original operation receipt.

Export a JSON handoff for binding and print a readable view. Accept a supplied
reply only against that same session and state. Extend the existing `step`
transaction with optional expected session/state hashes, checking both under its
existing lock before any write or dispatch. Reuse the provider, execution,
receipts and budget handling; do not duplicate the transaction in a tutor adapter.
An outdated handoff must fail without changing the student or sending a request.

The wrapper's extension leaves the student prompts, schemas, action transitions
and runtime modules unchanged. Explicitly support the original wrapper source
at commit b2a417b as one compatible replay version, with every other source/schema
pin still exact. Keep old manifests and receipts unchanged; new operations record
the actual current engine. Unknown source changes continue to fail closed. Verify
the authentic saved v1 session and controlled old/new continuation, including
mixed-version receipts. This is a narrow additive compatibility rule, not general
session migration or permission to ignore source pins.

Completion means an educator can inspect the saved work, supply a reply using
that handoff, and continue the same student safely. Verify current-feedback
handling, endpoint diffs, pending-message visibility, stale/cross-session refusal,
compatibility and the command-line path offline. No new model batch or student
plausibility judgments are needed to test this context/interaction change.

## Tutor workflow

Inspect a saved student and export the exact handoff you are responding to:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.tutor_context data/my-student --output data/handoff.json
```

The command prints a readable view and creates the JSON file without overwriting
an earlier export. It does not generate messages or execute code. Inspection works
for active and terminal states too, but only a pending student message permits
a tutor reply. Remaining decision budget is shown separately from student status.

When a message awaits the tutor, write the reply in a UTF-8 file and continue:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.agents.notebook_student step data/my-student --send --context-file data/handoff.json --tutor-file data/tutor-reply.txt
```

The handoff's content hash detects accidental edits. Its session/state bindings
are checked inside the student's existing exclusive transaction lock. A stale
or cross-session reply is rejected without a new receipt or dispatch. A second
reply against the same handoff cannot silently answer a later student message.
The raw `--tutor-file` path remains available for existing callers; it does not
claim to bind the reply to an earlier exported view. A supplied reply may have
been written by a person or an external tutor system; no author identity is inferred.

## Completed verification

The existing command-line provider path accepts a context-bound reply and continues
from the saved work. Controlled tests cover current checked feedback, edit/check/edit
invalidation, net diffs across action pauses, exact multiline tutor text, one pending
message, Markdown fences within source, create-only exports, altered handoffs,
stale and differing-session bindings, and budget enforcement across old/new receipts.
New version-2 receipts require the current engine exactly; the original wrapper
is accepted only with its original versionless operation format.

The related offline suites pass: **31 passed, 1 skipped**. The skipped case requires
an explicitly selected local container image; no model or Docker calls were made
for this update. The command was:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m pytest tests/test_tutor_context.py tests/test_notebook_student.py tests/test_notebook_session.py tests/test_notebook_action.py tests/test_notebook_check.py tests/test_notebook_runtime.py tests/test_student_task.py -q
```

The authentic saved session in `data/episode-pilot/continuing-student-v1/session`
still replays exactly, with every file unchanged. Its environment-error stop stays
terminal and ungraded. A readable context, JSON export and verification record are
retained separately in ignored `data/episode-pilot/tutor-context-v1/`. This is a view
of the existing trace, not a new model trajectory. The original wrapper source hash
was independently checked against commit b2a417b.

This completes the tutor-context milestone. It makes the current one-cell student
usable across tutor exchanges; it adds no evidence of learner fidelity, calibrated
behavior, general notebook execution or cross-task memory. No labeling batch or
instructor plausibility review was required.
