# Does earlier dialogue help identify the recorded continuation?

**TL;DR:** Run one automatic choice diagnostic on existing conversations: Gemini
selects the actual next student message among four recorded alternatives, with
and without earlier dialogue. Fix 19 cases and 38 requests before dispatch; no
manual labels, repeated samples or production changes. This tests recognition
of a logged continuation, not the realism of generated students.

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
