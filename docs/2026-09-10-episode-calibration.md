# Episode pilot: first calibration findings

Seven development episodes have completed reviews by Minchan. This is enough to identify concrete changes for the next codebook draft; no additional reviews are needed for this diagnostic pass.

These are model-visible development judgments, not blind evaluation. The first five used manual entry and the next two used the simplified review flow. Agreement, reliability, learning, and review-speed effects are not estimated. Historical timing includes passive viewing.

## What episodes 6 and 7 established

| Episode | Recorded human review | Implication |
| --- | --- | --- |
| 6 | Accepted confirmation and mixed tutor response; changed follow-up from clarifies-request to other, suspecting a new question. | The next contribution visibly requests debugging help. Its relationship to the original task is uncertain: the tutor introduces another question, while the student does not identify the target of the follow-up. |
| 7 | Changed assistance requested from solution to confirmation; accepted hint and substantive-contribution. | Submitting code is not sufficient evidence of asking for a finished solution. Confirmation is a plausible contextual interpretation; submitting work is directly observable. |

Episode 7 also contains the useful sequence this pilot was meant to uncover: submitted code, tutor guidance, then a revised code submission incorporating the suggested operations. It does not establish a passing execution, independent understanding, or a causal learning effect.

Episode 6 should remain recorded as Minchan's judgment. A possible task switch is not a verified task switch, and this memo does not relabel it.

## Direction for the next codebook draft

Separate three questions currently entangled in the categories:

1. **What is visible?** For example, the student submits work, asks for help, acknowledges a response, or has no recorded follow-up. Use explicit subtypes where they add meaning, such as revised code.
2. **What help is requested?** Require evidence for a finished-answer request. Code submission alone must not trigger solution. Keep unknown available when intent cannot be determined from the request and prior context.
3. **How does this contribution relate to the task?** Distinguish same task, different task, and uncertain. Do not infer the link simply because messages are adjacent, or because the tutor mentions a new question.

This is a proposed separation of concepts, not a frozen replacement taxonomy. Preserve the useful tutor-response dimension. Use the reviewed examples to write inclusion and exclusion rules before generating another draft. In particular, clarification of an existing request needs evidence of that relationship; a generic debugging question is insufficient.

The immediate development target is an inspectable description such as “student submitted revised code after a hint, on the same task.” Each part needs its own evidence, and uncertain links remain visible. This gives an instructor more to inspect than a broad substantive-contribution label alone.

## Provenance and next step

- Bundle: `data/episode-pilot/pilot-v3/bundle.json`, ID `91cec33de48aa423`.
- Source snapshot: `20260811-1d1e79d39fda-7bc759`.
- Rubric/prompt hash: `7c6c01c2737d1ea03029d3c1ec31971c32c4b0d59fbffd34d465da503805b464`.
- Draft model: `gemini-2.5-flash`.
- Reviews: `data/episode-pilot/pilot-v3/reviews/development-development-minchan.json`.

The current bundle and human judgments remain unchanged. Draft the revised definitions against these seven development reviews first. Any later classifier revision needs a new version and provenance pin; the reserved conversations stay out of this calibration loop. The snapshot's prior exploratory exposure also prevents calling the reserved split a pristine evaluation set.
