# Help/work measurement audit and results

**The explicitly approved recovery completed all 88 coding requests, with no
transport errors or retries.** Agreement with saved human judgments is 76/87
(87.4%) for work presence and 35/86 (40.7%) for help requests among binary,
nonconflicted comparisons. One message received unclear for both flags; another
has a conflicting human help judgment. This measures coder–reviewer agreement,
not simulated-student realism. Neither flag is adopted as a validated scorer.

The original 88-request attempt remains a closed transport failure. Its schema
parameter was corrected and checked on invented text before the user approved
the separate recovery batch. The recovery changed no messages, human judgments,
rubric, model, schedule or scoring logic. No new student replies were generated,
no unused target messages were inspected and no further human labeling occurred.

## Completed recovery results

The user explicitly approved "the corrected 88-request batch". The local
`data/behavioral-measurement-schema-recovery-v1/approval.json` binds that response
to the frozen plan and exact disclosure; it precedes dispatch. All 88 raw provider
responses and receipts are saved locally. `report.json` reparses those responses
and verifies the unchanged prompts, human sources and prior failed-run evidence.
Independent verification reproduced every raw response, aggregate and per-prefix
metric, Wilson interval and kappa; all 223 source-file pins verify. Approval
precedes every request, and the original failed run remains unchanged. The local
`closure.json` records completion with no adopted scorer or further dispatch.

Request accounting is 88 failed original attempts, two authored diagnostic
generation requests and 88 completed recovery requests, plus one metadata-only
lookup. There were no retries within either batch or other generation calls.

| Compared with saved human flags | Work present | Help request |
| --- | ---: | ---: |
| Eligible human judgments | 88 | 87; one conflict excluded |
| Binary model coverage | 87/88 (98.9%) | 86/87 (98.9%) |
| Model unclear | 1 | 1 |
| True positives | 54 | 31 |
| False positives | 11 | 0 |
| False negatives | 0 | 51 |
| True negatives | 22 | 4 |
| Agreement on binary comparisons | 76/87 (87.4%) | 35/86 (40.7%) |
| Precision | 54/65 (83.1%) | 31/31 (100%) |
| Recall | 54/54 (100%) | 31/82 (37.8%) |
| Specificity | 22/33 (66.7%) | 4/4 (100%) |
| Cohen's kappa | 0.713 | 0.054 |

The unclear case has human help=yes and work=no. It stays outside confusion
cells, which is why help recall uses 82 rather than 83 and work specificity uses
33 rather than 34. The human help conflict does not discard its agreed work=no.
Failures, unclear outcomes and conflicts are never converted into negative labels.

All sixteen prefixes contain a binary help disagreement; eight contain a work
disagreement. The saved report includes each prefix's counts. Across prefixes,
help disagreement counts are 1 (one prefix), 2 (six), 3 (three), 4 (three), 5
(two) and 7 (one). Work disagreement counts are 0 (eight prefixes), 1 (five)
and 2 (three). These are shared contexts, not 88 independent student accounts.

Descriptive Wilson 95% intervals for work precision, recall and specificity are
72.2–90.3%, 93.4–100% and 49.6–80.2%, respectively. For help, they are
89.0–100%, 28.1–48.6% and 51.0–100%. These intervals assume independence, which
shared prefixes and a single reviewer violate; they are not population intervals.
The four help-negative cases cannot establish strong specificity even with
four matching answers.

### Interpretation and stopping decision

This audit exposes a mismatch between the automatic coder and our saved
judgments. It does not establish which source is correct in every disagreement.
Among the eleven work disagreements, nine candidates visibly contain declarative
answers, code or explanations, one offers a tentative answer as a question, and
one merely says a function exists before asking how to use it. The first pattern
suggests that some saved judgments used a narrower meaning of work than the
written rubric, which counts answers and reasoning. The last pattern exposes a
potential model error: mentioning earlier work is not itself submitting it.
These are qualitative observations, not replacement labels or adjudications.

Inspection of the 51 help disagreements found code submissions, answers to tutor
questions and acknowledgments of readiness to continue. Forty-one already have
human work=yes; ten have work=no. Their prefixes often start with a request for
help and end by inviting an attempt or answer. One interpretation is that the
model distinguishes answering from requesting help, while the human judgments
carry an implicit request for checking forward from the conversation. The saved
categorical outputs cannot establish the model's reasoning. This is exactly the
rubric boundary between context-supported terse requests and code/output that
does not automatically imply a request; neither side is adjudicated here.

Do not use these scores as a realism percentage or treat the model's flags as
reliable ground truth for a fresh student benchmark. The protocol froze no
numerical adoption threshold; none is invented after seeing these results.
No label changes, prompt tuning, replacement draws or additional coding calls
are queued. The failed original run and successful recovery are both closed.

The next measurement decision is to separate observable message content from
inferred intent: presenting an answer is observable; whether a bare answer is
implicitly asking for confirmation requires interpretation. Keep the existing
human judgments and automatic judgments separately inspectable. A later
benchmark needs a declared operational definition and uncertainty treatment
before its scores can support a student-fidelity claim. This report requests no
new manual labeling and does not automatically launch that benchmark.

## Reusable evidence

All three reviews use identical `help-work-v1` definitions and independent
yes/no/unclear flags: a message can request help and present work simultaneously.

| Completed source | Human-coded rows | Important scope |
| --- | ---: | --- |
| [Fixed help/work benchmark](2026-09-15-help-work-results.md) | 72 | Eight references and 64 generated replies; all references help=yes, work=no |
| [Cached communication review](2026-09-22-cached-communication-results.md) | 23 | Eight references and 15 unique generated replies; one repeated draw shares a judgment; references include three work=yes cases |
| [Retrieved-example comparison](2026-09-27-retrieved-student-example.md) | 14 | New generated replies only; original references reused without new labels; duplicate pairs share judgments |
| **Total reviewed rows** | **109** | Overlapping inputs must not count as independent evidence |

The two sets of eight recorded references are development evidence; all sixteen
have help=yes, and three have work=yes. Generated-message judgments are useful
for auditing a coder but are not observations of real-student frequencies. The
retrieval study's reused references must not be counted as new observations.

Older primary-action labels cannot be converted into these two independent
flags: their work-first hierarchy suppresses co-occurring help. The six-case
[joint preference review](2026-09-21-joint-fidelity-check.md) explicitly left
its help/work flags blank, and the [paused bulk audit](2026-09-19-minimize-manual-labeling.md)
does not supply completed labels. Neither supplies missing ground truth.

## Exact-input deduplication

An audit input is the candidate's exact text plus its complete ordered sequence
of visible `(role, text)` pairs, concatenating earlier context and the current
exchange. Ignore opaque IDs and origin/condition metadata; do not trim whitespace,
rewrite text or deduplicate identical messages with different prefixes.

This produces **88 unique inputs across 16 distinct prefixes**, removing 21
duplicate rows from 109. Ten unique inputs have multiple reviewed occurrences.
All original judgments remain attached to their occurrences; no old study's draw
weights, report or labels change.

One identical input received **conflicting human help judgments** in the cached
and retrieved-example reviews: no versus yes. Its work judgments agree on no.
Preserve this as a help conflict rather than choosing the newest answer, voting,
or asking a model to adjudicate it. Retain its valid work judgment.

| Flag | Unambiguous yes | Unambiguous no | Conflicted | Eligible unique inputs |
| --- | ---: | ---: | ---: | ---: |
| Help request | 83 | 4 | 1 | 87 |
| Work/evidence present | 54 | 34 | 0 | 88 |

There are no returned unclear or unfinished flags in these three sources; a
deduplication conflict is a separate disposition. Among the 87 inputs with both
flags unambiguous, 54 are help-and-work, 29 help-only and four neither. There is
no work-only example. The remaining input has work=no and unresolved help.

## What a one-shot audit can establish

Use all 88 existing inputs once with one frozen coder, prompt, schema and
definition. Withhold saved human flags, notes, source identities, origins and
conditions from its inputs. Retain per-flag conflicts, abstentions, invalid outputs
and failures explicitly. Freeze the interpretation rule before sending anything;
report class-specific confusion counts, precision/recall, coverage and uncertainty
instead of relying on overall accuracy. Do not tune the coder and repeat this
audit on its revealed answers.

Work has both classes represented, but observations share only 16 prefixes.
Help-negative support is **four inputs in four prefixes**. An always-yes help
coder would already achieve 83/87, or 95.4%, accuracy. Even four correct negative
decisions out of four yield a Wilson 95% lower bound near 0.51 for specificity,
under an independence assumption. This set can expose gross errors; it cannot
establish strong two-class help reliability or justify a joint gate solely from
high average agreement. The absence of work-only examples further limits testing
whether a coder keeps the flags independent.

These are single-reviewer judgments with prior development exposure. The human
agreement ceiling is unknown, and the observed duplicate conflict demonstrates
that the saved answers are not infallible. The labels support a bounded
development audit, not independently validated ground truth or a population
prevalence estimate. Account separation is not established for these older cases.

The [August classifier audit](2026-08-10-two-annotator-audit-round.md) concerns
different taxonomy labels and schema vintages; its precision, recall and agreement
cannot validate these flags. The existing [work-probability forecast](2026-09-22-work-presence-forecast-status.md)
failed its declared screen. It predicts future work probability, rather than
coding a realized message, and cannot substitute for this measurement audit or
for measured generated behavior.

## Original transport attempt

Packet/review identities, exact common definitions and complete judgment coverage
were checked during the inventory. After specific approval, the audit consumed
all 88 scheduled requests, with 88 `ClientError` dispositions, zero usable labels
and no missing slots. That initial attempt produced no accuracy estimates,
adopted scorer or fresh-cohort findings. Both flags had zero coverage; precision, recall,
specificity and kappa are undefined, not zero.
Any new benchmark needs a separately frozen measurement gate and explicit handling
of its weaker help evidence. No additional human labeling is requested here.
All existing experiments, reports, judgments and stopping decisions remain closed
and unchanged.

Preparation verified 120 legacy source-file bindings against the closed reports.
The ignored local artifact is `data/behavioral-measurement-v1`; its dispatch plan
SHA-256 is `f3c651a3fa4a39a536515621e9b1838f0e2b5b83e9bbd12de66d0f2f8205fbbb`.
It contains 88 exact prompts of 2,436–7,555 characters. Human judgments remain
local and excluded from every request. Two saved reviewer identifiers are
aliases, not evidence of two independent reviewers.

The existing Gemini transport is reused without modifying closed experiments.
The audit and runner have 28 passing authored checks, covering deduplication,
conflicts, source pins, prompt isolation, confusion arithmetic, explicit failures,
raw-response replay and refusal to resend an interrupted batch. Private source
messages, review forms and provider responses remain ignored by Git.

Automatic approval review initially rejected dispatch before process creation.
The user then explicitly approved the exact transfer with "Yes, you may".
The local `approval.json` binds that answer to the plan and disclosure and
precedes launch and every receipt. `send-blocked.json` retains the earlier
rejection as history. The frozen runner's older standing-approval note is not
the sole authorization record.

The fixed run is closed. Its saved report replays all 88 terminal receipts;
there are no raw model responses, retries or substitutions. Independent review
verified approval chronology and all 127 distinct source-file pins (including
the 120 legacy evidence bindings). The offline tests and earlier review did not
exercise the actual provider schema conversion; they missed this integration bug.

Run the offline checks from this worktree with:

```sh
PYTHONPATH=. python -P -m pytest -q experiments/2026-09-30-help-work-measurement
```

## Transport diagnosis and approved recovery

A model-metadata request confirmed that the key can access `gemini-2.5-flash`.
One invented message with the frozen configuration returned HTTP 400
`INVALID_ARGUMENT`: unknown `additional_properties` in
`generation_config.response_schema`. The strict Pydantic JSON Schema was passed
through `response_schema`, which this API route did not accept. Changing only
that parameter to `response_json_schema` preserved the schema, including its
restriction on extra fields, and returned the expected two flags for the same
invented message. The local parser remains strict. Google's
[structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output)
describes JSON Schema support, including `additionalProperties`.

These were **two separate authored diagnostic generation requests** and one
metadata request, with no private conversation content. They are not audit
observations. The original receipts retained only exception types, so the
specific HTTP 400 is established by reproducing the frozen configuration, not
by saved error bodies for each of the original 88 requests.

A separate recovery directory retains the failed run unchanged and reuses the
exact 88 prompts, human references, schedule, model, rubric and analysis. The
only configuration change is:

```python
configuration['response_json_schema'] = configuration.pop('response_schema')
```

No prompt wording or human answers change. The existing runner is reused without
copying or modifying frozen code. Source bindings now also include the failed
plan/report, explicit approval, every failed receipt and the separate diagnostics.
All original preparation artifacts and prompt payload bytes were copied exactly;
the existing verifier reconstructs all 88 inputs successfully. The corrected
synthetic output passes the same strict parser with help=yes and work=no.

The prepared local directory is `data/behavioral-measurement-schema-recovery-v1`.
Its dispatch plan SHA-256 is
`de531030846f7918c26c68a69cc1bdabc1435c382e57ef2a321a82f72bfe4c5b`.
The exact transfer disclosure is its `dispatch/disclosure.md`. After explicit
approval, this recovery completed 88/88 requests; the results are reported above.

The recovery used a separately approved budget of at most 88 private requests,
because the original approved budget had been consumed. The local authorization
record preserves that scope. No fresh student benchmark or additional human
review is queued.

## Fixed measurement audit protocol

This is the first prerequisite for the approved account-separated behavioral
benchmark. It checks a coder against existing human judgments; it does not
generate new students, forecast their behavior, or repeat a completed experiment.

- All 88 distinct inputs, once each; no label-based sampling or replacement.
- Gemini 2.5 Flash, temperature 0, thinking budget 0, 2,048 output tokens,
  120-second timeout, one SDK attempt, one adapter attempt, sequential calls.
- Exact common definitions and complete reviewed context; one candidate per
  request. No examples, reference labels, notes, source identities, conditions or
  other candidates. Output only the two yes/no/unclear flags.
- Freeze exact prompts, source bindings, schema, configuration and order before
  dispatch. Save raw provider responses and terminal dispositions. An interrupted
  run remains incomplete; no restart, retries, rerolls or repair prompts.
- Compare each flag separately against its unambiguous saved human judgment.
  Preserve the help conflict while retaining that input's usable work judgment.
  Report confusion counts, precision, recall, specificity, coverage and kappa;
  show per-prefix counts. Errors, abstentions and missing outputs stay explicit.
- Wilson intervals describe binomial proportions under independence, not
  population uncertainty: these inputs share 16 conversation prefixes. No
  measured human-agreement ceiling is available.
- Stop after this fixed audit and one report, even if it fails or is incomplete.
  Do not tune/retest the coder against these answers, adopt it, or automatically
  dispatch the fresh-cohort benchmark.

The interpretation is deliberately asymmetric: errors can expose an unsuitable
measurement, but high agreement on this small, development-exposed set cannot
establish general classifier validity. In particular, help specificity rests on
only four negatives regardless of the audit result. The user was asked whether
work should be primary and help secondary for the subsequent benchmark; that
preference does not affect this audit's inputs or scoring.

## Fresh-cohort readiness

The existing metadata pool has 108 provisional course accounts remaining after
excluding the complete accounts of the ten now-exposed history cases. It covers
1,018 conversations and 4,652 structural checkpoints. The exclusion removes 167
conversations, not merely the ten previously selected ones. The original 425
exposure-source pins and four prior selection-source pins still verify. Recent
evidence-card work reuses those ten accounts; notebook continuation traces back
to an already-excluded account. No additional known local exposure was found in
the remaining pool.

These are candidate counts, not a chosen cohort or a claim of verified student
enrollment. No new target text was inspected or fetched. Once measurement is
settled, selection must freeze a new seed, sample accounts first, choose one
checkpoint per account, and isolate references before generation. The old
private selector has fixed counts/seed and module-level side effects; do not
import or rerun it as though it were a generic selector. Unknown external
exposure and provider pretraining remain outside this local audit.
