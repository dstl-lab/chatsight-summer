# Test action choice before extending the simulation

The action flow passes its offline checks. Test whether the model uses the new
choice on the same exposed continuity branch that previously produced unsupported
current outcomes. This is a developmental probe, not a held-out evaluation.

Prepare four Gemini 2.5 Pro requests: two with the explicitly supplied current
code/check option and two with no check option. Preserve the exact visible
dialogue in both conditions. The code option is caller-selected from the saved
student request; it does not install a tutor's suggested revision or represent
an observed notebook state. No new source dialogue, current grader result, human
verdict, identity or runtime ID is sent. The model receives the existing style
guidance and the new reply/no-reply/request-check schema.
The option also repeats the current code and names its grader target; differences
between conditions cannot isolate availability from this additional salience.

Use the actual next_step helper to construct and route each action. A selected
check remains pending with no result supplied and no continuation model call.
Ordinary reply/no-reply remains available; an unavailable check is an explicit
routing error, never silently recoded. Preserve every returned selection,
including one rejected by the local boundary. Freeze exact inputs, schemas,
settings, parent/source hashes and authorization before sending. Keep a pending
record before each call so an interruption cannot silently resubmit it.
Keep logical draw identities independent of fresh check UUIDs and preserve each
returned request when reopening the cache. The existing adapter retries up to
four times per logical request, including parse/schema errors; individual
attempts and raw rejected API responses are not retained. Preserve selections
returned by the adapter separately from any subsequent routing failure.

Standing model-run authorization and the latest continuation instruction cover
this routine diagnostic; record that basis without inventing an exact-payload
approval. Respect any automatic approval review decision at execution. Raw inputs,
outputs and receipts stay in ignored `data/episode-pilot/student-action-choice-v1/`.
All 350 previous experiment pins and the earlier negative result remain unchanged.

Inspect action validity and unsupported current-outcome claims first. Do not ask
for a plausibility judgment on a reply with an ungrounded result. If structurally
valid actions/replies remain useful to judge, present their exact context and
choices for human review. Leave reply probability, correctness, policy effects
and student realism unmeasured; four exposed draws cannot establish them. No
notebook execution, new labels, or longer rollout is introduced.

## Prepared diagnostic

Experiment `2b0a7e2414c69fe984d81a8b50a3786897fe9a4bf85a95680015f364b7b95611`
contains two exact prompts and four distinct logical draws. Its 358 file pins
include all 350 unchanged parent pins. Offline preparation, prompt/disclosure
parity and invented cache checks pass. The cache checks cover reopening without
dispatch, preserving a rejected unavailable-check selection, changed-record
rejection and interruption before completion. The prepared prompts contain no
current outcome; both retain the same historical dialogue. Private authorization
records the standing grant and the literal latest instruction, “Lets continue.”

Independent review found no blocker. A separate invented same-prompt/different-draw
check confirms distinct dispatches and unchanged cached selections/request UUIDs
on reopening. This is an offline routing check, not model behavior evidence.

## Automatic approval checkpoint

Automatic approval review rejected the send before process launch because the
prompts contain private student dialogue sent to Gemini. Its stated reason was
that the standing approval and continuation instruction do not specifically
authorize this newly prepared payload and destination. The user has already
granted standing permission; the additional specific permission is required by
the automatic review, not by a new project approval policy.

No requests were sent and no results cache exists. All 358 pins still verify.
The exact rejection and hash-linked permission request are saved privately as
`automatic-approval-rejection.json` and `approval-request.json` beside the exact
`disclosure.md`. The frozen preparation remains unchanged. Do not retry this send
or use an indirect route without resolving the automatic review's requirement.
