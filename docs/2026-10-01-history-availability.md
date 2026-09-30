# Availability of earlier account histories

**TL;DR:** Richer earlier conversation histories exist: 80 of the 108 remaining
accounts have at least two earlier query-bearing conversations and ten nonempty
query events before an eligible later conversation. This supports preparing a
history-conditioned comparison. Notebook/task separation remains unverified;
the cluster's authentication service returned HTTP 503. No model batch ran.

## Frozen scope

Written before the inventory on 2026-10-01. Reuse the saved read-only linkage,
candidate-account and exposure records. Exclude the entire accounts of the ten
now-exposed history cases, in addition to the original account-wide exposure,
diagnostic and identity exclusions. Use course accounts, not verified students.

For each remaining checkpoint-eligible conversation, count all same-account
conversations wholly inside the historical interval whose last chat event is
strictly before this conversation's first chat event. Include earlier one- and
two-query conversations; the checkpoint-eligible subset alone is not the history
pool. Exclude overlapping or later conversations from history. Require valid
timestamps. Query counts retain the original SQL's nonempty-string definition,
which is not a semantic count of help requests or distinct actions.

Report account-level availability at one, two and five earlier conversations,
and at five, ten and twenty earlier queries. These are descriptive thresholds,
not validated minima for identifying a persona. Also report the joint threshold
of two earlier conversations and ten earlier queries as a practical candidate
for a bounded comparison. Account maxima describe availability, not a selected
cohort or a representative distribution of all course use.

If the local inventory supports multiple such accounts, retrieve only missing
notebook-identity metadata for their historical conversations using the existing
read-only probe, the same fixed export cutoff and private account salt. Return
hashed identities, counts and timestamps; do not export question/response text,
notebook cells, outputs or future message characteristics. Keep missing and
conflicting identity explicit. A distinct notebook name is a proxy, not proof
of a distinct task/version. Task identity stays unknown without an explicit
reliable field.

All linkage and per-account artifacts remain ignored and private. Pin source
bytes; save create-only results. Verify exclusions and temporal boundaries with
an authored check and independently reproduce the aggregates. Stop after one
availability report and a concrete next-study recommendation. No model calls,
new labels, future-content inspection, generator changes or UI work are part
of this step. Freeze a separate prediction protocol before any later generation.

## Local inventory result

The saved metadata covers 9,597 linked conversations. Reapplying the original
account-wide exclusions and removing all ten now-exposed development accounts
reproduces the expected remaining population:

| Availability | Accounts | Eligible later conversations |
| --- | ---: | ---: |
| Remaining candidates | 108 | 1,018 |
| At least one completed earlier linked conversation | 105 | 979 |
| At least two | 100 | 924 |
| At least five | 75 | 809 |
| At least five earlier nonempty query events | 88 | 902 |
| At least ten | 80 | 841 |
| At least twenty | 67 | 750 |
| At least two earlier linked conversations and ten query events | 80 | 834 |
| Same, requiring two **query-bearing** earlier conversations | 80 | 833 |

The full history pool contains 2,646 conversations, including ones too short to
contain a target checkpoint. None has missing chat timestamps. The 1,018 possible
later conversations contain 4,652 structural checkpoints; these are neither
independent people nor verified request/response pairs. The ten excluded accounts
remove 167 conversations from the old checkpoint-eligible pool, rather than just
the ten previously selected conversations.

Independent review identified 588 history-pool conversations with no linked
nonempty student query. Accordingly, the original frozen linked-conversation
counts are retained, and the last table row is an explicitly additional usability
check. It changes one candidate conversation and no account counts. Response-only
histories are omitted from the prepared notebook lookup. Even query-bearing
records require a later prefix-only usability check: the SQL's `<> ''` definition
includes whitespace-only strings, and event counts do not establish distinct
requests or enough evidence for a stable personal tendency.

This resolves the immediate sparse-history concern from the ten exposed cases:
we have a larger source pool worth investigating. It does **not** show that
profiles differ, improve predictions, remain stable across tasks, or capture the
full sequence of notebook actions. A comparison restricted to these 80 accounts
would describe accounts with richer recorded histories, not a randomly chosen
DSC 10 student. Sparse histories still need a generic fallback.

## Prepared lookup and external blocker

The private lookup plan covers the 833 later conversations and their query-bearing
earlier histories: **1,839 distinct conversation IDs across 80 accounts**. It reuses
the original cutoff and account salt. SQL returns pseudonymous notebook identities,
missingness, event counts and timestamps. It returns neither raw notebook names
nor message text, source cells, outputs or raw account identifiers.

For a later comparison, only the **first chronological chat event's** notebook
identity may describe the target conversation's starting context. The aggregate
notebook identities from a completed earlier conversation may describe history;
the target conversation's later identities must not select or construct its
profile. Different filenames remain a proxy for notebook separation, and cannot
establish different questions or versions.

The sandboxed connection attempt failed DNS resolution. The permitted network
attempt then reached the cluster authentication service, which returned **HTTP
503 Service Unavailable**. This is an external service failure, not an approval
rejection. No database query was dispatched and no tunnel was opened. The lookup
is prepared, not executed or verified against the database. Its SQL received a
static review; that does not substitute for a successful receipt.

When access returns, run this metadata lookup through the existing read-only
probe, then verify conversation IDs, identities, counts and times against the
saved linkage. Fail on unexpected drift rather than silently replacing the frozen
population. Save the receipt create-only. Exact checkpoint boundaries and prefix
content are a later step; neither was downloaded here.

## Next comparison and stopping point

Prepare one fixed comparison of **generic, matched-history and other-account
evidence cards**, with matched versus generic as the primary contrast. Reuse the
existing communication-form endpoint and empirical-form baseline. This would
test whether pre-existing usage history helps predict communication, not whether
a simulator perfectly reenacts an individual or predicts unseen notebook actions.
The other-account condition diagnoses whether matching matters; avoiding a bad
donor alone is not improvement over the generic baseline.

Before fetching fresh reference text, freeze the cohort, chronological checkpoint,
history allowance, profile construction, donor matching, model settings, draw
budget, failures and stopping rule. A ten-account development comparison is a
reasonable bounded next step; no ten-account cohort or provider batch has been
selected or dispatched by this inventory. Inspect only the selected pre-cutoff
history for usability and profile contrast before spending on generation, and
retain failed/sparse cases rather than silently replacing them. Task-separated
claims require evidence beyond the available conversation metadata.

The local inventory is closed. Its practical result is **enough earlier
conversation history to prepare the comparison, with notebook separation still
pending the metadata lookup**. No labeling request or user review is needed now.

## Reproduction and saved evidence

From this worktree, using its existing Python environment:

```sh
python experiments/2026-10-01-history-availability.py check
python experiments/2026-10-01-history-availability.py verify
```

The first command checks account-wide exclusion and strict temporal boundaries.
The second recomputes the entire inventory from pinned metadata and compares it
with the saved private artifact. An independent implementation reproduced every
per-target history list and all aggregate counts. Private files remain ignored
under `data/history-availability-v1/`: `conversations.json`, `notebook-plan.json`
and the permission-restricted `notebook-params.json`. The plan pins its SQL,
parameters, source inventory, wrapper and read-only probe. An initial inventory
artifact is preserved separately after correcting JSON key serialization for
reproducible verification; counts and selections did not change.

`python data/history-availability-v1/verify-notebook-plan.py` also reproduces the
query-bearing subset and verifies all seven plan pins, the parameter file's
restricted permissions, and unchanged salt/cutoff. Independent review reproduced
the 80/833/1,839 scope. It deliberately omits 439 zero-query earlier conversations
within this subset; the 588 count above concerns the entire 108-account history pool.

Receipt acceptance must require exactly one row per requested conversation and
matching frozen event/query/response counts, chat times, account sets and missing
identity counts, as well as matching SQL/parameter/probe hashes and `read_only`.
A null notebook aggregate means missing evidence. Observing a different notebook
hash alongside missing identities does not establish that all earlier messages
concern another notebook. Exact stored strings are hashed without normalizing
whitespace, filenames or paths; a rename can therefore look like a new identity.
