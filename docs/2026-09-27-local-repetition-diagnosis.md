# Diagnose saved student repetition

Inspect the closed local conversation cohort before changing the model. This is
a post-hoc diagnostic of existing outputs, not another fidelity benchmark. Keep
all cases and both arms, with no new generation, training or human review packet.
Preserve the closed source files and their hashes.

Use the existing exact-repetition measure to check all student transitions, then
separate the initial recorded-to-generated boundary from generated positions two
and three. For each repeated message, record whether the text already appeared
among the original student's messages or first entered through generation.
Check the immediately preceding tutor text for equality to the tutor text before
the previous student message. This detects a repeated message pair, not its cause.
Retain exact source paths so every diagnostic can be inspected in context.

Check that each later student request actually extends its own previous prefix
with the delivered student and fresh tutor messages, that input tokens change,
and that within-arm seeds differ. Reuse the completed token/history audit rather
than rerunning the model. Inspect all repeated sequences for concrete examples
and alternative explanations; researcher interpretations are not validated labels
or an automated semantic score.

The final note should distinguish verified execution facts, literal text patterns,
and hypotheses that require a controlled test. Audit the response-only training
and generation contract explicitly: it supplies observed reply targets and always
requests another reply. Do not turn missing follow-ups into silence labels or add
a repetition penalty merely because the diagnostic counts repeats. Close with
one justified next step, keeping the default simulator and saved weights unchanged.

Inspection extension: a generated tutor sometimes repeats the pending student
message. Check exact equality across every saved tutor call, not just calls next
to repeated student outputs. Report full-message equality separately from mere
substring inclusion, which can be legitimate quotation or a short question ID.
This extension follows inspection and must not be presented as preregistered.
