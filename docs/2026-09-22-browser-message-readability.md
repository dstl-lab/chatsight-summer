# Read saved tutor replies comfortably

Use the existing Python Markdown dependency to display tutor paragraphs, lists,
emphasis and fenced code in the connected browser. Student text stays literal;
Inspect source retains every original message. Formatting is only a display
projection, never a change to saved evidence, model inputs or state bindings.

Keep remote content inert: no active links, images, raw HTML or message-supplied
attributes. Add scoped typography and scrollable code blocks to the existing
shell. No new editor, highlighting library, generation, labeling or experiment.
Verify hostile formatting, exact source preservation, notebook/chat display and
the read-only saved collection before committing in the existing worktree.

## Result

Tutor messages now use restricted Markdown at the HTTP presentation boundary.
The existing Markdown version is declared directly so the browser does not depend
on installing Marimo. The renderer disables HTML, links/images/references and
fence attributes; code blocks retain indentation and support keyboard scrolling.
Original text and student typing remain literal. No state/receipt/engine changes.
This is basic Markdown display, without math rendering or syntax highlighting.

All 509 Python tests pass (three optional container skips); Marimo, all three
Node checks and the offline lockfile check pass. Independent review exercised
additional hostile inputs and found no remaining issue. Browser inspection
verified Scenario 01's formatted code, lists, exact-source view and keyboard focus,
plus the completed notebook view. Sending stays disabled on ports 8428 and 8427.
All 29 scenarios load; all 105 chat files and five notebook files remain unchanged.
The local audit is in ignored `data/browser-message-readability-verification/`.
No model requests, code execution, labels or new student-fidelity evidence.
