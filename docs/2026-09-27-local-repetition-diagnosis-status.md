# Saved repetition diagnosis complete

The [post-hoc diagnosis](2026-09-27-local-repetition-diagnosis.md) is closed.
It inspected every saved student transition and generated tutor reply, with no
new model calls, training, human labels or modifications to the closed cohort.
Mechanical results and context observations remain private in
`data/local-repetition-diagnosis-v1/REPORT.md`.

Updated branch histories, changed prompt tokens and distinct within-branch seeds
are verified. Exact repeated text exists in the generated token receipts, so the
inspected cases are not explained by stale context or duplicated display output.
Most repetition occurs in generated exchanges rather than at the recorded start.

Two interaction assumptions need attention before further student training.
The local adapter always supplies a reply, even after apparent acknowledgments
or completion. It has no learned message-timing or silence decision. Separately,
some generated tutor replies copy the entire pending student message and thereby
fail their intended role. Student and tutor behavior are coupled in later turns;
the counts cannot attribute all repetition to the student model.

The authored diagnostic check and independent receipt/code inspection passed.
All closed artifacts and source pins remain intact. Literal repeats and substring
matches are not automatic plausibility labels. The diagnosis does not establish
a causal effect, training-data memorization or the correct student stop behavior.

Next: isolate tutor-role behavior on fixed saved requests before evaluating a
longer student run. Native chat roles are a candidate representation; the current
JSON prompt already requests a tutor reply, so a format change must be tested,
not assumed to fix the issue. Keep student weights and the default simulator
unchanged, and avoid another instructor labeling packet.
