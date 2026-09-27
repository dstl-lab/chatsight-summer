# Context for repeated student messages

Before changing the saved student model, measure exact text repetition in the
existing recorded development library. This is an offline descriptive check,
motivated by the closed local conversation example; no new generation, tuning,
human labels or model-based judging is part of it.

Reuse the historical baseline's training rows and frozen source checks. Each row
already represents one tutor-response block followed by an observed student
message. Compare that target with the last student message in its prefix. Count
only this pair, never all overlapping pairs in the earlier context. Check source
turn joins and reject duplicate conversation/turn pairs even when row IDs differ.
Consecutive student messages without an intervening tutor and terminal tutor
blocks without an observed followup are outside this denominator.

The primary statistic is exact, case-sensitive Unicode text equality. Report
counts, the pooled proportion of eligible pairs, and the mean of within-conversation
proportions, giving each eligible conversation equal weight. Exclude pairs with
either message blank after stripping, reporting exclusions. Zero eligible pairs
produce an unavailable rate rather than zero. Report the fraction of eligible
conversations containing at least one repeat. As declared descriptive checks,
also report equality after stripping only outer whitespace and stratify by
previous-message length (at most 40 Unicode characters versus longer).
Do not normalize punctuation, case, internal whitespace or code indentation.

Apply the identical measure to all three student outputs in each saved local arm,
including its first recorded-to-generated boundary. Thus each arm contributes
three pairs, not just the two wholly generated transitions. Keep arms separate:
they share one recorded starting context and are not independent sampled students.
Preserve a private row/turn audit, aggregate report, source hashes and readable
summary. Verify saved local outputs read-only; do not extend the conversation.

Repeated text is not automatically a simulator error. A student may repeat a
request, paste the same code, or send the same short message after changing a
notebook that is not observable here. Duplicate logging is another possible
explanation. This measure does not identify semantic repetition, intent, task
progress or human plausibility. The library was used for development/training;
its rate is context, not an independent validation score for the trained model.

Stop after this comparison and verification. Do not impose a repetition penalty,
relabel examples or select another model checkpoint from these observations.
