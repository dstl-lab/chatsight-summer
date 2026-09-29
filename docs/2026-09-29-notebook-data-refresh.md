# Refresh notebook observability before another realism experiment

Minchan requested a read-only Kubernetes database check for new notebook state
and recommendations for making simulated students more realistic. Inspect the
existing raw-log database through its configured localhost tunnel. Reuse the
saved ingestion probe, require a read-only transaction and retain its 20-second
statement timeout. Close the temporary tunnel afterward. No database or cluster
resources are modified.

Inventory schema, event dates/types and notebook-field coverage first. Compare
records since 2026-08-07 UTC with the historical notebook-pair audit's exclusive
upper boundary; preserve a fixed upper timestamp for this refresh. Check whether
current source, revisions/diffs, stable cell IDs, execution evidence and chat
request attribution are present. Presence alone does not prove a usable sequence.
Use aggregate queries before content inspection; retain learner identities only
within database joins and never print credentials or raw student records.

If newer captures exist, inspect only bounded metadata/structure needed to test
their usefulness; do not bulk-export notebooks or execute student code. A failed
connection/query may be retried unchanged, with the failure recorded. Keep old
exports, experiments and their splits unchanged. Private SQL, parameters and
receipts stay under ignored `data/notebook-data-refresh-v1/`.

End with a dated availability result and a concrete next modeling recommendation.
No generation, training, new annotation, simulator change, remote publication or
automatic follow-up experiment is part of this check.

## Result

The read-only check succeeded on September 29. Fixed new-record window:
`[2026-08-07T00:00:00Z, 2026-09-29T03:45:27Z)`. Counts refer to this
window, not an untouched research cohort. Account counts are distinct internal
database account identifiers, not independently verified student identities.

| Available records | Count | Interpretation |
| --- | ---: | --- |
| Tutor queries / responses | 350 / 333 | Includes instrumented and legacy activity; unequal counts do not establish missing replies without joins. |
| Notebook-info records | 332 | 161 contain an initial notebook capture; 155 distinct linked conversations, 84 accounts. |
| Autograder events | 3,802 | Legacy notebook-level grading; not automatically linked to a particular captured revision. |
| Tutor queries carrying request-time notebook JSON and SHA-256 | 29 | One account, September 24–27; 25 matching responses and four matching failures. |
| Cell source-change events | 20 | Revision/count/length metadata; these records do not carry the changed source or an edit diff. |
| Execution requests / finishes | 21 / 21 | All pair by account, analytics session and execution ID with equal cell, kernel, notebook-session and submitted source. |

The richer tutor-query captures all parse, all 29 stored notebook checksums
match the captured UTF-8 bytes, and all nested request IDs match their envelopes.
Only 19/29 notebooks have nonempty, unique IDs on every cell. Across these
captures, 36/2,002 cell occurrences have IDs; capture-level coverage therefore
must not be mistaken for good coverage of larger notebooks. Seventeen captures
have outputs/execution counts. Presence of output does not establish its freshness
or correctness. Ten top-level questions differ from nested `student_question`;
preserve both rather than silently treating them as interchangeable.

All execution pairs report complete output, with 14 `ok` and seven `error`
statuses. Execution success is not assignment correctness. All 21 pairs have
increasing client sequence numbers, but four have reversed server arrival times.
Reconstruct within verified sessions using client sequence and shared identities,
not server timestamps alone. No duplicate identifiers were found for the checked
query/response/failure/execution event groupings. Every execution's notebook and
analytics session also contains a tutor query; that is overlap, not yet a verified
complete pedagogical trajectory.

Detailed action records occur only during September 27, 06:07–06:16 UTC, under
one account and seven notebook sessions. All source-change and execution records
have notebook names matching test/smoke/fixture/diagnostic indicators. Seventeen
of the 29 richer queries also match these indicators. Separate explicit diagnostic
events exist. This strongly suggests instrumentation testing; account roles and
natural course use have not been independently established. Do not call these
records a new student cohort or use them to learn student behavior.

Nested active-task contexts are populated in the newer instrumented events, while
top-level query task ID/version remain null. Presence is not proof that these are
correct course/question identities; ingestion must retain the field source and
validate attribution. The older chat importer does not automatically import any
of this new observation data.

## What this changes for realism

Treat realism as observable fidelity in separate dimensions: communication style,
choice of action/channel, work and mistakes, and response to tutor guidance.
Plausible wording or improved recorded-reply likelihood alone does not validate
the whole student simulation. Multiple continuations can be plausible; the target
is their distribution and dependence on context, not exact reproduction of one
future message.

The concrete modeling priority is to supply observed work and prior behavior at
the prediction boundary. A terse “help” after a code change is a different state
from the same message without progress. Reuse the current notebook engine's edit,
run, ask and stop actions; do not require every action to produce chat. Bind claims
about errors or passing to available execution/grader evidence. Preserve observed
partial work and errors instead of treating fully correct solutions as inherently
better simulations. Do not invent a competence level or stable personality where
the history does not establish one.

Keep dialogue history: the closed local diagnostic found lower recorded-reply
loss with history for 15/18 affected conversations in the trained model. Training
gains nevertheless persisted without history, and generated behavior remains
mixed. This supports retaining context, not claiming that training learned
individual personalities. See `2026-09-28-student-history-value-status.md`.

Next recommended deliverable: one offline, source-linked replay of the richer
records, explicitly marked as probable test activity. It should show the notebook
at a tutor request, the matching response/failure, submitted execution source and
result, and any subsequent captured work. Missing intermediate source remains
unknown. Reuse `observation_contract.py` concepts; do not load real records as
synthetic container-run receipts. Stop when one episode either reconstructs with
verified boundaries or has precisely documented gaps. No model or manual-label
loop is needed for that milestone.

Then assess genuine historical snapshot/chat boundaries separately. Use earlier
work as input and later work only as an outcome; compare a fixed baseline with
one state-grounded candidate on a frozen, appropriately separated sample when
the available data supports it. Measure style, action choices and work behavior
separately. Test records can validate mechanics but cannot provide a student
behavior benchmark. The 161 newer initial captures and existing historical
snapshot pairs remain potential bounded-context data, not recovered full action
trajectories. Audit natural-use provenance and cohort overlap before new training.

Recent primary research supports separating these targets: Scarlatos et al.,
[Simulated Students in Tutoring Dialogues: Substance or Illusion?](https://aclanthology.org/2026.acl-long.1960/),
report limitations in linguistic, behavioral and cognitive fidelity even after
training; [StudentSim](https://arxiv.org/abs/2609.01591) separates behavior fidelity
from responsiveness to guidance. Neither establishes performance for DSC 10 or
validates our current simulator.

## Verification and limits

Five successful query receipts preserve the SQL, fixed parameters and probe
hashes and assert read-only transactions. Existing 20-second statement timeouts
were retained. Two attempts failed because the temporary port-forward exited on
connection close; unchanged retries succeeded. One local inspection assumption
(question-field equality) failed and was replaced by a reported mismatch count,
not suppressed or repaired in the source data. Saved receipt/checksum/structure
checks now pass. Raw queries, bounded captures and inspection scripts stay in
ignored `data/notebook-data-refresh-v1/`; no account identifiers, notebook source,
credentials or student messages are included here. The temporary tunnel is closed.
No database writes, student-code execution, model calls, training, labels or remote
publication were performed. This is an availability audit, not a fidelity result.
