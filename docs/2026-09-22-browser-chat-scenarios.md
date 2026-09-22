# Saved chat scenarios in the browser workspace

The browser currently opens only notebook sessions, while existing conversation
scenarios remain in Marimo. Add an explicit `--chat` launch option for one saved
chat session using the same browser and existing Python continuation operations.
This connects the interface to our available conversation evidence without another
experiment, generation batch or labeling pass.

Verify the saved chat through its existing loader under a shared read-only lock.
Project the original supplied prefix and each saved decision into playback frames.
Keep origins and pending messages, count failed decisions against the budget, and
preserve `ready`, awaiting-tutor, no-reply and error states. Do not expose source
identifiers or raw diagnostics. Missing work, changes, activity and execution
feedback remain null; code in a chat message is not a recovered notebook cell.

Render chat as a conversation with a concise unavailable-notebook notice rather
than an empty notebook panel. Reuse existing bound advance/policy/manual controls,
with sending disabled by default. Reject notebook-only reference configuration
for chat. Preserve duplicate, stale, terminal and interrupted-exchange guards.
No changes to either generator, saved engine, schema, or previous research runs.

Verify with authored saved chats, control callbacks, tampering/error checks and
browser playback. Open an existing historical session read-only if its saved
engine is compatible; never migrate or regenerate it just to make it open.
One session per server remains the limit; catalog, import and matched comparisons
are separate work. Authorization follows the user's standing continue instruction.

## Result

Implemented with the existing chat loader and continuation functions; no engine
or prompt changes. All 497 Python tests pass (three optional container skips),
both Marimo checks and all three Node checks pass. New authored checks cover
read-only playback, null notebook evidence, source-ID omission, tampering,
errors/interruption, locks, stale/budget/terminal guards, policy/manual dispatch,
CLI configuration and refusal of notebook-only references.

All 29 existing historical workspace scenarios render with 105 saved files
unchanged; the local audit is in ignored `data/browser-chat-verification/`.
The actual browser on port 8428 displays case 1 read-only: ten supplied-prefix
messages, five saved decisions and the pending simulated message. Initial and
later playback states, source inspection and disabled sending were verified.
Independent frontend/backend review found no remaining blocker. No new model
request, runtime execution, label, migration or fidelity claim was produced.
