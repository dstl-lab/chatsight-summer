# Behavioral measurement readiness

**The existing automatic labels are not established as reliable measurements of
`help_request` and `work_present`.** Three completed human reviews provide a
bounded audit set for these exact flags. Reuse those judgments before treating
an automatic coder as a behavioral benchmark instrument. The inventory and
preparation inspect no new reserved targets; the separate, fixed coding audit
below uses only previously reviewed messages.

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

## Status

Packet/review identities, exact common definitions and complete judgment coverage
were checked during the inventory. The audit is prepared but dispatch is blocked;
there are no automatic-coder results, adopted scorer or fresh-cohort findings.
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

Independent review found no remaining dispatch, retry or replay issues. Automatic
approval review rejected the attempted launch **before process creation** because
general benchmark approval did not specifically authorize sending these 88 private
course-conversation prompts to Google. There is no execution directory and zero
requests were sent. The local `send-blocked.json` records the rejection; exact
prompts remain in `dispatch/disclosure.md`. The only dispatch blocker is explicit
approval for this fixed transfer to Google Gemini 2.5 Flash. Do not bypass the
rejection or substitute another provider. This is a transfer approval, not a
request for more human labeling. The audit remains unrun and has no results.

Run the offline checks from this worktree with:

```sh
PYTHONPATH=. python -P -m pytest -q experiments/2026-09-30-help-work-measurement
```

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
