# Full recorded-reply training pass complete

The [fixed full-pass run](2026-09-28-training-coverage.md) completed once within
its time and memory limits. The final adapter was saved, reloaded and scored
against the unchanged recorded development replies. It improves both the
equal-conversation and pooled-token prediction losses over the original base
and the previous small-subset adapter. Most development conversations improve
over the previous adapter; the private report retains every paired difference.

The predeclared development-prediction rule is met. This is a result on exposed
development cases, not a held-out generalization or simulator-adoption result.
Additional data coverage and updates changed together. No generated conversations
were added, so reduced repetition and more realistic interaction remain untested.

Independent checks verify the complete training update log, target-token total,
final checkpoint identity, unchanged reference tokens, source hashes and paired
score arithmetic. Authored scope and comparison guards pass. The earlier browser
run and all prior model artifacts remain unchanged; the new adapter is separate.

The private `data/local-student-full-pass-v1/REPORT.md` contains the measured
comparison, resource use and verification command. The completed target-membership
diagnosis is under `data/training-coverage-diagnosis-v1/`. Private data and model
artifacts remain ignored by Git. This run is closed with no retries, additional
training, generated conversations or human labeling queued.
