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
