# Trained student browser check complete

The [bounded check](2026-09-28-local-browser-check.md) completed through the
actual browser controls: initial student continuation, then a manually entered
tutor reply followed by another student continuation. Both local requests
finished at their message boundary without retries, failure or token caps.
Cloud generation was disabled; no Gemini request, notebook execution, training
or human labeling occurred.

The student repeated its question after the authored tutor reply. Exact saved
history confirms the new tutor text was delivered, and token verification
confirms the repeated text came from two actual generations. This is not a stale
display or replayed cached reply. One exchange does not establish how often
repetition occurs or whether it is plausible here; the reply-only model's
behavior remains unvalidated.

The browser now names the configured student backend for initial/typed replies
and both configured backends for generated tutor replies. It no longer assumes
all callbacks use Gemini. The existing JavaScript smoke check covers these
notices; controls and layout are unchanged.

The result reloads with sending disabled. The wrapper's two-request limit is
reached; one underlying session decision remains unused. The unanswered final
message therefore reflects the declared test stop, not student silence.
Independent saved-receipt review, exact input/output token checks and original
source hashes verify. Private scope, receipts, audits and results remain under
`data/trained-student-workspace-v1/`; its `UI-REPORT.md` records the literal result.
This check is closed with no replacement outputs or further calls queued.
