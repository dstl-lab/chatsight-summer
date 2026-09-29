# Bounded history comparison: completed

**Result:** Earlier dialogue slightly reduced literal message-form error on these
ten account-separated checkpoints: **0.430 → 0.400**, a paired difference of
**−0.030**. History improved three cases, worsened two and tied five. The exact
visible-student form-frequency baseline scored **0.155**, lower than either
sampled model condition. This is a mixed, narrow result; it does not establish
better simulated students or support changing the simulator.

The baseline is a probability distribution over message forms, not a generated
response or a semantic simulator. Its lower score makes it a useful reference
for this diagnostic, not a replacement for the generative model. The secondary
mean absolute character error was 43.02 for current exchange and 38.86 for history
(50 replies per arm); this does not replace the primary result.

## Execution and stopping point

The user approved “Let's do the bounded run then.” Exactly **100 scheduled
Gemini 2.5 Pro calls** completed, sequentially, from 14:29:28 to 14:50:24 UTC on
2026-09-29. There were **zero failed calls, retries or replacement draws**.
All returned decisions were replies: 50 per condition. Every account has the
planned five valid samples per arm, so all ten pairs enter the primary score.

The twenty prompts, schedule, model configuration, original inputs and scoring
protocol stayed unchanged. The recorded next messages were excluded from every
generation request and loaded only for offline scoring after dispatch completed.
All 100 saved provider outputs replay to their accepted decisions. Returned model
versions and reported token usage are included below. The plan and dispatch
receipts record the authorization and source hashes; private artifacts remain
under ignored `data/course-account-history-v1/` and are not committed.

The [predeclared protocol](2026-09-29-course-account-history-protocol.md) is now
closed: one batch and one report, no tuning, extra samples, manual labels or
automatic follow-up. The application simulator is unchanged. Account eligibility
remains unverified as requested. Ten accounts and five draws per arm do not
support significance or population-realism claims. This return-to-chat cohort
also cannot validate probabilities of silence or hidden notebook activity.

The tested runner/report code is in commit `85f318e`. Authored checks cover the
fixed dispatch order, failure preservation, refusal to resend, raw replay,
reference binding, primary/baseline scoring and explicit missing outcomes.

## Full automatic report

Ten provisional course accounts; student eligibility unverified.

Complete case pairs: 10/10; scheduled requests: 100.

All-ten history-minus-current-exchange score: -0.0300.
Complete-pair contrast: -0.0300.
Missing-outcome bounds: [-0.0300, -0.0300] (not a confidence interval).

Primary arm means below use the same complete pairs. Lower form error is better.

| Condition | Mean form score | Reply | No reply | Error |
| --- | ---: | ---: | ---: | ---: |
| current-exchange | 0.4300 | 50 | 0 | 0 |
| history | 0.4000 | 50 | 0 | 0 |

Visible-student form-frequency baseline, all ten cases: 0.1550.

| Case | Current score | History score | History − current | Baseline |
| --- | ---: | ---: | ---: | ---: |
| course-account-v1-01 | 0.1000 | 0.1000 | 0.0000 | 0.2500 |
| course-account-v1-02 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| course-account-v1-03 | 0.3000 | 0.0000 | -0.3000 | 0.0444 |
| course-account-v1-04 | 0.2000 | 0.0000 | -0.2000 | 0.0000 |
| course-account-v1-05 | 1.0000 | 0.3000 | -0.7000 | 0.0000 |
| course-account-v1-06 | 0.0000 | 0.6000 | 0.6000 | 0.2500 |
| course-account-v1-07 | 0.7000 | 1.0000 | 0.3000 | 0.0059 |
| course-account-v1-08 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| course-account-v1-09 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| course-account-v1-10 | 1.0000 | 1.0000 | 0.0000 | 1.0000 |

Secondary diagnostics use reply draws only; counts include all five scheduled draws per arm.

| Case | Condition | Reply / no reply / error | Character MAE | Newline rate | Backtick rate | Reply denominator |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| course-account-v1-01 | current-exchange | 5 / 0 / 0 | 15.8000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-01 | history | 5 / 0 / 0 | 16.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-02 | current-exchange | 5 / 0 / 0 | 7.8000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-02 | history | 5 / 0 / 0 | 5.8000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-03 | current-exchange | 5 / 0 / 0 | 72.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-03 | history | 5 / 0 / 0 | 4.6000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-04 | current-exchange | 5 / 0 / 0 | 41.0000 | 0.0000 | 0.2000 | 5 |
| course-account-v1-04 | history | 5 / 0 / 0 | 5.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-05 | current-exchange | 5 / 0 / 0 | 61.6000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-05 | history | 5 / 0 / 0 | 28.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-06 | current-exchange | 5 / 0 / 0 | 23.2000 | 1.0000 | 0.0000 | 5 |
| course-account-v1-06 | history | 5 / 0 / 0 | 138.8000 | 0.2000 | 0.0000 | 5 |
| course-account-v1-07 | current-exchange | 5 / 0 / 0 | 69.4000 | 0.0000 | 0.4000 | 5 |
| course-account-v1-07 | history | 5 / 0 / 0 | 50.2000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-08 | current-exchange | 5 / 0 / 0 | 73.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-08 | history | 5 / 0 / 0 | 73.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-09 | current-exchange | 5 / 0 / 0 | 19.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-09 | history | 5 / 0 / 0 | 19.0000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-10 | current-exchange | 5 / 0 / 0 | 47.4000 | 0.0000 | 0.0000 | 5 |
| course-account-v1-10 | history | 5 / 0 / 0 | 48.2000 | 0.0000 | 0.0000 | 5 |

Saved provider responses: 100/100; responses without a returned model version: 0.

| Returned model version | Responses |
| --- | ---: |
| gemini-2.5-pro | 100 |

Usage totals cover reported top-level integer fields; missing fields are not zeros.

| Usage field | Total | Reporting responses |
| --- | ---: | ---: |
| candidates_token_count | 3529 | 100 |
| prompt_token_count | 250780 | 100 |
| thoughts_token_count | 125874 | 100 |
| total_token_count | 380183 | 100 |
| cached_content_token_count | 79556 | 12 |

- Primary: finite-ensemble-corrected half-scaled categorical Brier; lower is better. Negative history-minus-current-exchange means lower literal message-form error.
- The correction assumes independent, stationary draws; five draws per arm remain noisy.
- Incomplete pairs stay in the scheduled population; missing-outcome bounds are not confidence intervals.
- Character error and newline/backtick rates use reply draws only; every denominator is reported.
- No-reply is category 12, not zero-length text. Errors are missing outcomes, not student behavior.
- The sample is conditional on a recorded return message and cannot measure real silence probabilities.
- Earlier dialogue contains task and tutor information. Literal form does not establish semantics, personalization, eligibility, overall realism or an adoption decision.
- The fixed batch ends here: no retries, replacements, tuning, new labels or automatic follow-up.
