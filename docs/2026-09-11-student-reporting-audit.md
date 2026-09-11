# What students choose to report after help

The continuity review identified a communication-choice problem: a possible
successful outcome need not produce a message announcing it. Before adding
another prompt instruction, inspect the existing development inventory for what
students actually report. This is an offline diagnostic under the standing
instruction to continue, using no new source conversations or external calls.

Reuse `data/episode-pilot/student-behavior-v1/inventory.json`: all 75 response
opportunities from the original 12 development conversations, including 64 next
student contributions and 11 opportunities without a recorded follow-up. Preserve
the inventory and its source pins. The review has already exposed these
conversations; this is not a held-out evaluation or an independent sample.

Inspect every recorded next student contribution for explicit resolution or
failure reports. A resolution report says that work ran/passed, an error was
fixed, or a concrete problem was resolved. A failure report says that an error,
failed test or unsuccessful operation occurred or persisted. Greetings, thanks,
agreement, speculative correctness, work that looks complete, and a tutor's
assessment do not by themselves establish either report. Printed expected
values within a failed-test artifact are not a passing report. Retain ambiguous
cases separately.

For reports, record whether the contribution also requests help or supplies
substantive work beyond the report itself. Multiple report types can coexist;
do not force them into mutually exclusive categories. Cite exact nonblank student
source lines, use earlier dialogue only to resolve references, and keep assistant
coding explicitly separate from human ground truth. Do not infer actual execution,
correctness, independent work, learning, or a probability of reporting success.

Check the extraction boundary for absent follow-ups and timestamp coverage. No
further recorded message may reflect a finished task, an unfinished task, an
unobserved continuation elsewhere, or export limits. The snapshot does not reveal
which. Delays among observed messages cannot identify the chance of no response.

Save source excerpts, per-window assistant judgments, evidence checks and local
counts under ignored `data/episode-pilot/student-reporting-v1/`. Cross-check all
positive and ambiguous judgments and a fixed sample of negatives. Report counts
per conversation alongside totals because these windows are clustered. No new
classifier, taxonomy admission, generator prompt, persona, model batch, or
automatic tutor policy is introduced by this audit.

## Findings

The assistant audit found **no clear success-only update among the 64 recorded
next student contributions** under the definition above. One contribution
included four passing subtests together with a failed subtest. That is evidence
of a mixed test-output paste, not an announcement that the task was completed.
Two other contributions explicitly reported a syntax error or missing output.
The missing-output complaint describes an unmet expectation; it does not establish
an execution failure, since ordinary notebook display behavior could explain it.

These three report-bearing contributions come from two conversations. The two
test/error artifacts have no additional request or substantive work outside the
artifact. The missing-output complaint also asks for help. Do not turn this small
descriptive result into a rule that students never report success or only report
failures.

Nine further contributions remain ambiguous about failure: three report
unspecified persistent incorrectness and six ask diagnostic questions without
identifying an observed error, test result, or unsuccessful operation. Eight of
these nine explicitly ask for help. A question about a problem may refer to the
assignment itself or incorrect work; tutor diagnoses cannot fill in missing
student evidence.

| Development conversation | Opportunities | Recorded follow-ups | Pass/resolution reports | Definite problem reports | Ambiguous problem reports |
|---|---:|---:|---:|---:|---:|
| 1 | 1 | 0 | 0 | 0 | 0 |
| 2 | 8 | 7 | 0 | 1 | 4 |
| 3 | 3 | 2 | 0 | 0 | 1 |
| 4 | 3 | 3 | 0 | 0 | 1 |
| 5 | 1 | 0 | 0 | 0 | 0 |
| 6 | 17 | 16 | 0 | 0 | 2 |
| 7 | 24 | 23 | 1 | 2 | 0 |
| 8 | 2 | 1 | 0 | 0 | 0 |
| 9 | 3 | 2 | 0 | 0 | 0 |
| 10 | 3 | 2 | 0 | 0 | 0 |
| 11 | 6 | 5 | 0 | 0 | 1 |
| 12 | 4 | 3 | 0 | 0 | 0 |
| Total | 75 | 64 | 1 | 3 | 9 |

Report columns overlap: the sole pass-report contribution is also one of the
three definite problem reports. All counts describe assistant coding of exposed
development conversations, not human ground truth. Conversations 6 and 7 supply
41 of the 75 opportunities and 39 of the 64 follow-ups; these are clustered
observations, not 75 independent students.

All 11 absent follow-ups are at the ends of exported conversations. Inspection of
the exporter at the snapshot's recorded revision (`8bc35d8`) found conversation
limits but no explicit per-conversation turn cap. That rules out that particular
mechanical explanation, but the data still provides no close reason, cross-session
learner linkage, or declared observation horizon for each opportunity. **11/75 is
not a calibrated probability of choosing not to reply.** Conversation termination
does not establish completion, abandonment, or success.

All 64 observed response-to-next-query event gaps have timestamps: median 132.4
seconds, range 12.6 seconds to 93.7 minutes. These are event gaps within observed
conversations, not measurements of notebook work, reading time, or a threshold
after which a student has left.

## Cross-check and provenance

The two primary annotation files cover all 75 opportunities without overlap.
The coordinating assistant reread all six originally positive or ambiguous
contributions with the primary judgments visible.
A separate assistant selected three negatives from each annotation group using
the fixed SHA-256 ordering in `negative-cross-check.json`, then reread the full
contributions and relevant context. Five supported the primary negatives; one
diagnostic question exposed the boundary described above. All three selected
negatives outside conversation 7 happened to come from conversation 6; the fixed
selection was retained.

The coordinating assistant then reread all 37 primary-negative follow-ups outside conversation 7 and
the full windows of six analogous diagnostic questions. `adjudication.json`
preserves their changes from negative to uncertain, with explicit help requests,
while leaving the original annotations intact. The initial three uncertain
judgments and these six changes yield the nine ambiguous cases above. This
conservative adjudication does not change definite-report or success-only counts.
These assistant cross-checks are not a blind human reliability study.

Ignored `data/episode-pilot/student-reporting-v1/` contains the preserved initial
audit definition, both primary annotations, exact line evidence, positive and
negative cross-checks, adjudication receipt, boundary audit, and `verify.py`.
`verification.json` records source hashes, primary and adjudicated counts, and
per-conversation totals. The check validates all 75 rows, 54 evidence references,
the fixed negative selection, source pins, source conversation endings, event
gaps and historical exporter hashes. It can be rerun from the repository root:

```sh
PYTHONPATH=. uv run python data/episode-pilot/student-reporting-v1/verify.py
```

The existing inventory reconstruction also reproduced its unchanged contents.
No real or generated dialogue is added to Git; no model or database request was
made. The generator and previously reviewed experiments remain frozen.

## Consequence for student simulation

Retain the distinction between **what could happen after help** and **what the
student would communicate**. A tutor's repair advice is insufficient reason to
generate a success announcement. Keep error pastes, terse requests and follow-up
work available rather than banning outcome reports. Use the student's visible
formatting, as established by the preceding continuity review.

The next generator comparison should test these communication and formatting
constraints together across the already exposed contexts, retaining the current
outputs as the baseline. Review content conditional on a reply separately from
whether a reply would occur; unknown occurrence remains acceptable. Do not train
or tune a no-reply rate from this audit. Estimating that rate requires an explicit
observation horizon and richer linked activity records. No additional human
labeling is needed merely to establish these limitations.
