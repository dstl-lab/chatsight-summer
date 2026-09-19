# Recorded behavior audit using saved simulations

## Decision fixed before new coding

The corpus description is complete. The next question is whether the existing
simulator's saved next messages contain work/evidence more or less often than the
recorded next messages, with help requests measured alongside it. This is a new
secondary analysis of previously generated development outputs. The completed
length comparison, eight-case help/work study, prompts and their results remain
unchanged.

Reuse all 29 query conversations from the historical-response baseline and the
completed communication-candidate run: 29 recorded messages, 29 original-generator
replies, and 28 candidate replies. The candidate's one no-reply remains a separate
disposition. **Zero new model requests; 86 messages / 172 help/work flags; one blind
coding pass; one report.** No selection or replacement based on target content.

The earlier candidate repeats student messages already visible in the original
prompt. Its comparison tests presentation of existing context, not additional
retrieved evidence or a new grounding method. It is secondary here.

## Observation and sampling boundaries

Keep the saved order and exact 29 query IDs, conversation membership, prefixes,
references, prompts, model, outputs and dispositions. The generator was Gemini
2.5 Pro with provider-default temperature, one draw per condition per case. No
cached message is duplicated into an additional draw. Each conversation has equal
weight; separate conversation IDs do not establish independent students.

The target remains the **first recorded student message following the current
tutor response**. One case has a five-message consecutive student block; the other
28 have a single-message block. Do not concatenate that block, show its later
messages, or infer absence of work across the whole contribution from the first
message. Notebook actions between messages remain unknown.

The sample is narrow: 26 conversations start in February 2026, one each in March,
May and July. Ten prefixes have no earlier student message; 19 contain earlier
student context. Prefixes contain 2–10 turns / 924–14,274 characters (median 3,950).
Of 33 current-request messages, 30 modes are missing, two are tutor and one is
chatgpt. Twenty-five cases have incomplete prefix timestamps and missing target
timestamps. This is the existing query set, not a representative draw from the
252-conversation corpus, a student-separated sample, or an untouched holdout.

## Human measurement

Reuse the `help-work-v1` definitions and existing portable communication review UI.
Both flags can be yes. Code only what a candidate message communicates in the
visible context; do not rank it, assess plausibility, infer sentiment/ability, or
judge its correctness. Previously assigned labels and assistant suggestions are
not supplied.

- **Help request:** asks for explanation, solution/completion, correction, checking,
  confirmation or clarification; a supported terse request or posed exercise can
  count. Code/output alone does not automatically imply a request.
- **Work/evidence present:** substantive candidate code, answer, calculation,
  reasoning or diagnostic output, including copied/unchanged work. A bare problem,
  identifier, unfilled template, work plan or unsupported error assertion alone
  does not count.

Each flag is yes/no/unclear. Unclear requires a short note; unfinished stays null.
One reviewer supplies provisional coding, with their identity and self-reported
prior exposure recorded. No inter-rater reliability is established.

Show the full shared prefix once per case. Randomize the two or three candidate
messages once using a private recorded seed; use opaque independent IDs. Keep
condition/origin mappings outside the HTML, along with the absent-output slot.
Identical candidate text remains separate; do not selectively deduplicate replies.
Content may reveal origins despite concealment. Reading 29 prefixes is a real
burden beyond the 172 flag choices; existing browser-local autosave and draft
export permit pauses. Serve only the UI directory on localhost.

## Frozen analysis

**Primary: original-generator work-incidence gap.** For every case with determinate
work flags for both original and recorded messages, calculate
`original_work - recorded_work` (yes=1, no=0). Average equally over those cases and
report the signed gap in percentage points and the count difference. Positive
means more work-bearing messages in these original-generator outputs.

Always accompany the gap with its denominator and a 2×2 table: both have work,
neither has work, original-only work, recorded-only work. Also report the
disagreement fraction `(original_only + recorded_only) / N`. A zero incidence gap
can conceal disagreement; disagreement with one realized message does not show
that the other message was implausible.

Help-request incidence and disagreement are secondary and use their own
flag-complete denominator. Joint help/work category counts (neither, help-only,
work-only, both) use cases where both flags are determinate for both messages.
Report known reference category coverage even when a generated flag is unclear.

For the candidate comparison, separately for each flag, use only cases with known
reference, original and candidate flags and two generated replies. Report each
condition's incidence gap against the same references, plus candidate-minus-original
change in disagreement. A change in output frequency alone is not an improvement.
Joint-category comparisons likewise use the common complete subset.

Keep all 29 cases in coverage accounting. Report missing/unclear reference,
original and candidate flags separately; no-reply/error is not no/no. Unclear help
does not exclude a known work comparison. Zero denominators yield unavailable
scores. Missing form entries are unfinished and not silently imputed. No follow-up
adjudication batch, replacement cases or model-assigned flags.

One draw per condition cannot estimate context-specific action probabilities or
calibration. No Brier score, confidence interval, significance, universal realism
percentage, causal tutor effect, personality fidelity or learning claim is made.
Any finding remains a descriptive result on these saved messages.

## Completion and stopping

Freeze hashes of this protocol, scoring source, source artifacts, case coverage,
opaque mapping and reviewer payload before showing the review. Verify exact
cached-output/reference/prefix correspondence and absence of origins or labels in
the reviewer payload. Reuse the existing UI unchanged; preserve the old scorer
that is bound to its eight-case/four-draw study.

Stop for the single human coding pass. On return, validate the packet-bound form,
score once, and publish one report, including unresolved labels or limited target
variation. Keep the current simulator. A new grounding candidate requires a
specific discrepancy and a separate bounded decision after this report; no
automatic tuning, rerolls or repeated plausibility checks.

## Preparation status

The 29-case/86-message packet is prepared in ignored
`data/episode-pilot/recorded-behavior-audit-v1/`. Independent inspection reproduced
every prefix, first recorded message, cached output, missing-output disposition,
opaque mapping and within-case order. The HTML is exactly the existing template
plus the escaped strict packet; only `ui/index.html` belongs in the reviewer handoff.
No labels or behavioral results exist yet.

An invented-data browser check exercised navigation on a 29-case page, three- and
two-message layouts, browser-local progress across reload, and incomplete-form
rejection. No real reviewer details or judgments were entered. The new scorer's
authored tests cover incidence cancellation, flag-specific uncertainty, common
paired subsets, missing outputs, strict form/mapping intake and create-only output.

Verify the frozen preparation, then serve only its UI directory:

```sh
PYTHONPATH=. python data/episode-pilot/recorded-behavior-audit-v1/prepare.py verify
python -m http.server 8423 --bind 127.0.0.1 \
  --directory data/episode-pilot/recorded-behavior-audit-v1/ui
```

Open http://127.0.0.1:8423/ or the portable `ui/index.html`. Enter reviewer details,
answer both flags for each message, and use Finish review → Download answers.
Retain the returned JSON byte-for-byte under a new path in `received/` before
running the scorer. Drafts may be paused; null entries remain unfinished.

```sh
python -m src.eval.cached_communication_scoring \
  data/episode-pilot/recorded-behavior-audit-v1/review-packet.json \
  data/episode-pilot/recorded-behavior-audit-v1/private-mapping.json \
  path/to/completed-review.json path/to/new-report.json
```

The scorer remains separate from the frozen eight-case scorer. This preparation
stops at the human coding input; the next artifact is one result report, including
any unclear labels. The original generator remains unchanged.
