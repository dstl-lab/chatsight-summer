# Cached communication result: work appears in different situations

**TL;DR:** This one-pass diagnostic is complete. Common-rubric coding now covers
both recorded work-absent and work-present messages: five and three cases,
respectively. Generated replies include work in 6/10 draws for work-absent
references, but omit it in 2/6 draws for work-present references. The measurable
gap concerns when work is communicated, not a blanket requirement for shorter
messages. No generator change or additional review follows this report.

## Completed intake

The returned form supplies all **23 unique messages / 46 flags**, with no missing
or unclear judgments and no notes. The exact packet, rubric, IDs and order match
the prepared review. One duplicated generated message shares a judgment while
retaining both draw occurrences: eight references and sixteen generated replies
remain in the analysis. All eight cases are comparable for each flag.

The return arrived as chat text containing HTML space entities and escaped
underscores in JSON field names. Its literal transcription is preserved, alongside
a normalized JSON copy and an explicit normalization receipt. Only the transport
formatting and the leading “Done” were removed; no IDs, labels, notes, order or
reviewer metadata changed. Original browser-export bytes were not provided.
The submitted prior-exposure answer is preserved as **no**, a self-report. These
cases nevertheless have documented prior development exposure; this does not
establish an untouched holdout or successful blinding.

## Observed communication

| Measure | Recorded messages (8) | Generated occurrences (16) |
| --- | ---: | ---: |
| Requests help or a check | 8 (100%) | 13 (81.25%) |
| Presents work/evidence | 3 (37.5%) | 10 (62.5%) |
| Help only | 5 | 3 |
| Help and work | 3 | 10 |
| Work only | 0 | 0 |
| Neither | 0 | 3 |

The generated work frequency is 25 percentage points higher overall. Separating
the reference groups shows why simply suppressing work would be insufficient:

| Recorded reference group | Cases | Generated work present | Generated work absent |
| --- | ---: | ---: | ---: |
| Work absent (all help-only here) | 5 | 6/10 | 4/10 |
| Work present (all also request help) | 3 | 4/6 | 2/6 |

These are discrepancies from the observed messages, not verdicts that every
different continuation is implausible or a student error. Work may be copied
code, an answer or diagnostic evidence; its presence does not verify notebook
execution, learning or correctness.

## Frozen descriptive measures

The [declared rules](2026-09-22-cached-communication-review.md) use the fraction
of two draws with a flag as `p`, and the recorded binary flag as `y`. Squared
error is `(p-y)^2`, averaged equally by case. Lower means closer flag agreement
on these cases; it is not an accuracy percentage or calibrated probability.

| Measure | Result |
| --- | ---: |
| Help incidence gap, generated minus recorded | −0.1875 |
| Help Brier error, 8 cases | 0.15625 |
| Work incidence gap, generated minus recorded | +0.25 |
| Work Brier error, 8 cases | 0.4375 |
| Work Brier error, 5 work-absent cases | 0.5 |
| Work Brier error, 3 work-present cases | 0.333333… |
| Balanced work Brier, equally weighting the two groups | 0.416667 (5/12) |
| Declared always-no-work flag rule, balanced work Brier | 0.5 |

Both groups now have comparable coding, so balanced work error is available for
this slice. The small difference from the constant rule is only a descriptive
diagnostic, not evidence that the simulator is realistic or an improvement has
been demonstrated. No success threshold, significance test or adoption criterion
was declared. One reviewer, eight exposed conversation cases, two draws per case
and incomplete historical context sharply limit interpretation; coding reliability
and individual learner identity are unestablished.

## Decision and stopping point

The missing **measurement coverage** has been filled for this development slice:
we can observe discrepancies both when work is absent and when it is present.
The remaining **improvement evidence** has not been supplied: this set contains
one historical chat generator condition, with no matched current-exchange-only
or changed-generator comparison. It does not evaluate the newer notebook agent.

Close this pass now and retain the generator. Do not pool these results into the
earlier benchmark, reopen past studies, demand another reviewer, relabel cases,
reroll outputs or automatically launch a prompt experiment. Any future improvement
comparison needs matched conditions and its own advance decision rule. This
report provides a concrete failure description and reusable development evidence,
not a validated student persona or an established grounding benefit.

## Reproduction

Private evidence remains under `data/episode-pilot/cached-communication-review-v1/`:
`received/message.txt`, `received/review.json`, `intake-receipt.json`, frozen
`report.py`, and `result.json`. All 50 preparation pins were verified before intake.
The frozen scorer supplies the per-case exclusions, counts and source hashes;
exact replay must match the saved result. The original page, mapping, source
messages, report rules and historical labels remain unchanged. No new model calls
or notebook executions occurred.

Independent transcription and arithmetic audits passed: all 23 submitted rows
match the user message, the 50 preparation pins and result provenance verify,
and every case/count/score matches separate arithmetic. `closure.json` records
the exact successful report replay and the decision to queue no further labels.
