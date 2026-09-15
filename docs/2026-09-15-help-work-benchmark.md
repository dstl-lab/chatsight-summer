# One fixed help/work comparison

The fixed benchmark is complete: 64 requests, one returned coding pass, one report.
See [results and stopping decision](2026-09-15-help-work-results.md). The frozen
protocol and historical preparation/generation record remain below.

## Decision and scope

Minchan authorized a finite recorded-behavior comparison and selected
“Help-seeking versus work submission, with one fixed blind coding pass.” This
supersedes the pending-benchmark status in the earlier continuity memo. It does
not resume the incomplete six-case `history-ablation-v1` experiment. That work,
all older prompts, labels, reviews and traces remain frozen.

The question is whether retaining earlier dialogue changes how closely the
existing chat continuation generator matches two observable features of the
next recorded message. This measures the older `student_continuation` interface,
not the current notebook action policy. Chat records cannot validate quiet edits,
execution sequences, chosen stops or learning. No end-product design is included.

## Frozen protocol

- Eight conversation cases, four independent draws for each of two conditions:
  **64 logical requests**, at most four adapter attempts each. Gemini 2.5 Pro,
  existing continuation prompt/schema, provider-default temperature. Record retry
  events. No generated draw becomes another draw's input.
- Grounded receives at most six earlier dialogue turns plus the current student
  request and tutor response. Current-exchange receives the identical payload
  with `context=[]`. Both explicitly mark current work and execution unknown.
  Remove turn IDs tied to original indices. Neither receives future messages,
  labels, student identities, snapshot metadata or reference judgments.
- Earlier context contains tutor/task information as well as student language.
  A difference cannot be attributed solely to style, personality or student memory.
- Use the eight canonical exports already inventoried. Deduplicate identical
  dialogue by conversation; prefer the lexicographically newest snapshot ID for
  metadata, reject dialogue conflicts. Exclude all 47 conversations in the known
  continuation exposure ledger. No local student identity exists for separation.
- An eligible window has a current request, tutor response, recorded subsequent
  student contribution, at least one earlier student turn, at most 6,000 visible
  characters, and complete visible/follow-up timestamps. The reference is the
  first subsequent student message, including a blank message, not the whole
  adjacent student-message block. Selection never reads its semantic content.
- Rank eligible windows by SHA-256 of the raw UTF-8 string
  `help-work-benchmark-v1-20260915:<episode_id>`, tie-break by episode ID; take the
  first window for each distinct conversation until eight. Preserve any shortfall
  without relaxing eligibility. The metadata audit found 29 windows/14 conversations.
- Order requests by draw 1–4 then case 1–8, alternating condition order by
  `(draw + case) % 2`. Freeze candidate IDs/order with a separate private random
  seed before generation; do not reorder or select based on outputs.

All source/prompt/script hashes, selection, full exact payload disclosure,
authorization and request order are saved before dispatch under ignored
`data/episode-pilot/help-work-benchmark-v1/`. Existing standing Gemini approval
applies. Actual dispatch status must be recorded separately from preparation.

## One coding pass

Each message receives two independent yes/no/unclear judgments. Both can be yes.
No priority hierarchy suppresses an attached help request when work is present.

| Flag | Yes | No |
|---|---|---|
| Help request | Requests explanation, solution/completion, correction, checking, confirmation or clarification. Includes supported terse requests and a pasted exercise posed to the tutor. | No observable request; code/output alone does not automatically imply one. |
| Work/evidence present | Substantive candidate code, an answer, calculation, reasoning or actual diagnostic output. Copied or unchanged work counts. | Only a problem statement, bare identifier, unfilled template posed as a question, work plan or assertion of an error without substantive work/output. |

Read with the visible prefix. Do not judge correctness, originality, revision,
execution, ability, sentiment or plausibility. Diagnostic output is submitted
evidence; it does not authenticate a notebook execution. “Unclear” means the
available text cannot resolve that flag and requires a short note. Blank means
unfinished, not no or unclear.

One portable page shows each shared prefix once and up to nine messages below it:
eight generated draws plus the recorded reference. Origins, conditions, mapping,
old judgments and assistant suggestions are absent from the reviewer payload.
An opaque-ID mapping stays private outside the HTML. Reviewers see full context
for both conditions; the intervention varies generator inputs, not coding inputs.
Record reviewer identity and self-reported previous case exposure. Context/content
may reveal origins; concealment does not guarantee successful blinding. One
reviewer supplies provisional measurement without inter-rater reliability.

At most 72 messages / 144 flag judgments. Generated no-reply/error slots have no
message to code; retain them separately without inventing flags. Recorded blank
messages remain in the review. Export partial drafts or one complete final form.
There is no subsequent forced adjudication or plausibility-review batch.

## Score and stopping rule

For each condition and flag, `p = yes_count / 4`; binary Brier is `(p-y)^2`, where
`y` is the recorded message's flag. The primary case score is the mean of its two
flag scores (range 0–1). Average equally over eligible complete cases and report
the paired difference **grounded minus current-exchange**; negative favors grounded
for this descriptive endpoint. Report each flag separately and every case's
contribution. The comparison condition is the baseline; no artificial training
labels or unrelated training-frequency model are introduced.

A case enters the primary comparison only if both reference flags and both flags
of all eight generated reply draws are yes/no. Preserve all 64 scheduled slots,
every error/no-reply/unclear and each exclusion reason. Never count no-reply as
no/no or silently estimate frequencies using fewer draws. If no case qualifies,
report no primary score. No replacement, reroll or best-output selection.

Four-draw frequencies are coarse and noisy. Finite-ensemble Brier is descriptive,
not a precise estimate of the underlying generator distribution; equal draw
budgets do not eliminate sampling bias or uncertainty. Flag matching can reward
contextually wrong messages. These eight conversations are new only to known
continuation experiments: the snapshots have prior audit exposure, the prompt
was developed on the same course, and students cannot be separated. This is an
exploratory comparison, not an untouched holdout, population accuracy, calibrated
persona model or evidence of transfer across courses.

**Stop after the frozen requests, one coding pass and one fixed report, even if
inconclusive.** Retain production behavior. No significance, reliability,
practical-improvement threshold or automatic model adoption claim. Additional
data, tuning or another batch requires a new research decision.

## Implementation plan

The existing extraction, prompt, schema, provider and atomic JSON writer remain
unchanged. No dependencies or new simulator abstractions.

- [x] Prepare the private metadata selection, identical-condition canary check,
  future-text exclusion check, source pins, exact disclosure and create-only run
  ledger using existing `episodes`, `student_continuation` and `llm` helpers.
- [x] Add `src/eval/communication_review.py` and `.html`: strict blind packet,
  grouped messages, two native radio groups, packet-bound autosave and export.
  Verify with one invented regression and a browser exercise without real ratings.
- [x] Add `src/eval/communication_scoring.py`: validate the private mapping and
  completed human form; compute the fixed paired score/coverage. One invented
  numerical regression also checks ambiguous/missing slots and mapping rejection.
- [x] Freeze and independently audit selection/input/scoring boundaries.
- [x] Dispatch the fixed 64 slots once if permitted, preserving failures and interruptions.
- [x] Build and verify the concealed-origin page, commit code/memo, update draft
  PR #25 without merging, and stop for the single human coding pass.
- [x] After intake, run the frozen scorer and publish the limited report without
  automatic tuning or another batch.

## Prepared result and dispatch boundary

Preparation completed with 38 pinned artifacts. Independent metadata/prompt audit
reproduced 252 distinct conversations, 47 known exclusions, 29 eligible windows
in 14 conversations, eight selected distinct conversations and 64 fixed requests.
The future-text/private-metadata canary leaves selection and prompts unchanged.
An invented pipeline check covers reply/error/no-reply retention, retry receipts,
no resending an existing run, blind page construction and scorer intake. Twelve
related tests passed; the new UI also passed an invented browser exercise.

Automatic approval review rejected the exact dispatch command **before process
creation**. It considered these private student–tutor excerpts sensitive and
required specific authorization to send them to Gemini, beyond the logged standing
project approval. That rejected attempt sent no requests and created no outputs.
The rejection is preserved in `send-blocked.json`; the exact
16 distinct prompts (each to be sent four times) are in `disclosure.md`. No indirect
execution or alternate destination was attempted. Minchan subsequently answered
Yes to that specific payload and destination. `approval-response.json` preserves
the answer and binds all four disclosed/preparation/rejection artifacts. The same
frozen command then ran successfully; approval predates its first request.

## Completed generation and review handoff

The fixed run completed on 2026-09-15, 02:16:48–02:33:16 UTC. All 64 logical
requests returned valid replies. One adapter retry produced 65 adapter attempts;
physical HTTP attempts below the SDK were not instrumented. No final errors or
no-reply outputs occurred in either condition (32 replies each). This says nothing
about the quality or labels of those messages. No outputs were replaced, fed into
subsequent inputs or used to change prompts.

The concealed-origin page contains 72 messages / 144 independent flag judgments:
nine messages under each of eight shared prefixes. The exact 34 prefix turns and
all candidate texts were independently matched to source without assigning labels.
All 38 preparation, four approval, three review and 12 completion-artifact hashes
verify; these groups overlap and are not a count of distinct files. Exact offline
replay passes. The HTML equals the frozen template plus the strict blind packet;
its payload has no origin/condition/reference mapping or preselected judgments.

The page is served locally at http://127.0.0.1:8422/ and was opened to its blank
introduction. Browser inspection did not enter reviewer details or judgments.
Only `ui/` is served. The portable `ui/index.html` also works independently; the
private origin mapping and run report must stay outside the reviewer handoff.
Earlier UI behavior checks used invented data and a separate packet identity.

One reviewer completes the two yes/no/unclear flags for each message; both yes is
valid and unclear needs a note. Copy or download the final JSON and return it for
intake. Browser-local drafts allow pauses but do not sync between computers.
At this generation-stage handoff, no human form had been returned and no behavior
score existed. The subsequent completed intake and results are recorded in the
[results report](2026-09-15-help-work-results.md).
`run-summary.json`, `RUN_REPORT.md` and `completion-verification.json` preserve
this stage. `report.py` verifies the approved completed run and produces those
create-only artifacts; it does not assign labels. This generation stage stopped
for the single human input, which has since been received and scored.

Reproducible commands from the isolated worktree:

```sh
PYTHONPATH=. ../main/.venv/bin/python data/episode-pilot/help-work-benchmark-v1/check.py
PYTHONPATH=. ../main/.venv/bin/python data/episode-pilot/help-work-benchmark-v1/benchmark.py verify
PYTHONPATH=. ../main/.venv/bin/python -m pytest tests/test_communication_review.py tests/test_communication_scoring.py tests/test_coding_review.py tests/test_behavior_scoring.py tests/test_student_continuation.py -q
```

The completed command was `benchmark.py verify --send`; its exclusive results-file
claim prevents resubmission. Do not rerun it or repackage the finished review.
`benchmark.py replay` verifies the completed receipts offline. Serve/share only
`ui/index.html`, not the directory containing the private mapping or source
artifacts. After the single completed human form is received, the scoring command is:

```sh
PYTHONPATH=. ../main/.venv/bin/python -m src.eval.communication_scoring \
  data/episode-pilot/help-work-benchmark-v1/review-packet.json \
  data/episode-pilot/help-work-benchmark-v1/private-mapping.json \
  path/to/completed-human-form.json path/to/new-report.json
```

Preserve the received form separately and verify its packet identity. Do not fill
missing answers with model labels. The scorer rejects incomplete/mismatched forms
and refuses to overwrite a report. Only public methods, UI, scorer and invented
checks enter the draft PR; private source/output/authorization data stays ignored.
