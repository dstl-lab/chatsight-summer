# Use the trained student through the existing browser controls

The approved hybrid exchange established that the saved local student can answer
a Gemini tutor. Make that connection available through the existing conversation
controls instead of writing another experiment or asking for labels.

Add one optional `generate_reply(prefix) -> str` callback to the chat workspace
and browser app. Supply the exact ordered `{role, text}` history from verified
session state, after the actual tutor reply has been added. Preserve whitespace
and Unicode; do not reconstruct history from the line-based legacy prompt. Read
state before the engine takes its lock and require the displayed binding. The
existing engine still handles receipts, errors, decision budgets and replay.

This callback produces a message, not a decision about whether to reply. It is
suitable for the current reply-only trained model; it does not learn silence.
Existing schema-based generators and default behavior remain available unchanged.
Conflicting student callbacks fail before dispatch. Browser use requires chat
mode and an explicit tutor callback; policy-comparison creation/runs are excluded
because their independent runner does not carry this callback.

Use an isolated checkout so prior experiments retain their pinned source files.
Check both a single session and selected conversations with authored callbacks,
including manual/generated tutor replies, exact history, stale bindings, errors
and no resend. Reuse the frozen local worker in a private launcher for the saved
runtime; keep actual role identities and raw call receipts separate. Do not
publish private conversations, weights or local paths.

No new provider request, training or fidelity experiment belongs to this change.
The completed hybrid session remains closed and read-only. A working browser
integration is an implementation result, not evidence of student realism or
instructor-policy effectiveness.

## Completed

The callback now works for both a single chat and selected conversations. The
same backend receives initial, manually prompted and policy-guided student turns;
the latest tutor text enters its exact history once. Blank/invalid outputs and
backend exceptions become saved errors and cannot be resent. The default
schema-based path is unchanged. No new CLI flag or model dependency was added.

For Python launchers, pass `generate_reply=trained_reply` and
`generate_tutor=tutor_callback` to `browser_workspace.create_app(...,
chat_mode=True)`. `trained_reply` takes the raw ordered list of role/text objects
and returns nonblank text. Its model adapter may use the existing
`student_training.messages(prefix)` serialization. The legacy session model
field does not identify two providers; a mixed launcher must retain actual role
identities and call receipts separately, as the private launcher does.

The private launcher under `data/trained-student-workspace-v1/` connects those
callbacks to the unchanged saved local and Gemini workers with bounded
subprocesses and no retry. A separate three-decision session is prepared, has
zero generated decisions, and loads with sending disabled. The original hybrid
exchange remains closed in its original worktree. No requests were sent here.

Verification: all 699 Python tests passed, with three optional skips. Five new
tests cover exact histories, two selected conversations, lock safety, routing,
stale/budget/send guards and failures. An authored private check verifies worker
commands, settings, timeouts and receipts without subprocess generation. The
actual prepared launcher loads through the browser API read-only, and an attempted
submission is refused before either backend. Independent review found no
remaining issues; the original frozen source and closure hashes still verify.
