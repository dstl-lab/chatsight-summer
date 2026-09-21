# Does earlier dialogue help identify the recorded continuation?

**TL;DR:** Closed: Gemini identified the recorded continuation in **8/16 complete
pairs (50%) with history and 8/16 (50%) without it**. Word overlap scored 7/16.
This fixed run found no accuracy benefit from earlier dialogue. Five of the 38
requests have no choice because of a schema failure described below. No manual
labels, replacement cases or generator changes; recognition is not generation fidelity.

## Result and decision

Both conditions are scored on the same 16 complete pairs from the original 19
eligible conversations. All complete pairs used the same repaired wire schema.

| Method | Correct / paired cases | Accuracy |
| --- | ---: | ---: |
| Gemini with earlier dialogue | 8 / 16 | 50.0% |
| Gemini with current exchange only | 8 / 16 | 50.0% |
| Current-exchange word overlap | 7 / 16 | 43.8% |
| Shortest option | 4 / 16 | 25.0% |
| Longest option | 6 / 16 | 37.5% |
| Uniform random choice | Expected, not sampled | 25.0% |

The primary difference is **0 percentage points**. There are zero history-only
wins, zero current-only wins, and 16 accuracy ties: eight both-correct and eight
both-wrong. The chosen option itself agrees in 15/16 pairs; in the other pair,
both conditions choose different incorrect options. Neither accuracy ties nor
this choice agreement establish that the model ignored history internally.

Coverage is 16/19 history choices and 17/19 current choices: 33 valid choices,
four provider failures, and one interrupted request. Original cases 1 and 3 lack
both choices; case 4 lacks history. Its successful current-only choice does not
enter the paired accuracy. Under every possible completion of the missing choices,
the all-19 history-minus-current difference ranges from **−15.8 to +10.5 percentage
points**. These are missing-outcome bounds, not a confidence interval. The lexical,
shortest and longest baselines on all 19 cases are 7/19, 7/19 and 6/19; do not
compare those denominators directly with the paired model scores.

The amended dispatch completed all 33 untouched jobs without a retry, with zero
resends. Together with the original interrupted attempt, it used at most 53 adapter
attempts, below the approved 152 ceiling. Raw and combined receipts remain private.
The code verifies the frozen source hashes, exact request order, outcomes, retry
records and reproducible scoring without making another model call.
Independent recomputation from the raw receipts and original source references
confirmed every metric and baseline, including option construction, coverage,
missing-choice bounds and the attempt budget. Its receipt is saved privately as
`independent-result-check.json`.

**Decision: close this comparison and retain the generator.** This supplies a
bounded automatic measurement without another instructor labeling queue, but no
observed benefit of history on this development task. Both model conditions score
only one more correct case than word overlap. That is insufficient evidence for
an improved simulator, a useful model advantage over that baseline, or removing
history from student generation. Do not reroll the failed cases, tune options,
resume manual labeling or initiate another comparison to seek a positive result.
Any future fidelity claim still needs evidence about generated behavior; this
recognition result cannot supply it. The five missing choices, small exposed set,
one draw per condition and potentially plausible alternatives limit the conclusion.

## Why this is the next step

The [six-case instructor pass](2026-09-21-joint-fidelity-check.md) produced useful
qualitative feedback but no validated binary behavior labels. Reopening that
queue would repeat the same measurement problem. Recorded message identity gives
this narrower task an automatic answer key; other options may also be plausible.

The current Gemini adapter generates structured responses. The official API's
[response log probabilities](https://ai.google.dev/api/generate-content) describe
generated tokens; this route does not score an arbitrary supplied target sequence.
We therefore do not call output log probabilities recorded-message likelihoods.
[Response selection research](https://aclanthology.org/2020.acl-main.55/) motivates
the task while emphasizing that alternative construction matters. Its validation
does not validate our automatically retrieved alternatives or simulator.

## Frozen comparison

- Reuse `historical-response-baseline-v1`: 1,179 training examples from 156 library
  conversations and 29 query/reference pairs, preserving its conversation split
  and any available learner-overlap checks. Unknown learner identities prevent a
  claim of learner separation. These development cases have prior exposure.
- Before constructing options, include only queries with an earlier student turn
  before the current student request and tutor response: 19 included, 10 excluded.
  This population is conversations with recorded continuation and visible history,
  not randomly sampled students, silence, or future courses.
- Parse the current exchange using the existing chat initialization helper. Fit
  TF-IDF on training current exchanges only, using word unigrams and bigrams and
  token pattern `(?u)\b\w+\b`. Rank training exchanges by cosine similarity to the
  query's current exchange, breaking ties by source example ID. Earlier dialogue
  does not affect the alternative construction in either condition.
- Choose three next messages from three distinct training conversations. Skip
  blanks and texts duplicating the recorded answer or another option after NFKC,
  whitespace normalization and case folding. If fewer than three remain, exclude
  explicitly; do not relax the rule or curate alternatives manually.
- Hash-rank eligible query IDs with seed `recorded-continuation-selection-v1` and
  assign the answer position by rank modulo four: 5/5/5/4 for 19 cases. Order the
  other options by their seeded source-ID hashes. Freeze these identical options
  and positions for both conditions.
- **History:** earlier dialogue plus the current exchange. **Current:** the same
  exchange, with empty earlier context. Both see options A–D and choose one using
  a strict JSON choice schema; no rationale or self-reported probability.
  Source IDs, retrieval scores, origins and the answer key are private metadata,
  absent from model prompts. The actual continuation is intentionally one option;
  it is not supplied as the answer or fed into later requests.
- Gemini 2.5 Pro, existing provider defaults, one request per condition and case,
  alternating condition order across cases. Maximum 38 logical requests and 152
  adapter attempts under the existing four-attempt retry limit. SDK-level HTTP
  retries are not independently instrumented. Errors retain their fixed slot.

## Measures and stopping rule

Primary result: history accuracy minus current accuracy on complete pairs. Report
the number of complete pairs out of 19, each arm's coverage, all request outcomes,
paired wins/losses/ties, and best/worst bounds across all 19 if choices are missing.
No complete pairs means the primary result is unavailable; errors are not choices.

Report three simple baselines on all eligible cases and the same complete pairs:
current-exchange-to-option-text TF-IDF cosine, shortest option and longest option.
Ties choose the earliest visible letter. Uniform random choice has 25% expected
accuracy. Source-prefix similarity is never a scoring baseline because it would
reveal which option belongs to the current conversation. Inspect option lengths
as a possible artifact without changing the frozen cases.

Stop after this one run and report, regardless of direction. No rerolls, new human
coding, alternative replacements, prompt tuning or automatic generator adoption.
The effect is descriptive for this fixed set and provider sampling; one response
per arm does not separate a small difference from sampling variability. A positive
result supports only that history helped this identification task. Topic overlap,
question numbers, code and answer length could explain success without modeling
student communication habits. A negative or tied result also closes the study.
Neither direction measures free-generation fidelity, causal policy effects,
learning, hidden notebook behavior, stable personalities or calibrated probabilities.

## Reproduction and authorization

`src/eval/continuation_selection.py` contains offline preparation, prompt creation
and scoring; authored tests need no private data or provider key. The ignored
`data/episode-pilot/recorded-continuation-selection-v1` folder holds the private
runner, exact prompts, source mappings, answer key, immutable protocol copy,
hash manifest, authorization record, request receipts and aggregate result.
Preparation verifies the original baseline receipt and source pins. Dispatch
verifies frozen artifacts and claims a create-only result ledger before any call;
an existing ledger cannot be resent. Replay and scoring make no model calls.

Minchan's current “Let's do it” approves the proposed automatic comparison. The
existing standing grant is “Yes, you always have the approval. Make sure to log
this.” Record that basis accurately; do not claim a separate exact-payload reply.
Only the frozen prompts go to Gemini, including historical dialogue and candidate
recorded student messages, which may contain identifying details. Private student
text and provider credentials remain outside Git. Preserve the current simulator,
old studies, paused bulk audit and deferred workspace redesign.

## Preparation status (September 21)

The fixed preparation reproduced: 19 included, 10 excluded solely for lacking
earlier student messages, balanced answer positions 5/5/5/4, and 38 exact prompts.
The lexical, shortest and longest baselines select the recorded answer in 7/19,
7/19 and 6/19 cases, respectively. Median option lengths are 39 characters for
recorded targets and 33 for library alternatives. These are offline properties of
the fixed task, not Gemini results or evidence that history helps.

Independent reviews found no remaining blocking issues in the method or runner.
The runner's create-only ledger comes before credential loading; a separate
read-only preflight confirmed a key is present without constructing a provider.
An authored dispatch check verified all 38 slots, a four-attempt failure, retained
error scoring, and refusal to resend completed or interrupted runs. The full suite
passed 422 tests with two optional container skips and one upstream deprecation
warning; both Marimo apps and the Node navigation check passed.

Automatic approval review initially rejected dispatch, requiring approval specific
to the private dialogue payload and Gemini destination despite the standing grant.
Minchan then replied “Approved.” The supplementary `payload-approval.json` binds
that authorization to the frozen experiment, inputs and exact `disclosure.md`.
PR #42 merged the offline comparison and protocol as `b179876`.

## Transport amendment before the first valid choice

The initial dispatch encountered a deterministic HTTP 400 schema rejection:
the installed SDK serialized `additionalProperties: false` as the unsupported
`responseSchema.additional_properties`. Four requests exhausted their retries;
the fifth was interrupted during retry backoff. None returned a valid choice.
The original ledger and source-pinned runner remain unchanged and cannot resend.

An offline check through the installed SDK and a mock HTTP transport reproduced
the schema defect. A private `WireChoice` subclass removes only that wire field;
the schema title, allowed choices, required field and all request text remain
identical. Strict local validation still rejects extra fields and invalid choices.
No shared provider code, dependencies or frozen selection module changed.

Before any valid choice, `transport-amendment.json` fixed completion of only the
33 never-started jobs with this compatible schema. The original four failures
remain errors, and the fifth pending receipt is represented as an interrupted
error in the combined report, with its raw receipt preserved. No started job is
resent. Original calls consume at most 20 adapter attempts; the remaining 33 jobs
allow at most 132, preserving the approved overall ceiling of 152. A repeated
schema rejection halts this amended dispatch instead of initiating another repair.

The original 19 cases, 38 job identities, option texts/order, prompts, answer key,
baselines and scoring stay fixed. The final primary comparison can contain at most
16 complete pairs. Report coverage and all-19 missing-choice bounds alongside it;
the schema failure makes the complete subset less representative of the fixed set.
Authored dispatch checks and independent review verified the 33-job scope, retained
five failures, exact ordering, strict validation and refusal to resend. No real
responses informed the repair, and no manual labels or replacement cases were added.
