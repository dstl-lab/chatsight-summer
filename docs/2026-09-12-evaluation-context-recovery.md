# Recover context for the fixed comparison candidates

Continue from the four candidates frozen by the evaluation-readiness inventory.
Reuse the existing bounded read-only ingestion probe and three saved query
definitions to retrieve conversation event metadata, initial notebook records
and same-subject event windows. Keep the selection fixed; missing context or
ambiguous attribution is a result, not a reason to substitute a different case.

Use a new ignored `data/episode-pilot/evaluation-context-v1/` directory. Bind the
selected conversation identifiers and exact source episodes to the saved
inventory and snapshot hashes. The existing probe enforces read-only transactions,
connection/statement timeouts and create-only outputs; the query row caps must
remain unreached before claiming a complete inspected window. Student account
identifiers stay inside the database join and are not exported.

Reuse `recover_initial` and `context_for` to align initial query, notebook capture
and embedded tutor response. Retain missing, multiple and incompatible cases
explicitly. A dated initial capture does not establish current work at the later
selected response. Preserve all missing work as unknown and distinguish it from
empty source or unchanged work.

Keep recovered initial context and visible-prefix projections separate from
reference next messages and intervening check records. Same-notebook checks in a
subject/time window are associated observations, not proof of the submitted code
or a unique task link. Future text and post-capture query metadata must not affect
the recovered generator context. Save direct source/output hashes and verify
exact offline reproduction without rerunning queries.

After recovery, choose only a comparison supported by the available evidence.
Use actual initial work for an initial-encounter action; later work actions need
later current work. If that remains unavailable, restrict a later comparison to
communication conditional on a logged contribution and expose that limit. Do not
equate one simulated silent edit with a later chat message or infer reply rates.
No generator changes, student-code execution or model requests are part of this
recovery. Completed artifacts and production helpers remain unchanged.

## Recovered evidence

The three read-only queries returned 72 conversation-linked metadata rows,
20 notebook-info records and 181 subject-window rows, all below their caps.
The tunnel dropped during retrieval. Successful receipts were preserved, failed
connections recorded separately, and only interrupted queries repeated with the
same SQL and parameters after reconnecting. No model requests occurred.

All four fixed cases have one initial notebook capture. Cases 1, 3 and 4 recover
through the existing alignment helper. Case 2 has two preceding unlinked queries
with the same text fingerprint, both satisfying that helper's conditions; neither
is selected merely because it is closer in time. This case remains explicitly
unavailable for a context-dependent comparison. All four selected source
request/response/followup sequences align to the saved event metadata.

Reference-only same-notebook check counts are 2, 1, 1 and 1 between the selected
response and next query. They do not identify executed source or synthetic
outcomes. Current notebook work remains unknown in all four cases; only code
actually pasted into a visible message is direct evidence of that submitted
excerpt. The initial captures remain historical context.

The new supplement reopens identically offline. Nineteen direct source hashes
and three output hashes verify, including the failed/recovered query records.
The invented check covers ambiguous attribution and future isolation; replacing
future messages or later query metadata cannot alter recovered input context.
An independent check confirms the hashes and case 2's two competing queries.

Proceed with the three recovered cases as a communication comparison using the
frozen continuation prompt/schema and clearly dated historical excerpts. Preserve
case 2's exclusion and the original four-case selection. The protocol is in
`2026-09-12-context-grounded-communication.md`; no course runtime extension or
assumed intermediate work is required.
