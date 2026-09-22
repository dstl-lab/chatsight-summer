# Give workspace tutors the configured library reference

**TL;DR:** Connect the notebook workspace to the library-reference support already
used by the tutor and lesson commands. This closes an input mismatch without
changing either generator or adding a new source of student evidence.

Add optional notebook-only `--reference-file` to the app and `reference=None` to
student_workspace.respond. Parse an explicit UTF-8 JSON file once using the
existing LibraryReference schema. Missing, malformed or blank fields stop setup;
chat mode rejects this notebook option rather than silently ignoring it. No
argument preserves existing behavior. Show a small configured-reference notice.

Forward the reference only when generating a tutor reply. Reuse notebook_tutor's
exact library/version validation and request receipt; mismatch fails before any
provider call or exchange creation. Manual replies and quiet student decisions
do not receive the reference directly. The configured reference is not proof it
was delivered, executed or learned. Reload neither rereads the file nor sends it.

Use authored callbacks and the existing Marimo harness to verify exact tutor-only
payload/receipt delivery, invalid-file handling, mismatch refusal, absent-option
compatibility and no calls on load/reload. Update the notebook launch examples to
pass the same reference used by the lesson command. No live run, labels, engine
or prompt changes, file watcher or layout redesign.

Implemented and verified: the new regression cases failed before the change
(unsupported backend option, ignored app file) and pass through the actual Marimo
controls afterward. They verify unchanged defaults, exact tutor payload and saved
receipt, no raw reference in the student input, preserved loaded content after
disk changes/reload, malformed input rejection and mismatch refusal before an
exchange or provider call. Full suite: 466 passed, three optional container tests
skipped, one existing dependency warning. Both Marimo checks and Node navigation
pass. No live calls, executions or labels were added.
