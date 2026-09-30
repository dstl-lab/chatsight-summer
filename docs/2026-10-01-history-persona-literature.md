# Student history, personas, and behavioral fidelity: literature review

**TL;DR:** The general idea has been studied, including history-conditioned
tutoring dialogue, student code revisions, and correct-versus-shuffled persona
controls. We should build on that work. The useful question here is whether
recorded history improves predictions of programming-assistant usage over a
generic simulator, while preserving variation between and within accounts.
Exact replay of one recorded future is not the objective. Our current ten-case
development set is too sparse to treat every account as a well-supported persona.

Reviewed 2026-10-01. This is a targeted literature review, not an exhaustive
systematic review or a claim that a research niche is unoccupied. Search themes
were history-conditioned student simulation, personalized user simulation,
programming submission trajectories, distributional fidelity, and shuffled-persona
controls. We followed primary papers and their references; publication status is
only stated where verified. Paper findings below are authors' reported results,
not independent replications. Design recommendations are our inferences.

## Closest precedents

| Primary source | What it evaluates/reports and what we should borrow | Boundary |
| --- | --- | --- |
| [Who Am I? History-Aware Profiles for Student Simulation in Tutoring Dialogues](https://arxiv.org/html/2605.30051v2), Duan et al., 2026 preprint, v2 | Directly studies next tutoring turns conditioned on earlier question-answer records and dialogues. Compares history and profile approaches, with a trained profile generator and simulator. Uses student-separated evaluation and measures acts, correctness, errors, and language similarity. This is the closest precedent for our history-conditioned chat proposal. | One math dataset and turn-level evaluation. Its future work explicitly includes when students request help, fully simulated dialogues, and programming. A profile prompt alone is not the same intervention as its trained system. |
| [ParaStudent: Generating and Evaluating Realistic Student Code by Teaching LLMs to Struggle](https://arxiv.org/html/2507.12674v1), Miroyan et al., 2025 preprint | Uses real introductory-programming submission streams, contrasting prompting and fine-tuning. Evaluates semantics, functionality, style, and progression at different temporal resolutions. Includes unseen-student and unseen-problem tests. Borrow multidimensional code evaluation rather than exact strings or correctness alone. | One course. Its high-resolution experiment conditions each next submission on real prior attempts; the authors leave freely generated full streams to future work. Our sparse notebook captures are not equivalent to its submission streams. |
| [INSIDE the Student's Mind: Jointly Modeling Latent Reasoning and Action in LLM Student Simulators](https://arxiv.org/html/2608.10492v1), Niousha et al., 2026 preprint | Predicts the next student code submission from prior attempts and AI-tutor feedback. Compares generated and real distributions of pass rates, code length, syntax-tree structure, and style using Wasserstein distance. This directly overlaps programming behavior after tutor feedback. | Internal reasoning is reconstructed by a teacher model, not observed student thought. Code-conditioned reasoning alignment cannot establish psychological truth. Its evaluated action is a next submission, not the full choice among chat, editing, execution, and stopping. |
| [CoderAgent: Simulating Student Behavior for Personalized Programming Learning with Large Language Models](https://arxiv.org/html/2505.20642v1), Zhan et al., IJCAI 2025 | Models programming practice using knowledge/ability memory, planning, reflection, and compiler feedback. Evaluates next submissions, modification intentions/locations, code similarity, and correctness on real datasets. Borrow explicit state and feedback grounding. | The abstract's broad data-independence wording should not obscure the history-conditioned formulation and real-data evaluation. Some judgments are model-based. These results do not validate frequencies of asking for help or quiet notebook work. |
| [Customer-R1: Personalized Simulation of Human Behaviors via RL-based LLM Agent in Online Shopping](https://arxiv.org/html/2510.07230v2), Wang et al., 2025 preprint | Explicitly compares correct, absent, and shuffled personas. In its SFT+RL condition, next-action exact accuracy is 39.58%, 37.80%, and 28.94%, respectively. This supplies a useful control: determine whether matched information helps, rather than merely whether extra profile text changes outputs. | Shopping personas come from surveys/interviews. Their effects vary by model condition. Participant-disjoint evaluation was not verified in this review. Correct-versus-shuffled alone can reward avoiding misleading information; correct-versus-generic must remain primary. |
| [StudentSim: Training LLM-based Student Simulators](https://arxiv.org/html/2609.01591v1), Yang et al., 2026 preprint | Pooled training followed by individual specialization across chess, English writing, and mathematics. Separates fidelity to recorded responses from responsiveness to teaching. Borrow explicit separation of objectives and individual evaluation. | Its responsiveness metric evaluates a post-guidance response against a canonical correction, not that student's observed reaction. That metric would not establish realistic compliance, persistence, or refusal in our setting. |

## HCI and distributional evaluation

| Primary source | Implication for this project |
| --- | --- |
| [Classroom Simulacra: Building Contextual Student Generative Agents in Online Education for Learning Behavioral Simulation](https://arxiv.org/html/2502.02780v1), Xu et al., CHI 2025 | Uses a six-week, 60-student study and course/history context, with reflection to improve predicted learning performance. Shows that contextual student simulation and individual/classroom evaluation already have an HCI lineage; course context should accompany historical tendencies. Its performance endpoints do not establish AI-help usage. |
| [Unveiling the Capabilities of Large Language Models in Simulating Student Behavioral Dynamics and Supporting Peer Feedback to Augment Task Performance](https://xyzhang.ucsd.edu/papers/Songlin.Xu_CHI26_LLMSimStudentLearning.pdf), Xu and Zhang, CHI 2026 | Studies input-information ablations, including prior assessments versus demographics for final-score prediction. Supports studying which evidence improves simulation as a research contribution. Score prediction and sensory/learning behavior differ from our notebook/chat choices; correlations are not calibrated action probabilities. This review verified the relevant experiment in indexed primary PDF text; full PDF retrieval exceeded the browser tool's size limit. |
| [Measuring the Behavioral Fidelity of Long-Horizon Human Activity Simulations](https://arxiv.org/html/2609.01257v1), Cheng et al., 2026 preprint | Compares persona descriptions, examples, and statistical priors against office activity traces. Separates individual/population fidelity and temporal scales. Statistical priors can improve aggregate distributions while reducing within-person variation and fragmenting routines. Borrow both levels of analysis; matching cohort averages alone can conceal poor individual simulations. Its core longitudinal analysis concerns five people in one office setting. |
| [ConvApparel: A Benchmark Dataset and Validation Framework for User Simulators in Conversational Recommenders](https://arxiv.org/html/2602.16938v1), Meshi et al., 2026 preprint | Combines population statistics, a discriminator, and validation under a different recommender. Uses human interaction data for both stronger and weaker recommender conditions. Borrow distributional comparisons and the distinction between historical fit and response to a changed system. We cannot claim tutor-policy validity from replaying one historical policy; its classifiers also do not validate our help/work evaluator. |
| [LLM Agents Grounded in Self-Reports Enable General-Purpose Simulation of Individuals](https://arxiv.org/abs/2411.10109v3), Park et al., 2024 preprint revised 2026 | Originally titled *Generative Agent Simulations of 1,000 People*. Grounds individual agents in interviews/surveys and compares predictions with human responses, including a human test-retest benchmark. Borrow the idea that people themselves vary, so literal perfect reproduction is an inappropriate universal ceiling. We lack equivalent repeated human observations and cannot import its accuracy values or normalization. |

Additional relevant precedents are [Synthetic Students](https://arxiv.org/abs/2410.09193)
(MacNeil et al., 2024), which compares synthetic and observed programming-bug
distributions; [Simulated Students in Tutoring Dialogues: Substance or Illusion?](https://arxiv.org/html/2601.04025v2)
(Scarlatos et al., 2026), which compares prompted/trained students on multiple
dialogue dimensions; and [Embracing Imperfection](https://aclanthology.org/2025.acl-long.488/)
(Wu et al., ACL 2025), which uses programming histories and knowledge profiles.
These further rule out broad novelty claims about imperfect, diverse, or
history-informed student simulation.

[RealUserSim](https://arxiv.org/html/2605.20204v1) is another close 2026 precedent
for deriving behavioral/style profiles from real chat histories. Its reported
fidelity relies on model judgments. Its profile commands can use full histories
even when examples from a test conversation are removed, and task descriptions
use early messages from that conversation. Our prospective prediction design
must exclude future information before constructing profiles, not merely remove
examples afterward. We should not adopt that setup as evidence of a strictly
prefix-only forecasting protocol.

## What changes in our research framing

The broad ingredients already exist. Our next work is an adaptation and empirical
test, not a claim to have invented student personas, history grounding, or
distributional evaluation. The candidate question is:

> Does a student's recorded interaction history improve predictions of their
> programming-assistant usage, while preserving the range of behaviors observed
> across and within accounts?

Joint communication and workspace behavior remains a useful focus, especially
when the tutor invites dialogue but a learner instead edits code or asks another
short question. The reviewed papers cover important parts of this problem; this
review does not prove that the combined problem is unique. A future HCI
contribution would also need evidence that exposing these predictions and their
limits helps instructors make better-supported design decisions. The workbench
alone does not establish that contribution.

Represent a persona as evidence-backed tendencies with missingness and sample
counts. Avoid turning intuitive groups into fixed identities, mastery judgments,
or requirements that every continuation must obey. Keep task context and
individual tendencies conceptually separate, while acknowledging their interaction.

## What we have already tried

These studies are closed and should not be silently rerun:

- [Full earlier dialogue](2026-09-29-course-account-history-results.md): literal
  form error 0.430 current exchange versus 0.400 with history, across ten accounts.
- [Earlier student-only context](2026-09-30-student-only-history.md): 0.420 versus
  0.390, with three improved, three worsened, and four tied cases. One case accounts
  for more than the net improvement. Both are worse than the narrow empirical-form
  distribution baseline of 0.155; that baseline is not a coherent generator.
- [Continuation recognition](2026-09-21-recorded-continuation-selection.md): both
  conditions correctly selected 8/16 recorded continuations.
- The [existing student evidence card](2026-09-30-student-evidence-card.md) already
  summarizes visible communication form. Reuse it instead of inventing a second
  profile system. Its illustrative comparison did not establish improvement.
- The [notebook observation audit](2026-09-15-observation-window-readiness.md)
  supports descriptive next-capture net changes, not unseen intermediate actions.
  The two compatible inspected pairs are exposed development examples, not a new
  held-out benchmark.

A metadata-only review of the frozen ten-case history plan finds earlier student
message counts of **1, 1, 14, 4, 3, 1, 12, 1, 1, 0**. Six accounts have at most one
earlier student message. All of these histories are within the same conversation;
they do not establish stable behavior across tasks. Three messages is an inventory
cutoff for displaying the better-supported examples, not a validated sufficiency
threshold. No future target content was inspected for this inventory.

## Construction of the next comparison

The following is a study design, not a dispatched model batch or a new default.
First complete an offline feasibility check using existing exposed inputs. It
should determine whether evidence cards actually differ and whether their counts
support meaningful comparisons. Do not call another ten-case generation batch
a persona study merely because the prompt has a persona field.

If existing records support a useful comparison, keep the same current task,
tutor exchange, and available notebook context in every arm:

| Arm | Additional evidence | Purpose |
| --- | --- | --- |
| Generic | None | Main baseline |
| Matched | Descriptive tendencies from the account's pre-cutoff history | Test incremental predictive value |
| Other account | A comparable account's descriptive tendencies | Diagnostic control for whether matching matters |

Build profiles from pre-cutoff data only. Swap descriptive features rather than
raw code/questions so a donor does not change the task. Match evidence quantity
and course/task exposure where possible; report weak or impossible matches. Keep
sparse accounts visible as sparse, with generic behavior as the fallback. Treat
same-conversation evidence as local context, not proven cross-task personality.
The primary contrast is matched versus generic. Beating a misleading donor alone
is insufficient. This estimates the value of the history-derived evidence card;
it does not establish that summarizing history is better than supplying raw
history. Do not reuse older stochastic draws as concurrent controls.

Choose an observable endpoint that matches the evidence being tested:

- Communication evidence can first support communication-form forecasts. Reuse
  the existing distribution score and empirical baseline, while retaining its
  narrow interpretation. The [help/work scorer](2026-09-30-evaluator-source-disagreement.md)
  cannot currently establish small semantic improvements.
- Work-pattern evidence needs actual earlier work observations. For comparable
  notebook captures, predict distributions of changed-cell locations and extent,
  with an unchanged-notebook baseline. A profile about message brevity alone is
  not adequate evidence for a theory of notebook editing. Textual change is not
  effort, correctness, or learning, and equivalent code need not match literally.
- Define the outcome as the next eligible captured return under naturally
  occurring subsequent activity. Never align a generated self-selected stop with
  an arbitrarily later capture, reveal the eventual return time as a known input,
  or infer silence from missing messages. Intervening help remains unobserved.
  This conditions evaluation on an observed return; its score cannot validate
  return/stop probabilities or the behavior of accounts that do not return.

For any later generation study, freeze account eligibility, temporal cutoffs,
donor assignment, cell correspondence, outcome, model/configuration, draw budget,
and failure handling before target inspection or dispatch. Use account-level
weighting and uncertainty; repeated draws are not additional people. Report
individual cases, within-account variation where observable, and cohort results.
One observed future can contribute to a probabilistic forecast score across
cases; it cannot identify the entire distribution for that individual.

Stop after one prespecified report, including a null or inconclusive result.
Retain failures and do not add success-seeking retries, new labels, or prompt
variants. If the feasibility check finds too little history or too little profile
contrast, close it with that result and inspect availability in already-collected
records before spending on generation. No future-quarter collection is required
to conduct that availability check. Reliability of action application remains a
separate engineering question from behavioral fidelity.

## Status

Literature review, study design, and offline feasibility check are complete.
The check reused the existing evidence-card and form definitions, excluding each
complete current exchange. Among 38 earlier student messages, 32 are short,
three medium, and three long; four contain newlines and one contains a backtick.
These are raw formatting observations, not help-seeking or code-submission labels.

For the four cases with at least three earlier messages, pairwise total-variation
distances between the 12 literal form-category distributions range from 0 to
2/7 (about 0.286). Two of those four have identical form distributions despite
different sample counts. This describes limited contrast in the selected finite
samples, not a statistical finding of equivalent people or stable groups.

**Decision:** do not spend another generation batch on these ten cases as a test
of stable personas. The next useful preparation step is to check existing-record
availability for task-separated, pre-cutoff histories and aligned observable
outcomes. Select by metadata before reading future content; preserve the known
exposure exclusions. No new semantic labeling or future-quarter data is required
for that availability check. If sufficient histories are unavailable, retain the
generic simulator with explicit uncertainty instead of inventing personal traits.

Reproduction uses the private create-only
`data/history-profile-readiness-v1/analyze.py` and `report.json`. Source/code hashes
are pinned in the report. From this worktree:

```sh
PYTHONPATH=. /Users/minchan/github/chatsight-summer/episode-pilot/.venv/bin/python -P \
  data/history-profile-readiness-v1/analyze.py verify
```

The report reproduces exactly. An independent direct-prefix partition and an
alternate total-variation identity also confirmed the counts and distances.
No provider requests, database reads, new labels, generated continuations, or
untouched evaluation targets were involved. No donor assignments were selected.
Private receipts stay under ignored `data/`; only aggregates are recorded here.
