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

At this checkpoint no requests were sent and no results cache existed. All 358 pins verified.
The exact rejection and hash-linked permission request are saved privately as
`automatic-approval-rejection.json` and `approval-request.json` beside the exact
`disclosure.md`. The frozen preparation remains unchanged. Do not retry this send
or use an indirect route without resolving the automatic review's requirement.

## Specific approval and execution

Minchan answered “Yes” to sending these four prepared prompts, including the
previously reviewed student dialogue, to Gemini 2.5 Pro. The private
`approval-response.json` binds that reply to the displayed question, disclosure,
inputs, jobs, model and experiment. All 358 pins verified before execution.
The unchanged runner was launched only after recording this specific approval;
the earlier rejection and preparation remain preserved.

## Schema transport failure and corrective retry

All four logical requests failed before returning a selection: Gemini returned
HTTP 400 because its response schema rejects `additional_properties`. The adapter
retries this permanent error; individual attempts are not retained. This is a
schema compatibility failure, not evidence about student action choice.

`NextAction` inherited the local check-record configuration, which exposes
`additionalProperties` in JSON schema. Existing student/tutor selection models
already remove that unsupported wire keyword while retaining local extra-field
rejection. Reuse the existing Continuation configuration for NextAction alongside
its strict, frozen check-record settings. Add a regression covering the actual
schema sent by the adapter and retained local validation; change no prompt or
action semantics.

Preserve the four failures and their receipts. The original 358 pins include the
gate module and tests, so archive their exact `e39d1aa` bytes before editing and
verify those archived bytes against the original manifest. All 350 earlier pins
remain live and unchanged. Later reproduction of this failed run must use its
original sources, not assert that edited current files still match its manifest.

Prepare a separately versioned corrective retry in private
`student-action-choice-v2/`, reusing the original cache helpers and exact four
approved prompts, model, default settings and local action validation. Its schema
diff must consist only of removing the unsupported keyword. Link the specific
approval and the failed experiment, distinguish retry calls from the original four
failures, and preserve every old result. This is a corrective retry under the same
approved prompt scope, not a newly received human approval or a new scenario.

The schema regression fails against the original configuration and passes with
the one-line reuse. The full suite passes 297 tests, the Node review-navigation
check passes, and all 350 live base pins verify. One pre-existing Starlette/httpx
deprecation warning remains. These checks establish local compatibility handling;
successful remote acceptance still requires the corrected retry.

The corrected experiment is
`0dac97d8f1b89d68c0bdee55adca1360a359ae76010c3a4f3b58367ba5492f08`.
Its 370 pins verify, including the 358 original pins through the explicit two-file
archive mapping and the 350 unchanged live base pins. Inputs are byte-identical
to the original approved preparation; prompt/job hashes, model and settings match.
The verifier requires the schema diff to contain only the unsupported keyword
removal and checks the original failure cache without resubmitting it.

## Corrected retry result

The corrected schema was accepted. All four requests returned structurally valid
actions; three routed successfully and one failed local routing. The original
four schema failures remain separate: eight logical requests across both runs,
with four returned actions only in the corrective run. Adapter attempts were not
individually recorded.

| Condition | Draw | Returned choice | What the program did |
|---|---|---|---|
| Check available | 1 | request-check | Preserved a pending request; no message or result |
| Check available | 2 | request-check | Preserved a separate pending request; no message or result |
| No check option | 1 | reply | Emitted an unsupported current-success report |
| No check option | 2 | request-check | Rejected the unavailable action; retained the selection as a routing failure |

The success report says the work succeeded, but no current observation was
supplied. It does not explicitly assert that every grader test passed, and no
execution proves the reported success false. The issue is ungrounded current
state. The rejected choice is neither student silence nor a failed grader test.
No draw selects no-reply. Neither requested check executes code or calls the
after-check generator.

The two available-check draws demonstrate use of the new pending path in this
exposed situation. The other condition shows that prompt instructions do not
reliably constrain missing capabilities or ground free-form reports. Do not
promote this to longer rollouts or ask for style judgments on the unsupported
report and routing error. These draws do not estimate response probability or
isolate the effect of availability from repeated code salience.

All 370 current pins verify; the old 358 verify through their documented archive
mapping and all 350 earlier live pins remain unchanged. Reopening the completed
cache makes no dispatches and preserves the original pending request IDs. The
exact review displays all four draws against one common dialogue, preserving
the failed selection and separate original schema failures. Rerendering is
identical and all human judgment fields remain blank. Completion and presentation
receipts are private beside the results.
Independent outcome review confirms these distinctions and the approval, source
and cache bindings; its separate assistant audit adds no human judgments.

The next useful investigation is whether the saved assignment assets can support
an actual bounded check against a known state. Locate the notebook, input data
and grader definitions before adding more continuation prompts or an executor.
Historical grader events alone cannot supply results for the pending checks.

The subsequent [reference fixture](2026-09-11-reference-grader-fixture.md) found a
runtime error before grading. That new authored state does not retroactively
turn the earlier unsupported success report into a proven false claim about the
unobserved original state, and its error was not backfilled into these draws.
