# Check eligibility before selecting ten students

The user approved the first proposed step: select up to ten distinct held-out
students, one recorded checkpoint each, with later answers separate from future
generation inputs. The local audit cannot establish any eligible students. The
recommendation assumed a holdout existed; that assumption needs correcting.

| Existing local evidence | Verified result |
| --- | --- |
| Eight canonical chat exports | 455 rows, 252 distinct conversations; no learner identifier |
| Existing historical baseline library | 1,179 examples from 156 conversations; all learner IDs missing |
| Existing query/reference set | 29 conversations; 19 have an earlier student turn before the current exchange |
| Separation | Training and query conversations are disjoint; learner separation is unknown |
| Exposure | The query set has already been used in development; it is not a fresh holdout |

`rawlog.Conversation` retains a conversation ID and chat-event index, not a
learner ID. `student_index` counts turns within a conversation. The sequence
queries use `events.user_email` for joins inside the database but do not export
a reusable learner mapping. An independent local audit found only authored
fixture identifiers elsewhere, not a real conversation-to-learner map.

This is a local export limitation, not evidence that the historical database lacks
eligible students. The [earlier snapshot-pair inventory](2026-09-15-notebook-snapshot-pairs.md)
counted 222 learner identities remotely under its pairing criteria. Only three
selected pairs were saved locally; they are development-exposed and contain no
reusable learner keys. Pair eligibility alone does not establish holdout eligibility.

The September 29 notebook refresh does not fill this gap: its saved aggregate
account counts are not a local learner mapping, and the richer action traces
look like instrumentation tests. See the [availability audit](2026-09-29-notebook-data-refresh.md).
The [earlier fidelity memo](2026-09-22-browser-student-fidelity.md#limits-and-next-decision)
already records the holdout limitation.

No cohort was selected and no conversation sample was substituted for students.
The private audit and empty selection are saved under
`data/heldout-student-eligibility-v1/`. They reproduce source hashes, counts,
conversation separation and query/reference linkage. Reference text was not
copied into new inputs; original files remain unchanged. No database queries,
generation, training, new labels or UI changes were performed.

The next useful step is a read-only linkage check against the existing historical
database: derive stable pseudonymous account IDs, establish which accounts are
students, and map prior training/development exposure across their conversations.
Recovering IDs cannot undo prior exposure. Only then can we count eligible
students and freeze one checkpoint each, selecting without examining later
answers. If none remain, keep the existing cases explicitly as development
evidence; do not rerun the closed history comparison as a new holdout study.
