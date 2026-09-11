# Help-seeking episode pilot

Approved by Minchan on 2026-09-10 after the evidence-grounded brainstorming in this task.

Question: after receiving help, what does the student visibly do next?

Build a snapshot-only pilot, reusing the existing Python/FastAPI/Gemini stack. The initial unit is one observed tutor-response opportunity: the preceding student request(s), the tutor response(s), and the next student contribution(s), with six earlier turns available as context. This is a short conversation episode, not a claim that a complete question-level learning trajectory was reconstructed. Question references are unverified hints; missing code edits, grader events, and later activity stay unobserved. No live database or simulator is required.

Sample at most one episode per conversation, seeded, and reserve disjoint conversation sets for 12 development and up to 40 held-out episodes. Existing snapshots omit learner identifiers, so learner-level independence cannot be claimed. This snapshot already informed exploratory analysis and prior message audits: the reserved split prevents subsequent within-pilot development overlap, but it is not a pristine evaluation set. Use a fresh snapshot or verified exclusions for prior exposure for formal measurement.

Use three small human-readable dimensions: assistance requested, tutor response, student follow-up. Each machine verdict has a quoted evidence span linked to a role/turn, or an explicit unclear/no-follow-up value. No sentiment or learning inference is required. Store raw dialogue and all derived artifacts only under ignored data/. Hash the rubric, source files, extraction version and sampling configuration. Never alter old snapshots. Annotate development first; held-out model annotation is a separate explicit command after rubric review.

The localhost review page has development (visible drafts), coding (no machine answers), and comparison (legacy labels, timeline, or timeline plus annotations, counterbalanced by reviewer cohort) tasks. Every task sees the same raw chat evidence; only the annotation overlay changes. Holdout coding does not expose model answers even after save. Save partial progress atomically and resume. Save condition, evidence IDs, judgments, review time, and optional instructor action. No review or validity result is fabricated by the agent.

Development review offers Accept all, individual Accept/Change/Cannot assess decisions, and preselected evidence in the correction drawer. Viewing a suggestion does not accept it. New reviews record `workflow: draft-review` and each decision's `assessment`: `accepted`, `changed`, or `cannot-assess`. Cannot assess records reviewer inability with no student category or evidence; it is separate from an unclear student label. Legacy reviews retain the manual workflow and remain valid without these fields. Passive viewing in the new UI creates no writes. Coding and comparison retain the manual form. The five existing label decisions and notes are preserved, and the model rubric and bundle bytes are unchanged. Historical timing from the old UI includes passive viewing and must not support speed comparisons.

Correct the existing shared per-turn sequence lookup's future-event scoping and 45-minute bounds for future labeling runs, with regression checks and a new provenance pin. The pilot does not treat legacy sequence proxies as raw facts. Other historical audit/statistics issues remain documented rather than expanded into this pilot.

Acceptance: deterministic disjoint samples; validated source/turn/evidence references; no model answers in blind payloads; no raw text embedded as executable HTML; recoverable saves; working localhost page; development bundle generated from the existing snapshot; original suite and focused tests pass. Human agreement/usefulness and question-level reconstruction remain unmeasured.

## Running the pilot

From this worktree, install the existing dependencies with `uv sync`, or use the existing runtime `../main/.venv/bin/python` in place of `uv run python`.

```sh
uv run python -m src.labeling.episodes prepare \
  ../main/data/snapshots/20260811-1d1e79d39fda-7bc759 \
  --out data/episode-pilot/pilot-v3/bundle.json

uv run python -m src.eval.episode_review data/episode-pilot/pilot-v3/bundle.json \
  --reviewer minchan --task development
```

Preparation refuses to replace an existing output. The prepared September 10 bundle contains 12 development and 35 held-out episodes. Five of the source snapshot's 52 conversations contain no tutor response and cannot form the required unit. Open http://127.0.0.1:8400. Missing machine drafts do not prevent manual development review. Progress is saved under `data/episode-pilot/pilot-v3/reviews/`.

Version 3 asks Gemini to select numbered source lines; the application copies those lines verbatim into evidence quotes and validates their turn, role and phase. This avoids model rewriting of Markdown or language and preserves the stored annotation format. The source files, episode content and development sample match earlier versions, while the new provenance pin includes the selection schema and line-rendering version. Version 1 (`data/episode-pilot/pilot-v1.json`) and version 2 (`data/episode-pilot/pilot-v2/bundle.json`) remain archived and are incompatible with the current protocol. All 12 version 3 development drafts pass evidence validation and are available in the restarted review page; the 35 reserved episodes remain unannotated. Exact quote provenance does not establish that a label is correct; the drafts still require human review.

To generate machine drafts, provide `GEMINI_API_KEY` through the environment or this worktree's `.env`. This sends the selected split's dialogue to the configured Gemini service. Minchan explicitly authorized disclosure of the 12 development episodes, including student and tutor dialogue; this authorization does not cover the held-out split.

```sh
uv run python -m src.labeling.episodes annotate data/episode-pilot/pilot-v3/bundle.json --split development
```

Each successful episode is saved immediately; rerunning retries only missing/failed drafts. The model ID is pinned in the bundle. Restart the review server after annotating so it reads the new drafts.

After the development rubric has been reviewed, conduct independent human coding without model answers:

```sh
uv run python -m src.eval.episode_review data/episode-pilot/pilot-v3/bundle.json \
  --reviewer reviewer1 --task coding --split holdout
```

A second reviewer uses a different name. Blind coding never returns model annotations or legacy labels to the browser, including after save. Do not use the development reviewers on this holdout for a formal study without checking prior exposure. If the rubric changes, create a new version and reserve new evaluation conversations; do not edit a bundle in place.

For the representation comparison, separately generate the holdout drafts with the frozen rubric and authorized service. Run reviewers with `--task comparison --cohort 0`, `1`, or `2`. Each episode rotates through legacy-label, plain-timeline, and annotated-timeline conditions across cohorts; a reviewer sees only one representation of each episode. Raw dialogue is identical across conditions. Annotation conditions are refused when their machine draft is absent. This comparison is anchored by design and must be reported separately from blind coding.

Review JSON records judgments, exact evidence, optional instructor action, assigned condition, and elapsed time. It contains evidence quotes and is student data: keep it under ignored data/. Counts are preparation facts only. No human reliability, pedagogical usefulness, or simulation fidelity has been established by this implementation.

## Version 4 development preview

The [v4 codebook](2026-09-10-episode-codebook-v4.md) separates student action, assistance requested, tutor response, follow-up action, and task relationship. The protocol dispatches by `manifest.rubric_version`; a missing version means v3. The v3 prompt, schema hash, bundle, and seven saved reviews remain intact.

```sh
uv run python -m src.labeling.episodes prepare \
  ../main/data/snapshots/20260811-1d1e79d39fda-7bc759 \
  --rubric-version v4 --out data/episode-pilot/pilot-v4/bundle.json

uv run python -m src.labeling.episodes annotate \
  data/episode-pilot/pilot-v4/bundle.json --split development
```

Generation is complete following Minchan's explicit renewed approval to send the same 12 development episodes to Gemini. Source/sample content matches v3 exactly. All 12 saved drafts pass structural evidence validation; two first drafts were rejected for future request evidence and blank tutor evidence and then regenerated with the unchanged prompt. All 35 reserved episodes remain unannotated and match v3 exactly. `data/episode-pilot/pilot-v4/preview.md` compares actual v3/v4 predictions, preserves the seven earlier human judgments, and separates the assistant's semantic audit from both. Returned selections, including rejected drafts, are retained in `selections.jsonl`; preservation and validation facts are recorded in `verification.json`.

V4 is a file-based preview. The current three-field review server rejects five-field bundles, and the active page continues using v3. Do not treat old human judgments as annotations under the revised definitions. Verification: 240 Python tests and the review navigation checks pass, including v3 compatibility, evidence phase restrictions, paired citations, absence consistency, and resumable development-only generation.

Structural validation does not establish semantic support. Episode 7 captures the code-submission/hint/revision sequence, but infers confirmation intent from bare code. Episode 6 still assumes a task switch from a tutor-proposed question. Episode 5's retry cites a permitted student turn while its rationale still uses future tutor information. These outputs remain unaltered machine drafts; the separate audit flags them. The next proposed change is to remove future text from the request classifier's input, with stronger task-link evidence and a clearer distinction between tutor evaluation and supplying a solution. No additional human annotation is required for this calibration pass.

## Version 5: isolated intent input

The [v5 continuation](2026-09-10-episode-v5-input-isolation.md) implements separate stateless calls for pre-help student action/intent and after-help tutor response/follow-up/task relation. Field definitions remain those of v4. The before-help call receives only context and current request lines; after-help cannot overwrite its judgments. Both results must validate before an episode is saved. Failed episodes retry both calls.

```sh
uv run python -m src.labeling.episodes prepare \
  ../main/data/snapshots/20260811-1d1e79d39fda-7bc759 \
  --rubric-version v5 --out data/episode-pilot/pilot-v5/bundle.json

uv run python -m src.labeling.episodes annotate \
  data/episode-pilot/pilot-v5/bundle.json --split development
```

The prepared bundle already contains all 12 development drafts; preparation refuses to overwrite it and annotation skips completed drafts. V5 remains a file-based preview at `data/episode-pilot/pilot-v5/preview.md`; the three-field UI continues using v3. All 35 reserved episodes are unchanged and unannotated. Earlier v3/v4 artifacts and seven reviews are preserved.

All 246 Python tests pass. The real prompt hashes confirm the input restriction. Episode 5's intent is now unclear, while inference from permitted prior context remains in episodes 7 and 10. The preview distinguishes the technical boundary guarantee from these unresolved interpretations. No additional human annotation is needed for this pass.

## Version 6: checking work

Minchan approved separating checking existing work from supplying a completed new
answer or repair. The [v6 codebook memo](2026-09-10-episode-codebook-v6.md) records
the definition and request-interpretation anchors. V6 retains the two input stages
and omits blank model-visible lines without renumbering the source. All 251 Python
tests pass, including prior-version hashes, evidence rejection, and stage isolation.

```sh
uv run python -m src.labeling.episodes prepare \
  ../main/data/snapshots/20260811-1d1e79d39fda-7bc759 \
  --rubric-version v6 --out data/episode-pilot/pilot-v6/bundle.json

uv run python -m src.labeling.episodes annotate \
  data/episode-pilot/pilot-v6/bundle.json --split development
```

The prepared bundle is `bf03c1b5c407365b`, protocol
`7785fe56ca0b215038012e21577964067416a83ab6da06bfae1c9c68ed93a6db`.
Its source and sample match v5. The local `pilot-v6/run.py` wrapper restricts actual
prompt hashes to the same 12 authorized development episodes and records returned
selections, including rejected drafts. Earlier artifacts have preservation copies
and hashes under `data/episode-pilot/pilot-v6-preservation/`. The review UI remains v3.

## Version 7: derive recorded absence

V6 rejected three episodes twice for inventing follow-ups. V7 requests only a tutor
judgment when no student follow-up turn exists, then inserts the two recorded
absence values. It preserves blank observed student turns as present. The new
conditional schema, prompt, input rule, and fixed judgments are hash-pinned.

```sh
uv run python -m src.labeling.episodes prepare \
  ../main/data/snapshots/20260811-1d1e79d39fda-7bc759 \
  --rubric-version v7 --out data/episode-pilot/pilot-v7/bundle.json

uv run python -m src.labeling.episodes annotate \
  data/episode-pilot/pilot-v7/bundle.json --split development
```

All 12 v7 drafts completed on the first pass, with 24 returned stage selections;
seven absence pairs are derived directly. All 257 tests pass. The short comparison
is `data/episode-pilot/pilot-v7/preview.md`. Source/sample and all earlier artifacts
are preserved; the 35 reserved episodes remain unannotated. The existing UI remains
on v3. Tutor checking is now distinct, but mixed and task-link application errors
remain documented separately. No reliability or simulation-readiness claim follows.

## Fixed v7 model comparison and next review

The [model comparison](2026-09-10-episode-model-comparison.md) keeps the codebook and
all actual prompt bytes fixed while replacing Gemini 2.5 Flash with Gemini 2.5 Pro
in a separately identified development run. Pro corrected the two flagged tutor
judgments; task-link errors remain. The default model and prior outputs are unchanged.
Results: `data/episode-pilot/comparison-v7/comparison.md`.

The next human check is `data/episode-pilot/blind-v7/README.md`, with six cases in
two three-case files and predictions hidden. The source is outside pilot drafting
but not demonstrably free of earlier snapshot exposure. Save explicit chat answers
in `reviews-minchan.json`; do not invent citations or treat known absence as a human
judgment. No answers or model predictions have been recorded for this packet yet.

## Tutor component revision after three reviews

The packet status above records its initial preparation. Minchan subsequently
answered cases 1–3 and clarified that same-task means the tutor reply addresses
the request. Those original answers are saved with their clarified scope, without
altering student-follow-up labels. Cases 4–6 are paused, not another review task.

The [tutor-move revision](2026-09-10-tutor-moves.md) now represents co-occurring
functions explicitly in source order. It writes a separate tutor-only result using
`src/labeling/tutor_moves.py`; the existing review UI and v3–v7 outputs remain
unchanged. The local preview is `data/episode-pilot/tutor-moves-v1/preview.md`.

Minchan accepted the two displayed breakdowns. The subsequent v2 prompt check is
complete under `data/episode-pilot/tutor-moves-v2/`; known model errors remain.
The current human task is `data/episode-pilot/blind-tutor-moves-v2/cases-4-6.md`:
list functions present in three tutor replies. This replaces the paused v7 task for
those unanswered cases and does not ask for passages, ordering, or task relations.

## Return to the simulated-student objective

Minchan questioned why tutor labeling continued when the objective is simulated
students. The assistant's reassessment is that the fine tutor-passage work became
a detour: its value for student generation has not been demonstrated. Defer the
unanswered D–E passage review, retaining its frozen packet, empty answers, and
results. This is an assistant priority correction following the question, not a
new human endorsement of a model architecture or a changed label definition.

Tutor actions can describe experimental conditions and support instructor-facing
policy comparisons. A continuation model can instead receive the actual tutor
reply and prior dialogue directly. Fine passage boundaries and exhaustive tutor
component overlap should earn their role by improving a downstream result, rather
than becoming a prerequisite by default. Existing unreliable labels are not
silently promoted to the simulation state space or accepted as measurements.

The useful next diagnostic is a one-turn student continuation: hide the real next
student contribution and all derived future judgments; condition on only preceding
dialogue and the actual tutor reply; compare observable student actions, partial
work revisions, further help requests, and unsupported invented progress. The real
continuation is one observed outcome, not the only plausible answer. Begin with a
raw-dialogue baseline; test tutor metadata later only if it improves a defined
behavioral evaluation. Reliable evaluation, longer-history grounding, and the
existing archetype/IRB decisions remain necessary before cohort simulation claims.

A local structural inventory found that the selected 12 development windows have
only five recorded student continuations. The complete source conversations for
those same 12 development conversations contain 75 response opportunities, 64
with nonblank next-student text and 11 without a recorded continuation. These are
overlapping opportunities within already exposed conversations, not independent
learners or a fresh evaluation set. Counts and source pins are saved in
`data/episode-pilot/student-transition-readiness.json`. No additional windows were
sent externally and no simulator code or generated student replies were created.
Missing follow-up remains missing observation, not established disengagement;
visible revisions do not establish correct execution, understanding, or learning.

## Approved one-turn continuation diagnostic

Minchan asked to continue after the raw-dialogue baseline proposal. Run a bounded
feasibility diagnostic on the five original development windows with recorded
follow-ups (4, 6, 7, 11, 12), using Gemini 2.5 Pro and only the dialogue prefixes
already approved for that service. Prepare two stateless draws per window, retain
every result, and compare observable behavior with the separately stored recorded
continuation. Do not inspect or send additional windows from the 64-count inventory.

Each prompt contains only the existing earlier context, current student request,
and current tutor response, with no tutor labels, student labels, reviews, future
text, or examples drawn from target behavior. Save a minimal reply/no-reply output
with text; no-reply has empty text. Including that option provides a stopping
capability but does not calibrate it: selection is conditional on an observed reply.
Freeze the source, prompt, schema, model configuration, exact inputs, two-draw
schedule, and previous artifacts before generation. Check input isolation with an
invented future canary and verify cache identity and output consistency offline.

This explicitly authorized diagnostic proposes possible continuations of short
situations. It creates no persistent per-student persona, inferred personal traits,
archetype grounded in label profiles, cohort, policy replay, or admitted label state
space. The existing archetype/IRB and measurement decisions remain open; approval
to run this narrow diagnostic is not a claim that those decisions are resolved.
Keep the experimental driver in ignored data rather than adding a Phase 3 subsystem.

Audit each output for its visible action, comparable changes to prior student work,
task continuity, contradictions, and claimed off-chat activity. New code or reasoning
can be a plausible continuation even though it was not in the prefix. Claims of
execution, success, or understanding are unverified simulated reports, not observed
progress or automatic prediction errors. Real follow-ups are one observed outcome;
the assistant's comparison is qualitative development diagnosis, not independent
human evaluation, a fidelity score, or a causal result. Do not tune to these five
targets or ask another tutor-passage review before assessing this baseline.

The baseline completed all ten draws. Its initial outputs motivate one bounded
context ablation: remove earlier context while keeping the current student request,
tutor reply, generation instructions, model configuration, and two-draw schedule
unchanged. Run only the four cases whose inputs actually change; case 4 has no
earlier context and reuses its original draws as an identical-input reference.
Freeze the baseline outputs before the ablation and retain all results. This is
post-baseline diagnosis of dependence on visible history, not a preregistered
fidelity test or a claim that a small stochastic difference establishes an effect.
No new source dialogue or target behavior enters the prompts. Stop after this
comparison to identify what requires human judgment before further generator tuning.

Prepare a minimal human plausibility check using the first scheduled case and its
first draw, with the entire model-visible conversation. Ask only whether the next
student contribution feels plausible and, if not, what feels off. Permit cannot
tell; require no labels, passage boundaries, or rewritten reply. Omit the recorded
continuation from this view, while retaining it in the complete experiment report.
The material has prior development exposure and the generated reply is shown, so
this is qualitative feedback rather than blind measurement. A plausible answer
does not establish behavioral frequencies or justify copying one real next turn.

## Student-continuation results and current checkpoint

The raw-dialogue baseline completed ten structurally valid draws across five
development situations. The earlier-context comparison completed eight more across
the four changed inputs; the unchanged case reuses two baseline draws. These are
18 logical generation requests, not 20 independent draws. The shared adapter may
retry a logical request; individual transport/parse attempts were not logged. Every
saved output chose to reply. This sample contains only situations with recorded
follow-ups and cannot estimate response or disengagement rates.

In the grouping-expression example, both conditions produce identical code. In the
accumulation-repair example, both consistently implement the suggested structural
repair, while the recorded student revision retains a variable-name inconsistency.
In another example, full-context outputs ask for help on the earlier subproblem;
context-removed outputs acknowledge the guidance and state an intention to repair.
The remaining comparison preserves the broad work-check request but changes its
phrasing and specificity. Two draws per condition cannot establish a general
context effect. None of these static code comparisons demonstrates execution,
understanding, learning, or tutor-policy effectiveness.

The baseline is saved under `data/episode-pilot/student-continuation-v1/`, experiment
`5bffb1a328ed90f022bfc6912b14641e6ba5c64000b3db4a976359e26460ff49`.
Its `context-ablation/` experiment is
`374127afae212f7b2286cbda66e9eb9c128da82e7f8f9c2ac44575bb2a6a5d84`.
Both include every generated output and qualitative assistant comparisons; the
recorded continuations remain separate from model inputs. Fresh offline checks
passed for future isolation, reply consistency, cache identity, the context-only
transformation, and all 282 baseline / 288 comparison file pins. No production
agent subsystem or additional source windows were introduced.

The next human task is the single short `review.md` in the baseline directory:
judge whether the displayed generated student reply is plausible from the supplied
conversation, mentioning anything that feels off or saying cannot tell. Its
`human-review.json` remains unanswered. This checks an actual student continuation;
the earlier D–E tutor-label review remains deferred. Preserve these results before
any further generator tuning, and do not turn one plausibility judgment into a
fidelity score.

## First student-reply feedback and bounded style comparison

Minchan judged the first displayed continuation as substantively plausible while
finding that its style did not fit the visible student writing. This is feedback
on one shown output, not a human validation of the other draws or a fidelity score.
Preserve the pinned review request and append the exact response separately in
`data/episode-pilot/student-continuation-v1/human-review-response-1.json`.

The reviewed input contains only one student contribution. Its lowercase, informal
prose supplies limited surface cues; it does not establish an enduring style or
ability. Following the standing instruction to continue, make one bounded prompt
comparison on the same five already approved dialogue prefixes, with the same
model, schema and two-draw schedule. Add only a light instruction to use visible
student writing for wording, brevity, capitalization, punctuation and prose
formatting. Do not manufacture typos, modify code syntax or identifiers for style,
or infer ability, emotion or personality from typing. Do not insert a rewritten
answer, the recorded follow-up, human feedback text, or target behavior into any
generation prompt. Keep the original results unchanged.

Save this throwaway experiment under the baseline's `style-comparison/` directory,
reusing its runner and response schema. Retain all ten outputs. Inspect surface
style and substantive action separately, including code consistency, help-seeking,
and claims of progress; a more casual reply is not evidence of a more realistic
learner. The first case motivated the revision; the remaining four are previously
exposed development checks, not held-out validation. Freeze the proposed instruction
before generation and stop after this comparison to assess what it supports.

The style comparison completed ten valid replies, experiment
`1dc0495e07a83fe0a7df7e57abb6f76c11d670f6e7acfb4f7ba25e65dd102d18`.
A first execution produced only connection failures in the restricted environment.
Its ten failed logical requests and status were preserved under
`style-comparison/connection-failures/`; `network-retry.json` records why the same
frozen requests were repeated with network access. No generated output was discarded.
There are twenty logical requests across those attempts and ten generated replies;
adapter attempts within each logical request are not individually logged.

Both revised replies for the reviewed case begin lowercase and omit inline-code
formatting, while still asking for confirmation about rounding. That aligns with
some visible cues but does not establish the user's intended style correction.
The grouping expression remains unchanged and the accumulation repair remains
consistent. In the earlier-subproblem example, the new questions ask specifically
for ranges or for the reason to repair; those are substantive variations, not just
stylistic ones. The range-check example keeps its terse pattern with generated
endpoints. No output establishes execution, understanding, or learning, and the
small stochastic comparison does not establish an effect of the prompt change.

All outputs and these qualifications are in `style-comparison/report.md`. Its
first section shows both new draws for the already reviewed case and asks whether
they fit the visible student writing better. The original human feedback is
recorded; these revised outputs remain unreviewed. No additional tutor labeling or
production simulator code was introduced.
