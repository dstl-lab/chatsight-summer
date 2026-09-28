# Fixed-input reply check for the full-pass adapter

The full training pass improved prediction of recorded replies. Check generated
text once using the existing trained-adapter requests from the closed conversation
cohort. Reuse every saved student request in that arm, in case/position order,
with its exact messages, seed, sampling settings and output budget. Change only
the student adapter. The earlier trained outputs are cached comparisons; no new
tutor calls or baseline draws are needed.

Keep two populations separate. The first reply in each case follows recorded
student/tutor history and has a recorded next-message reference. Later requests
contain the old adapter's simulated replies and tutor outputs. These later
requests probe response choices on fixed synthetic histories; the new responses
are never fed into subsequent requests. This is not a new conversation rollout
or a test of the new model's repetition rate in its own conversations.

Use the existing local worker and installed model/runtime. Freeze all request,
source, adapter, runtime and protocol hashes before execution. Allow at most 39
student calls, 256 output tokens each, 120 seconds per call and 20 minutes total,
with the existing 16 GiB memory checks and 4,096-token context limit. No retries,
replacement draws, seed changes, new labels, cloud calls or parameter tuning.
Retain failures, blanks and capped outputs; stop on a failed/incomplete call and
report the remaining slots as not attempted rather than silently dropping them.

For the recorded-history group, report coverage, raw Unicode character lengths,
paired absolute character-count errors against recorded text, and exact/outer-
whitespace repetition of the latest student message. Include median errors,
per-case differences and the largest case contribution so one outlier cannot be
mistaken for broad improvement. For later fixed histories, report repetition and
length separately, without attaching the original first-reply references. Retain
every literal output and whether it matches its cached counterpart.

Verify exact prompt tokens, model identity, output tokens, stop reasons and saved
request equality against the cached arm. Existing studies stay closed and
unchanged. Close this check after reporting all planned slots, including failures;
do not choose a winner from a composite score or automatically replace the
browser model. These exposed development cases and surface-text diagnostics do
not validate semantics, learner personalities, silence, notebook actions,
generalization, or real-student responses to tutor-policy changes.
