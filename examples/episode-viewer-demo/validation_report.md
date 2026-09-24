# Synthetic Lab 1 cohort validation

All students, messages, tutor responses, timings, and outcomes are synthetic.
No real student text or student-level trajectory was used.

## Run

- Students: 100
- Potential student-question paths: 800
- Represented paths: 757
- Raw episode events: 8390
- Synthetic transcript rows: 566
- Reconstructed episodes: 970
- Questions: 8
- Direct-request scenario assumption: 25% of tutor-using paths

## Historical sequence calibration

These targets apply only among generated tutor-using paths.

| Pre-chat state | Historical target | Generated share | Generated count |
|---|---:|---:|---:|
| ask-first | 27% | 26.9% | 76 |
| fail-then-ask | 17% | 17.0% | 48 |
| pass-then-ask | 56% | 56.2% | 159 |

Source and limitation: docs/2026-08-09-sequence-pilot-first-numbers.md; 7,782 historical tutor conversations; notebook-level join; 45-minute pre-chat and 20-minute outcome windows.

## Scenario-generated interaction acts

These are synthetic ground-truth choices, not measured historical rates.

| Interaction act | Share of tutor-using paths | Count |
|---|---:|---:|
| direct-request | 25.1% | 71 |
| debugging-request | 11.3% | 32 |
| syntax-help | 11.3% | 32 |
| conceptual-clarification | 13.1% | 37 |
| assignment-reference | 8.1% | 23 |
| validation | 31.1% | 88 |

## Claim boundary

This cohort tests analytics and interface behavior. It does not estimate
real DSC 10 prevalence, learning, student intent, or tutor causality.
