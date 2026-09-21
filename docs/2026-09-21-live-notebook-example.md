# One live walkthrough of the public notebook example

**TL;DR:** Run the prepared public example once through the existing lesson
runner. Six student decisions, at most two tutor replies, actual local checks
only when requested. Save and inspect the result; no new labels or rerolls.

The setup and scripted container tests are complete. This walkthrough exercises
the user-facing setup with generated actions and replies on the exact supplied
task, table and initial code. All starting content is authored and public. No
historical student dialogue, notebook capture or profile enters these requests.

Use the existing `data/notebook-example/session`, its concise hint policy and
the checked-in Babypandas 1.0.0 reference. Both model roles use Gemini 2.5 Pro,
with existing provider defaults. Freeze the initial manifest/state, first student
prompt, schemas, policy, reference, runtime image and implementation files before
dispatch. Later prompts depend on the saved generated actions and actual check
feedback; existing operation receipts save their exact content for replay.
The separate expected answer stays out of both agent and worker inputs.

The fixed limits are six student decisions plus two tutor replies: at most eight
logical requests and 32 adapter attempts. Actual adapter retries and SDK HTTP
attempts are not individually recorded. At most six local checks could be
requested, each in the existing restricted container with its saved timeout.
Do not force a check, error, correction, chat response or no-reply to obtain a
preferred trajectory. Preserve failures and stop at the existing lesson stop
reason; one invocation only, with no replacement sample or budget extension.

Acceptance concerns operation: exact saved replay, unchanged startup files,
bounded requests and source-linked real execution feedback when requested.
Report model decisions, tutor replies, local checks and stop reason separately.
A pass checks one scalar against the authored expected answer. A no-reply is a
model choice, not observed abandonment or evidence of learning. Free-form chat
and student fidelity remain unvalidated. This is not a policy comparison or a
measurement of improvement over the chat-only run.

Authorization is the current “Continue” instruction and the recorded standing
approval for project Gemini runs. These wholly authored inputs use no private
student payload and do not rely on the previous cohort's exact-payload approval.
The scope and result live under ignored `data/notebook-example/live-run/`.

## Status

**Complete and closed.** The generated walkthrough ran from 14:57:53 to 14:58:23
UTC on September 21, 2026. It followed this saved sequence:

1. **Quiet code revision.** The student divided the count of blue rows by the
   number of rows. No chat message accompanied the edit; work became revision 1.
2. **Requested local execution.** The declared container returned float `0.5`,
   which passed the supplied scalar evaluation for revision 1.
3. **Generated no-reply.** The model ended the encounter with three decisions
   still unused. This was not budget exhaustion or observed abandonment.

The run used **three logical model requests and one real container check**.
There were no model/runtime errors and no generated tutor replies. Actual adapter
retries are unrecorded; the three requests imply at most 12 adapter attempts,
within the approved ceiling of 32. No rerolls or further steps followed.

The configured hint policy and API reference were never delivered to a generated
tutor because the student never requested another tutor turn. The opening hint
was already authored in the initial dialogue. This run does not test the effect of
that policy or establish that generated chat respects all context boundaries;
it contains no generated chat messages. Nor did the live run first observe a
failing check: its only requested check followed the revision and passed.

All 77 frozen setup/source files match. Existing replay reconstructs every prompt,
action, result and execution binding without model or container calls; rendering
and the rejected repeat invocation leave session files unchanged. The evaluator
is absent from each actual student prompt. The saved `scope.json`, `dispatch.json`,
`audit.json`, `OVERVIEW.md` and `replay.html` document the result under
`data/notebook-example/live-run/`. Original prepared `initial.html` remains intact.

The operational acceptance criterion is met: generated actions can change supplied
work, request real execution feedback and stop without a forced chat response.
Preserve this run; student realism, learning and policy effects remain unvalidated.
Independent terminal audit confirmed all pins, exact prompts and schema, absence
of evaluator fields from actual model inputs, ordered call timestamps and the
four expected new session files. No remaining audit issue was found.
