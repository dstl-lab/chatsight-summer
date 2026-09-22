# Make saved simulation progress easier to follow

The user finds the workspace insufficiently engaging and easy to use. The actual
chat view leads with a large unavailable-notebook notice, several equally weighted
controls and generic step names; its latest saved state opens chat at the earliest
prefix. At the narrow desktop app width the header buttons overlap the chat panel.

Keep the dedicated browser, existing light green palette and right chat sidebar.
Replace the chat-only center placeholder with a selectable saved activity list:
the initial context and actual student decisions, with literal message previews.
Describe actions without inferring student intent or unseen notebook behavior.
Selecting a saved state reveals its latest message in the sidebar; initial and
comparison context still begin at the top. Keep manual First/Last navigation and
exact source inspection. The notebook-unavailable boundary remains explicit but
secondary. Put previous/next playback together, group supporting research views
under Run details, and keep the continuation entry clear when sending is enabled.

This is a presentation-only change. Reuse existing state, rendering and dispatch;
no new policy-pair feature, provider requests, study, labels, generation logic,
notebook evidence or dependencies. Verify selection, source escaping, drafts,
read-only/budget/error states and real desktop layout. Use the existing authored
and saved fixtures without modifying evidence. Commit on a separate codex branch
above the current browser PR; preserve main's independent-review requirement.

## Result and validation

Chat-only replay now uses a selectable list of the actual saved student decisions,
with escaped literal previews and the initial supplied-message count. The current
step is brought into view, and the sidebar opens at its latest message. Initial
and comparison context start at the beginning. Previous/Next are together in the
playback footer; notebook replay retains its existing state buttons. The unknown
notebook boundary and distinction between no-reply and budget exhaustion remain.

Run details groups saved results, run context and tutor setup. A continuation
entry appears when sending is enabled, subject to the existing constraints; it
opens the existing controls and never submits automatically. Details now replace
only the center content, preserving scenario heading, chat and playback. Native
disclosure keyboard access, Escape closure and focus return are retained. The
standalone authored prototype is unchanged.

Validation: 544 Python tests passed, three optional container skips; all three
Node checks and both Marimo checks passed. The controller regression covers
literal preview escaping, no-request playback, latest-message positioning,
previous/next boundaries and disabled continuation at earlier states. Independent
JS review found no blocker. Actual browser checks at the narrow desktop pane and
1280px verified no page overflow, selected-step visibility, persistent heading and
playback during details, comparison isolation, and notebook change inspection.
The design detector fell back to regex because optional parsers were absent;
it reported two existing quote/message-selection borders, not a complete audit.

No engine, API or prompt changes; no provider requests, notebook execution, new
labels or evidence writes. These are usability improvements, not measured
usability gains or new simulator-fidelity evidence. Added to the existing browser
PR #48; independent review is still required before merging to main.

## Follow-up: explain conversations, decisions and missing replies

User feedback: scenarios and steps remain ambiguous, and student messages without
following tutor replies look like missing UI content. Read-only exact replay found
29 conversation starts: 27 retain only the imported first student decision; two
have five and three decisions. All currently end awaiting a tutor. Six tutor
replies are saved across the two continued conversations. Five supplied histories
already contain consecutive student messages; the browser preserves them exactly.
Ingestion can skip empty/null responses, so their absence cannot establish that a
tutor never replied.

Clarify conversation selection and one-decision playback in place. Label the
initial supplied history separately, show when a later decision includes a tutor
reply, and explain pending student messages at the point where the reply would
appear. Earlier playback positions must acknowledge later saved activity; the
latest position must not claim a reply was never generated. Keep missing recorded
replies distinct from simulated pending replies. No generation or evidence edits.

Implemented and verified: the catalog now says Conversation, the starting context
is labeled separately, and completed versus failed continuation attempts have
appropriate labels. Activity titles identify newly added tutor replies. Pending
message notes distinguish earlier playback from the latest saved result, read-only
mode, running/blocked requests and decision limits. Source-history gaps receive
neutral recorded-absence notes. The 34 browser Python tests and Node controller
check pass; the browser confirmed both earlier/latest explanations and a typical
single-result conversation. Independent semantic review found no unsupported
claim or functional blocker. No request was sent and the preview remains read-only.
