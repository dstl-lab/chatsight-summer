# What reliable means for our student evaluator

**Working definition:** the evaluator is reliable enough for a stated use when
its measurement errors and uncertainties are unlikely to change the research
decision we make from its output. For the first use, identify large, recurring
differences between simulated and recorded message content. Do not claim that
this also validates individual continuations, ranks small improvements, or
measures overall student realism.

This is a proposed measurement contract, not a new scorer, passed evaluation,
or authorization to reopen a closed study. The user asked to begin by defining
reliable. Pending their preference, the recommended use is large-gap diagnosis.
No new human judgments, private-data transfers, simulations or labels occur here.

## The decision and the observation

Start with: **Does the simulator systematically supply more or less answer/work
content in chat than the recorded students, given the supplied exchanges?**
Use the existing `content_supplied` definition unchanged. Code, proposed answers,
reasoning and diagnostic output count; copied content counts. A task statement,
work plan or claim of success alone does not. Keep `expressed_request` as a
separate diagnostic until it has its own supporting evidence.

The unit is an existing message plus a fixed preceding context window. Both
recorded and generated messages receive the same permitted window. Exclude
later messages, notebook outcomes not visible at the checkpoint, source origin,
condition names and previous judgments from the evaluator input. A recorded
next message is one observed outcome, not the only plausible continuation.

This measures a communication property. It cannot establish learning,
motivation, correctness, hidden notebook activity, or whether a student ought
to behave differently. Match the measurement to that limited interpretation.
The distinction between repeatability and measuring the intended construct is
central to [Jacobs and Wallach's measurement framework](https://arxiv.org/abs/1912.05511).

## Five requirements, with evidence for each

| Requirement | Concrete check | What does not establish it |
| --- | --- | --- |
| Shared meaning | Independent readers apply the written definition to actual messages; retain disagreements and unclear cases. | The researcher agrees with model labels already displayed. |
| Supported judgments | Compare definite labels and evidence against blinded human readings, with errors reported separately for recorded/generated sources and yes/no classes. | Valid JSON, exact quotations, or a model claiming message-only support. |
| Repeatability | Code the same fixed inputs in two predeclared passes; report flips and whether the research conclusion changes. | Temperature zero or agreement among repeated calls alone. |
| Honest uncertainty and coverage | Report definite errors, abstentions, human conflicts and technical failures separately; assess which sources/types are excluded. | High accuracy on a silently selected easy subset. |
| Decision robustness | The claimed large gap survives defensible measurement uncertainty and is not driven by one account. | A small positive difference or a pooled accuracy threshold. |

Human agreement provides evidence about interpretation and reproducibility. It
is neither infallible ground truth nor an absolute ceiling on model accuracy;
two readers can share a mistake. Report their original judgments and agreement
table alongside any consensus reference. Agreement coefficients depend on the
label distribution and assumptions; use them as supporting descriptions, not a
universal pass mark. [Artstein and Poesio](https://aclanthology.org/J08-4004/)
explain these distinctions and limitations.

For uncertainty, evaluate both how often the coder abstains and errors among
the labels it retains. The error/coverage tradeoff is the relevant principle
from [selective classification](https://arxiv.org/abs/1705.08500); that paper's
image-classification guarantees do not transfer to this LLM scorer. A model's
self-reported uncertainty does not supply an error bound.

Hide origin and simulator names and use a common input format. Break down errors
by real/generated source, terse/longer messages and context dependence. This
checks whether the evaluator could favor one simulator's writing style.
[Zheng et al.](https://arxiv.org/abs/2306.05685) document LLM-judge biases; their
chat-preference results are not validation of our student-content task.

## A decision rule instead of an arbitrary accuracy target

Before evaluating a new comparison, choose a smallest consequential gap,
`delta`, in percentage points. **Proposed initial resolution: 20 percentage
points**, an illustrative provisional choice for the large-gap use. This is a project
choice for discussion, not a literature standard or a retroactive threshold
for prior experiments. A smaller delta requires more precise evidence.

At each sampled account's fixed checkpoint, compare the recorded content label
with the content rate among existing generated messages from the fixed draws.
Keep unresolved existing-message labels in that denominator with interval values;
report no-reply and technical failures separately. Zero existing generated
messages leaves the account unavailable. Average with equal account weights.
Draws are samples from a simulator, not additional students.
Keep per-account results visible and check the result with each account removed
in turn. Do not treat messages sharing an account as independent observations.

Compute a range for the generated-minus-recorded gap that includes unresolved
interpretations and defensible possible errors in definite labels. An initial
simple sensitivity calculation gives unresolved existing-message labels both
possible values, then widens the range for definite-label errors supported by
an independent audit. Do not assume that errors cancel across sources. If their
size is unknown, report how much differential error would erase the finding;
call that a sensitivity analysis, not evidence that the finding is robust.

- Entire supported range above `+delta`: a substantial excess of supplied content.
- Entire supported range below `-delta`: a substantial deficit.
- Entire supported range within `[-delta, +delta]`: no material aggregate gap
  at this chosen resolution, within the supported scope.
- Otherwise, or without a defensible error assessment: insufficient evidence.

These are bounded comparisons, not a probability that a student is realistic.
An aggregate match can conceal opposing errors across accounts and does not
validate conditional behavior. Ranking which of two simulators is closer to
recorded behavior needs uncertainty in both distances; this rule does not
automatically authorize that stronger use.

Illustration only: a 40-point observed gap with a defensible worst-case combined
measurement distortion of 15 points leaves 25–55 points, exceeding a proposed
20-point threshold. A 10-point gap under the same distortion leaves -5–25 and
is inconclusive. These numbers are invented, not results from our data.
Such measurement ranges alone describe only the fixed saved outputs. Estimating
the simulator's response rate even at those fixed checkpoints also requires
uncertainty from the finite number of generated draws. Population claims further
require representative sampling and account-level uncertainty;
the existing ten exposed checkpoints support development descriptions only.

## Absence and failed requests remain distinct

Content rates are conditional on a message existing. An explicit generated
no-reply, a missing recorded follow-up, a blank message, an unclear content label
and a technical error remain separate statuses. None becomes content=no.
Publish reply/no-reply/error counts and all planned denominators per condition.
For an existing message whose label is unresolved, include both binary values
in sensitivity bounds. For no usable message or unknown existence, retain the
checkpoint as unavailable for this comparison; do not silently drop it and
generalize the survivors to the full cohort. A result dependent on those missing
checkpoints remains conditional or inconclusive. Silence needs a separate
observation model and suitable records.

## What our existing evidence establishes

| Evidence | Current conclusion |
| --- | --- |
| Original audit: 88 distinct inputs, old rubric, one reviewer, shared prefixes | Useful diagnosis; cannot validate the clarified definition or establish independent human agreement. |
| Always-yes help baseline: 83/87 = 95.4% against eligible saved judgments | Overall agreement alone would reward a useless discriminator on that sample. |
| Revised authored check: 8/8 direct controls; 1/6 expected unclear; 0/6 required context citations | Implementation works on explicit cases; context/uncertainty behavior fails the specification check. |
| Message-only filter admits 5 content and 6 request judgments requiring context/uncertainty | Automatic exclusion by self-reported basis is unsupported. |
| Literal message length, newline and backtick measures | Mechanically reproducible descriptions; they remain limited to form. |

See the [closed audit](2026-09-30-behavioral-measurement-readiness.md) and
[bounded revision](2026-09-30-message-content-context-check.md). Current semantic
scoring is **unsupported for the proposed decision**. No additional batch is
needed to rediscover the failures already observed. The evidence does not say
whether the simulator itself is good or bad on this clarified semantic measure.

## A finite verification process when there is a candidate worth testing

First freeze this use, the definition, delta, evaluator version/configuration,
allowed context, selection rule and total review/call budgets. The failed
candidate remains closed; this contract schedules no replacement.

Use one fixed blinded real-message reference pass when a future candidate is
ready. Sample from the intended recorded/generated input distribution before
viewing labels; include independent coding on a fixed overlap. Use a separately
identified boundary panel for failure diagnosis, not population error rates.
No existing old-rubric labels are automatically converted. Authored and generated
reference expectations cannot substitute for independent human readings of
recorded messages. Generated messages can be human-coded to test the evaluator,
but are not observations of real-student behavior.

Choose the finite sample budget from the precision needed for the decision and
available reviewer time. There is no universal minimum count that proves
reliability. Precompute attainable error bounds before asking anyone to label:
if even the best result at that budget cannot resolve delta, narrow the claim
or report insufficient evidence. One reviewer can support an external check;
independent human agreement requires additional independent coding. No repeated
consensus meeting or automatic top-up is required.

Use two fixed model-coding passes on that same frozen panel to measure
repeatability, preserve both outputs, and produce one report. Failures consume
the declared budget; no automatic replacements, repairs or retries. Report class
and source support, uncertainty in estimated errors and abstention rates, and
the resulting decision range. Correlated repeated judgments do not increase the
number of independently sampled accounts.

Stop with one of: **usable for the specified large-gap development comparison**,
**usable only in an explicitly narrower scope**, or **unsupported/insufficient
evidence**. A changed rubric/model/prompt is a new development version and does
not get tested repeatedly against revealed validation answers. No new manual
review request, cohort selection or API call follows from this document.
