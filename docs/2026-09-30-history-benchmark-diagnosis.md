# Saved history benchmark: diagnosis and one prospective target

The closed ten-case result remains **0.430 current-exchange versus 0.400
history**, a history-minus-current difference of **−0.030**: three cases improve,
two worsen and five tie. The visible-student form-frequency baseline scores
**0.155**. This supports a small, mixed change in literal communication form,
not adoption or improved student realism. The [original result](2026-09-29-course-account-history-results.md)
and [protocol](2026-09-29-course-account-history-protocol.md) remain closed.

This offline diagnosis inspected **all ten recorded targets and all 100 saved
replies**, every visible student message and each complete current exchange.
The frozen receipt verifier replayed all 100 raw outputs; reference hashes and
the unchanged report computation match the saved report. No generation,
database query, eligibility reassessment, new labels or simulator change occurred.

## Automatic literal evidence

Counts below reuse the original raw Unicode character count, length bins,
newline/backtick indicators and form categories. Distribution totals are
descriptive regroupings of those saved measurements, not a new benchmark score.
The recorded side contains one outcome per case; each generated arm contains
five draws per case. Percentages account for these different denominators.

| Literal property | Recorded, n=10 | Current-exchange, n=50 | History, n=50 |
| --- | ---: | ---: | ---: |
| 0–40 characters | 8 (80%) | 16 (32%) | 28 (56%) |
| 41–300 characters | 2 (20%) | 34 (68%) | 22 (44%) |
| Over 300 characters | 0 | 0 | 0 |
| Contains newline | 1 (10%) | 5 (10%) | 1 (2%) |
| Contains backtick | 0 | 3 (6%) | 0 |
| Mean characters | 41.50 | 71.56 | 45.24 |
| Character MAE against paired target | — | 43.02 | 38.86 |
| Reply / no reply / error | 10 / — / — | 50 / 0 / 0 | 50 / 0 / 0 |

The recorded category counts are 0:8, 4:1, 6:1; current-exchange counts are
0:16, 4:26, 5:3, 6:5; history counts are 0:28, 4:21, 6:1. Other categories
have zero observations. Category 0 is short/plain, 4 medium/plain, 5
medium/backtick and 6 medium/newline. These are literal forms, not semantic
classifications of questions, code or work.

Every case is retained below. Case numbers are the existing pseudonymous suffixes.
Short counts use five replies per arm; MAE uses those same five replies.

| Case | Target chars / category | Short current / history | Form score current / history | Character MAE current / history |
| --- | ---: | ---: | ---: | ---: |
| 01 | 59 / 4 | 2 / 2 | 0.10 / 0.10 | 15.8 / 16.0 |
| 02 | 15 / 0 | 5 / 5 | 0.00 / 0.00 | 7.8 / 5.8 |
| 03 | 10 / 0 | 2 / 5 | 0.30 / 0.00 | 72.0 / 4.6 |
| 04 | 11 / 0 | 2 / 5 | 0.20 / 0.00 | 41.0 / 5.0 |
| 05 | 23 / 0 | 0 / 2 | 1.00 / 0.30 | 61.6 / 28.0 |
| 06 | 198 / 6 | 0 / 4 | 0.00 / 0.60 | 23.2 / 138.8 |
| 07 | 14 / 0 | 0 / 0 | 0.70 / 1.00 | 69.4 / 50.2 |
| 08 | 21 / 0 | 0 / 0 | 1.00 / 1.00 | 73.0 / 73.0 |
| 09 | 29 / 0 | 5 / 5 | 0.00 / 0.00 | 19.0 / 19.0 |
| 10 | 35 / 0 | 0 / 0 | 1.00 / 1.00 | 47.4 / 48.2 |

History still assigns no sampled short replies to cases 07, 08 and 10. Visible
student messages are already short in 12/13, 2/2 and 0/2 messages respectively,
so history supplies useful short-form evidence for the first two but not the
third. Conversely, case 06 becomes much shorter than its recorded continuation:
mean generated length falls from 174.8 to 59.2 against a 198-character target.
The near-matching overall history mean conceals these opposing errors; a blanket
short-message rule is unsupported.

## Qualitative observations, not scored labels

Reading the complete saved set suggests a recurring tendency to complete the
tutor's teaching sequence instead of continuing the student's own request.
These observations are interpretation, not automatic categories, a validated
semantic score or judgments that every alternative continuation is implausible.

- **01–03:** replies often acknowledge a fix or claim success. The recorded
  continuations instead raise a conceptual question, ask about another problem,
  or report the unresolved error. Case 03's history score becomes zero even
  though its replies assert success where the observed message reports trouble.
- **04–05:** history more closely retains the pattern of brief requests. In 04
  it introduces subsequent exercise references rather than the observed continued
  difficulty. In 05 it includes another brief help request as well as answers
  and code responding to the tutor. Form improvement does not settle task intent.
- **06:** generated replies supply corrected work for the existing task; the
  observed continuation presents another task. Matching its multiline form in
  the current-exchange arm does not mean matching its communication purpose.
- **07–08:** replies answer the tutor's conceptual or coding prompt. The observed
  messages seek a definition or further guidance. Earlier terse student
  questions are visible, but adding full history does not recover their form.
- **09–10:** replies answer the tutor's probability prompt or supply code for the
  tutor-proposed exercise. The observed messages seek clarification or return to
  an earlier unresolved question. Case 09 shows that even perfect form scores
  cannot distinguish these alternatives.

Each recorded next message is **one observed outcome**, not the only plausible
continuation. Generated claims of passing checks are not observed executions;
the saved chat prefixes cannot verify intervening notebook work. This cohort is
conditional on returning to chat and cannot estimate silence, abandonment or
hidden work. Account eligibility remains unverified, and ten cases with five
draws per arm do not establish population frequencies or significance.

## One prospective intervention target

**Target: make earlier student communication more influential relative to the
tutor's teaching sequence.** The concrete candidate is a **student-only earlier
context condition with the identical complete current exchange**, compared with
current-exchange-only input. Preserve chronological order, verbatim student
content, role boundaries, current message blocks, instruction and schema. This
would change which earlier turns are supplied; it would not add a length cap,
force help requests, copy target text or infer a persona.

There is a measurable short-form gap and a plausible presentation issue:
earlier context contains 67,796 tutor characters versus 2,854 student characters
across the ten prefixes. Those raw input totals are a post-hoc description,
not evidence that tutor volume caused the observed gap. Removing earlier tutor
turns can lose necessary task context, so the candidate could also worsen results.
Case 10 has no earlier student turns: its candidate and current-exchange inputs
would be identical, and it must remain in the set rather than being dropped.

This proposal does not repeat the completed [student-message duplication
candidate](2026-09-15-student-communication-result.md), which retained full
dialogue and yielded only a −1.25-character paired MAE difference without adoption.
It also differs from the existing [evidence-card guidance](2026-09-30-student-evidence-card.md).
Repository documentation and experiment/source searches found no completed
student-only earlier-context replacement comparison. The current prompt already
says that tutor questions need not be answered; repeating that instruction is
not the proposed change.

The one prospective comparison is **planned, not run**. It is a hypothesis, not
an established fix or a queued run. The existing form score could measure its effect on literal form only;
it cannot validate the broader communication-purpose hypothesis. These ten
targets are now exposed development evidence, not fresh validation. A formal
confirmatory test would require fresh, independently reserved cases; none are
selected here. No prompts, calls, labels, cohort extraction or adoption follow
from this diagnosis, and the
closed benchmark and current generator remain unchanged.
