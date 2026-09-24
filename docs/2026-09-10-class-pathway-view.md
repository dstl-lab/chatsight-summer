# Class-level tutor pathway view

Date: 2026-09-10. Status: superseded in the main interface.

The pathway API remains available for audit. The main grid described here has
been replaced by the
[professor-facing lab briefing](2026-09-10-professor-briefing.md).

## Problem

The previous viewer ranked questions with isolated counts such as students
with an error, repeated attempts, tutor use, or no recorded pass. Those facts
are observable, but none is meaningful alone. Errors are normal in
programming, retries may be productive, and a passing autograder result does
not establish learning.

The revised viewer answers two instructor questions:

1. Where did recorded work take more steps across the assignment?
2. For tutor-using student-question journeys, what was recorded before the
   first tutor question and after the first tutor response?

## Analytic unit

The class-level unit is one pseudonymized student, notebook, and question
journey. It combines all reconstructed sessions for that key. Successful
autograder checks and 30-minute inactivity still split source episodes, but
they do not cause the same student-question journey to be counted twice.

Unknown-question events remain excluded from question-level aggregation.

## Crossed pathway model

The first axis records context before the first tutor query:

- **Used tutor before editing or running code:** no notebook edit, non-autograder run,
  failed check, error, or pass was recorded.
- **Used tutor after editing or running code:** an edit or non-autograder run was recorded, without a
  recorded error, failed check, or pass.
- **Used tutor after an error or failed autograder check:** an execution error or failed autograder check
  was recorded.
- **Used tutor after passing the autograder:** a passing autograder check was recorded for the
  same student and question.

The second axis records notebook action after the first tutor response:

- **No code change recorded after the tutor replied:** no exact transfer and no later edit.
- **Code edited; no exact tutor code used:** a later edit, without an exact tutor-code
  insert or paste.
- **Exact tutor code used; no later edit:** exact tutor code inserted or pasted, without a later
  edit.
- **Exact tutor code used, then code edited:** exact tutor code inserted or pasted and a later
  edit was recorded. The edit is not assumed to modify the transferred code.

Each tutor-using journey with a recorded response lands in exactly one cell.
Cell percentages use those grid-eligible journeys as their denominator.
Tutor queries without a recorded response are reported separately rather than
silently assigned.

Exact transfer requires recorded exact-hash provenance. Similar-looking code
is not inferred as tutor-derived.

## Process-cost comparison

Questions are ordered by:

1. median non-autograder code attempts per represented journey;
2. median active recorded time, as a deterministic tie-breaker;
3. question ID.

The viewer separately displays median active time and median tutor turns among
tutor users. It does not combine these measures into a hidden score. Active
time is the sum of reconstructed episode durations, so inactivity gaps that
caused a split are excluded.

These are process descriptions, not difficulty, risk, or learning estimates.

## Interaction design

The page opens at class scope:

1. a question comparison shows where work took more recorded steps and the
   most common tutor pathway for each question;
2. a 4×4 pathway grid shows the distribution of combined before/after
   behavior across the class;
3. choosing a question filters the same grid to that question;
4. choosing a cell shows later-test and later-pass context plus three
   deterministic examples;
5. transcript text and ordered source events remain opt-in evidence.

The API exposes:

- `GET /api/insights` for class and per-question aggregates;
- `GET /api/pathway-examples` for deterministic evidence examples from one
  selected cell;
- the existing episode detail endpoint for event-level provenance.

## Claim boundary

Allowed:

- “No recorded attempt preceded the first tutor query.”
- “Exact tutor code was pasted and a later notebook edit was recorded.”
- “This pathway was more common on one question than another in this bundle.”
- “Question 4.3 had a higher median number of recorded attempts.”

Not allowed:

- “The student was dependent on AI.”
- “The student understood the tutor response.”
- “The tutor caused the later pass.”
- “This pathway is productive, unproductive, or evidence of cheating.”
- “The student learned.”

The crossed model is informed by research on help-seeking, response use, and
programming-process trajectories, but its categories are intentionally
bounded to facts this telemetry can support.
