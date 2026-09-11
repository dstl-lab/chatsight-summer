# Episode codebook v4: observable sequences

This implements the direction in the [seven-review calibration memo](2026-09-10-episode-calibration.md), authorized by Minchan's “Let's continue.” The development question remains: after receiving help, what does the student visibly do next? Version 4 is a machine preview on the same 12 development episodes. Version 3 and its seven reviews remain intact. The 35 reserved episodes are not used for calibration or sent to Gemini.

## Five separate judgments

| Field | Question | Categories |
| --- | --- | --- |
| Student action | What did the student visibly contribute before help? | submitted-code, submitted-work, asked-question, acknowledgment, other, unclear |
| Assistance requested | What kind of help did they request? | explanation, debugging, confirmation, solution, practice, other, unclear |
| Tutor response | What instructional response was provided? | asks-question, hint, explanation, worked-solution, mixed, other, unclear |
| Follow-up | What did the next recorded student contribution contain? | revised-code, submitted-code, submitted-work, asked-for-help, acknowledgment, other, insufficient-evidence, no-followup-observed |
| Task relationship | Does that follow-up concern the original student task? | same-task, different-task, uncertain, not-observable |

These are primary categories within each field, not a claim that a message performs only one function. An artifact takes precedence in the action fields; assistance intent is recorded separately. This keeps a code submission from becoming an inferred request for a finished answer and keeps an observable help request separate from an uncertain task switch.

## Inclusion and boundary rules

**Student action.** Submitted-code requires a substantive implementation presented as student work. A function name inside a question or a copied problem statement is insufficient. Submitted-work covers non-code answers, reasoning, calculations, or diagnostic output offered for inspection. If an artifact accompanies a question, prefer submitted-code, then submitted-work; record the requested help in its own field. Asked-question includes imperatives such as a request to check an answer. Acknowledgment is a social response or a bare report of understanding; a report of continuing failure is not an acknowledgment.

**Assistance requested.** Use only the current request and earlier context. Debugging targets a problem in an existing attempt, including asking why that attempt failed. Explanation asks about a concept or method without requesting diagnosis of an existing attempt. Confirmation asks for a correctness check, either explicitly or through an unambiguous preceding invitation to submit work for checking. A code-only submission does not, by itself, distinguish these intentions. Solution requires a request for a finished answer or code; possessing code, working on a solution, or receiving a solution does not establish such a request. Practice requires requesting another exercise. When competing intentions cannot be resolved, use unclear rather than choosing from the tutor's later response.

**Tutor response.** A complete answer or complete repair for the requested part is worked-solution, even when accompanied by explanation. A partial next step leaving substantive work for the student is hint, even when accompanied by a brief explanation or closing question. Explanation develops an account of a concept, error, or method without supplying a complete requested answer or primarily directing the next action. Asks-question primarily elicits student reasoning. Mixed requires substantial independent instructional moves, such as explaining the current task and coaching a separate new task; ordinary explanation accompanying a hint or solution is insufficient. State the distinct moves in the rationale.

**Follow-up.** Use the same artifact precedence. Revised-code additionally requires comparable earlier student code and a visible implementation change: quote both versions. Cosmetic changes, identical reposts, resemblance only to tutor-provided code, and assumptions about unseen edits do not qualify; use submitted-code. A new or repeated question is asked-for-help without assuming its relationship to the original task. No-followup-observed means no later student contribution appears in this recorded conversation; it does not mean abandonment.

**Task relationship.** Compare the follow-up to the original student request, including prior context when needed to identify that request. Require positive evidence linking the student contributions for same-task or identifying distinct targets for different-task. Adjacency, a shared notebook, generic variable names, and a tutor proposing a new question are insufficient on their own. A comparable student code revision can establish same-task. A generic follow-up with no identifiable target is uncertain, even when the tutor has introduced another question. Not-observable is used only when no follow-up exists.

Other means an interpretable contribution outside the listed categories. Unclear or insufficient-evidence means its function cannot be established. A human reviewer's cannot-assess status remains separate from these student categories.

## Evidence and version boundaries

Every judgment selects numbered source lines; the application copies exact quotes. Student action cites the current student request. Assistance requested may also cite earlier context but must cite the current request for a known category. Tutor response cites current tutor turns. Follow-up cites the next student contribution; revised-code also cites earlier student work. Same-task and different-task cite both the original student request and follow-up; context can supply additional linkage. Unknown judgments may have empty evidence. Missing follow-up requires both no-followup-observed and not-observable.

Codebook, prompt, output schemas, extraction settings, and source content are pinned. The original v3 protocol remains the default and its saved hash remains loadable. V4 adds version dispatch and a separate output bundle; it does not migrate human reviews or replace the active v3 review page. Real dialogue and the before/after preview remain under ignored `data/`.

## What this pass can establish

Episode 6 motivates describing a help request separately from uncertain task continuity. Episode 7 motivates describing code submission and visible revision without inventing finished-answer intent. These examples informed the definitions and cannot independently validate them. The model need not reproduce every v3 human judgment: one review explicitly reported language uncertainty, and several categories now have different boundaries.

The preview can expose whether these definitions produce inspectable descriptions and whether evidence rules work. It cannot establish classifier accuracy, human reliability, sentiment, understanding, correctness, passing execution, or effects of tutoring. The labels remain developmental and are not admitted to a simulation state space.

## Development generation findings

All 12 v4 development drafts were generated with `gemini-2.5-flash` after explicit disclosure approval; the prompt and codebook were unchanged during the run. Two drafts required retry after structural validation rejected future request evidence and blank evidence lines. The 35 reserved episodes, the v3 bundle, and seven human review records remain unchanged.

The new fields expose a useful code-submission → hint → revised-code sequence in episode 7. They also expose unresolved inference problems. Episode 6 predicts a task switch from the tutor's new-question suggestion; episode 7 infers confirmation intent from code submission alone. Episode 5's structurally valid retry still invokes the later tutor response in its request rationale. Episode 12 treats a complete correctness assessment as a worked solution, revealing an ambiguity in the tutor-response definitions. Sparse or excessive citations also remain a review burden.

These are development findings, not an accuracy estimate. The actual predictions and a separate assistant audit are in ignored `data/episode-pilot/pilot-v4/preview.md`; machine outputs and human judgments are not silently corrected. The next proposed implementation change is to classify pre-help intent using an input that excludes future turns. Task relationships need student-target linkage, and evaluative feedback needs a clearer boundary from supplying a finished solution. That change is not implemented in this version.
