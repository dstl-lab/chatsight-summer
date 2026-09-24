# Simple question interactions

The visible record is one student's recorded work associated with one question,
including return visits. Existing episode storage remains an internal detail.

Each tutor request anchors four sections: before asking, student request, tutor
response, and afterward. Subsequent exchanges retain access to earlier context.
The full ordered event trace remains available, including activity while waiting
for a response. Passing checks and time gaps never remove earlier context.

Replies are linked by turn IDs when available. Ambiguous IDs stay unlinked;
legacy order fallback is only available when both turns lack IDs. Code transfer
claims require a matching response ID. Subsequent activity stops at the next
request for the exchange display; its ordering is not evidence of causation.

Question groups use ordered recorded action progressions over every exchange.
They are not intent categories. Request categories present in synthetic data are
explicitly labeled as scenario-supplied demo labels. No contextual intent model
has been trained or validated by this UI change.

Request origin and tutor mode show 'Not recorded' unless the event explicitly
provides them. Existing legacy follow-up events are not silently guessed into
this contract. Future instrumentation should link transcript, origin, mode,
and notebook snapshots to stable turn IDs, preserving the question context at
request time even if the active cell changes before the reply.

Code edits, inserts, and pastes each show a code-diff availability note: current
logs preserve hashes and edit counts, not arbitrary before/after source.
Gaps of at least one minute receive a visible elapsed-time marker, scoped to
events on this question; this is a display choice, not an analytical boundary.
There are no thinking, attention, reading, or reflection claims from time.

The simple version does not reconstruct missing notebook snapshots or infer
cross-question conversation intent. Those are explicit evidence limitations.
