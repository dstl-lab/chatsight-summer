# Separate notebook edits from chat

The completed continuous sequence exposed a model output that put proposed code
in chat and installed a placeholder in the notebook. Both tutors discussed the
proposal without addressing the installed cell. The user asked to clarify this
contract and make new messages easier to follow in the workbench.

New sequence plans use explicit `replacement_code` and `chat_message` fields.
Only replacement code edits the selected cell; chat can contain code without
editing or running it. Preserve quiet edits, empty-cell edits and incorrect code.
The tutor must distinguish the installed cell from a pasted proposal and ground
any execution claim in current feedback. This clarifies the interface; it does
not establish that model behavior improves until separately tested.

Keep the completed version-one plan and raw receipts unchanged and replayable.
Version one is read-only; future preparations use version two with new schema,
prompts and current code pins. All other source/runtime/input checks stay strict.
No new provider batch or student labeling is part of this change.

In chat, mark newly revealed messages with a visible label and restrained
highlight. Advancing a step should smoothly reveal new content when following
the conversation, preserve a reader's manual position, and respect reduced
motion. A pending message becoming committed is the same message. Steps without
new chat should leave the conversation still; switching runs resets this context.

Validate with authored sequence tests, unchanged offline replay, controller tests
and the existing browser workbench. Keep the UI's present layout and styling.

## Implemented and checked

Version-two preparation now exposes the explicit provider fields and descriptions;
existing action application still stores canonical source/text internally. Tutor
context instructions identify the installed revision and distinguish it from chat
proposals. The original version-one prompts and schema remain available only for
exact replay with the known historical engine hash; new dispatch is refused.

Chat uses ordered role/text identity to detect appended messages independently of
pending/committed metadata. New content gets a visible New label, an outline and a
polite announcement. Native smooth scrolling follows updates near the bottom;
earlier readers keep their place with an explicit jump. Unchanged stages do not
initiate scrolling, and reduced motion uses instant positioning. Redundant caller
scrolls were removed so they cannot override the shared behavior.

Verification: 1,003 Python tests passed, three optional tests skipped; the existing
Starlette/httpx deprecation warning remains. All ten Node suites passed. Independent
review confirmed the original engine hash against Git, exact replay of the private
completed run, all eight original artifact files unchanged, and rejection of old
or mixed field names in the new contract. Authored tests preserve invalid code and
chat-only proposals without execution or automatic repair.

Browser verification on port 8455 confirmed one new student/tutor marker at a
time, pending-message continuity, preserved manual reading position, the explicit
jump, retained timeline focus and no movement on the final no-action step. No
browser console errors were reported. The design detector ran in degraded regex
mode because optional parser modules are unavailable; its two warnings concerned
pre-existing accent borders outside the added styles, so this is not a clean
automated design audit. The changed UI was visually inspected.

No private generation or execution was dispatched. The schema and prompt change
is implemented and mechanically checked, not a demonstrated model-behavior gain.
