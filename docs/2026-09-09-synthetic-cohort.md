# Synthetic class cohort for episode-viewer validation

Date: 2026-09-09. Status: implementation decision.

## Purpose

Generate a reproducible 100-student Lab 1 event stream to test whether the
episode pipeline and instructor viewer remain understandable at class scale.
This is interface and analytics validation, not a substitute for real student
evidence.

## Grounding boundary

The cohort uses three documented historical aggregate shares among tutor
conversations:

- ask-first: 27%;
- fail-then-ask: 17%;
- pass-then-ask: 56%.

Source: `docs/2026-08-09-sequence-pilot-first-numbers.md`, n=7,782
conversations. These values came from a notebook-level join with 45-minute
pre-chat and 20-minute post-chat windows. In particular, historical
pass-then-ask may mean a student passed one question while asking about
another. The synthetic manifest repeats this limitation; the generated
question-scoped paths must not be presented as an estimate of real
question-level prevalence.

No real message text, student identity, or student-level trajectory is used.

## Explicit scenario assumptions

Direct requests default to 25% of tutor-using student-question paths.
Sensitivity targets of 10% and 40% are recorded because no sufficiently robust
historical aggregate supports one exact value. Skip, resolution, error,
transfer, and tutor-use probabilities are also simulation parameters rather
than DSC 10 estimates.

## Avoiding cloned personas

Each fictional student receives continuous traits for pace, persistence, error
propensity, tutor propensity, directness, code-transfer propensity, and
self-correction. Question difficulty interacts with those traits. The result
is longitudinal variation: one student may solve independently, ask first,
debug after failure, transfer tutor code, skip, or remain unresolved on
different questions.

These traits generate behavior; they are not inferred psychological profiles
and are not shown as claims in the instructor viewer.

## Outputs

Each run writes to `data/synthetic/lab1-100/<run_id>/`:

- `events.jsonl`: valid episode events plus explicitly marked synthetic legacy
  transcript rows;
- `manifest.json`: generator version, seed, aggregate anchors, scenario
  assumptions, question definitions, and observed distributions;
- `cohort_summary.json`: fictional student traits and generated path facts;
- `validation_report.md`: readable target-versus-observed checks and claim
  boundary.

The run ID is deterministic over generator version, configuration, and public
question specifications.

## Viewer implications

The viewer compares questions by median recorded attempts, with median active
time and tutor turns shown separately. It does not rank questions by isolated
error occurrence or unresolved work, and it has no hidden composite score.

At class and question scope, the primary view crosses the context before the
first tutor query with notebook action after the first tutor response. This
makes exact transfer, revision, testing, and prior work interpretable only in
combination. Choosing a populated cell shows three deterministic student
examples. Transcript turns and human-readable source events remain behind an
optional evidence control. See `docs/2026-09-10-class-pathway-view.md` for
definitions and claim boundaries.

## Claim discipline

Allowed: “the synthetic scenario contains 25% direct-request paths” and “the
viewer remains navigable over this generated class.”

Not allowed: “25% of DSC 10 students directly request answers,” “these are
realistic student archetypes,” or any claim about learning or tutor effects.
