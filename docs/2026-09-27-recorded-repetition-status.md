# Recorded repetition check complete

The [declared offline check](2026-09-27-recorded-repetition.md) is complete.
`src.eval.student_repetition.summarize` now measures exact text reuse between
the last student message before a tutor reply and the first student message after
it. It reports pooled and equally weighted conversation rates, outer-whitespace
sensitivity, and short/long message strata. Empty populations remain unavailable;
blank endpoint pairs and duplicate row IDs are handled explicitly.

The private driver reuses frozen baseline rows and verifies source-window
uniqueness. An independent checker matches every prefix and target to canonical
recorded turns and proves coverage of the eligible pair set, avoiding overlapping
window and duplicate-export inflation. The same metric reads all three saved
student decisions per local model, including the initial recorded-to-generated
transition. It does not extend those closed sessions.

Six focused tests pass, covering conversation weighting, multiple consecutive
student/tutor messages, preserved case/internal whitespace, blank/empty inputs
and duplicate IDs. Both independent source verification and the saved artifact
hashes pass. Results and source-pair audit remain private in
`data/recorded-repetition-v1/`; its `REPORT.md` explains the comparison.
No model calls, new labels, training updates or simulator changes were made.

Exact repetition occurs in the recorded data, so this statistic is a diagnostic,
not an automatic error label or penalty. The saved model arms share one selected
conversation; they cannot establish a model-wide frequency or fidelity ranking.
Historical notebook changes and duplicate logging are not resolved by text
equality. Existing training/development exposure remains a limitation.

This check is closed. The next generation evaluation should be one fixed set of
short conversations, report repetition alongside response length and existing
prediction scores, and stop before changing the model. It should not add another
manual labeling packet or tune to the demonstration that motivated this check.
