# CLAUDE.md — Top-Down Labeling + Learner-Agent Simulation (one repo, temporary name)

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
No frontend until Phase 4 needs the instructor-facing views; results live in notebooks and
memos until then.

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
