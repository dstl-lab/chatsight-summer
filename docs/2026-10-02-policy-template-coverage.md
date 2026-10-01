# Compare recorded patterns with policy templates

**TL;DR:** Both original coders yield **3/10 recorded messages with a matching
template, 6/10 without one, and 1/10 unresolved**. The code can represent every
resolved combination, but its six templates express only a subset. The main
implementation gaps are general help and solution requests on another task. This
is template coverage, not a realism score or a probability update.

## Fixed comparison

Use the same ten recorded pilot messages, retaining both original assistant
judgments. Report each coder separately and the subset with complete, agreed
labels. The sixteen human-reviewed messages remain coarse help/work references;
their rubric cannot determine a full policy behavior and will not be translated.

An exact match of requested assistance, supplied material and task relationship
to `behavior_policy.TEMPLATES` establishes that a template exists. Unknown values
remain unresolved. A missing template is not silence. Required literal inputs
(work, diagnostic or next task) are listed without extracting them from the
recorded future message. Matching context and actual rendering are not evaluated.

Keep source messages and context available in a private readable report beside
the original labels and any matching authored template. Explicitly distinguish
structural coverage from suitability of the wording. Recorded messages do not
determine the current authored policy's probabilities.

Reverify the previous audit before comparison, preserve all old files, and save
the new comparison and readable report under ignored
`data/policy-template-coverage-v1/`. No new labels, database/model requests,
reserved test messages, behavior selection or simulator defaults change. Stop
after a reproducible report, independent count check and concrete implementation
recommendation. Work stays in the existing isolated branch.

## Result

| Existing recorded labels | Messages | Current template |
| --- | ---: | --- |
| Checking, no material, same task | 1 | Present; no literal slots |
| Hint, no material, same task | 1 | Present; no literal slots |
| Hint, no material, different task | 1 | Present; requires independently supplied next task |
| General help, no material, same task | 2 | Missing |
| Solution, no material, different task | 1 agreed case | Missing |
| Solution with work, different task | 1 | Missing |
| No assistance requested, no material, same task | 1 | Missing; labels alone do not identify what to say |
| General help versus solution, no material, different task | 1 disputed case | Missing under both interpretations |
| Checking, no material, task unclear | 1 | Unresolved; not counted as a missing template |

The disputed case is one message with two original interpretations, not two
independent examples. Across the **eight messages with complete, agreed labels**, three match
templates and five do not. All nine complete bundles under each coder are accepted
by the existing behavior schema; no new behavior category is needed to represent
them. Only three of the six templates are illustrated by this small selected set.
Absence from this set is not a reason to remove the other three templates.

The sixteen coarse human-labeled references remain outside this comparison. Their
labels cannot select a hint, checking or solution template. Neither their counts
nor the pilot's counts are used as policy probabilities.

## Why this matters for implementation

The shortfall is partly **expression coverage**: the policy already represents
the observed label combinations, but the renderer has no pattern for six of the
ten coded messages. The optional Gemini wording layer also requires an already
renderable choice, so it does not fill these gaps automatically. A larger model
does not address this particular implementation boundary.

The three matches are not three proven realistic replies. Two patterns need no
literal fields; the new-task hint needs `next_task`. This comparison did not
extract future task content, work or diagnostic material from the target to make
a template executable. Even with those inputs, literal wording such as “another
hint” may imply context that has not been established. Matching a label tuple is
weaker than semantic suitability.

The recorded prefix exists, but its preceding requested-assistance field remains
uncoded and no revision-bound execution feedback is supplied. The policy's
authored-only admission contract is unchanged. This report does not make these
records eligible for the sampler or evaluate notebook actions or silence.

## Next implementation

Extend deterministic wording first for general help on the current task and
solution requests on a supplied next task, with optional explicitly supplied work.
Use authored boundary cases to verify that required content is preserved and
missing content stays blocked. Keep the empirical examples as illustrations;
do not tune behavior-selection probabilities to maximize this coverage count.

Leave the unresolved task case and disputed label intact. A message with no
assistance or material is not necessarily a greeting, acknowledgment, or silence;
inventing one would go beyond these labels. It needs explicit communicative
content before a deterministic renderer can choose appropriate wording. No new
human review is necessary to implement the clear expression gaps above.

## Reproduce and inspect

The private comparison contains the recorded message, original coder values,
matching template and required inputs. Preceding conversation and source links
are available in expandable details in its Markdown report. They provide context
for inspection, not inferred matching features. Both the machine-readable result
and readable report are create-only and verify against the previous audit and
current template source.

```sh
PYTHONPATH=. python -P experiments/2026-10-02-policy-template-coverage.py verify
PYTHONPATH=. python -P -m pytest -q tests/test_policy_template_coverage.py \
  tests/test_behavior_policy.py tests/test_behavior_expression.py tests/test_behavior_pilot.py
```

The focused verification passed **41 checks**. The new check first failed on the
missing implementation, then passed with absence/unknown distinctions, joint
labels, coder disagreement, literal requirements and unchanged inputs preserved.
An independent read-only calculation reproduced the same coverage counts. Code
review identified a raw-HTML quoting issue in expandable context; a rendering
regression failed before the context was escaped and passed afterward. Review
found no remaining material issues. This does not claim a whole-repository test
run or a semantic wording evaluation.
