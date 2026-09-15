# An interactive learning expedition for educators

Current decision: Minchan selected coaching, deferred the other two directions,
and requested Animal Crossing as a stylistic reference. The
[coaching-session prototype](2026-09-11-coaching-session-prototype.md) implements
an original cozy visual direction. The alternatives below preserve the discussion.

Latest priority: Minchan asked to make the simulated students work before designing
the end product. Interface exploration is paused; the selected direction remains
recorded for later. The storyboard is an authored example, not simulator progress.

## Confirmed motivation and audience

Minchan identified Park, Bernstein and colleagues' Generative Agents as the
primary inspiration: an interactive world inhabited by simulated students should
be engaging to explore and use. The broader research ambition is to improve
learning as technology and society change. Minchan selected educators/researchers
experimenting with student support as the first audience, and tentatively named
Pokemon as a game reference while raising intellectual-property concerns. Minchan
subsequently added NBA2K, FIFA and Bloons Tower Defense as other possibilities;
no game structure has been selected.

The proposed North Star is an explorable world where educators investigate how
learners respond to different forms of support, with behavior grounded in real
interactions and its limits visible. The game concept below is a recommendation,
not a completed prototype or a user-approved detailed implementation design.

## Research position

[Generative Agents](https://arxiv.org/abs/2304.03442) combines experience memory,
reflection and planning in a Sims-inspired world and evaluates behavioral
believability. Its architecture and interactive presentation are useful references;
believability alone does not establish educational usefulness or learning.
[GPTeach](https://web.stanford.edu/~cpiech/bio/papers/GPTeach.pdf) already supports
teaching practice with simulated students, and
[Classroom Simulacra](https://arxiv.org/abs/2502.02780) studies student simulation
using logged learning behavior and course context. This bounded literature check
does not establish novelty. A different visual theme alone is insufficient as
the research contribution.

The candidate contribution is a playful, inspectable way for educators to develop
and question hypotheses about supporting learners in an AI-mediated setting.
Start with choices already close to the data, such as explaining an answer versus
offering guidance and a question. Broader changes to AI access, assessment or peer
support require additional evidence or clearly authored scenarios.

## Proposed game loop

The expanded references suggest three possible educator roles. These are design
interpretations, not evidence that their educational versions will work:

| Reference | Proposed educator role | Additional assumptions needed |
|---|---|---|
| NBA2K / FIFA coaching and management | Support a persistent group, adjust the approach, inspect and replay encounters | Team effects, skill ratings and development rates are not established by these logs |
| Bloons Tower Defense | Arrange support resources and observe how learners use them | Resource choice, capacity, movement and timing need authored scenarios or new evidence |
| Pokemon / adventure | Explore task encounters and accumulate experiences with fictional learners | Locations organize scenarios; they do not establish social relationships or mastery |

The coach's practice session is the closest initial fit to the available tutoring
episodes. It can reuse the small encounter below without committing to a season
simulator or resource-placement system. The playbook records support offered and
observed responses; learners retain control over their contributions. Official
references for the management and support-placement inspirations are
[NBA 2K MyNBA](https://nba.2k.com/2k24/en-GB/modes/mynba/),
[EA Manager Career](https://help.ea.com/en/articles/ea-sports-fc/career-mode/) and
[Ninja Kiwi's Bloons TD 6 description](https://store.steampowered.com/app/960090/Bloons_TD_6/).

Explore → encounter a learning problem → offer support → observe learner choices
→ inspect and replay a decision → discover another situation.

Begin with two fictional learner characters, a tiny original map, one substantive
task encounter and up to three coaching decisions. The educator chooses where to
go and what help to offer; learners choose their next contributions. Suggested
coaching actions can open editable responses, allowing mixtures of explanation,
guidance and questions. A tutor prompt never obliges a learner to follow it.

Persistent history should record the task, actual interactions and supplied
feedback within that fictional branch. Reuse visible-prefix continuation and
branch-provenance helpers first. Separate model hypotheses from observed events;
add reflection/retrieval machinery only when a demonstrated memory limitation
requires it. The current data does not justify human biographies, fixed learner
types, social networks or a simulated mastery score.

Progress can unlock authored locations and encounters and accumulate a journal of
teaching experiments. Such unlocks are game rules, not inferred student learning.
The journal asks what the educator expected, what the learner did, and what
evidence changed the educator's interpretation. Student work and verified task
feedback may be displayed; hidden ability, emotion and off-chat progress remain
unknown. Missing replies do not determine a learner's fate.

Replaying a decision starts a distinct branch from the same prior evidence and
allows a different tutor intervention. Retain all generated alternatives, even
uninteresting or identical ones; do not force a dramatic contrast. These are
simulated possibilities, not verified counterfactuals or estimates of real policy
effects. Course execution remains optional for authored feedback conditions, as
specified in the portability memo. Unknown-state failures remain unresolved.

## Smallest next steps and evaluation

First storyboard one complete encounter with invented dialogue and explicit
feedback assumptions. Test whether its decisions are interesting before building
a whole world. Then implement that encounter using the existing continuation
helpers while running the pending real/generated behavior comparison in parallel.
The behavioral study does not need a complete game, and interface exploration
does not require finishing every label category.

Keep three evaluation questions distinct: whether agents reproduce observable
behavior on held-out real interactions; whether the game helps educators notice
evidence, consider alternatives and calibrate their conclusions; and whether
using it eventually improves real teaching or learning. For the interface study,
compare the game with a plain presentation of the same underlying interactions
and replay options. Engagement is a result in its own right, not a learning proxy.
This concept work launches no human study, cohort simulation or new model run;
existing research/data requirements still apply.

Labels remain provisional descriptions of actions, ordered tutor moves and task
relationships. They can support the journal and comparisons once validated;
they are neither personality classes nor compulsory inputs to generate speech.

## Original design

Use original characters, names, art, maps, writing, audio and interface treatment.
Pokemon is a reference for broad adventure and encounter structures. The U.S.
[Copyright Office](https://www.copyright.gov/circs/circ33.pdf) distinguishes ideas
and methods from protected expression; trademark and patent questions are
separate. This observation is not legal clearance for a particular implementation.

This memo records the revised motivation and a proposed first experience. It
does not change frozen generators, claim validated transfer, or replace the
preserved negative results with a successful-game narrative.
