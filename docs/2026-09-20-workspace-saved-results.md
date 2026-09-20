# Inspect saved policies and outcomes

The workspace's **Saved results** tab reads existing chat and notebook receipts.
Each student step shows the saved tutor policy when its delivery can be linked,
the tutor reply, student messages or notebook actions, and the recorded outcome
and remaining budget. Current form drafts do not replace the saved policy.

The view distinguishes no-reply, budget exhaustion, a pause after an action,
student-generation failure and local execution faults. Notebook checks remain
local checks, not course-grader results or evidence of learning. Quiet edits are
shown as work changes rather than invented chat messages. Saved timestamps can
describe importing cached replies and are not presented as fresh generation times.

## Failure visibility

Tutor generation and student continuation are separate operations. A completed
tutor request can still have failed delivery or a failed student request. The view
keeps unmatched tutor records visible with their saved policy, any saved reply and
failure/incomplete status. A supplied reply without a confirmed policy link is
not assumed to have been written by a human.

Policy attribution requires matching the pre-step session/state binding, exact
tutor reply and completed continuation's saved student result. Ambiguous or
inconsistent matches remain unlinked. Notebook context hashes are checked before
linking. Each notebook step displays its own calls, not its cumulative history.

If normal session replay cannot load an interrupted run, the tab still shows
readable receipts and no continuation control. These are explicitly unverified
records when replay is unavailable. Malformed individual records are identified
without hiding other readable steps. Nothing is repaired, retried or overwritten.
This display does not replace the existing replay validation.

## Implementation and verification

`src/agents/workspace_history.py` supplies the read-only rendering used by the
existing Marimo app. It does not construct a provider, execute notebook code,
dump prompts/manifests/private evaluators, or change source-pinned student engines.
It discovers workspace tutor receipts under the session's `tutor-exchanges/`;
historical tutor receipts stored elsewhere are not automatically located.

The full suite passes 400 tests, with two optional container tests skipped and one
upstream Starlette/httpx deprecation warning. Marimo validation passes. Authored
checks cover policy/manual results, stale delivery, failed and interrupted calls,
corrupt records, multi-action notebook steps and partial saved progress.
Browser checks verified a completed run, an interrupted continuation with its
policy retained, a tutor error, and reloading with sending disabled.

Private UI fixtures and verification are under
`data/episode-pilot/saved-results-ui-v1/`. No live model calls, notebook execution,
new labels or changes to earlier evidence were needed. Task-list item 1 is complete;
comparing two policies from one starting conversation remains the next item.
