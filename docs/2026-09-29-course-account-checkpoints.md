# Freeze ten checkpoints from provisional course accounts

Minchan explicitly declined student eligibility verification: “Let's not verify
student eligibility.” Proceed with **course accounts**, without requesting a
roster or treating accounts as verified students. Keep the established identity,
known-exposure and diagnostic exclusions; those are separate from role checks.

This completes selection/preparation only. No model calls, training, new labels,
or simulator/UI changes are part of this step.

## Selection fixed before reading message content

Use the existing 118 candidate accounts and their 1,185 conversations from the
read-only linkage recovery. Fix seed `course-account-checkpoints-v1-20260929`.
Rank accounts by SHA-256 of `seed:account:<account_id>` and take the first ten.
Within each selected account, rank eligible conversations by SHA-256 of
`seed:conversation:<conversation_id>` and take the first. This gives each eligible
account one entry, rather than weighting accounts by how much they chatted.

For those ten conversations only, retrieve checkpoint metadata with the same
fixed cutoff, event-ID ordering and nonempty-message conditions as the recovered
candidate pool. A checkpoint ends at a tutor response immediately before a third-
or-later student query. Rank boundaries by SHA-256 of
`seed:checkpoint:<conversation_id>:<target_event_id>` and choose one per
conversation. Freeze the account, conversation and event IDs before fetching text.
Do not replace cases based on message content or unexpected results.

Reuse the existing read-only probe, its transaction assertion and 20-second
statement timeout. Fetch only the selected conversation prefix through its tutor
boundary and its one recorded next student message; preserve exact text and
event IDs. No later messages or notebook contents are needed. Keep the full
prefix without silently truncating; report its size before any later generation.

Save query-only inputs in the existing `retrieval_baseline.Query` format, with
the pseudonymous account in its legacy `student_id` field. The field name does
not verify student status. Save recorded targets in a separate references
directory and do not expose them to generation. Source receipts and raw
conversation IDs remain private under ignored `data/course-account-checkpoints-v1/`.

Verify exactly ten distinct accounts, no overlap with known exposed accounts or
the historical training library, consistent identities, exact boundaries, source
hashes and target exclusion. A changed/missing source stops preparation rather
than silently replacing a selection. Preserve all earlier study artifacts.

These are account-separated cases from a filtered historical population, not a
random sample of verified DSC 10 students. Event adjacency does not prove request
pairing, and an observed next message conditions the sample on return to chat.
This cohort cannot estimate silence rates, notebook actions or learning gains.

## Completed

All ten provisional accounts, conversations and checkpoints were frozen as
specified; no cases were replaced. The metadata query returned 50 eligible
boundaries across the selected conversations, matching their prior counts.
The content query retrieved exactly 117 events: 107 prefix turns and ten recorded
next messages. Prefixes contain 4–31 turns and 1,997–28,131 characters. None of
the retained turns or targets is whitespace-only. No prefix was truncated.

The selected accounts have zero overlap with the full known-exposure account
set, the historical training library or its inherited query set. Student
eligibility remains deliberately unverified, as requested.

Private `inputs/queries.json` contains only the ten prefixes in the existing
Query schema. `references/recorded-next.json` contains the ten outcomes separately.
`selection.json` and `frozen-checkpoints.json` bind those files to the fixed
selection, source identities and event boundaries. `prepare.py verify` rechecks
both read-only receipts, source pins, account separation, exact event IDs/order,
boundary roles, query validation and target exclusion. An authored regression
checks that future text does not enter the prefix and missing targets are rejected.
Independent offline review reproduced the result and confirmed the ordering of
selection, metadata retrieval, checkpoint freeze and content retrieval.
Original recovery/study files remain unchanged and all private artifacts are ignored.

Both queries succeeded once using the existing probe and timeout. Temporary
tunnels closed on connection teardown; no database writes, model calls, training,
new labels or UI changes occurred. Message and target text were not printed or
semantically inspected during selection/preparation.

This completes the first milestone. Before generation, fix the baseline versus
history comparison, context budget and scoring rule for these same ten cases.
Keep the references reserved for scoring and retain any failures rather than
replacing cases or adapting prompts after inspecting their outcomes.
