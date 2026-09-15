# Two things to explore

## 1. What can we actually reconstruct about a student's work?

Take a look at the existing tutor logs and, if available, the code that records
them. How much of a student's activity can we piece together: changing code,
asking for help, running a check, and moving to another question? Try following
one example and separating what we can directly observe from what we're guessing.

The interesting question is where the gaps come from: data we haven't connected
yet, or events that were never saved. Bring back a short walkthrough and your
thoughts on what would make these records useful for evaluating simulated students.

Starting point: [observation-window findings](2026-09-15-observation-window-readiness.md).

## 2. What could a useful simulation workspace look like in Marimo?

Explore how Marimo could help an educator or researcher follow a simulated
student's work. What would you want to see or control: code changes, tutor
interactions, checks, pauses, or alternative teaching decisions? Pick whichever
part seems most useful and try a sketch or a small toy example.

We're interested in whether readable Python diffs and Marimo's execution model
make the student's activity easier to understand. Think about how to distinguish
an edit, an explicitly requested run, and something the interface reruns
automatically. Bring back what felt promising, awkward, or worth trying next.

Starting point: [Marimo documentation](https://docs.marimo.io/) and our
[saved-student workflow](2026-09-14-continuing-student.md).
