# Fixed-codebook classifier comparison

Minchan approved comparing the current classifier with one stronger model, then a
short blind review on episodes outside the 12-case drafting sample. Keep v7's
definitions, prompts, schemas, evidence rules, stage windows, and retry policy fixed.
This is a bounded development experiment, not another rubric version.

Compare the saved Gemini 2.5 Flash run with Gemini 2.5 Pro, using the same provider
and the same 12 episodes already authorized for disclosure. Google's
[model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-pro)
lists the stable Pro model and structured-output support; the account's model
metadata confirms generateContent availability. Use the existing adapter and API
default generation settings for both. Model-specific defaults can differ; this is
a comparison of model configurations, not an isolated causal effect of capacity.

Protocol: `e1f4a23939ff68eb4dd3ba2fde303486bb93f94c6e6a70d8fc107171d63b477b`.
Preserve the Flash bundle and outputs byte-for-byte. Copy the sample into a separate
Pro bundle with empty development annotations, changing only experiment/model
metadata. The existing bundle ID identifies sample/protocol and does not include
model; add a separately hashed comparison run ID including model and generation
settings. Verify every actual prompt hash against the saved Flash run before sending.
Keep all dialogue, drafts, and comparisons under ignored data/. Do not send reserved
episodes to Gemini under the development disclosure authorization.

## Checks declared before the Pro run

- Human development anchors with compatible meanings: requests 1/3/4/5/6/7;
  tutor responses 3 (worked-solution), 6 (mixed), and 7 (hint).
- Approved definition examples, distinct from independent annotations: tutor
  checking on 12 and checking plus a next step on 8.
- Assistant audit hypotheses: avoid mixed for a single complete repair on 5 and
  unsupported definite task relationships on 4/6. Inspect citations and regressions
  across all 12; fewer mixed labels alone is not success.
- Do not exact-score older mixed judgments on 1/4/5 against the narrowed definition.
  Episode 2 had human language uncertainty. No v3 human task_relation judgments
  exist. Derived absence fields receive no classifier credit.

Report cases and evidence, without an accuracy percentage or combining human
judgments, category approval, and assistant audit into one score. One run per model
does not establish repeatability. A subsequent blind packet should focus on tutor
response and observed task linkage, with predictions withheld and answers saved
separately. The reserved pool is disjoint from pilot development, but historical
snapshot exposure is uncertain; do not call it a pristine formal evaluation set.

## Result

All 12 Pro drafts completed on the first pass. Every one of the 24 actual prompt
hashes matches the saved Flash run. The only category changes were tutor response
5 from mixed to worked-solution (assistant audit hypothesis) and tutor response 7
from mixed to hint (preserved human development anchor). Complete solution on 3,
mixed on 6/8, and checks-work on 12 were retained. No category regressions appeared
in this run, but retained predictions are not all validated.

Task links 4/6 remain unsupported definite changes. Some evidence selection remains
incomplete, and related checking/guidance moves can still be described as mixed
without clearly separate aims. Pro is a candidate for the next blind tutor-response
check, not an automatically adopted default or an admitted simulation classifier.

Experiment `cb5fe74a0d496f6b` and its comparison, returned selections, and verification
are under ignored `data/episode-pilot/comparison-v7/`. All 24 preserved file hashes
match, including classifier source and seven human reviews. The codebook, production
code, default model, and active review UI were unchanged by this experiment.

## Blind pilot packet

Six reserved cases outside the 12-case drafting loop were selected using a fixed
metadata recipe before inspecting Pro outcomes: seed 20260910, six notebooks,
four observed follow-ups and two absent follow-ups, balanced short/medium transcripts
(up to 1500 / 1501–4000 characters including context). CJK-script cases were omitted
given the earlier reviewer's language uncertainty. This limits representativeness.
Selection did not use model predictions. The 35 reserved bundle records remain
unchanged and unannotated; no reserved dialogue was sent to Gemini.

Packet `bbb3baefbc1fa04a` is under ignored `data/episode-pilot/blind-v7/`. It shows
the unchanged definitions and complete raw context/turns, with no predicted labels,
rationales, or legacy labels. Start with three cases; responses are two labels in
chat, with optional notes and no evidence highlighting. Explicit answers will be
saved separately; all reviews are currently empty. Two absent task relationships
are supplied as source facts, not counted as blind human judgments. Thus the packet
requests six tutor judgments and four observable task relationships.

The existing three-field UI could not serve this packet without changing its mode
and evidence rules, so it remains untouched. The Markdown packet was checked for
exact source coverage, prediction exclusion, sample disjointness, and empty answers.

## Subsequent review changed the representation

Minchan has since answered cases 1–3 and requested the actual component functions
inside mixed replies. His same-task judgments concern the tutor addressing the
student request, not the later student's task. The raw answers and clarification
are saved separately; they must not be scored as v7 follow-up relationships.
The original packet remains preserved, and cases 4–6 are paused and unanswered.

The [ordered tutor-move revision](2026-09-10-tutor-moves.md) removes primary-label
exclusions and permits overlapping functions. Earlier mixed-versus-single-label
findings above apply only to v7's definitions; they do not establish that those
functions cannot coexist. Cases 1–3 inform this revision and cannot independently
validate it.
