# Behavioral comparison pilot

**TL;DR:** Replace length-only inspection with three independently uncertain
observations: requested assistance, supplied material, and task relation. Reuse
ten exposed recorded replies and the first saved generic draw for each case.
Two separate assistant coding passes, eight invented boundary examples, one
report, then stop. No new student generation, provider batch or human queue.

## Scope fixed before coding

Use all ten cases from the closed cross-notebook study, each recorded next reply
and generic draw 1, retaining every occurrence. No sample is chosen by its content.
Inputs contain the identical permitted current-conversation prefix for each pair.
Only the current candidate differs. The old three-arm form report remains intact;
this pilot cannot rerank those conditions or establish a behavioral improvement.

Prepare eight invented checks for: bare code versus explicit checking; an answer
fragment with and without context; a requested task quotation; a hint plus an
explanation with a negated solution request; a new task with starter code; and
an attempt plus diagnostic output. These are specification examples, not human
ground truth or real-message reliability evidence.

Shuffle all 28 items deterministically using `behavior-pilot-v1-20261001` and
opaque IDs. Keep case, origin, arm and authored expectations in a separate map.
Each assistant sees only the codebook and numbered prefix/current-message lines,
with no other coder's output or source map. Prior project exposure and recognizable
content limit blinding; these are not two independent human reviewers.

## Definitions

- **Assistance requested:** a set of expressly requested kinds: `hint`,
  `explanation`, `solution`, `checking`, or `unspecified`. Several kinds may
  coexist. `solution` means asking to produce/complete/correct an answer or code;
  `checking` means assessing or diagnosing work. Generic help without a specified
  form is `unspecified`, not automatically a solution request. Empty means no
  expressed request; null means unresolved. Do not carry an earlier help request
  into a later bare answer. Negated requests and quoted task instructions are
  not requests by the student merely because of their wording.
- **Material supplied:** a set containing `work` (candidate answer, code,
  calculation or explanation) and/or `diagnostic` (literal error/test/output
  artifact). Empty means neither; null means unresolved. A task statement or
  explicitly supplied starter scaffold is not proposed work. Claims of having
  worked or passed are not the work/output itself. No authorship or execution
  authenticity follows from a paste.
- **Task relation:** `same`, `different`, or `unclear`, relative to the latest
  identifiable active task in the prefix. Judge the current requested/focal task.
  An explicit move from one question to another is different; quoted history is
  not itself a move. If multiple focal tasks or the anchor cannot be resolved,
  retain unclear. Missing a new question number does not establish same-task.

Every dimension carries numbered-line evidence and a basis: message-only,
preceding-context or unresolved. Absence needs all nonblank current lines;
resolved task relation needs a prefix anchor. Reuse existing citation validation
and quote reconstruction. Evidence validity cannot establish semantic accuracy;
the prior unreliable message-only exclusion filter is not reused as an accuracy
gate. No trait, motivation, emotion, hidden work or learning label is introduced.

## Report and stopping

Validate exact item coverage and source bindings for both coding files. Report
authored value/basis checks, per-dimension agreement, unresolved judgments and
all disagreements. A disagreement is retained, not repaired, voted away or sent
to the user for adjudication. Agreement between assistants is not correctness.

For the ten recorded/generated pairs, describe per-dimension label counts
separately for each coder, including all unknowns. Do not calculate a single
realism score, confidence interval, model ranking or population behavior rate.
This is one already-exposed cohort and one generated draw per account, with no
notebook action sequence measured. Existing human labels are not converted into
this new rubric. The rubric and mechanism remain experimental regardless of
authored-check performance. End with one report; no prompt tuning, additional
passes, fresh data, automatic adoption or manual labeling round.
