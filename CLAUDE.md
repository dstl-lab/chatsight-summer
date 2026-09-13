# CLAUDE.md — Top-Down Labeling + Learner-Agent Simulation (one repo, temporary name)

## Current North Star (2026-09-11 clarification)

Minchan's primary inspiration is Generative Agents: an interactive world of
simulated students, engaging to explore as part of the broader goal of improving
learning amid technological and societal change. The first audience is
educators/researchers experimenting with student support. Minchan selected the
coaching direction (NBA2K/FIFA inspiration), deferred adventure and support placement,
and requested Animal Crossing stylistically, using original characters and assets.
Minchan then explicitly prioritized making the simulated students work before
designing the end product. Pause interface development; the exploratory storyboard
is preserved, not a current deliverable or a functioning student model.
The research context is in docs/2026-09-11-learning-expedition.md.
One invented worksheet/action loop with computed feedback is implemented in
src/eval/student_task.py; two live traces and their limits are recorded in
docs/2026-09-11-student-task-loop.md. It tests mechanics; human-audited real-data
fidelity remains a separate, incomplete requirement.
Four new-to-continuation development comparisons are complete in
data/episode-pilot/real-student-comparison-v1/ (docs/2026-09-11-real-student-comparison.md).
Specific send approval is recorded; all four generated replies and A/B review
pairs are preserved. Human review is complete; qualitative judgments and their
conditions are recorded separately without changing the original blank packets.
The bounded notebook audit in docs/2026-09-11-notebook-context-recovery.md found
omitted initial assignment context and first queries, plus reference-only grader
events. Later work changes remain unknown. Recover work context before tuning
communication; preserve the completed prompts and keep future observations out
of generator inputs. No additional model batch was run for that audit.
Recovery now has a supplemental snapshot and a one-cell edit/optional-chat path
(docs/2026-09-11-work-context-snapshot.md). Four initial exchanges are restored
without renumbering old turns; current work at the later cutoffs remains unknown.
Two initial-encounter draws are complete in data/episode-pilot/notebook-action-v1/.
Minchan specifically approved the exact disclosed payload after automatic review
initially rejected it; both approval and rejection are preserved. Both draws made
the same source revision without chat. Neither executed code or obtained feedback.
The private review.md presents that action once; Minchan accepted it as plausible.
The separate human-review-response.json preserves that judgment without implying
correctness or execution. All 16 pins still verify.
The new src/eval/notebook_check.py connects edits, requested computed fixture
feedback and optional chat (docs/2026-09-11-notebook-check-loop.md). It recognizes
two count-expression forms on authored data without executing candidate source;
unsupported code stays ungraded. An edit clears current feedback. The accepted
revision passed the limited scripted control. After Minchan's specific approval,
the bounded live trajectory in data/episode-pilot/notebook-check-v1/ completed:
request-check -> computed fixture pass -> no-reply, across two logical requests.
No new edit or message occurred. Exact offline replay and all 31 pins verify;
approval precedes both calls. Preserve the original automatic rejection,
approval and receipts. No candidate code or course grader ran; Minchan accepted
the new check/stop sequence as plausible, with that answer recorded separately.
This is one exposed development trajectory, not calibrated behavior.
The two authored controls in docs/2026-09-11-failed-check-continuation.md are
complete. notebook-failure-v1 reached an unsupported method and the action limit;
its final code is ungraded and no no-reply was generated. student-task-failure-v1
uses the existing structured worksheet: scripted failure -> generated correction
-> requested computed pass -> generated answer summary; stopped awaiting tutor.
All 17/14 pins and exact replays verify. These test mechanics, not learner fidelity.
Before another notebook behavior run, declare its runtime and checker capabilities;
do not conflate unsupported checks with student mistakes or patch spellings merely
to turn a retained run into success. The completed modules and traces stay frozen.
The new standalone src/eval/notebook_runtime.py now evaluates one cell inside an
explicit local Docker image (docs/2026-09-11-declared-notebook-runtime.md).
It separates checked answers, runtime errors, execution limits and environment
errors; only checked answers have Boolean success. Actual runtime, source,
revision, branch, activity, image, checker and timeout bind the observation.
Under newly declared environments, both retained authored revisions pass in
pandas 2.3.3 and raise AttributeError in Babypandas 1.0.0. The original unspecified
activity remains ungraded. All 13 new pins verify; no model requests were made.
The full suite passes 319 tests including isolated-container controls. The older
behavior loops are unchanged; the next new notebook trajectory must declare its
library before code selection and keep environment faults separate from learner
errors. The runtime checks cooperative code, not adversarial grading integrity.
The new src/eval/notebook_session.py connects that runtime to individual actions
without modifying the completed loops. Requested checks install verified feedback;
edits clear it, runtime errors stay ungraded, and environment/limit failures stop
the session. docs/2026-09-11-runtime-student-trajectory.md records the authored
three-decision probe, completed 2026-09-12. Its failed Docker setup attempt is
preserved; after recovery, a separately recorded actual runtime error preceded
three model choices: quiet revision -> requested actual pass -> no-reply. The
error was scripted, the correction/check/stop were generated. All 25 preparation
pins and six execution-file hashes verify; exact replay makes no Gemini or Docker
calls. The full suite passes 321 tests. This establishes one execution-backed
action/state example, not real-student recovery rates or learning. Human behavior
review remains separate; realistic work-context fidelity is the next bottleneck.
Minchan approved the three-case developmental review in
docs/2026-09-12-initial-action-review.md. It uses the remaining recovered initial
encounters (1/2/3), the frozen notebook_action prompt/schema, and one proposal per
case. Relevant captured supporting code is read-only; no code execution or later
state reconstruction is part of this pass. Keep all human fields blank until
review and all private payloads/results outside Git. Existing experiments stay frozen.
The three-case batch is complete in data/episode-pilot/initial-action-review-v1/.
Automatic review first blocked dispatch; Minchan then approved the exact disclosure,
recorded separately in approval-response.json before all three calls. Preserve the
original rejection and standing grant. All proposals revise the selected cell
without chat; no code ran and no grader outcome exists. Exact replay, 20 preparation
pins and nine completion-file hashes verify. Human review is complete in the separate
human-review-response.json: cases 1/2 plausible, case 3 plausible but leaning toward
implausible because finishing both functions after one tutor response seems doubtful.
Do not count the third judgment as an unqualified acceptance or binary rejection.
The original packet and its blank fields remain unchanged. An invented offline
check confirms partial edits already fit the schema; a source revision has no
defined duration or silent-attempt count. The next bounded probe should compare
original versus neutral partial-work wording with fresh draws, keeping cases 1/2
as controls, without forcing mistakes or inventing ability. This is a wording
diagnostic, not pacing calibration. The Markdown review is cumbersome but usable;
show future cases individually and defer a new review UI. No new calls were made
while recording feedback or checking the action contract.
Minchan approved that comparison; docs/2026-09-12-progress-wording.md defines six
fresh requests, original/clarified per case, in data/episode-pilot/progress-wording-v1/.
Tasks and state JSON stay identical; the sole prompt addition neutrally permits
unfinished work. Do not feed earlier generated actions or human verdicts into it.
No execution, pacing calibration or fidelity claim is part of this probe. Present
one case per Markdown file, retain both candidate receipts even when identical,
and preserve all completed sources and earlier reviews.
That comparison completed after Minchan's separate exact-prompt approval, which
precedes all six calls. Preserve approval-response.json and the earlier rejection.
Six silent revisions completed without retries; cases 1/2 are identical pairs,
and both case-3 draws fill one function while leaving the other unfinished. Since
the original wording also produced partial work, this batch does not establish
an added benefit from clarification; do not adopt a prompt change on this evidence.
Exact replay/31 preparation pins and 12 completion hashes verify. No code executed.
Case 1 repeats the previously accepted action with identical context; case 2 only
adds a final display expression to its earlier proposal. Keep new judgment fields
blank and earlier reviews separate. Minchan accepted both case-3 partial edits as
plausible and noted only variable-name differences; human-review-response.json
records the exact reply and both judgments. No condition preference or new case1/2
judgment is inferred. Close this diagnostic and retain the original prompt; no
further wording batch is needed. The next useful check is continuity from accepted
partial work using existing actions and explicit generated-state provenance, with
no invented intervening tutor reply, execution or outcome. This is not evidence
of calibrated action frequency, learning or a need for a new memory framework.
Minchan approved that continuation. docs/2026-09-12-partial-work-continuity.md
defines one next action in data/episode-pilot/partial-continuity-v1/, seeded from
progress-wording-v1 case3 original/call4. Current work is exact generated revision1;
the single model history event retains revision0, with no new tutor/feedback/run.
Original prompt/schema/settings remain fixed, and human acceptance stays outside
the input. Keep captured_at explicitly tied to the original capture, not generated
work or inferred time. All previous experiments and human reviews remain frozen.
That request completed after Minchan's separate exact-payload approval. Preserve
approval-response.json, the prior rejection and the standing grant. One quiet
edit fills the remaining function while preserving the earlier function and all
calling code; work advances 1→2. No tutor turn, chat, execution or outcome occurs.
Exact replay/50 preparation pins and nine completion hashes verify. The private
review.md retains its original blank human fields. Minchan accepted quietly
finishing the remaining function as plausible after an inline clarification of
the available guidance, earlier formula and exact change. The separate private
human-review-response.json records that answer and six evidence hashes. Close
this example; retain the earlier qualified judgment of the one-proposal solution.
Two model calls do not establish two real attempts, elapsed time or frequencies.
The next step in docs/2026-09-12-student-evaluation-readiness.md is an offline
inventory of existing snapshots and a fixed four-conversation context-recovery
candidate list. Reuse the extractor and existing exposure ledgers; do not send
models, query the DB, assign semantic labels or alter generators for this check.
Prior label audits and source searches preclude a pristine-holdout claim. An
observed next message cannot measure silent edits; historical initial code is
not current work at a later cutoff. Keep private metadata outside Git.
That inventory is complete in data/episode-pilot/evaluation-readiness-v1/.
Eight snapshots contain 252 distinct conversations; the primary source has 55
eligible windows across 24 conversations after known exposure and prefix filters.
Four distinct candidates are fixed using the existing raw-string digest; an
earlier JSON-ranking preparation is preserved as superseded, without target
review or model dispatch. All four have complete timestamps but no recovered
initial work. Exact regeneration, future-text isolation and 32 hashes verify;
an independent check matches the saved candidate metadata. No model/DB calls.
Next recover context for those fixed candidates via the existing read-only
ingestion path; preserve missing cases and distinguish initial captures from
unknown later work before constructing any generator payload. No user review is
needed for this inventory. Do not extend the count-only runtime to grade the
accepted two-function exercise merely to continue a closed development example.
Context recovery is complete in data/episode-pilot/evaluation-context-v1/;
docs/2026-09-12-evaluation-context-recovery.md records the bounded read-only queries.
Cases1/3/4 align; case2 has two matching unlinked initial queries and remains
ambiguous. Preserve it rather than selecting the nearer query or substituting a
case. Nineteen sources/three outputs verify; failed tunnel/query attempts remain
separate. All later work is still unknown and reference checks stay excluded.
Continue with docs/2026-09-12-context-grounded-communication.md: one fresh
communication proposal for each recovered case, original continuation prompt and
schema, explicit historical selected cells, null current work/observation, no
invented intermediate execution. This is conditional development comparison,
not reply-rate calibration or simulated notebook actions. User explicitly
reiterated continuing until a concrete human review is needed; do not stop after
routine preparation/verification milestones or request routine run permission.
The three requests are fully prepared in data/episode-pilot/evaluation-communication-v1/.
All 35 pins and both private checks pass; independent payload audit found no
material issue. Automatic approval review rejected the actual send before
process launch, requiring this exact private dialogue/code disclosure to Gemini
to be approved separately. send-blocked.json preserves the rejection/question
and five hashes. Minchan then approved the exact requests; the separate
approval-response.json binds that reply to the unchanged preparation and prior
rejection. All three calls completed in order without retry notifications and
selected reply. No student code ran and no current observation was supplied.
Exact replay, 35 preparation pins and 14 completion hashes verify; all three
review pages reproduce identically. An independent audit checked source text,
hidden origin mappings and five approval links; approval precedes every call.
Minchan tentatively prefers case1 A over B because the tutor already supplied
the complete function, making sending it back unnecessary. The separate private
human-review-case-1.json preserves the exact reply and six evidence hashes;
neither candidate receives an absolute verdict. Case3 B is preferred conditional
on prior evidence of student awareness that the tutor sees the notebook; the
separate human-review-case-3.json preserves this qualification and seven hashes.
The visible short notebook references are consistent with shared context, but
explicit awareness and a broader trend remain unknown. Minchan judged case4's
messages equivalent, without a preference or absolute plausibility verdict.
human-review-case-4.json and human-review-summary.json close this review while
preserving the original blank fields. Recorded messages were preferred with
qualifications in cases1/3; case4 was equivalent. No accuracy score follows.
Next, docs/2026-09-13-communication-channel.md defines six fresh paired requests
with the same three inputs and one neutral chat-channel clarification. Preserve
the original prompt; neither force terse/no-code replies nor assert the student's
knowledge of tutor notebook visibility. All six exact requests are now prepared
in data/episode-pilot/communication-channel-v1/. The only insertion is 220
characters; paired JSON is byte-identical. All43 pins and both invented checks
pass, including the runner/reviewer seam, with independent audit confirmation.
Automatic approval review initially rejected dispatch before process launch;
send-blocked.json preserves the actual rejection/question and six hashes.
Minchan then approved all six exact requests; approval-response.json binds that
reply to the unchanged preparation and prior rejection before every call.
All six calls completed with no retries and selected reply. Exact replay/43 pins
and14 completion hashes verify; the three review pages reproduce identically.
Independent audit confirms five approval/six rejection links, approval timing,
all candidate mappings and blank human fields.
Case1 pairs an acknowledgment with a function; case3's functions differ only in
formatting; case4's messages both ask about choice2. No code ran or work changed.
All new human fields remain blank and no prompt change is adopted. Begin with
chat-review-case-1.md's single new acknowledgment, keeping its condition hidden;
this asks only about candidateA, with B and cases3/4 unjudged. Preserve earlier
qualified preferences without transferring them into fresh candidate judgments.
Do not reveal origin-key.json before recording the judgment or infer any verdict
from request-send approval. Preserve case2's ambiguity and all completed evidence.
Labeling and continuation diagnostics
support this goal. Behavioral fidelity, educator usefulness and real learning
outcomes remain separate questions; the invariants below still apply.

## What this project is

Research codebase with two subsystems (decision memo:
`docs/2026-08-01-topdown-labeling-same-repo.md`):

1. **Labeling — top-down, instructor-facing.** The instructor states what trends they want
   to see from the data — conceptual ("which topics are students struggling with"),
   behavioral/affective ("confused, satisfied, angry"), or other. The tool pulls a
   *stratified* sample of real messages, drafts labels against that intent, and shows the
   labeled sample. Instructor accepts the direction → mass-label the corpus; or tweaks by
   describing what they want differently → new prompt, new draft, review again. Every tweak
   iteration is a new schema version.
2. **Simulation.** LLM agents grounded in real students' logged behavior with an AI tutor,
   used to screen tutor-policy changes ("never give direct answers," "answer-then-probe")
   against a synthetic cohort **before any real student is exposed**. Consumes the labeling
   subsystem's output as the **state space of the simulation**.

Raw data: DSC 10 tutor chat logs in an external PostgreSQL database (`dsc10_tutor_logs`),
reached read-only via `kubectl port-forward` into the Kubernetes cluster — the same access
pattern ChatSight uses (see its README for tunnel setup; replicate the pattern, not the code).

An agent is a thing that moves through label-space ("instrumental ask" → "got hint" →
"re-engaged" vs. → "extracted answer" vs. → went silent). The classifiers are the projection
that maps any transcript — real or synthetic — into that space. A "policy effect" is a shift
in the distribution of trajectories through it.

## The relationship to ChatSight — READ THIS FIRST

**ChatSight (`github.com/minchan/chatsight`, local: `~/github/chatsight`) is a sibling, not
an upstream.** It does bottom-up labeling (instructor labels first, classifier generalizes)
for its fall instructor pilots; this repo does top-down intent-compiled labeling. Both read
the same raw-log database. This repo was deliberately created outside ChatSight so research
cadence never destabilizes those pilots.

**Rule 1 — Never modify ChatSight from here, never import or vendor its code.**
Reference its conventions freely (kubectl tunnel pattern, backend stack, .env layout). This
repo's classifier is a deliberate independent reimplementation — not a fork claiming
equivalence. Corollary: **labels produced here and labels produced by ChatSight are never
compared or mixed in any claim** unless a dedicated calibration study earns it.

**Rule 2 — Classifier parity is the load-bearing wall (now internal).**
Every fidelity and policy claim depends on synthetic transcripts being scored by *the same
classifier that labeled the real corpus* — same prompt/config hash, same schema version.
Every results artifact records: schema version ID, classifier prompt/config hash, corpus
snapshot ID, model IDs. No orphan numbers.

**Rule 3 — The live-DB boundary runs inside this repo.**
`src/labeling/` and `src/ingest/` may open the raw-log Postgres (read-only, through the
tunnel). The labeling subsystem's output is an immutable labeled-corpus snapshot in
`data/snapshots/<id>/` (JSONL: conversations, turns, label applications, schema version)
with a manifest (export date, schema version, classifier hash, row counts). The simulation
subsystems (`eval/`, `trajectories/`, `agents/`, `replay/`) consume **only snapshots, never
the DB**. If labels change, that is a *new snapshot*; old experiments still reproduce
against the old one.

**Rule 4 — Student data never enters git.**
Snapshots contain real students' conversations (IRB-covered, DSC 10). `data/` is gitignored
from the first commit. Same for `.env`, API keys, and anything derived that quotes verbatim
student text. Check `git status` before every commit; if a student utterance appears in a
committed file (including notebooks and test fixtures), treat it as an incident: purge
history, tell Minchan.

## Non-negotiable research invariants

1. **Evaluation ground truth is human-labeled real data. Always.** Synthetic/generated data
   may train, densify few-shot pools, or probe boundaries — it never sits in an eval set and
   never judges anything. The whole chain is Gemini four layers deep (drafts labels → mass-
   labels → plays the student → scores the result); the human-audited sets are the only
   contact with ground truth. Guard them.
2. **Judge classifiers against the human-agreement ceiling, not 100%.** If two instructors
   agree 80% on a label, a classifier at 78% is near-perfect and an agent at 75% agreement
   with real students may be near the achievable maximum. Every reported agreement number
   carries its ceiling next to it.
3. **A label enters the simulation state space only if its classifier clears the admission
   threshold** (Phase 0 defines it; human decision #1 below). Unreliable labels stay
   analytics-only in ChatSight; here they are poison.
4. **Personas are cluster-level archetypes, not per-student agents.** Grounded in label-
   trajectory profiles and behavioral summaries, not verbatim reproductions of one student's
   turns. This is both an IRB position and an honesty position about the method's resolution.
5. **Claim discipline.** Allowed: "policy X changed simulated help-seeking behavior (fidelity:
   …)"; "agents reproduce the labeled behavioral/transition distribution of the real cohort."
   Never allowed, not even hedged: "policy X improves learning"; "policy X would work with
   real students." The contribution is a *screening instrument* — it narrows twenty candidate
   policies to the three worth a real quarter.
6. **Experiments pin a schema version.** Label schemas evolve upstream (merge/split/rename).
   An experiment binds to one schema version + one snapshot; cross-version comparison is its
   own explicit analysis, never an accident.
7. **Agents must be able to not respond.** Quiet exit (student silently defects to ChatGPT /
   gives up) is the most important negative signal in the framing. An agent that always
   replies cannot reproduce it; model non-response as a first-class action from day one.
8. **Blind measurement, anchored drafting.** The review-and-tweak loop shows model-drafted
   labels — anchored, fine for *drafting*. Reliability numbers for the admission threshold
   come only from instructor labels produced blind (messages without model labels), on a
   held-out sample never used in the tweak loop. Approval of a shown label is not ground
   truth; anchoring inflates agreement.
9. **Stratified review samples.** Samples shown to the instructor are deliberately composed
   (model-uncertain, embedding-diverse, boundary cases), never the first N or a uniform
   random pull — rare behaviors (quiet exit, answer-extraction) are the point and won't
   surface in a quick random sample.

## Phase plan (full details in the pipeline memo)

Each phase has a publishable fallback; never let a phase's success become a bet the next one
must win.

- **Phase 0 — classifier eval harness. START HERE; blocks everything.** Per-label
  precision/recall vs. human-audited held-out real messages; human-agreement ceiling from
  double-labeled samples; admission threshold proposal. Runnable on the first DSC 10 snapshot.
- **Phase 1 — intent-compiled schema.** Elicit the instructor's *what-if question* / desired
  trends, backward-chain to required constructs, run the draft→review→tweak loop
  (invariants 8–9), verification gate = boundary cases + negative-space coverage + per-label
  reliability (invariant 3). Lives in this repo's `src/labeling/` — the first
  instructor-facing surface.
- **Phase 2 — trajectories.** Mass-labeled corpus → label trajectories per conversation →
  empirical transition matrix (grounding data, fidelity target, and screening baseline all at
  once) → 4–7 clustered archetypes. *Standalone paper fallback: descriptive dynamics of
  help-seeking in a real AI-tutored course.*
- **Phase 3 — agents + fidelity.** Held-out turn prediction (agent generates turn k+1; real
  and synthetic both classified; agreement measured **on labels**, against the ceiling);
  distributional fidelity (does the cohort reproduce the spread, or collapse to a modal
  agent?); transition fidelity (dynamics, not marginals); fidelity-vs-depth decay curve
  (report the usable horizon). All on historical data, no live students. *Fallback: a
  rigorous failure characterization of LLM learner simulation is itself a contribution.*
- **Phase 4 — replay + policy screening.** Multi-turn replay of variant tutor policies ×
  archetype cohort → scored → diffed against the Phase 2 baseline. Instructor study (3–5
  instructors) observing what they *decide*. Interface contract: policy in → inspectable
  cohort out; aggregate numbers click through to individual synthetic trajectories;
  per-construct confidence shown as ranges; flag policies whose gains concentrate in
  low-confidence label regions (a policy can game the classifier, not the learning).

## Suggested layout

```
CLAUDE.md                  ← this file
docs/                      ← memos, dated `YYYY-MM-DD-topic.md`, discussion-memo register
data/                      ← gitignored; snapshots/<snapshot_id>/ with manifest.json
snapshots.md               ← human-readable ledger of known snapshots + provenance
src/
  ingest/                  ← raw-log DB access (tunnel) + snapshot loader/manifest validation
  labeling/                ← Phase 1: intent elicitation, stratified sampling, draft
                             classifier, review/tweak loop, mass-label → snapshot emission
  eval/                    ← Phase 0 harness (first real code)
  trajectories/            ← Phase 2 extraction, transition matrices, archetype clustering
  agents/                  ← Phase 3 persona construction + generation (incl. non-response)
  replay/                  ← Phase 4 engine + policy variants
  scoring/                 ← thin wrapper pinning this repo's classifier config — no logic here
experiments/               ← one dir per experiment: config (pins), results, notebook
```

Python-first; match ChatSight's backend conventions where sensible so context transfers.
Frontend work is paused by Minchan's latest instruction. Build and evaluate the
student behavior loop before returning to the selected coaching presentation.

## Decisions already made (don't relitigate without new information)

- Separate repo from ChatSight, as a *sibling* sharing only the raw-log data source
  (2026-08-01 memo). Chosen so pilot-facing ChatSight stays stable through fall. Price:
  independent classifier with no label-continuity to ChatSight's corpus.
- Labeling is top-down intent compilation with an instructor review/tweak loop; drafting may
  be anchored, measurement must be blind (invariants 8–9).
- Archetype-level personas, not per-student (invariant 4).
- Intent-first (top-down) schema drafting is *compilation of instructor intent*, arbitrated
  on real data — not a return to upfront rubrics. The instructor's arbitration sample is the
  metrological foundation of everything downstream.
- Synthetic data: amplifier, never substitute; human labels define, synthetic multiplies,
  real data judges.

## Open decisions — need Minchan (and usually Sam). Do not decide unilaterally.

1. Admission threshold for the state space (blocks Phase 1 gate design).
2. Archetype granularity the data actually supports.
3. Schema freeze/migration policy across quarters.
4. IRB: confirm archetype personas from label profiles are within the existing protocol /
   amendment scope **before Phase 3 code exists**.
5. Who owns the DSC 10 tutor's prompt/policy surface (prerequisite for any replay; open
   since the July memo — it's an email, chase it).
6. Kubernetes credentials/namespace for this repo's own read-only tunnel to
   `dsc10_tutor_logs` (replaces the dissolved ChatSight-export question).
7. Permanent name for this repo/tool — current name is explicitly temporary.

## Related work you must know before writing anything

Park et al., *Generative Agents* (arXiv 2304.03442) and *LLM Agents Grounded in Self-Reports*
(arXiv 2411.10109) — method provenance; we transpose grounding from self-reports to
behavioral logs. **PromptDecipher** (arXiv 2605.16605) — closest neighbor and the clock
pressure: validates tutors on pre-defined scenarios, not real course logs; our differentiator
is grounding + instructor-authored metrics. TutorGym (arXiv 2505.01563) — replay for agent
benchmarking, researcher-facing. EvalGen / "Who Validates the Validators" (UIST 2024) —
criteria drift supports the bottom-up gate. AIED/EDM simulated-student literature simulates
*generic* novices from knowledge models; we instantiate from one real course's labeled
behavior. Re-run the novelty search before each paper; this area moves monthly.

## Working style

- **Standing model-run approval (2026-09-11).** Minchan explicitly said: "Yes, you
  always have the approval. Make sure to log this." This authorizes continued model
  runs for this project's student-simulation and labeling work, including new batches
  and prompt iterations with the established provider, Gemini. Do not ask again for
  routine batch approval. Record each experiment's scope and results; human judgments
  of generated behavior remain separate. The exact response and the immediately
  approved batch are recorded in
  `data/episode-pilot/student-continuation-check-v1/interaction-comparison/approval-response.json`.
- Every substantive direction change gets a dated memo in `docs/` *before* the code — that is
  how this project thinks. Match the register of the existing memos: claims carried with
  their limits, "honest limit" sections, must-cite tables.
- When results look good, the next task is attacking them (circularity? register cue? ceiling
  effect? snapshot leakage into eval?). When they look bad, characterize precisely — that is
  the Phase 3 fallback paper.
- Context: Minchan is applying to PhD programs (HCI/CS-ed, fall 2027 entry) with this work as
  the centerpiece; Sam Lau (UCSD HDSI) advises. Evidence that exists by **December 2026**
  matters more than elegance. Paper 2 drafting starts mid-October (CSCW rolling / L@S
  ~mid-Jan / LAK); Phase 0 + a Phase 2 descriptive result are the December targets.
