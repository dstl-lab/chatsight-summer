# Test one recorded notebook replay

Minchan approved the proposed one-episode offline replay after the notebook data
refresh. The question is whether the richer logger records support an inspectable
request capture, tutor outcome and subsequent code execution, with gaps explicit.
This is a feasibility probe, not a simulator evaluation or production importer.

Reuse the read-only probe and the refresh's fixed August 7–September 29 cutoff.
Inventory instrumented analytics sessions using metadata only. Select the earliest
session with at least two tutor requests, an execution request/result and exactly
one nonempty notebook-session identity; break ties by an opaque session key.
Freeze that selection before reading content. Fetch at most 100 events/2 MB for
that session, retaining account identifiers only in SQL joins. Include linked
notebook-info records by request identity, not proximity. If the selected session
is incomplete, report the gaps rather than replacing it with a nicer example.

Verify event/session identities, unique client sequences and request/response and
execution/result links. Check request-time notebook hashes. Display submitted
execution source and recorded result; compare source endpoints only for the same
native cell in the same notebook session. Source-change metadata does not supply
the edit itself. The server arrival clock must not override client sequence.
Keep prediction-time input separate from later evidence. No student code runs.

Create a private, self-contained static HTML replay with escaped notebook/chat
content and no active scripts or external resources. Use existing text-rendering
helpers, not the synthetic-session loader. Label the origin as recorded notebook
events / probable instrumentation test. Show unavailable source and unverified
natural-student provenance explicitly. The replay script stays a private one-off
probe; no new product importer or browser mode is introduced.

Finish after one replay or a documented reconstruction failure, with a runnable
local check and a local commit of this memo/results. No model calls, labels,
training, remote publication or changes to closed experiments are authorized by
this probe. Database access remains read-only and its temporary tunnel is closed
after extraction.

## Result

The probe reconstructed one episode. Metadata identified nine analytics sessions,
seven eligible. The frozen earliest eligible session spans approximately 4.4
seconds on September 27. It contains two linked tutor exchanges, three linked
execution request/result pairs (two `ok`, one `error`), and two request captures
whose stored checksums and native active-cell identities verify.

The initial event-type filter returned 29 events and appeared to omit client
sequence 7. A second query of all event types in the same frozen session found
the omitted `session_start`. The retained full extract contains consecutive
client sequences 1–30. Both queries/receipts are preserved. Five adjacent event
pairs have reversed server arrival times relative to client order; replay uses
verified client order and displays both timestamps in its trace. Consecutive
logged sequences do not prove that every edit/keystroke was logged.

One native-cell source difference is recoverable between observed endpoints.
Source-change events themselves contain no replacement text, and the final such
event lacks a native cell ID. The replay displays those limits instead of filling
in edits. Execution results are labeled literally, not treated as assignment
passes/failures. The end is the end of the available recording, not a student stop.

The private artifact has origin `recorded-notebook-events`, prominently marked
as probable instrumentation activity. `prediction-input.json` stops at the first
matched tutor reply (sequence 12); `later-evidence.json` holds subsequent records.
They support inspection of a future prediction boundary, but no prediction has
been generated or scored. This demonstrates reconstruction mechanics, not a
gain in student realism or evidence of natural learner behavior.

`data/recorded-notebook-replay-v1/build_replay.py --check` verifies query/parameter
receipts, source and identity joins, projection reproduction, rejection of altered
captures/execution sources and duplicate events, plus exclusion of a changed
later reply from prefix content. The initial local probe command failed before DB
access because an older private `inspect.py` shadowed the stdlib module; Python
safe-path mode resolved it without modifying the original script. Database reads
were transaction-enforced read-only. The temporary tunnel is closed.

Private raw records, projection scripts and replay stay ignored by Git. No model
calls, student-code execution, training, labels, production changes or remote
publication occurred. The next research comparison should use genuine course
records with verified provenance; these likely test records only validate the
logging/replay path.

The self-contained `replay.html` places notebook/execution evidence beside one
conversation sidebar. Renderer checks cover escaping, cutoff labels, local
anchors, no scripts and create-only output. Exact regeneration matches the saved
page; it contains 34 unique element IDs and 44 valid local anchor links. Browser
security policy blocked automatic opening of its `file:` URL. No alternate
browser/server workaround was attempted, and visual inspection is unverified.
The user can open the saved private file directly. Independent source review
confirmed the selection, request/execution/capture joins, native-cell diff and
separation of the 12 prefix events from the 18 later events without new DB access.
