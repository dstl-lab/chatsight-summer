# Notebook observation-window readiness

## Scope fixed before this pass

Minchan authorized the offline readiness check and merging PR #25 if ready.
Reuse only the three previously selected notebook pairs, their saved metadata,
and the two saved first-exchange recovery receipts. No new database reads, model
calls, labels, target selection, prompt changes or simulator changes. Stop after
one reproducible report separating observable net state from inferred actions.
This does not reopen either completed benchmark or select a new holdout.

Check capture gaps, the matched first tutor response, later recorded replies in
that conversation, and the last linked chat time before the target capture.
Distinguish same-notebook attribution from same-question/task identity. Preserve
all old receipts and outcomes, including the V2 forecasts. The recovery query
includes at most 101 tutor responses from each initial conversation, but only
queries in the five minutes before its initial capture. A short query list
therefore cannot establish that no later student queries occurred.

Merge readiness is a separate engineering decision: run the complete Python test
suite and independent code review, then respect the repository's merge rules.
User permission supersedes older instructions to keep this PR draft/unmerged;
it does not supply a GitHub approval required by repository rules.

## Result and decision

**Ready for a descriptive net-state comparison; not ready for a same-task,
next-action fidelity benchmark.** This is a statement about the retained evidence,
not proof that every possible field in the underlying database is unavailable.
The existing simulator remains a usable research prototype; its human fidelity
is not established by these captures.

| Existing pair | Capture gap | Later tutor replies in the initial conversation | Other boundary evidence |
|---|---:|---:|---|
| 1 | 13.42 min | Not recovered in this pass | Cell layout changed; no positional forecast was made. |
| 2 | 3.35 min | 0 recorded | Last linked chat occurs 153.16 seconds after the first reply, 48.09 seconds before the target capture. |
| 3 | 66.44 min | 3 recorded | Last linked chat occurs 61.29 minutes after the first reply, 5.15 minutes before the target capture. |

The initial conversations have one and four saved tutor-response rows in pairs
2/3. Both are below the recovery query's 101-row limit. Pair 2's later linked chat
time is not a response timestamp; the inventory's chat events consist only of
queries and responses, so it implies at least one later linked student query.
Its text and the full later query history were not retrieved. Pair 3 demonstrably
includes three further tutor replies outside the forecast prompt. Zero recorded
additional replies in pair 2 does not establish absence of other help or work.
Unlinked or identity-ambiguous records can also interrupt the apparent adjacency.
Both initial student queries were unlinked; their recovery uses the saved learner
join, timing, exact text match and unique pairing with the capture/reply.

All three pairs match the learner/notebook attribution rules, but a notebook can
contain multiple questions. The retained metadata does not bind both endpoints
to one persistent question/task version. No same-task claim follows. The initial
captures are within 0.06 seconds of their matched first replies in server time,
with logging order differing between the two examples; this is not a timestamp
of when a student actually received or acted on a reply.

The V2 result is still a valid descriptive forecast of net source at the next
eligible capture, conditional on a recorded return and the selected layouts.
Subsequent help is part of the unobserved future in that target; withholding it
is appropriate for a prospective forecast. The new finding does not invalidate
or rescore V2. It prevents interpreting its error as a defect in a one-turn
student policy or evidence about one tutor response's causal effect. In particular,
the three later replies could matter, but their causal contribution is unknown.

## What can be measured

- **Observed:** elapsed server time, recorded tutor replies, and net textual
  changes at comparable notebook positions. Changed-cell count describes the
  extent of a net difference, not effort, number of edits, or time actively working.
- **Conditional future study:** predict the next eligible same-notebook capture
  under the naturally occurring subsequent interactions. Freeze eligible student
  groups before target inspection, report layout exclusions, define whether the
  horizon is fixed or a variable return time, and compare with prespecified
  baselines. An eventual observed return time must not become a supposedly known
  input to a prospective forecast. This pass does not establish an untouched
  holdout or authorize another model batch.
- **Not established here:** a same-question next action, complete action order,
  no-reply probability, execution tied to code revisions, learning, or the effect
  of changing a tutor policy. Those require records bound to the corresponding
  task, work revision and observation boundary.

## Stop and next engineering direction

Close this audit. Do not tune the simulator against the two exposed outcomes,
add labels, or ask for another plausibility review. Keep the existing runtime
and completed benchmark evidence unchanged.

The useful next engineering step is to define and verify a common observation
contract for real and simulated sessions: task/version identity, stable cell
identity and source revision, the tutor turn associated with each capture, and
checks bound to that revision. First establish whether the deployed logger
already retains those records; earlier bounded inspections did not recover
later work diffs, but did not prove global absence. A replayable recorded example
with those bindings is the acceptance criterion before a next-action fidelity
study. This does not require collecting keystrokes or claiming learning.

## Reproduction and merge validation

Run the saved audit without DB access, model calls or notebook execution:

```sh
python3 data/episode-pilot/observation-window-readiness-v1/inspect_window.py
```

The private result records source hashes; a second run must reproduce it exactly.
The authored time-window control excludes both boundary timestamps. Independent
recomputation checks the interval findings and their interpretation. All 28 V2
completion hashes and 20 prior notebook-pair hashes remain unchanged.

The full Python suite passed: 371 passed, two optional container tests skipped,
with one upstream deprecation warning. All three standalone Node state checks
passed. Two independent code reviews found no actionable blockers in the runtime,
agent, labeling, review and scoring paths; live model behavior and Docker
integration were not retested. Private data and audit receipts remain ignored.
The organization rule for main requires one approving GitHub review and a squash
merge. No approval is currently recorded; automated local reviews do not fulfill
that GitHub requirement. The PR can be made ready, but must retain that gate.
