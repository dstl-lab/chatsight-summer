# Student continuations as inspectable branches

The eight-context plausibility review is complete. Keep its final prompt fixed.
The next useful unit is a student continuation with an inspectable conversation
prefix and a place to describe the student's visible action. Labels measure the
result; this diagnostic does not require them as inputs to generation.

Move the reviewed prompt and strict reply/no-reply schema from the ignored pilot
runner into `src/eval/student_continuation.py`. Reuse the existing tutor-component
input projection so future replies, annotations and episode metadata cannot enter
the generator. Verify exact prompt/schema parity against the completed experiment
locally; never copy its student dialogue into Git. Keep its original files intact.

A branch can continue only from a generated reply and a separately authored tutor
bridge responding to that reply. Retain the visible prefix, replace the current
request/response with the generated student and scripted tutor turns, and record
their provenance and input hashes. Never append a historical future tutor reply
after synthetic divergence. A generated no-reply ends that branch; it does not
stand for a delay, observed abandonment, or an unseen notebook action.

Provide a small review-packet helper using the existing v7 follow-up-action and
task-relationship definitions. It presents recorded and generated next contributions
with the same prefix and blank human judgments. Keep recorded absence separate
from generated no-reply: the rubric's recorded-absence category does not describe a
prediction. Comparing these packets is developmental measurement preparation,
not classifier validation, a fidelity score, or evidence of learning. Reviewers
must cite comparable student work for revisions and both student contributions
for a definite task relationship. Code execution and grader outcomes remain unknown.

The implementation is a few pure functions, using existing Pydantic and standard
library code. No new dependencies, automatic tutor policy, persona, cohort, live
database access, or new label taxonomy. Existing frozen experiment files and the
source modules they pin stay unchanged. Every new private artifact belongs under
ignored `data/`. A later branch run must retain its scripted tutor bridges and all
draws, including failures; human plausibility judgments remain distinct from
observable-action labels.

This is diagnostic evaluation tooling. The repository's open decisions about
classifier admission, archetype/IRB scope and actual tutor-policy ownership still
apply before a production simulation or policy comparison.

## First continuity packet

Use cases 1, 5 and 7 from the completed interaction comparison, retaining draw 1
of each without searching for a better seed. These cases are exposed development
material. Author one brief tutor bridge for each retained reply using only its
visible branch; identify it as scripted, not the historical policy. Generate one
further student contribution per branch with the unchanged prompt and Gemini 2.5
Pro settings. Keep all three results and failures without semantic retries.

Save prompts, bridges, parent-draw identifiers, source/config hashes and results
under `data/episode-pilot/student-continuity-v1/`. Verify the frozen parent's pins
before and after. Review the resulting three continuations for plausibility and
contradictions with the visible branch; a student may change their mind or revise
work. Whether a reply would occur may remain unknown. Do not treat the scripted
tutor response or the model's output as evidence of an actual run or grade.

The batch uses the standing model-run authorization in `CLAUDE.md`. It is a small
branch-consistency diagnostic, not a held-out fidelity or tutor-policy experiment.

## Using the helpers

This invented example runs offline from the project root after `uv sync`:

```sh
uv run python - <<'PY'
from src.eval.student_continuation import (
    Continuation, behavior_review, branch_episode, make_prompt,
)

episode = {'id': 'invented', 'context': [], 'turns': [
    {'id': 's1', 'role': 'student', 'phase': 'request',
     'text': 'crates = [3, 8]\nHow can I combine the counts?'},
    {'id': 't1', 'role': 'tutor', 'phase': 'response',
     'text': 'The sum function combines numeric items.'},
    {'id': 's2', 'role': 'student', 'phase': 'followup',
     'text': 'combined = 3 + 8'},
]}
reply = Continuation(decision='reply', text='combined = sum(crates)')
print(make_prompt(episode))  # excludes recorded s2 and metadata
review = behavior_review(episode, reply)  # two origins, blank judgments
branch = branch_episode(episode, reply, 'What value does combined hold?')
assert 'combined = 3 + 8' not in make_prompt(branch)
assert all(not c['judgments']['followup']['value'] for c in review['candidates'])
print(branch['provenance'])
PY
```

Store actual source episodes, prompts, outputs and review packets only under
ignored `data/`. These functions do not call a model or save judgments. A behavior
comparison requires an original episode; a synthetic branch has no recorded
comparator after divergence. Review its continuity against its visible branch.

## Implementation and execution checkpoint

The three helpers are implemented. Six invented-dialogue regressions cover input
isolation, branch identity independent of hidden future/metadata, strict reply
validation, origin/absence distinctions, and independent blank human judgments.
The complete suite passes 282 tests; the Node review-navigation check and the
offline example above also pass. The reusable prompt, response schema, local
extra-field policy and all eight original inputs match the completed interaction
experiment exactly. Its 319 pinned files are unchanged. Independent review found
no remaining implementation or publication issue.

Sixteen blank comparison packets pair the eight recorded contexts with all sixteen
retained generated draws in `data/episode-pilot/student-behavior-comparison-v1/packets.json`.
Identical draws retain separate provenance; they are not independent contexts.
No behavioral judgments have been assigned, and no accuracy or fidelity number
is calculated from the earlier plausibility feedback.

The three continuity requests are prepared as experiment
`3a08fcd427177f3818ae5413eda397d4596f9ecf1089a6c579110a4085521e6b`,
pinning 327 files. At the initial checkpoint they remained **unsent**. Automatic approval review rejected the
initial call and a retry supported by an exact payload audit. The audit confirms
that every historical turn comes from the already approved eight prefixes, with
zero new raw source dialogue; additions are retained generated replies and scripted
tutor bridges. The reviewer nevertheless required explicit approval of this exact
new branch payload because it contains sensitive derived student content.

`prepared-branches.md` presents the three branches, `disclosure.md` preserves every
exact model prompt, and `approval-request.json` binds the requested three calls to
their hashes in `data/episode-pilot/student-continuity-v1/`. Both denials and the
authorization evidence are saved there. At that checkpoint no model process had
started, no request had been sent, and no generated-output review existed. The
user's standing approval remains logged in `CLAUDE.md`.

Implementation is published in draft [PR #25](https://github.com/dstl-lab/chatsight-summer/pull/25),
on the separate `codex/episode-pilot` worktree branch. Commits separate the sequence
fix, accumulated pilot, documentation cleanup, review-save fix and continuation
helpers. Main remains unmerged while the PR is reviewed.

## Specific batch approval and completed run

Minchan subsequently answered "Yes" to sending these three prepared branch prompts
to Gemini 2.5 Pro. The exact response is saved in `approval-response.json`, bound
to the unchanged request, input hashes and experiment ID. The original denials
and blocked execution status are preserved. The unchanged runner is now authorized
for these three requests; this response makes no human plausibility or continuity
judgment about their outputs.

All three logical requests completed with structurally valid replies and zero
failed draws. All 327 experiment pins still match, including the 319 parent pins.
Request, case/draw, output and approval hashes were verified, and reopening the
saved cache offline changed no outputs. `completion-verification.json` records
these checks. All human plausibility, continuity and reply-occurrence judgments
were blank at generation completion. Structural validity does not establish behavioral plausibility.

Independent review found that the original Markdown presentation could collapse
code formatting. The frozen runner, outputs and original review are preserved.
A separate `build_verbatim_review.py` reuses the existing fence helper to produce
`review-verbatim.md` and `reviews-verbatim.json`; all 27 source/generated text
blocks are preserved verbatim. Earlier dialogue is expandable, while each retained
student reply, scripted tutor bridge and new generated reply is explicitly named.
The new presentation is hash-linked to the original and its renderer.

The prepared human task was reviewing cases 1, 5 and 7 for plausibility and any
contradiction with their visible branch. Reply occurrence may remain unknown.
Generated reports about successful tests or resolved errors are simulated dialogue,
not observations of notebook execution or grading. No further tuning or model
requests are part of this completed batch.

## Human feedback and next constraints

The three-case review is complete. Case 5 received an unqualified plausible
judgment. Cases 1 and 7 received qualified plausible judgments: Minchan doubts
that the student would relay a report that all tests passed in case 1, and questions
the backtick formatting in case 7. Preserve these as two different reservations,
not three unqualified acceptances. No explicit continuity or overall reply-occurrence
judgments were supplied; those fields remain null.

`human-review-response.json` preserves the exact response and binds the before/after
hashes of `reviews-verbatim.json`. The prior blank record and earlier verification
snapshots remain intact. `human-review-summary.json` is the current review summary;
the original `reviews.json` belongs to the earlier presentation and is unchanged.
`human-review-verification.json` confirms the mapping, reservations and unchanged
327 experiment pins. Original outputs and both presentations are preserved.

A bounded audit of only the shown historical prefixes supports the formatting
concern. Case 7 has zero backticks across four student turns, while all four tutor
turns use them. Across these three prefixes, all nine historical student turns
contain zero backticks. All three retained generated seeds also contain none.
This local contrast does not establish a cohort habit or the cause of the model's
formatting. The counts and scope are saved in `visible-history-audit.json`.

Case 1's visible student history includes a pasted failed-test report and no
success-only report. This distinguishes reporting a problem from announcing
completion; it does not establish that the student would send no further message.
Case 7's reservation concerns formatting, so it does not reject the acknowledgment
and subsequent request in that candidate. Do not turn the feedback into a blanket
ban on outcome reports or a forced no-reply decision.

The next generator comparison must assess communication choice separately from
surface wording: a plausible outcome need not be something a student would tell
the tutor. Formatting should be grounded in visible student contributions. Keep
the current prompt and reviewed outputs frozen; removing delimiters alone would
not address case 1. Treat these as development constraints to check across contexts,
not admitted labels, a calibrated reply policy, or a fidelity result. This review
needs no further answer from Minchan.

The subsequent [student-reporting audit](2026-09-11-student-reporting-audit.md)
checks these communication constraints against all 75 opportunities in the same
12 development conversations. It found no clear success-only update in 64
recorded follow-ups and preserves ambiguous problem reports. All 11 absent
follow-ups occur at exported conversation endings, which cannot calibrate a
no-reply policy. The audit adds no model calls or prompt changes.
