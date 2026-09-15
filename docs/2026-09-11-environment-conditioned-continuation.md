# Separate environment observations from student communication

The grader-format correction identifies a missing boundary: the environment
supplies an outcome, while the simulated student chooses whether and what to say
about it. Test that boundary using continuity case 1's existing conversation,
generated student revision and scripted tutor bridge. No new source conversations
or actual notebook execution are needed.

Use two explicit scenario conditions: the current grader outcome is unknown, or
a successful check after the tutor reply is stipulated. Supply the success text
verified in the raw logs as an environment observation, outside the dialogue.
In this authored scenario the supplied representation is available to the student;
it does not reconstruct the unverified deployed notebook display.
This is an authored hypothetical condition, not the original student's future,
a claim that the generated revision passes, or evidence that the student ran it.
The empty observation means unknown, not no run, failure or silence. Do not assign
the original student's failing run to a generated revision.

Retain the communication/formatting prompt and exact dialogue suffix, adding only
one common instruction about the supplied scenario and its separate observation.
For the successful condition, distinguish all-pass output from passing subtests;
a student may quote a fragment or paraphrase, so exact full-message copying is
not the goal. For unknown outcome, do not manufacture a new run, result or error.
Reply and no-reply remain available in both conditions. More silence is not an
improvement measure, and four draws cannot estimate a reply probability.

Generate two draws per condition with the existing Gemini 2.5 Pro adapter, strict
reply/no-reply schema and durable request cache. This is a four-request development
diagnostic on one exposed context, not a policy comparison or held-out evaluation.
Keep every draw and failure; do not retry for semantic quality. The historical
unconditioned outputs remain available as context, not a matched control.

Freeze the exact prompts, observation provenance, model settings, source hashes,
runner, disclosure and standing authorization before sending. Minchan's instruction
to continue and recorded standing approval cover this batch; neither is represented
as a human judgment of the future results. Verify that authorization before loading
credentials. Reuse existing cache and review helpers. All raw/generated content
and diagnostic scripts remain under ignored `data/episode-pilot/environment-condition-v1/`;
only this method and verification status enter Git.

Show the common conversation once, followed by the two scenario conditions and
all candidates. Mark the generated seed, scripted tutor and hypothetical result.
Mechanical checks cover exact source/output preservation, scenario isolation,
request hashes and saved-answer preservation. Inspect adherence to the supplied
state separately, with assistant provenance; human plausibility fields remain
blank until supplied. Human review can address what the student would say
conditional on replying while leaving reply occurrence uncertain. Do not tune
again before reviewing this diagnostic's results.

## Frozen preparation

Experiment `04c560188445514964b4cbd8c400660c93a04c76d83bd7311a44e33c8281d948`
pins 350 files, including all 339 parent pins. The two scenario prompts retain the
exact same dialogue suffix, schema and API settings. The private runner verifies
standing authorization against all four exact requests before loading credentials.
Offline checks pass for scenario/dialogue separation, changed authorization job
bindings, cache reopening, review text preservation, duplicate draws, no-reply,
failed calls and saved human answers. No production generator or API was changed.

## Approval review checkpoint

Automatic approval review rejected the initial send before process launch. Its
stated reason was transmission of private student dialogue and derived context
to an external model destination; it did not accept general model-run approval
as specific authorization for this payload and destination. Zero requests were
sent and no results file exists at this checkpoint. The exact rejection and a
hash-bound four-request disclosure are saved privately. The standing permission
remains recorded; an audit of prior specific payload approvals is separate from
any claim that this new batch has received exact-payload approval.

The subsequent scope audit verifies that every current dialogue byte already
appeared in continuity case 1's specifically approved Gemini payload, including
the generated seed and scripted bridge. The only new prompt content is generic
instruction and the authored scenario packet. That prior user “Yes” was bound
to three earlier exact requests; it is not relabeled as approval of these four.
An evidence-supported review of the same unchanged send command was also rejected
because the scenario data makes this a different payload. Both decisions remain
saved. No further send is attempted without specific approval of the prepared
four-request disclosure.

Independent preparation and authorization-scope audits pass. All 350 frozen pins
remain intact; zero requests were sent and no model outputs or human output
judgments exist. The prepared diagnostic and exact approval request are complete;
execution is awaiting the permission required by automatic approval review.

## Specific approval and execution

Minchan subsequently answered “Yes” to sending these exact four prepared prompts,
including the previously reviewed student dialogue, to Gemini 2.5 Pro. The saved
`approval-response.json` binds that response to the unchanged experiment, input,
job and disclosure hashes. Both earlier rejections and the unsent checkpoint
remain preserved. No plausibility or reply-occurrence judgment is inferred from
permission to run the batch.

## Completed diagnostic and evidence-grounding failure

All four logical requests completed with structurally valid replies and zero
failed draws. The explicit approval, request/output mappings and all 350 frozen
pins verify. Offline cache reopening and rerendering preserve every protected
file byte-for-byte. Independent presentation verification checked all four
allocations and 15 exact fenced blocks. No human output judgments were supplied.
Adapter attempts are not individually logged; these are logical-request counts.

| Condition | Observed outputs | Assistant evidence check |
|---|---|---|
| Current outcome unknown | Two replies reporting outcomes | Both assert a current result unsupported by a supplied post-revision observation |
| Successful check stipulated | Two success replies | One copies the supplied output; one paraphrases success; both are consistent with the assigned result |

The first unknown-condition reply reuses a historical failure fragment and a row
count mentioned in an earlier student question. The number is not invented from
nothing: the error is promoting old or uncertain evidence into a current claim
after the generated code revision. The second unknown-condition reply presents
a new all-pass result. These are unsupported under the frozen scenario contract,
not proven false claims about an actually executed notebook. The hypothetical
success condition establishes neither the generated code's correctness nor the
real student's future.

`assistant-outcome-audit-independent.json` records exact historical and generated
evidence references separately from the blank human review. The other receipts
are `completion-verification.json`, `presentation-verification.json`, and
`independent-approval-verification.json`. All raw excerpts remain private.

This variant fails the intended handling of unknown current outcomes. Do not
promote it to longer rollouts, relabel the assistant checks as human ground truth,
or ask Minchan to review those unsupported current-result claims as plausibility
questions. The two consistent
success replies still have no human plausibility or reply-occurrence judgments;
consistency is not a demonstrated communication improvement. All four draws
reply, which does not estimate a response probability.

The next boundary to implement is the link between an action, its environment
observation and the code state it concerns. After a code revision, earlier grader
results remain evidence about earlier code; they do not establish the current
result. A requested check must remain pending until the environment supplies a
result. A student can still ask questions without running code; missing execution
evidence must not be converted into either a report or a predicted no-reply.
This diagnostic does not implement that action/execution loop. Preserve its
negative result before extending the simulation, rather than adding another
case-specific wording instruction or requesting the same plausibility review.
