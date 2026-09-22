# Fixed tutor-policy cohort milestone

The one-case policy lab demonstrates a saved A/B mechanism but cannot show whether
an outcome repeats across conversation starts. Add a bounded cohort layer that
composes existing immutable policy pairs. The researcher chooses one to 24
eligible saved scenarios, fixes the current and proposed policies once, and freezes
one independent comparison per scenario without making provider requests.

The cohort manifest pins every source identity, child comparison plan and exact
policy string. Running the frozen cohort makes at most one tutor and one student
request per condition. Completed, failed, interrupted and no-follow-up outcomes are
preserved and never rerolled. Reopening and summarizing are offline and do not
change saved files.

The first overview reports only lifecycle facts: ready, student replied, no
follow-up, incomplete and failed. One click runs independent cases concurrently
with at most four workers; it does not combine student conversations in one model
request. It also categorizes completed A/B pairs as both replied, both no-follow-up,
proposed gained a follow-up or proposed lost a follow-up. Unfinished and failed pairs
are explicitly not comparable. It does not use an LLM-written summary, behavioral
labels, a policy winner or a learning claim. Every summary row opens the individual
saved A/B conversation with recorded context, the shared starting question,
generated tutor reply and simulated follow-up.

This development version intentionally consumes the same eligible source contract
as the one-case lab: a recorded conversation prefix followed by one cached
simulated student question. It is not yet the research cohort described by the
Phase 4 plan, which must branch directly from fixed recorded student requests and
requires separately approved sampling and classifier provenance.
