# Saved local student conversation

The [bounded paired conversation](2026-09-27-local-student-conversation.md)
is complete. The starting local model and saved student adapter each generated
three student messages, with two fresh replies from the unchanged base tutor.
Both arms reached the declared decision budget; none of the ten calls required
a retry or ended at a token limit. This is a functioning learned continuation
through the existing chat engine, not adoption of a validated student simulator.

The read-only workspace opens the two independent branches directly. Conversation
01 is the starting model; Conversation 02 is the trained adapter. Both begin at
the same recorded prefix. The final unanswered message is a budget pause, not
evidence that the student chose silence. The model was trained only on observed
replies and has not learned the decision of whether to send a message.

Private selection, actual model prompts/token IDs, output tokens, exact text,
sampling settings, model identities and saved-engine receipts remain under
`data/local-student-conversation-v1/`. Its `REPORT.md` describes the observed
behavior and limits without adding instructor judgments or a fidelity ranking.
No historical future tutor replies or reference student targets enter generation.

The runner preserves exact transcript text rather than reconstructing it from
the legacy line-based prompt. Review found and corrected two integration issues
before freezing: random seeds must be reset after adapter loading, and delivery
must decode raw content tokens because the streaming decoder can strip leading
space. No engine, model weights, previous results or default simulator changed.

The authored offline check covers independent histories, blank lines, Unicode,
fixed call budgets, failure stops and no resending. Eight existing focused tests
pass. Saved replay and all 76 source pins verify; both branches were opened in
the existing browser with sending disabled. The private independent audit checks
actual template tokens and output decoding in addition to engine receipts.

This run is closed. A single exposed development conversation cannot establish
general fidelity or a tutor-policy effect. Use its literal observations to define
the next measurement against recorded messages; do not tune on this one example,
extend these branches, or reopen human labeling by default.
