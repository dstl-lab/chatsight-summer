# 2026-08-06 — Classifier prompt redesign: grounding CLASSIFY_PROMPT in what the corpus actually looks like

Status: **adopted (A + CourseProfile + abstention channel) — implemented on
branch `classifier-prompt`, 2026-08-06. B (message-form facet) and C
(few-shot exemplars) remain open.**

## Problem

`CLASSIFY_PROMPT` (src/labeling/draft.py) treats a student message as a self-contained
utterance: it shows the model one student message, the single adjacent tutor message on
each side, and the label block. Inspection of the raw corpus says most student messages
are not self-contained utterances, and the context we provide is not the context that
disambiguates them.

## What the data shows

Method: read-only pull through the kubectl tunnel on 2026-08-06. Two samples: (a) the
first 90 conversations by chatlog id, read closely (three full transcripts plus a
length-stratified handful of turns); (b) a 163-conversation random sample
(`ORDER BY md5(conversation_id)`, 782 student turns) for corpus-level rates. The DB held
9,441 distinct conversations at pull time. Scripts and outputs stayed in a session
scratchpad; per Rule 4, no student text appears in this memo — all examples below are
paraphrases or invented analogues.

From the random sample:

- **Student turns are very short.** Median 23 characters; 71% under 40; p10 is 4
  characters. The modal short turn is a deictic reference to an assignment item (a bare
  question number, or "help with <question number>") or a continuation of the previous
  exchange ("what's wrong now"-type turns). Some are a question number *alone* — the
  entire message.
- **Conversations are shorter than the close-read sample suggested.** Median 2 student
  turns per conversation, p90 = 9, max 55; 23% of conversations have exactly one student
  turn. The long, answer-extraction-heavy conversations exist but sit in the tail.
- **Pasted material is a modest but systematic minority.** ~2% of turns are error
  tracebacks (sometimes bare, no authored words at all); ~12% carry code. In the
  close-read sample, students also pasted assignment prompt text verbatim as their turn.
  A model judging affect or intent on pasted instructor prose or a bare traceback will
  mislabel systematically, not randomly.
- **Consecutive student messages are rare corpus-wide** (5 of 782 turns) — the pattern
  looked common in the close-read sample only because one 57-turn conversation was full
  of it. So "context_before is a tutor message" is *usually* type-correct; the real
  problem is that one adjacent tutor message is often not enough context to resolve a
  deictic turn.
- **Turns are not all English** (observed Chinese in the sample) and include throwaway
  probes ("test"-type messages).
- Coverage spans the course (homeworks, labs, midterm and final projects), so any prompt
  fix must not overfit to project-notebook behavior.

Implication: the classifier's unit of judgment must be **the student's act at this point
in the conversation**, not the surface text of the message. The current prompt neither
provides the context to recover the act nor tells the model that the surface form is
frequently pasted or deictic.

## Options

All three keep the architecture: one call per student message, instructor-compiled labels
injected as a block, binary verdict + one-sentence rationale per label (invariants
untouched; drafting stays anchored, measurement stays blind).

### Option A — context-faithful rewrite (recommended now)

1. **Course preamble**: two sentences of course context — for DSC 10: intro data
   science, Python/babypandas, tutor embedded in Jupyter notebooks; students often paste
   assignment text, code, or tracebacks, reference questions by number, and may write in
   languages other than English. Not hard-coded in the template: rendered from a
   `CourseProfile` (see "Generalization beyond DSC 10" below), so the template itself
   stays course-agnostic.
2. **Real context**: replace `context_before` (one tutor message) with the last ~6 turns
   of both roles rendered as a labeled transcript, most recent last. This is the
   load-bearing fix for deictic turns.
3. **Judgment rules** in the prompt: judge the act, not the surface text; pasted
   assignment prose and bare tracebacks carry no affect by themselves — label them by
   what the student is using them to do; very short messages inherit meaning from
   preceding turns; if a label is unjudgeable even with context, mark it false and say so
   in the rationale.

Cost: ~15 lines in draft.py (a context-window helper + new template). Output schema,
webapp, snapshot format unchanged. Risk: more input tokens per call (tutor turns are
long), and a model that drifts into labeling the conversation instead of the target
message — mitigated by the explicit "THIS message" framing. While editing, fold the
context-window size into the `classifier_hash` canonical string; today only the template,
schema version, and model are hashed, so a window-size change would otherwise be
invisible to provenance.

### Option B — A plus a message-form pre-step

Output schema gains a required first field: surface form of the message
(`authored-question | pasted-assignment | pasted-error | code-share | nudge |
answer-reply | other`), declared before the label verdicts.

For: forces the paste-vs-authored distinction to be made rather than merely encouraged;
gives every labeled message a free mechanical facet usable by stratified review sampling
(invariant 9), Phase 2 trajectory conditioning, and error analysis of classifier misses.
Against: output-schema change ripples into the Gemini wire model, snapshot rows, and the
webapp; and the form taxonomy is repo-authored, not instructor-compiled. Position taken
here: surface form is a mechanical property like message length, not a behavioral
construct, so it does not violate the top-down principle — but hybrids (pasted prompt +
authored question in one message) mean a single-valued form field is lossy; if adopted,
consider a list-valued field.

### Option C — A plus instructor-arbitrated few-shot exemplars per label

During the tweak loop, instructor-confirmed or -corrected (message, verdict) pairs become
per-label exemplars injected into the label block. Philosophically the purest top-down
move: the tweak loop compiles intent into criteria *and* demonstrations.

Deferred because the costs are structural, not prompt-level: exemplars are verbatim
student text, so they must live in gitignored snapshot-adjacent storage and load at
classify time; the exemplar set must be hashed into `classifier_hash` and recorded in
manifests; and exemplar messages are anchored (invariant 8), so the sampler must exclude
them from any blind reliability sample. This is a Phase 1 feature that should wait until
the tweak loop has been exercised with a real instructor.

### Recommendation

A now; B is cheap enough to follow within days if the form facet earns its keep in
sampling design; C parked until Phase 1 contact with an instructor. A ⊂ B and A ⊂ C;
B and C are independent.

## Also: ELICIT_PROMPT

Give the schema-drafting prompt the same course preamble plus one constraint: labels must
be judgeable on messages *as they actually occur* — mostly under 40 characters, often a
bare question reference, sometimes pasted code or tracebacks — not on articulate prose.
Otherwise the elicitation step drafts labels whose positive criteria assume evidence the
median message cannot contain.

## Generalization beyond DSC 10: the CourseProfile

The redesign should not bake DSC 10 into the template. Sorting what the inspection
produced: the *judgment rules* (act over surface text; deictic short turns inherit
meaning from context; pasted material carries no affect by itself; unjudgeable → false
with reason; turn-window context) mention nothing pandas-specific — they look like
properties of students talking to an embedded tutor. What is course-specific is the
vocabulary those rules operate over: the tooling, what pasted material looks like
(babypandas tracebacks vs. compiler/linker diagnostics or segfault output in, say, a C++
course), and how students reference assignment items.

Mechanism, in four parts:

1. **`CourseProfile` as a pinned input** beside the label schema:
   `{course_name, domain_description, tooling, paste_conventions,
   reference_conventions, message_shape_notes}`. The template gains a
   `{course_context}` slot; draft.py renders the profile into it. The profile is hashed
   into `classifier_hash` alongside the template — two courses sharing a template are
   still different classifiers, and provenance must say so.
2. **Corpus profiling as a repeatable step.** The inspection behind this memo becomes a
   standard pass for any new corpus: length distributions, paste rates, reference
   conventions, language mix, stratified transcript read. Its output fills the
   CourseProfile — and, under Option B, validates or amends the form taxonomy before it
   is trusted (a course without notebooks may lack `pasted-assignment` and need a form
   DSC 10 never produces). Cost: an afternoon per corpus. This is the honest version of
   "the prompt is grounded in the data" for every course, instead of inheriting DSC 10's
   grounding on faith.
3. **One ingest adapter per data source** — the only unavoidable new code. rawlog.py is
   written against this events table's payload shape; a new course's logs get their own
   adapter whose job ends at producing `Conversation`/`Turn`. Everything downstream
   already speaks that interface.
4. **Elicitation ports for free.** Top-down intent compilation is course-general;
   ELICIT_PROMPT takes the same `{course_context}` slot, including the judgeability
   constraint restated per-course.

Carried-over invariant (same reflex as the ChatSight rule): **labels from different
courses are never compared or mixed in a claim without a dedicated calibration study.**
A schema version binds to one CourseProfile + one snapshot. Two instructors may both
name a label `instrumental-ask`; the DSC 10 one and the C++ one are different constructs
measured by different classifiers. Cross-course comparison is its own explicit analysis,
never a byproduct.

Framing note: this also strengthens the paper story — "instrument ports to a new course
via profile + calibration" is a better claim than "instrument built for one course."

## The closed-set consequence: what mass-labeling cannot see

Mass-labeling is a closed-set instrument by design. `LabelVerdicts` carries one
true/false + rationale per schema label and nothing else; after the instructor accepts,
there is no channel through which the classifier can propose, flag, or hint at a label
that is not in the schema. This is deliberate and load-bearing: invariant 6 (experiments
pin a schema version) is meaningless if the label set can grow mid-run; Rule 2's
classifier parity requires the instrument to be frozen (`classifier_hash`); and the
top-down thesis assigns construct authorship to the instructor — a model that invents
constructs during application is bottom-up labeling re-entering through the side door,
unarbitrated and untested against the admission threshold. New labels have exactly one
entry point, and it is pre-handoff: the tweak loop, producing a new schema version.

The cost: **phenomena outside the schema are invisible after handoff.** If the corpus
contains a behavior the instructor never thought to ask about — and the stratified
review sample happened not to surface it — mass-labeling silently forces every message
into the existing boxes (or all-false), and nothing downstream ever knows. Current
mitigations are weak: invariant 9 pushes boundary cases in front of the instructor
pre-handoff, and per-verdict rationales record the model's reasoning, but nothing mines
them.

Proposed addendum to any adopted option — a **detection channel, not a labeling one**:

- During mass-labeling, an abstention-style signal per message ("no label fits this
  message well"), or equivalently a post-hoc pass over all-false and low-confidence
  messages, collecting candidates into a coverage-review pile.
- The pile feeds the instructor, not the schema. Anything it surfaces round-trips
  through the tweak loop → new schema version → re-label as a new snapshot. The
  classifier may say "something is here I cannot name"; it must never name it.
- This composes with Option B: the message-form facet gives the coverage pile structure
  for free (e.g., "the all-false pile is 60% pasted-error messages" is an actionable
  observation for the instructor).

Cost is one output field plus a review surface; it changes `classifier_hash` like
everything else here, so if adopted it should ship with A rather than after it.

## Honest limits

- Rates come from one 163-conversation random sample (782 student turns) plus a 90-
  conversation close read; no confidence intervals, and the notebook mix in the random
  sample was not verified against the corpus margin. Good enough to motivate prompt
  design; do not cite these percentages downstream without re-measuring on a snapshot.
- "Turn-window context helps" is an argument from inspection, not a measurement. The
  real test is Phase 0: run old and new prompts on the same human-audited held-out set
  and compare per-label agreement. Until then, adopting A is a bet, albeit a cheap one.
- The paste/traceback rates rely on regex heuristics; hybrid messages (paste + authored
  question) were observed but not counted separately.
- The 6-turn window size is a guess. It should be a pinned, hash-visible parameter so
  Phase 0 can compare settings if it matters.
- The abstention signal is itself an unvalidated model judgment — it detects "the model
  is uncomfortable," not "the schema has a gap," and the two correlate imperfectly. It
  is a triage heuristic for the instructor's attention, never a coverage measurement;
  actual negative-space coverage remains the Phase 1 gate's job.
- "The judgment rules are course-agnostic" is an argument from one corpus. The corpus-
  profiling step exists to check it per course: a course whose tutor lives in a web
  forum rather than the editor may produce long, articulate, paste-free messages, and
  the rules' emphasis (deixis, paste handling) would need retuning via the profile —
  which is exactly why message-shape facts live in the CourseProfile, not the template.

## Decision needed

Adopt A / A+B / defer entirely — and whether the first Phase 0 run should happen on the
current prompt first, so the redesign has a measured baseline to beat rather than an
argued one. If A is adopted, adopt the CourseProfile shape and the coverage/abstention
channel with it (cost is near zero when done together; retrofitting either later means
another classifier_hash migration).
