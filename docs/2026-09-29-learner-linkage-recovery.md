# Recover learner linkage from existing historical records

The user approved recovering the missing mapping after the local eligibility
audit. Reuse the existing read-only ingestion probe and temporary localhost
Kubernetes tunnel, with its read-only transaction assertion and 20-second
statement timeout. Do not change the database or existing study artifacts.

Recover conversation-to-account metadata, using a private random key to derive
stable pseudonymous IDs inside SQL; raw emails stay inside the database. Preserve
the key, SQL, parameters and receipts only under ignored
`data/learner-linkage-recovery-v1/`. Never publish these linkage records.
Check missing and conflicting identities rather than assigning a learner from
one convenient event. Case/whitespace normalization is an explicit account
matching assumption, not evidence of a verified person.

Use the historical candidate interval `[2026-02-01, 2026-08-07)` UTC and the
already-audited cutoff `2026-09-29T03:45:27Z` for exposure linkage. Exclude accounts
linked to any locally exposed conversation, including training, prior development
exports and notebook inspections. Check whether role/course provenance is actually
available; an email or account ID alone does not establish student status.

Stop after the mapping, exposure exclusions and eligibility counts are saved and
verified. Do not generate, train, label or fetch new conversation/notebook content.
If eligible identities remain unverified, retain them as candidate accounts,
not a frozen student cohort. Recovering identifiers cannot undo prior exposure.

## Recovered and verified

| Metadata result | Count |
| --- | ---: |
| Linked conversations before the fixed cutoff | 9,597 |
| Distinct normalized, pseudonymous accounts | 388 |
| Conversations wholly inside the historical candidate interval | 9,442 |
| Known exposed conversations matched | 262 of 262 |
| Accounts linked to those exposures | 132 |
| Remaining candidate accounts after conservative filtering | 118 |
| Candidate conversations / structural checkpoints | 1,185 / 5,336 |

Every returned conversation has exactly one normalized account and no missing
account events among the queried event types. Pseudonyms use PostgreSQL SHA-256
over a private random 256-bit salt, a separator and the normalized account value.
The salt is retained in a private, permission-restricted parameter file for
consistent future joins. These are pseudonyms, not anonymized public data.

The conservative exposure manifest includes all 252 canonical conversations,
six later notebook-pair endpoints, three adjacent conversations previously seen
as metadata, and one probable instrumentation-test conversation. A bounded local
audit pinned 425 source files and resolved the existing training/query aliases.
It is a record of known local exposure, not a guarantee about external work or
provider pretraining. All 262 IDs match the database without identity ambiguity.

Candidate filtering excludes an entire account when any linked conversation is
known exposed, has ambiguous/missing identity, or carries diagnostic/test evidence.
Explicit diagnostic events are checked across event types; notebook-name hints
are deliberately conservative and may exclude genuine course use. A candidate
conversation must fit wholly within the historical interval and have a third-or-
later nonempty student query immediately following a tutor response in event-ID
order. This is a structural checkpoint, not a verified request/response pairing.
Future answer text and notebook contents were not exported or used for selection.

## What the mapping changes

The old library contains 95 accounts across 156 conversations; its 29 query
conversations contain 26 accounts. **Twenty accounts overlap, covering 23 of the
29 query conversations.** Conversation separation did not provide account
separation, so learner separation was not established. This quantifies a previously documented limitation; it does
not change old predictions, training inputs or closed-study scores.

The private `existing-split-linkage.json` joins every one of the 1,208 old input
rows to its account without copying message text or changing the old files.
`candidate-accounts.json` retains the eligible account/conversation metadata;
`summary.json` and `verify.py` reproduce the counts and exclusions offline.
The original 29 queries are not candidates for a fresh holdout.

Student status remains unverified: the inspected schema and top-level event keys
contain no enrollment roster or explicit student/staff role field. An account
can represent staff or test activity, and a person may have multiple accounts.
No ten-student cohort has been frozen. The next step is to apply an existing
roster or staff/test exclusion list, or explicitly use “course accounts” as the
provisional population, before freezing ten distinct account checkpoints.

## Verification

Two read-only query receipts pin SQL, parameters and the existing probe. The
initial metadata query failed before saving a receipt; its SQL is preserved and
its UNION ordering was corrected before a successful query. Each temporary tunnel
closed on connection teardown and none remains listening. The 20-second statement
timeout remained in place. No database writes or provider calls occurred.

Offline checks verify source hashes, exact output fields, complete exposure
linkage, account-level exclusion propagation, legacy alias joins, and unchanged
original files. Authored checks cover an excluded account reappearing under
another conversation, missing/multiple identities and invalid checkpoint/window
eligibility. An independent SQL review caught and fixed diagnostic-account
propagation before the linkage query; an independent offline review reproduced
the final counts and account exclusions. No message/code content was downloaded,
no new model outputs or labels were produced, and private mappings remain ignored.
