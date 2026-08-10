# March–July sequence-grounded run — first varying-context results

Date: 2026-08-10. Snapshot `20260810-937c9f6ba4b5-4ae154` (49
conversations drawn uniformly from the 8,028 in the autograder-covered
window 2026-03-04..07-31, seed 0; composed 12-label schema on profile
`a5241abd5c25`; 170 label rows). Branch `march-july-run` adds
`--since/--until` and `--conv-sample-seed` plus a chunked, retrying
autograder fetch.

## The sampling lesson (cost one wasted run)

`ORDER BY chatlog_id LIMIT 60` inside the window returned only early-March
conversations, which came back 98% ask-first. Diagnosis showed that was
*real but unrepresentative*: those students' 9,266 autograder runs on the
same notebooks all postdate their chats (start-of-assignment help-seeking;
checks come later). Windowed fetches must sample uniformly
(`--conv-sample-seed`), not take the opening slice. The first-slice
snapshot was deleted.

## Message-level sequence distribution (n = 170)

| | share |
|---|---|
| pass-then-ask | 93 (55%) |
| fail-then-ask | 43 (25%) |
| ask-first | 34 (20%) |

Message-level shares closely mirror the pilot's conversation-level split
(56/17/27) — the two granularities agree, which neither was forced to do.

- **Question-level narrowing works at scale**: 90/170 messages carry a
  question ref; 75/170 (44%) resolve to question-level granularity, so
  "this question's tests were passing" is no longer notebook-confounded
  for nearly half the corpus.
- **error_verified** true on 66/170 (39%) — mechanically confirmed error
  states behind pastes-error-style judgments.
- Mode: 126 tutor / 44 chatgpt (26% — matches the corpus-wide ~21%).
  No in-tool defection events in this sample.

## First live outcome-anchor validation — anchors HOLD

```
Debugging Request:        24/57 positives in fail-then-ask (42% vs baseline 25%)
Direct Solution Request:   5/15 positives in fail-then-ask (33% vs baseline 25%)
```

Both labels concentrate above baseline in fail-then-ask conversations, as
their semantics predict. First empirical evidence that the LLM labels and
the mechanical sequence agree in the aggregate — the anchor instrument
works and nothing is flagged.

## Instrument catches on this run

- Distinctness flags one overlapping pair: Code Implementation Query ×
  step-by-step-prompt (J=0.46, co-fire 33) — a merge/tighten candidate
  for the next tweak pass (the pair straddles the instructor layer and
  the intent layer).
- Coverage: 10/170 (6%) abstentions.

## Honest limits

- One 60-conversation seed; distribution numbers carry no CIs yet.
- Label quality here is drafted, not audited (invariant 8) — a blind
  audit on this snapshot is the natural next Phase 0 exercise, and would
  double as the first mode-split reliability measurement.
- The 45m/20m windows remain unvalidated choices; the bracket-sweep found
  they miss chat-then-check-later workflows entirely (that is what
  ask-first means under these windows: no *prior* run — not "never
  checked").

## Blind audit results (minchan, 48 messages, 96 judgments, 2026-08-10)

First reliability measurement of sequence-grounded labels (single
annotator; per-label support is tiny — treat as direction, not verdict):

- **Strong**: Seeking Validation P=1.00/R=1.00 (κ=1.0), Alternative
  Method Query 1.00, outcome-focused-query and Debugging Request 0.75.
- **Zero-support**: Code Implementation Query, concept-misapplication,
  Conceptual Clarification, step-by-step-prompt — the human confirmed NO
  model-positive for any of them (κ≈0, "keep human-only" flag).
- **Human derived no-label-fits: 29/48 (60%)** vs model abstention 6% —
  a large under/over-labeling gap, direction unresolved.
- **First mode-split reliability**: tutor-mode agreement 74% (62/84) vs
  chatgpt-mode 50% (6/12) — chatgpt-mode messages are measurably harder
  to label reliably; mode-split reporting exists for exactly this.
- Human-side outcome anchor is weaker than the model's (Debugging 1/3 in
  fail-then-ask).

Annotator's own diagnosis (recorded verbatim intent): **label criteria
are too verbose to hold in mind while judging** — the four zero-support
labels carry the longest criteria (generated intent-layer + drafted
conceptual labels). Confounded hypothesis: verbose criteria depress human
yes-rates (comprehension fatigue) AND/OR those labels genuinely
over-fire (step-by-step-prompt was already distinctness-flagged, J=0.46).
A criteria-brevity pass + re-audit separates the two.
