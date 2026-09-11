# Compute one grader observation in an explicit reference environment

The action-choice diagnostic creates pending checks, but its prompts contain no
execution state. A targeted read-only inventory found a complete older course
assignment: source and student notebooks, the required dataset and matching public
tests for the selected question. The dataset copies agree, and the two public test
expressions match the earlier source trace. This does not identify the deployed
course version or recover the student's notebook state.

Use this as an explicitly authored reference fixture: older assignment data and
reference prerequisite cells, with the available local course runtime. Record
actual Python/library versions and hash the data, source cells, public tests,
runner and exact generated candidate code. Run only the reviewed prerequisite
cells and candidate; use the installed Otter test-file runner for the two public
checks. Keep all course source read-only and all outputs under ignored data. Do
not execute the complete notebook, copy course solutions into Git, open the raw
database or send another model request for this step.

Create a fresh CheckRequest bound to the explicit fixture state before execution.
The old pending requests describe a different authored state and must remain
untouched. Bind the computed observation to the fresh request, retaining its
executed basis and exact output. Verify that it reaches the existing continuation
gate with an invented callback and that old request/result pairings are rejected.
An invented callback is not a new simulated student or behavioral finding.

The intended demonstration is a bounded code → public check → observation route
in the named fixture; the attempt below stopped before completing that route.
A pass would not be complete correctness, a learning result, a deployed 2026
outcome or evidence about the student's unseen work. Keep the fixture provenance
attached to any future use; no longer rollout or classifier admission follows.

## Execution result

The reference prerequisites executed, but the exact generated candidate stopped
on its second line with an AttributeError: it calls `sort_index`, which this
Babypandas DataFrame does not provide. Independent method inspection confirms
that `sort_index` is absent while `sort_values` and `set_index` exist. No candidate
correction was installed and no second candidate execution was performed.

This is an observed **code-execution error**, not a failed grader test. The worker
never reached Otter test construction/run, and no GraderObservation was produced
or supplied to the continuation generator. Do not convert the exception to
`success=False` on a grader observation: that would claim a check ran. The error
and preserved request are recorded separately under private
`data/episode-pilot/grader-fixture-v1/`; both older pending requests stay untouched.

The prepared fixture is
`72ab0c322b9beace56ce78e99ac57e98cbe85303415d25e9a8f6c7c7340d4b44`.
Actual imports succeeded with CPython 3.14.0, Babypandas 1.0.0, NumPy/Pandas 2.3.3
and Otter 6.1.6. The selected older notebook records Python 3.9.5, so this is an
authored cross-version fixture, not a recovered student kernel. Data, notebook,
test, worker and input hashes verify before/after the attempt, and all 370 parent
pins remain unchanged. Runtime fingerprints cover the recorded versions and
listed module/executable hashes; they are not a complete container image.

This exposes another required event boundary for the simulator: running code can
stop before a grader result exists. A future runtime-error continuation needs
that exact exception as environment evidence and must remain distinct from
grader pass/fail. The current gate handles grader observations only; it has not
been extended silently or fed a fabricated grader result here. The prerequisite
state and course bundle used for the logged sessions still need identification
before claiming reconstruction of that environment.

The known spring-course directory candidates and the current winter checkout's
expected midterm-notebook location do not contain that bundle. Minchan was asked
to identify the assignment version or local bundle path used for the logged
course. Keep the older fixture explicitly separate while this remains unresolved.
