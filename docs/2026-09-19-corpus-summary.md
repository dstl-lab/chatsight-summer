# Existing-data corpus summary

## Scope fixed before analysis

This is step 1 of the simulation-fidelity research question: establish what the
existing data describes before selecting another behavioral comparison. It is an
offline descriptive audit, with no model calls, new labels, or reviewer task.

Reuse the eight hash-verified canonical exports and the completed historical
response baseline's split. Inventory all export memberships and conversation
identities. Restrict fresh message statistics to the unique conversation IDs
already present in `inputs.json`'s training library; do not resplit the corpus or
read query references. Preserve the baseline's sorted-snapshot, last-record
metadata selection and reject conflicting dialogue versions.

Report raw student-message character lengths, conversation sizes, literal
formatting, earlier-context availability, source/date coverage, and missing
timestamps/modes. Show message-weighted and equally conversation-weighted
statistics. Literal formatting is descriptive, not semantic coding. Conversation
IDs and student text remain in ignored local data; commit aggregate results and
the reproducible analysis only.

The stopping point is one verified corpus report. These previously examined,
selected exports are not a representative sample of all DSC 10 students or an
untouched evaluation set. Conversation identity is not learner identity; missing
follow-up is not observed abandonment. This step changes no simulator behavior.

## Results

The existing data supports a conversation-level, descriptive study of recorded AI
use. It does not yet support sampling verified individual students. Brief messages
are common, longer messages remain substantial, and long conversations contribute
disproportionately to a pooled message sample.

### What is in the saved corpus?

| Quantity | Count |
| --- | ---: |
| Canonical exports | 8 |
| Conversation records across exports | 455 |
| Distinct conversation IDs after deduplication | 252 |
| Repeated export memberships removed | 203 |
| Student messages in the deduplicated corpus | 1,786 |
| Tutor messages in the deduplicated corpus | 1,736 |
| Conversations with usable recorded-follow-up windows | 185 |
| Conversations without a usable follow-up window | 67 |

Six conversations have metadata variants across exports; none has a conflicting
role/text dialogue. As in the closed baseline, the last record in snapshot-ID sort
order supplies metadata. This makes the selection reproducible without inventing
a merge of partially populated versions.

| Export date / snapshot suffix | Records | Turns | New conversation IDs in sorted order |
| --- | ---: | ---: | ---: |
| Aug 3 / `73419b` | 151 | 2,745 | 151 |
| Aug 4 / `005c52` | 77 | 1,597 | 0 |
| Aug 6 / `2aa40b` | 19 | 586 | 0 |
| Aug 7 / `dda99f` | 6 | 152 | 0 |
| Aug 10 / `50215f` | 49 | 317 | 49 |
| Aug 10 / `4ae154` | 49 | 317 | 0 |
| Aug 10 / `927c22` | 52 | 460 | 52 |
| Aug 11 / `7bc759` | 52 | 460 | 0 |

New-ID counts depend on the declared ordering; exports are overlapping analysis
snapshots, not eight independent cohorts. Export dates are in 2026 and are not
the dates on which students interacted.

### Which records received fresh message analysis?

Only the **156 conversations already contributing 1,179 windows to the development
library** were profiled: 1,400 student messages and 1,378 tutor messages. The fixed
assignment had 212 library and 40 query conversations, but only 156 and 29,
respectively, supplied usable follow-up windows. Selecting all 212 assigned library
conversations would silently change the descriptive population.

The 29 query conversations retain their original assignment and their references
were not parsed for this analysis. They already supported a completed communication
comparison, so they are not untouched evaluation data. All eight source exports
had earlier analysis exposure. No new split was created.

### Message length and formatting

Message weighting samples a student message uniformly. Equal-conversation weighting
samples a development conversation uniformly, then a student message within it.
Neither weighting establishes equal probability over individual students.

| Measurement | Message weighted | Equal conversation weight |
| --- | ---: | ---: |
| Mean characters | 222.4 | 169.5 |
| Median characters | 34 | 33 |
| 75th percentile characters | 139 | 99 |
| 90th percentile characters | 496 | 340 |
| 95th percentile characters | 774 | 591 |
| At most 40 characters | 54.7% | 57.2% |
| 41–300 characters | 29.3% | 31.3% |
| More than 300 characters | 16.0% | 11.5% |
| Contains a newline | 23.8% | 18.9% |
| Contains a backtick | 1.4% | 0.7% |
| Contains a non-ASCII character | 5.7% | 4.7% |

Lengths count raw Unicode characters, including whitespace. Quantiles use the
inverse empirical cumulative distribution (the first value reaching the specified
weight), not interpolated percentiles. There are no blank-after-stripping student
messages in this subset. Non-ASCII presence is not language identification; newlines
and backticks do not establish code, copied work, or a student's intent.

The median conversation has **5 student messages** (25th percentile 3; 75th 11;
range 2–52). The largest 16 conversations contribute **506 of 1,400 messages
(36.1%)**. The lower conversation-weighted upper percentiles show why pooling every
message gives a different picture of typical communication.

These are all student messages within eligible development conversations. The
earlier baseline's 35-character training median described only the first recorded
follow-up messages, so it need not equal this report's 34-character median.

### Date, course, and observation coverage

| Conversation start month | All 252 conversations | Development 156 |
| --- | ---: | ---: |
| February 2026 | 151 | 99 |
| March 2026 | 9 | 6 |
| April 2026 | 21 | 11 |
| May 2026 | 42 | 25 |
| June 2026 | 14 | 7 |
| July 2026 | 15 | 8 |

All conversation starts are present: February 9–July 29 in the full corpus and
February 9–July 28 in the development subset, using the recorded calendar date.
About 60% of the full corpus starts in February. These are counts of the selected
exports, not enrollment or population activity estimates. The manifests do not
preserve the original sampling seeds/date filters, so inclusion probabilities
cannot be reconstructed from these exports alone.

In the development subset:

- **983/1,400 student timestamps are missing (70.2%).** Across both roles,
  1,969/2,778 timestamps are missing. Conversation start dates cannot substitute
  for per-message timing; complete pacing or session-gap estimates are unsupported.
- **1,047/1,400 student mode values are missing (74.8%).** The observed values are
  289 `tutor` and 64 `chatgpt`. Missing mode is retained as unknown. This subset
  is not verified tutor-only interaction.
- Every conversation has notebook-name metadata. This does not provide a verified
  task boundary, complete assignment, cell state, or intermediate execution history.
- Six of eight manifests include an authored DSC 10 course profile; two omit it.
  That configuration is not independently verified per-record course/version
  membership. No cross-course representativeness or transfer is established.

The development conversations yield **1,319 tutor-response windows** using the
existing extractor. Of these, 1,179 have a recorded follow-up and 140 do not.
There is at least one earlier student message in the six-turn context for
1,163 windows (88.2%); 156 have none. This describes availability in the extractor,
not how much persistent student history exists or reaches every generator.

**42 of the 1,179 follow-up windows contain multiple consecutive student messages.**
The old baseline targets only the first of those messages. A future benchmark must
explicitly choose first-message versus whole-contribution scoring; this audit
does not change that completed baseline. The 140 absent follow-ups do not establish
silence, abandonment, or successful completion.

### Implications for the next study

1. Use a conversation as the presently established sampling unit. The chat
   `Conversation` schema has no learner identifier, and `student_index` counts
   positions within a conversation. Do not describe 252 conversations as 252 people.
   The separate saved notebook-pair audit counted learner identities internally,
   but its exported metadata provides no usable learner mapping for this corpus.
2. Preserve both brief messages and the long-message tail. A universal brevity cap
   would discard observed variation; literal formatting cannot replace help/work
   coding or contextual appropriateness.
3. Sample at the conversation level and report mode/date/missingness coverage.
   Selecting more windows from long conversations changes the estimand, even when
   it increases the apparent sample size.
4. Keep this as development evidence. These exports cannot by themselves establish
   course-wide prevalence, an unseen-student test, response probability, notebook
   action fidelity, or learning effects.

### Reproduction and verification

Run with the project's existing Python environment:

```sh
python -m src.eval.corpus_summary \
  data/episode-pilot/historical-response-baseline-v1 \
  data/episode-pilot/corpus-summary-v1/report.json
```

The output parent must exist; output is create-only. The local report contains
aggregate statistics and source hashes, not message excerpts or conversation IDs.
It verifies the baseline's nine receipt entries and 19 pinned source files before
analysis, checks duplicate identities/dialogues and the library window count, and
pins the analysis and relevant extractor source. Query reference bytes are hashed
for preservation but never decoded as observations for this analysis. Existing
experiments remain unchanged.

Authored regressions check unequal conversation weighting, empirical percentiles,
unknown modes/timestamps, response-window grouping, order invariance, empty-input
rejection, changed-source rejection, and invariance of development statistics to
excluded target content. An independent recomputation matched the lengths, literal
rates, concentration and context counts. The corpus report closes this descriptive
step; no model, label, reviewer, or simulator change is part of it.
