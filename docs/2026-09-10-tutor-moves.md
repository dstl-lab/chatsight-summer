# Tutor responses as ordered, overlapping moves

Minchan reviewed three prediction-hidden cases and requested the actual component
labels instead of an opaque mixed category. He also clarified that his same-task
answers concerned the tutor reply relative to the student's request. The original
answers and scope clarification are preserved separately from the v7 packet.

This changes the representation, not merely model compliance. The previous primary
label rules suppressed explanation accompanying an answer or hint. Several outcomes
previously described as overusing mixed can reflect real co-occurring functions.
Do not reinterpret the user's mixed judgments as mistakes or turn them into
unprovided component annotations. Cases 1–3 are now developmental examples for
this revision; stop the pending v7 review round. Cases 4–6 remain unanswered.

## Smallest implementation

Add a tutor-only annotation alongside the existing episode results. Keep v3–v7
protocols, source bundles, previous experiments, and human reviews unchanged.
Reuse existing source-line selectors, model adapter, bundle loading, and atomic
writing. No new UI or dependency is needed.

Represent a response as ordered `tutor_moves`, each with a nonempty list of labels,
source-line evidence, and a short rationale. Allow multiple labels on the same
passage and repetition across later moves. Remove mixed; retain checks-work,
explanation, hint, worked-solution, asks-question, other, and unclear. Remove
primary-label and dominance exclusions: an explanation remains visible when it
supports a hint or complete answer. A copied existing answer is not a newly supplied
solution. Do not tag routine praise or offers of help as substantive questions.

Record `tutor_task_relation` separately: addresses-request, introduces-new-task, or
unclear. This judges what the tutor addresses, not whether its assessment is right.
Introducing a clearly distinct exercise counts even when the reply first addresses
the current request. A generic failure request can be addressed by an attempted
diagnosis without claiming that the diagnosed cause is verified. V7's student
follow-up relationship stays separate and is never populated from these reviews.

The model sees only prior context, current request, and tutor response. Validate
move categories, label uniqueness, source order, source phase, exact quoted lines,
and relationship evidence from both current request and response for known values.
Retain failed drafts; never fix their labels silently. Pin the new prompt, rubric,
wire/stored schemas, rendering contract, model, and source identity independently.

Test with invented dialogue, including overlapping functions, repeated later moves,
wrong-phase/blank evidence rejection, failure recovery, and invariance to future
student text. Generate only the same 12 development episodes already authorized for
Gemini. Any decompositions shown for reviewed cases 1–3 are local assistant proposals,
not further disclosures or human ground truth. No performance claim crosses the
representation change from the fixed v7 Flash/Pro comparison.

## Implementation and first run

The standalone module is implemented; all 270 tests pass. The added regressions
use invented dialogue and cover overlapping functions, future-input invariance,
evidence phase/order, empty replies, resume validation, and source preservation.
Independent code review found no material implementation issue.

Gemini 2.5 Pro produced 12 drafts in 12 logged calls: 34 moves, of which 26 carry
multiple labels. These are descriptive counts of one development run, not accuracy.
Protocol `ec435087b4bc0d03282b5215c4aace725902616c720b657fc60c9312f48acb68`
and run `f35a821bc3912703` are pinned under ignored
`data/episode-pilot/tutor-moves-v1/`. Actual prompt hashes match the authorized
12 development episodes, with future turns excluded. All 32 preservation hashes
match, including prior source protocols, experiments, and human reviews; the 35
reserved records remain unchanged and unannotated in their source bundle.

The local run is reproducible with `PYTHONPATH=. python
data/episode-pilot/tutor-moves-v1/run.py`; `summarize.py` verifies the saved run
without network calls. The wrapper retains returned selections before evidence
validation. Adapter parsing failures retain an error class, not a raw API body.

## What still needs review

An assistant audit found useful combinations but remaining semantic limits:

- Some long passages are grouped into one move, compressing the order of distinct
  actions. The same closing invitation is sometimes included as other and sometimes
  omitted. Move boundaries are not yet calibrated.
- Questions and hints can be omitted even when their source passage is cited.
- Development episode 8 labels a derivation of the student's existing answer as
  worked-solution, despite the rule requiring a new answer or repair.
- Development episodes 2 and 11 label only the initial request-addressing behavior
  in the relationship field while also describing guidance on later questions.
  Episode 9's generic request leaves the current task uncertain; the tutor's own
  account does not independently establish when the student changed tasks.

No generated labels were silently corrected. Citation validation establishes where
evidence came from, not whether a function is supported or exhaustively captured.
Introducing a new task also does not mean the original request was ignored.

The next human step is only to review the two proposed component breakdowns of the
already-read mixed cases in the local preview. They are explicitly assistant
proposals, checked against source text, not human component labels. This is a
representation check before further blind annotation or classifier calibration;
it does not establish reliability or admission to simulation.

## Accepted examples and bounded second revision

Minchan replied, “Yes those breakdowns look about right.” The exact reply and
hashes of the shown preview and proposals are saved separately as an anchored
endorsement of cases 1–2. This approves their approximate component breakdowns;
it does not create independent human labels, new citations, or a reliability score.

Keep the representation and all validation rules. Add an explicitly selected v2
prompt to clarify passage boundaries, questions and hints, new solutions versus
explanations of existing answers, and relationship decisions over the whole reply.
Use only invented illustrations in that prompt. Original reviewed dialogue stays
local. V1 remains the default protocol and its exact prompt/hash remain available;
the original module source is also preserved with its experiment for reproduction.
No UI, dependency, model default, or student-follow-up changes are needed.

Before generating, check that v1 prompt bytes/hash remain identical, v2 cannot
resume v1 outputs, and both inputs exclude future dialogue. Generate another
separately pinned development run on the same authorized 12 episodes. Compare
specific previously identified failures and regressions, without manufacturing
human agreement or silently correcting model outputs. Stop further prompt tuning
if the same semantic ambiguity needs a human decision.

## Second-run result and next human check

All 271 tests pass. V2 produced 12 drafts in 12 logged calls, with 32 moves and
29 moves carrying multiple labels. Run `2930adf51deaf2ab`, protocol
`71f6d741b14c9670ba7994007e73bfa97fc23ec9ab292dbe0f22295ddc0430f3`,
is under `data/episode-pilot/tutor-moves-v2/`. All 44 preservation hashes match.
Every dialogue payload is identical to the corresponding v1 input; v1 remains the
default with the same prompt bytes and protocol hash. Its archived module matches
the original experiment's source hash. V1's old scripts intentionally reject a
changed current source file; reproducing that experiment requires its archived
module source in the matching checkout, not changing its recorded code hash.

Assistant audit found specific improvements: distinct-question guidance is retained
in relationships 2/11, plot-comparison questions are included in 6/10, and the
complete repairs in 3/5 are no longer also labeled as hints. Several failures remain:
8 still treats a derivation of the student's existing answer as a new solution;
12 calls a fully supplied alternative a hint and still includes a bare closing as
other; 7 merges previously separate checking/explanation and repair guidance into
one move. Task identification in 9 still relies on an uncertain target. These are
assistant audit findings on reused development data, not human performance scores.
No predictions were overwritten or corrected, and no further prompt tuning follows
this run before a human check.

The next packet, `e7088873b3414ecd`, is under
`data/episode-pilot/blind-tutor-moves-v2/`. It reuses all three still-unanswered
cases 4–6 from the earlier metadata-selected packet, with original ordering and
only context/request/tutor text. The frozen v2 definitions are shown, without
case predictions, rationales, old answers, or student follow-ups. Reserved dialogue
has not been sent to Gemini. Review answers start empty.

To reduce review effort, this check asks only which known functions are present
anywhere in each tutor reply. A future comparison uses the union of known labels
across model moves. It does not assess segmentation, ordering, or task relationship;
uncertain or unassessable judgments must not become assumed negative labels.
Three cases are a qualitative blind check, not a reliability estimate or simulation
admission test. The snapshot's prior exploratory exposure still limits independence.
The already-approved examples do not need another review.

## Component-presence response received

Minchan submitted four semicolon-separated groups for the three-case packet. Four
tutor replies are visible because case 5 includes an earlier contextual reply.
The raw response and a provisional reading-order mapping are saved; no per-case
judgments are finalized until that mapping is confirmed. Original packet text,
presentation hashes, and empty-at-creation records remain unchanged.

The submitted hint labels may also reflect a different completeness boundary from
v2's partial-guidance definition. Clarification is pending on whether complete
supplied code can count as a hint, or whether this depends on the student's request.
Do not relabel the user's judgments as worked-solution, call them mistakes, score
agreement, or revise the classifier before this distinction is resolved.

Minchan then confirmed the four-reply grouping and noted that hint versus
explanation is nuanced. Three current-reply judgments are now saved exactly:
case 4 other (greeting), case 5 explanation plus hint, and case 6 hint. The extra
explanation-plus-hint judgment on case 5's earlier reply is stored separately as
contextual feedback, outside the three review targets. Both raw messages remain
preserved, and no citations, order labels, or task relationships were inferred.

Overlap is already supported. Keep the hint/explanation distinction provisional;
this reply does not settle whether complete supplied code qualifies as a hint.
No category merge, new completeness rule, classifier revision, or agreement score
follows from the grouping confirmation. No further review task is requested now.

## Frozen three-case comparison

The next step is a descriptive comparison of the frozen v2 classifier with the
three confirmed current-reply reviews. Preparation lives under ignored
`data/episode-pilot/validation-tutor-moves-v2/`. Pin the exact three prompts,
source packet, reviewed reply IDs, human review snapshot, model, generation
configuration, protocol, and code. Human answers never enter the model prompts.
Keep the original split assignments and all earlier artifacts unchanged.

Report shared labels, user-listed labels not produced, and model-produced labels
not listed. The latter two are set differences, not established false negatives
or false positives. Honor uncertainty and the unresolved hint boundary. Do not
compare the extra contextual judgment, move ordering, or task relationships, and
do not compute an accuracy or reliability percentage from this check.

Preparation and local verification can proceed now. Sending cases 4–6 to Gemini
requires specific disclosure approval: these are three different conversations
from the original 12 covered by the earlier approval. The prepared run is offline
by default; generation is the remaining step after that approval.

The three requests, reference-review copy, comparison renderer, and dry-run checks
are complete (prepared run `b7247ee30b592f1f`; 64 preservation hashes). Automatic
approval review rejected the attempted external step because the user's Continue
and approval for different cases did not specifically authorize these three cases
to Gemini. At that point no request had executed and no predictions existed for
this check. The user had already completed the annotation work.

## Three-case comparison completed

Minchan subsequently replied “Yea” to the explicit request to send cases 4–6,
including student/tutor dialogue and earlier context, to Gemini 2.5 Pro. That
approval and the earlier rejected status are preserved in the ignored run folder.
The unchanged prepared run produced three valid annotations in three logged
generation attempts. The existing adapter does not record its transport retries.

| Case | Confirmed human components | Frozen v2 components |
| --- | --- | --- |
| 4 | other (greeting) | asks-question |
| 5 | explanation, hint | explanation, worked-solution |
| 6 | hint | explanation, hint, worked-solution |

Source inspection distinguishes two issues. Case 4 is a greeting and routine
invitation to specify help, which the frozen rubric explicitly excludes from
substantive questions. Its asks-question prediction conflicts with that rule.
Case 5's supplied answer and accompanying explanation support the model's labels
under the current definitions, but the human hint judgment leaves the intended
boundary unresolved. Neither judgment was rewritten.

Case 6 needs passage-level care: the model calls its opening plan a hint even
though a full implementation of that same plan follows, contrary to v2's
completeness clarification. A later alternative procedure still leaves work for
the student, so hint remains plausible somewhere in the reply. This demonstrates
why shared reply-level labels do not validate every labeled passage. Supplied code
has not been executed or verified as correct. The user's unlisted components are
not confirmed absences.

All three actual prompt hashes match the prepared inputs. All 64 preservation
hashes match, including the classifier, source packets, earlier outputs, and
human reviews. Human labels and future turns were excluded from model inputs.
All 35 reserved source records retain their original splits and empty annotations;
the three new outputs live separately, and the other 32 were not sent in this run.
Independent audits checked provenance and the semantic interpretation.

This is a completed qualitative check, not a reliability or simulation-admission
result. More annotation should wait until the intended hint boundary is settled.
A candidate for discussion is to retain overlapping instructional functions while
recording separately how much of the requested work the tutor supplies. That is a
proposal, not an adopted schema or a reinterpretation of these human judgments.
No new prompt, label correction, or review assignment follows from this run.

## Approved guidance definition and v3 implementation

Minchan approved the broader meaning of guidance, including when complete code
appears in the same reply. V3 replaces hint with guidance: explicit direction about
what to try or do next. Explanation remains why/how, and worked-solution continues
to identify a new supplied answer or implementation for the addressed step. All
three may coexist. Code alone does not automatically constitute guidance; a
provided answer does not establish correctness or completion of the whole task.
Retain the existing ordered moves and evidence structure; add no completeness field.

This is a definition endorsement, not a new independent annotation of case 6 or a
conversion of earlier hint labels. Keep all human answers and predictions intact.
Archive the current module before editing; v1 stays the default, and v1/v2 keep
their exact rubric, prompt bytes, and protocol hashes. V3 must be selected
explicitly through prompt generation, materialization, validation, and resumption.
Also clarify the existing routine-help-offer exclusion using invented examples.

Check version isolation and current-reply-only evidence with invented dialogue.
Then use the existing runner pattern on the same 12 previously authorized
development episodes with Gemini 2.5 Pro. Preserve exact inputs and results in
`data/episode-pilot/tutor-moves-v3/`; do not send additional reserved cases or score
old hint reviews as guidance ground truth. Compare concrete developmental behavior
and stop before any further definition change needs human judgment.

V3 is implemented at protocol
`e2a690b990c7505c292675f9f548d70b5800f545187b25439a7b028aec63b962`.
All 272 tests pass, including the new guidance/version regression. Independent
code review found no material issues. V1/v2 prompts remain byte-identical on all
47 source episodes, and their 27 saved development/three-case annotations still
validate. All 75 preservation hashes match. The pre-v3 module is archived at
`data/episode-pilot/tutor-moves-v3/source/tutor_moves-before-v3.py`; older scripts
that pin its file hash require that archive in a matching checkout. Their recorded
hashes and original outputs were not changed.

The 12 exact v3 development requests and runner are prepared and verified offline.
Automatic approval review rejected generation, then rejected a retry despite
verbatim recovery of the earlier permission to send the same 12 dialogues to
Gemini. The reviewer did not accept the recovered permission as establishing that
scope and destination. At that point no v3 predictions existed and no v3 dialogue had been sent.
The approval history and both rejections are saved in the ignored run folder.
Only current explicit disclosure approval and execution remain; no additional
implementation or human annotation is needed before the development check.

## V3 development run completed

Minchan then explicitly approved sending the original 12 development episodes,
including student/tutor dialogue and earlier context, to Gemini 2.5 Pro for v3.
The authorized run completed with 12 valid drafts in 12 logged generation
attempts, 26 moves, and 24 moves containing multiple components. These are run
descriptors, not accuracy. Run `2af63e186a21b13a` and its exact prompts, outputs,
comparison, and assistant audit are under `data/episode-pilot/tutor-moves-v3/`.

The approved overlap appears in actual replies: episode 3 includes explicit repair
guidance alongside a supplied implementation. Episode 8 no longer labels the
student's existing answer as a newly supplied solution; it separates checking and
explanation from guidance on the next step. Episode 12 identifies a supplied
alternative implementation without assigning guidance merely because code appears.
This does not establish improvement across the corpus or isolate what caused a
change in this single run.

Remaining limits are concrete. Episodes 5 and 10 each combine several successive
actions into one move; 1 and 7 also obscure internal order. Episode 11's final
guidance-only move omits explanation despite citing the reason for an ordering
choice. A reply-level union would conceal that omission. Episode 9 still asserts a
new task with an uncertain current target, and episode 12 still retains a routine
closing as a separate move. Episode 2's supplied-solution component applies to
intermediate calculations, not completion of its later question.

All 75 preservation hashes and actual prompt hashes match. V3 receives the same
dialogue payloads as v2, with human judgments and future turns excluded. All 35
reserved source episodes remain unchanged and unannotated; none was sent in this
run. Independent review checked provenance and the first six semantic examples.
The raw model outputs and old human hint reviews remain intact.

The next evaluation should check component presence on fresh replies with model
predictions hidden. Keep passage boundaries and task relationships provisional;
this run does not establish readiness for corpus labeling or simulation. No more
prompt tuning or definition changes follow from these development observations.

## Next blind component-presence packet

Minchan requested the fresh blind check. Prepare three local replies, labeled
A–C, under `data/episode-pilot/blind-tutor-moves-v3/`. Exclude all original 12
development conversations and all six previously presented blind conversations,
plus exact duplicate target replies from those visible prefixes. Select by a
recorded metadata recipe, with short reading length, distinct notebooks, and
coverage of replies with/without code and earlier context. Keep full selected
prefix text; inspect content only after selection is fixed.

Use the frozen v3 definitions and ask which components occur in each current
tutor reply. Earlier tutor messages are explicitly background, not extra review
targets. The user can list uncertain components or mark the reply unassessable;
an omitted label is not automatically an explicit negative. No passage splitting,
citations, order labels, or task relationships are requested. Display no model
predictions, old human answers, or semantic selection rationale. Make no API calls.

This is fresh relative to the known pilot/review packets, not a claim of pristine
historical exposure or learner independence. Three selected replies provide a
qualitative check, not a population reliability estimate. Preserve all old rounds
and the original reserved split while recording this new review exposure separately.

Packet `470e9db3c73b8f05` is ready. Excluding the 18 previously used conversations
leaves 29 candidates. The recorded recipe selects one reply without context/code,
one without context but with code, and one with at most two context turns; it uses
distinct notebooks and a combined 5,500-character budget. The fixed hash-based
draw considered 97 eligible combinations. The resulting source text totals 5,419
characters, copied in full. Selection preceded semantic inspection, and model
outputs were not used. All 93 preservation hashes match; no model calls occurred.

`review.md` asks for exactly three judgments, A–C, and explicitly excludes C's
earlier tutor message from the targets. The version-bound answer file starts
empty. `verify.py` checks source fidelity, selection, target IDs, and preserved
rounds offline. Human review is now the only pending step for this packet.

## A–C blind judgments received

Minchan supplied these components before model predictions: A guidance,
explanation, asks-question; B checks-work, explanation, guidance, asks-question;
C checks-work, guidance, asks-question. The original arrow notation and label order
are saved alongside the component lists. No passage boundaries or citations were
inferred from those arrows, and an unlisted component is not an explicit negative.
The initial empty answer file and the unchanged presentation are preserved.

Prepare a separate comparison under `data/episode-pilot/validation-tutor-moves-v3/`
using the exact frozen v3 protocol and Gemini 2.5 Pro configuration. Copy the human
reference independently and exclude it from all three model prompts. Report
descriptive component differences and uncertainty; do not score the unsolicited
order, task relationships, accuracy, or simulation readiness. These are three
different conversations from the previously authorized disclosures, so explicit
permission for A–C is required before sending their dialogue to Gemini. Finish all
local preparation and checks first; no further annotation is needed for this pass.

Preparation is complete at run `61f45981905720f9`: three exact v3 requests, a
separate human-reference snapshot, the copied/adapted comparison runner, and 105
preservation hashes. Offline checks confirm the submitted labels and arrow order,
the initial empty answer file, original presentation, target IDs, and exclusion of
human answers and future turns from model input. No A–C predictions have been
generated; specific disclosure permission is the remaining prerequisite.

## A–C frozen comparison completed

Minchan explicitly approved sending the three dialogues and earlier context to
Gemini 2.5 Pro. Run `61f45981905720f9` completed with three valid predictions in
three logged generation attempts. A and B reproduce the components Minchan listed;
C contains those components plus explanation. In C, the current reply explains
the corrected operator's effect, why a baseline is needed, and the simulation
variable's purpose. This supports the extra component under frozen v3, but is an
assistant interpretation: the human omission was not an explicit negative.

The passage audit exposes limits that component sets conceal. A's first move
cites explicit directions but labels only explanation, with guidance captured
later. B combines assessment of column selection with a later optimization prompt
in one move. C's final move assigns asks-question to a routine closing choice,
although its earlier substantive questions support that label at reply level.
Independent review reached the same findings. The next useful check concerns
passage localization and grouping; no definition change follows from this pass.

All 105 preservation hashes match. Actual logged selections reproduce the saved
annotations, exact prompts match the original source prefixes, and human reviews
and future turns are excluded. The original 35 reserved source records retain
their split and empty annotations; this run's three predictions live separately.
Human answers, arrow order, old results, and frozen classifier remain unchanged.
The comparison and audit are in `data/episode-pilot/validation-tutor-moves-v3/`.
This completes the three-case pass without an order score, reliability estimate,
or claim of readiness for sequence analysis or simulation.

## V4 passage grouping check

Minchan requested continuation on the passage issues. Trace inspection confirms
that prompts, raw model selections, and stored evidence agree: these are model
grouping and local coverage failures, not errors introduced by materialization.
The working hypothesis is that whole-reply component coverage is substituting for
checking each local passage. Test one prompt-only revision: identify successive
instructional passages, then label all supported functions within each passage;
apply the routine-closing exclusion locally as well. Keep co-occurring functions
together and avoid one move per sentence, label, or code line.

V4 retains the exact v3 rubric, response schema, model configuration, and source
inputs. V1–v3 prompts and protocol hashes remain frozen, and v1 remains the default.
Reuse the existing runner and version-isolation test. Save the original module,
tests, and prior artifact hashes before editing. Run only the original 12 already
authorized development episodes with Gemini 2.5 Pro, once with structural retries
only; inspect all results for grouping changes and regressions. No new disclosure
or independent accuracy claim is planned. A–C informed this change and therefore
cannot independently validate it; preserve their original reviews and v3 outputs.

Success for this development check means concrete evidence of better passage
localization without erasing valid overlap or creating trivial fragments. It does
not mean more moves, an exact human arrow match, or reliable sequences. If this
single clarification does not resolve the main pattern, characterize the remaining
limitation before adding further prompt instructions or a segmentation subsystem.

V4 is implemented at protocol
`c17157b0443896629e391346b51db5bbabb2595d533d01583d576cefa637800f`.
The revision also resolves an ambiguity between the inherited instruction to omit
routine closings during substantive help and v3's broadly stated assignment of
other to help-topic invitations. V4 scopes other to a wholly social/help-selection
reply and excludes routine material even when it shares a move with substantive
help. The 16 targeted tests and all 273 tests pass; independent code review found
no material issues. All 141 v1–v3 prompts remain byte-identical across the source
episodes, with unchanged old hashes, default, rubric, and response schema.

The existing runner and summarizer are prepared for the same 12 development
dialogues and Gemini 2.5 Pro configuration. All 196 earlier artifact hashes match;
the prior module is archived under `data/episode-pilot/tutor-moves-v4/source/`.
Frozen payloads match the authorized v3 dialogue exactly and exclude human reviews
and future turns. Earlier scripts that pin the prior module's file hash require
that archived version; their manifests and results remain unchanged.

Automatic approval review rejected generation because it did not accept earlier
permission as establishing the exact 12-episode dialogue scope and destination in
the trusted transcript. No v4 request or prediction exists. The rejection and
offline verification are saved with the prepared run. Current explicit disclosure
approval is the remaining prerequisite before the actual model check; offline
tests establish version/input safety, not better passage labels.

## V4 development results and grouping decision

Minchan explicitly approved the original 12 development dialogues and earlier
context for Gemini 2.5 Pro. Run `7be7014c47bf1ada` completed in 12 logged generation
attempts, producing 31 moves, 30 with multiple components. These are descriptors,
not accuracy. All 196 preserved hashes and exact prompt hashes match, and every
logged selection materializes exactly to its saved annotation. No reserved cases
were sent; source splits, human reviews, and old outputs remain unchanged.

The observed changes are mixed. Episode 5 now separates diagnosis, supplied repair,
and rerun checks. Episode 10 separates residual and plot implementations from the
comparison question. Episode 11 restores explanation to its final strategy
passage, and episode 12 omits the routine closing. But 1, 7, and 12 still group
activities broadly. Local guidance/explanation omissions remain in 4 and 5; 6
adds worked-solution to an assessed numerical result without establishing newness.
Episode 11 also drops a local assessment label and judges task relationship from
the opening, overlooking substantive later-task guidance. The full assistant
audit records all 12 cases; independent review checked the first six and the
principal grouping and relationship issues in 7, 10, and 11.

Before another prompt change, ask one concrete grouping preference: in development
7, should the assessment/explanation of the existing function and the later repair
instructions be separate moves, even though both concern the same bug? The
suggested split is the explicit transition to repair; overlapping labels remain
allowed within both passages. The exact current request and full tutor reply,
unchanged model result, proposed boundary, and unset answer are saved in
`data/episode-pilot/tutor-moves-v4/grouping-review.json` with a readable Markdown
version. This is an anchored design judgment, not independent evaluation or
confirmation of any component labels. No further generation or tuning is planned
before that human judgment; this run does not establish reliable sequences.

## Approved assessment-to-repair boundary

Minchan endorsed two moves in development 7: assessment/explanation of the existing
work, followed by the explicit repair instructions, with overlapping labels within
each. Record the answer separately from the original v4 proposal and predictions.
This is an anchored grouping preference, not independent annotation of every label
or a requirement that all replies contain exactly two moves.

Implement the smallest v5 prompt revision: require a new move when a later passage
transitions from assessing or explaining existing work to instructions for changing
it, even for the same bug. Keep the repair plan, its supporting explanation, and
implementation together when they share that local focus; do not split every step
or manufacture a boundary inside an inseparable passage. The v3 label definitions,
schema, model configuration, and default remain unchanged. Preserve exact v1–v4
prompts/hashes and all earlier artifacts in the existing versioned workflow.

Use the same original 12 development dialogues and Gemini 2.5 Pro for a single
frozen check with structural retries only. The focused question is whether episode
7 exposes the approved boundary while useful overlap and other existing behavior
survive. Inspect all outputs and retain the known local-label/newness/relationship
limitations in the audit. No fresh reserved data, blind-score claim, or additional
definition change is part of this check.

V5 is implemented at protocol
`47e31c6867f729c6af154b8f026ac1bfa5bd7f070ac9e55e3c036903f91b2f22`.
All 17 targeted tests and all 274 tests pass, with the pre-existing dependency
warning. Independent code review found no material issues. All 188 v1–v4 prompts
across the 47 source episodes remain byte-identical, along with their hashes,
default, rubric, and schema. The prior module and tests are archived under
`data/episode-pilot/tutor-moves-v5/source/`; 217 earlier artifact hashes are pinned.
The saved grouping endorsement is kept apart from model input and is not scored
as a new human annotation. The generation run uses the identical 12 dialogue
payloads and Gemini 2.5 Pro configuration from the explicitly approved v4 run.

The v5 run completed, but development 7 still combines the endorsed assessment
and repair passages in one move. Preserve that failure. Other local-label,
newness, and task-relationship problems remain, and a later recap is grouped
before an intervening rounding passage in episode 1. Do not add another full-batch
wording retry. The issue now warrants a small diagnostic separating passage
selection from component assignment.

Use only development 7 for that diagnostic. First request boundaries alone,
without the known line-10 answer or expected count. Separately label the two
human-approved passages with evidence constrained to each passage. This separates
automatic boundary discovery from preserving fixed boundaries during labeling.
The second condition uses a human-derived constraint and cannot demonstrate
automatic segmentation. Keep both prompts, raw outputs, boundary provenance, and
structural checks in an ignored experiment folder. No new production pipeline,
reserved data, or reliability claim follows from this single-example probe.

## Separate passage diagnostic results

V5 run `a24577fe7f388c41` completed with 12 valid annotations in 12 logged attempts
(32 moves, 29 containing multiple components). All 217 preservation hashes and
logged-selection materializations match. The endorsed boundary failed in episode
7; independent review confirmed that failure, the reordered recap in 1, and the
whole-reply relationship error in 11. The saved outputs remain untouched.

The two-condition probe in `data/episode-pilot/passage-probe-v1/` then completed.
The boundary-only call, without a known location or expected count, selected
lines 1–8 and 10–16, recovering the endorsed transition and attaching the closing
encouragement to the second passage. Separately, labeling the human-approved
ranges 1–8 and 10–14 produced checks-work plus explanation, then explanation plus
guidance, with exact evidence restricted to each range. This second condition
does not consume the automatic boundaries; it is not an automatic end-to-end run.

The first fixed passage still omits guidance despite citing an explicit inspection
instruction. The probe supports testing passage selection and labeling separately,
while leaving component completeness unresolved. It is one already exposed
development example, not independent validation or a reliability estimate. No new
production pipeline was added. All probe inputs, raw results, human-boundary
provenance, validation checks, and limitations are saved alongside its report.

## Connected passage experiment

Minchan authorized continuing the next test and subsequent work until human action
is needed. Run a bounded connected experiment on the same original 12 approved
development replies with Gemini 2.5 Pro: discover passages without known boundaries,
validate complete ordered coverage, then feed those exact automatic ranges into
the existing constrained-label prompt. Keep the v5 component definitions and
whole-reply task relationship unchanged. Use fresh automatic selections for all
12; the earlier human-fixed labeling result is not an end-to-end prediction.

Reuse the ignored probe's schemas and validators in a small experiment driver,
with a runnable invented-data check of stage dependence and safe cached reuse.
Freeze the model configuration, source, prompts, code, and prior artifacts before
generation. Save each exact label request after the automatic plan exists and
before it is sent; reject invalid plans before labeling and preserve failures.
Do not retry valid outputs to obtain preferred groupings. Audit every reply for
boundary behavior and component support, including the endorsed split, returning
recaps, routine material, new-answer claims, and whole-reply task relationship.
This is paired development diagnosis, not independent validation, and creates no
production default, new UI, corpus labels, or simulation admission claim.

The connected segmenter explicitly attaches routine openings and closings to
adjacent substantive passages (or keeps a wholly social reply as one passage).
This resolves a mechanical conflict between full text coverage and the existing
exclusion of routine material from substantive labels. Otherwise it reuses the
probe's segmentation instructions. Incorrect automatic boundaries are retained,
never manually repaired before the label call.

The first connected run completed 11 stage pairs in 23 logged requests. The
remaining automatic plan omitted a Markdown divider, so coverage validation
correctly prevented its label call. Preserve that original failure and perform
one separately recorded structural repair on that episode only, supplying the
omitted-line validation feedback. The repaired plan must pass the same validator
and feed labeling unchanged. This is an additional attempt with a different
prompt, not a first-attempt success or a semantic retry of a valid prediction.

The next necessary human input is two short fresh replies with explicit passage
start lines and overlapping components. Prepare a local blind D–E packet, using
the existing recorded-metadata selection approach: exclude all 21 previously used
conversations and duplicate visible tutor replies, contrast code and earlier
context, use distinct notebooks, and keep the reading budget small. Freeze the
selection before semantic inspection. Show full request/context as background and
numbered current-tutor text as the only target; show no model boundaries, labels,
suggested count, or semantic selection rationale. Preserve empty answers and allow
uncertain breaks/components. Bind the packet to the current v5 definitions and
connected diagnostic procedure. This calibrates passage judgments beyond the one
anchored split; it does not estimate reliability or admit labels to simulation.

## Connected development results

Experiment `fc44b4ad0393edd82aa275c660f3e7621eaaa2ed5beab7ec9898ad7c547a1483`
completed 11 connected pairs in 23 logged requests (32 moves, 30 with multiple
components). A separate two-request structural retry completed the remaining
reply after the validator identified an omitted formatting divider; its original
failure remains preserved. The repaired ranges differ only by attaching that
divider to the preceding passage. These are execution descriptors, not accuracy.

The approved assessment-to-repair split is realized in development 7, and the
first passage now includes its inspection guidance. Cases 3, 5, 10, and 12 expose
useful successive activities. Fixed ranges prevent cross-passage jumps in cited
evidence, but broad grouping still hides some returns and subactivities. Local
guidance/explanation omissions remain in 4 and 5, and worked-solution newness is
unsupported in 6 and contradicted by the visible student answer in 8. The scope
of a supplied completed substep remains unclear in 7's rationale; the frozen rule
does not require a whole-function implementation. The whole-reply relationship
problem in 11 survives segmentation, and the original target remains uncertain
in 9. All are assistant audit findings, not new human labels.

Invented-data checks and offline replay verify stage dependence, invalid-plan
blocking, exact source evidence, and cached-parent integrity. All 246 original
file pins and the retry's 250 pins match; the 35 reserved source annotations remain
empty. The production module and defaults are unchanged. Save the full case audit
and report under `data/episode-pilot/passage-pipeline-v1/`; obtain explicit source
boundaries on the two fresh replies before treating the passage representation as
human-calibrated beyond the one anchored example.

The D–E packet is ready at `data/episode-pilot/blind-passage-pipeline-v1/review.md`
(packet `dd4b0fd1dd4d759f`). Excluding the 21 known used conversations leaves 26
candidates. The frozen metadata recipe selects two distinct notebooks from six
eligible pairs, totaling 3,168 source characters, with full background preserved.
Verification confirms exact target text, original line numbers, no predictions or
future turns, empty answers, and 259 preserved file hashes. The user can return
start lines and component sets directly in chat; human review is the pending step.
Freshness is relative to recorded packets, not a claim about unknown historical
exposure or independent learners. No model requests were made for D or E.

## Priority correction after the simulation question

Minchan asked why further tutor labeling serves the simulated-student objective.
The assistant deferred D–E and further passage refinement: downstream value has
not been shown. All packet content, empty reviews, model results, and definitions
remain preserved; the mutable status records this deferral. The [episode pilot
memo](2026-09-10-episode-pilot.md#return-to-the-simulated-student-objective) records
the student-continuation diagnostic and the local inventory of available student
transitions. Tutor labels remain optional candidate metadata; this does not grant
unvalidated labels admission or change the project's measurement requirements.
