# Student simulation: evidence and the next decision

Prepared for Minchan's research team meeting, 2026-09-14. This is a research
assessment and a proposed milestone, not a new experiment authorization or a
claim that the proposed benchmark has been run.

## Assessment

We have an auditable prototype that can propose student messages and notebook
edits, request execution, consume feedback and explicitly choose to stop. We
have not established that its choices reproduce real students' behavior. The
early reviews found useful requirements; repeatedly asking whether another
message sounds plausible now has diminishing value. Each pilot had a local
stopping rule, but the project lacked an agreed evidence target for ending the
pilot phase. Continuing that loop put too much review work on the instructor.

The next milestone should test a limited claim about observable behavior against
a simple baseline. It should not require an exhaustive student taxonomy. More
chat review cannot recover notebook events or learning outcomes that are absent
from the observations.

## What has been built and learned

1. Broad, overlapping message labels evolved into episodes and ordered tutor
   response components. A tutor reply can explain, guide and ask a question;
   the catch-all label "mixed" hid useful structure.
2. Student continuation reviews exposed communication habits: terse checks,
   copying supplied work, language choice, and the difference between possible
   and likely responses. These are development observations, not calibrated
   persona traits or population estimates.
3. Notebook actions were separated from chat. A quiet edit is possible without
   a message; a chat code block does not prove an edit or an execution. A
   source revision invalidates old feedback, and an execution result must be
   bound to the source and declared environment that produced it.
4. A saved authored example connects those mechanisms: an imposed Babypandas
   error is followed by a generated quiet revision, a generated check request,
   an actual result of 3 with passing feedback, and generated no-reply. The
   task, data and initial error were researcher supplied. This demonstrates
   execution and state handling; it does not measure student recovery or learning.
5. A fixed communication review now provides a descriptive result beyond
   individual anecdotes. All 24 candidate messages were judged plausible,
   while their primary action mix differed.

| Primary message action | Recorded messages (8) | Generated messages (16) |
|---|---:|---:|
| Help/checking request | 4 | 0 |
| Code submission | 2 | 6 |
| Code revision | 1 | 2 |
| Non-code work | 1 | 5 |
| Acknowledgment | 0 | 3 |

These are eight conversation cases with two generated draws each, not 16
independent students. They are exposed development cases selected to have a
recorded follow-up. One instructor reviewed fit; action/task labels were
assistant-suggested and human-approved. Substantive work takes precedence over
an attached question, so zero primary help labels does not mean zero questions.
Two reference help labels have documented alternative work readings; using both
would reduce the reference help count to 2/8, without changing the generated
0/16. Preserve the accepted labels. These findings warrant investigation, not
a population claim, statistical significance claim or accuracy score.

Task relationship was uncertain for 3/8 references and 12/16 generated replies;
only two generated/reference pairs were known on both sides. This metric is not
currently informative enough to lead the evaluation.

## Is this a decision tree or a Markov chain?

The implementation is an LLM choosing actions inside a stateful runner. The
action menu is small, but messages and source edits are open-ended. The runner
updates work and feedback and controls when code can execute. No giant tree of
student responses has been enumerated, and no transition matrix has been fitted.

One can write a Markov-style description by including the whole available
history in the current state. That does not show that a compact label such as
"test failed" contains enough information to predict student behavior. Knowledge,
intentions and some activity are unobserved. A partially observed decision
process is a useful conceptual framing, but this prototype has no fitted latent
learner dynamics, belief update or reward optimization. It is not a validated
POMDP or evidence that students themselves follow a simple Markov process.

A transition-frequency model would be a useful inexpensive baseline. The
question is whether richer history or labels add predictive value beyond it.
Labels should earn their role as measurements or useful summaries; they do not
need to enumerate every human circumstance before a simulator can exist.

Park et al.'s Generative Agents motivates memory, retrieval and believable
behavior, and evaluates components through ablations. Our distinct challenge is
fidelity to recorded educational behavior. Its results do not validate our
students or establish learning effects. [Primary paper](https://arxiv.org/abs/2304.03442).

## Data limits

The inventory covers 455 conversation records across eight overlapping snapshots,
with 252 distinct conversation IDs, not necessarily distinct learners. In the
primary snapshot, 110 of 147 request/response opportunities have a subsequent
student contribution; the 37 absences can reflect export boundaries and cannot
be used as observed no-reply decisions.

Recovered initial notebook captures do not establish current work at a later
turn. Missing linked revisions, execution results and observation boundaries
prevent validation of silent-work sequences and stopping probabilities. The
current work also does not establish hidden sentiment, longitudinal learning,
generalization to other courses or causal effects of changing the tutor policy.

## Proposed finite milestone

**Question:** given the visible student history and tutor reply, how well does
the model predict the action of the next recorded student message? This is
conditional on a recorded message; it does not estimate whether a student replies.

Propose a two-week milestone, with a data/readiness decision after the first two
working days. These are planning budgets for team agreement, not scientific
success thresholds.

- Inventory usable encounters and prior exposure. Group by student when identity
  is known, otherwise by conversation and disclose that weaker separation.
  Previously inspected cases remain development data. If fresh evaluation data
  is unavailable, report an exploratory analysis and seek suitable new records;
  do not rename an exposed set a pristine holdout.
- Freeze the existing observable-action definitions, inputs, split, budget and
  analysis before evaluation. Two reviewers independently code a bounded sample
  of recorded messages. Preserve ambiguity. If the action distinctions cannot
  be coded reliably, simplify or clarify them on development data before freezing
  the evaluation set; do not revise categories after seeing model results.
  Predefine adjudication and which unresolved cases are excluded from the score;
  report that coverage and every exclusion. Annotation uncertainty is not a
  student action. Check the output-labeling procedure independently and include
  that review work in the fixed budget; if it is unreliable, stop at readiness.
- Compare a training-set frequency baseline and, where prior actions are known,
  a smoothed transition baseline with a model using raw visible history. A
  label-augmented model is one optional, separately specified addition. This
  tests whether the labeling machinery adds value instead of assuming it must.
- Estimate next-action probabilities from a fixed number of fresh generator draws
  per encounter, with sampling and labeling rules fixed beforehand. Score them
  using multiclass Brier score (lower is better). Account for sampling noise and
  retain model errors/no-reply as separate outcomes, rather than silently dropping
  them or treating them as observed student stops. The old two-draw pilot supplies
  no such benchmark score. Asking an LLM to state a probability vector would be a
  separate forecasting task; those numbers cannot be assumed to describe the
  continuation generator's actual choices.
  Report per-action performance and uncertainty, accounting for repeated
  encounters within conversations/students. Exact wording or agreement with a
  single recorded message is not simulation accuracy.
- Retain context-fit review as a secondary failure screen. Keep state consistency
  separate: fabricated outcomes, unobserved edits and stale feedback are mechanism
  failures, not low student ability. Keep unknown observations explicit.

Beating a frequency/transition baseline does not isolate history's causal
contribution: the model and its inputs differ in several ways. Only a controlled
input comparison could support that narrower attribution.

The team should set the practical improvement margin and sample/call budget
before running the comparison, informed by data availability and uncertainty.
Do not invent a reliable "80% realism" threshold. No new benchmark or calls are
part of this meeting preparation.

## Stop, continue or pivot

End the milestone at its fixed report even if the result is inconclusive.
There is no automatic next batch.

| Evidence at the gate | Decision |
|---|---|
| Required observations or reliable action coding are unavailable | Stop model tuning; improve capture or narrow the claim to observable chat |
| Richer model does not improve over the baseline by the agreed margin, or uncertainty cannot support that conclusion within the budget | Retain the simpler model; report the limit; require a new research decision before extending |
| A recurring failure supports one specific hypothesis | Allow at most one planned revision tested on reserved evaluation data; no repeated prompt/review cycle on the same cases |
| Improvement is supported and state consistency holds | Proceed to a separate short-sequence benchmark with linked notebook events |

A successful next-message benchmark would justify the next stage, not a claim
that we can estimate learning or rank tutor policies. Those claims require their
own observations and validation. A rigorous account of why the available data
cannot support a stronger simulation claim is itself a concrete research result.

## Meeting decision and immediate status

Recommend agreeing on observable next-action prediction as the first fidelity
milestone, assigning data and independent-review owners, and fixing its budget
and comparison rules. Keep the coaching interface and broad persona taxonomy
deferred. The instructor should review consequential ambiguous definitions and
the final decision, rather than approve an endless stream of generated messages.

The proposed history-ablation experiment is paused before preparation/dispatch.
Its private implementation drafts are incomplete; no results exist. Completed
experiments and production modules remain unchanged. This assessment and the
pause are documented on `codex/episode-pilot` for draft PR 25; no merge is requested.

## Evidence for the presentation

- [Saved runtime mechanism](2026-09-11-runtime-student-trajectory.md)
- [Data readiness inventory](2026-09-12-student-evaluation-readiness.md)
- [Closed communication evaluation](2026-09-13-fixed-communication-evaluation.md)
- Private exact counts and notes: `data/episode-pilot/fixed-communication-eval-v1/REPORT.md`
- Private authored execution receipts: `data/episode-pilot/runtime-student-v1/`
- Private meeting deck and builder: `data/episode-pilot/team-update-2026-09-14/`

The presentation uses aggregate counts and an authored runtime example; it does
not embed raw student messages or credentials.
