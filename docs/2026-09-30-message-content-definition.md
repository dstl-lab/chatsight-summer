# Measuring message content separately from student intent

**Decision:** describe what a student message supplies and what it expressly
requests as two independent observations. Keep inferred motivation outside the
quantitative benchmark. The unit is one student message with its permitted
preceding context, not the whole conversation's purpose.

This follows the completed [help/work measurement audit](2026-09-30-behavioral-measurement-readiness.md).
Its disagreements exposed a boundary problem: a student can answer a tutor's
question while still broadly seeking help. A single label for both meanings
cannot distinguish those actions. This definition is a prospective research
decision, not a new model result or a relabeling of that audit.

## Two observations

| Observation | Yes | No | Unclear |
| --- | --- | --- | --- |
| **Content supplied** | The current message includes candidate code, a proposed answer, calculation, explanation or diagnostic output. Copied and unchanged material counts. | It supplies only a task statement, identifier, work plan, acknowledgment or a claim of work/results without the work or output itself. | Available context cannot distinguish an answer/attempt from a question reference, task statement or fragment. |
| **Expressed request** | The current message expresses a request for information, explanation, a solution, correction or checking. Terse requests and confirmation questions count when their referent is supported. | The current message supplies an answer, acknowledgment or other statement without expressing a request. An earlier request does not automatically carry forward. | The message's function cannot be resolved from its wording and permitted preceding context. |

Both can be yes. Neither implies correctness, original authorship, understanding,
effort, confusion or a notebook action. Content includes ordinary prose answers;
it does not require code. An assertion about doing work does not import the
earlier work into the current message.

These names avoid treating a conversation's continuing help-seeking purpose as
an observable request in every turn. They remain **semantic observations**:
clearer names do not make them mechanically measurable or validate a coder.

## Boundary examples

All examples below are authored for this definition, not copied from students.

| Permitted context and current message | Content supplied | Expressed request | What it supports |
| --- | --- | --- | --- |
| `total = sum(values)` with no other request evidence | Yes | No | Code is supplied; an intention to obtain checking remains unspecified. |
| “Please explain this function.” | No | Yes | An explanation is requested; the function itself is not supplied in this message. |
| Tutor: “What is 6 divided by 3?” Student: “2.” | Yes | No | A proposed answer to the tutor's question. |
| Same tutor question; student: “2?” | Yes | Yes | A proposed answer expressed as a confirmation question. |
| “2?” with no resolving context | Unclear | Unclear | Could refer to an exercise, answer or missing context. |
| “Can you check this? `total = sum(values)`” | Yes | Yes | A request and code coexist. |
| “Exercise: Write a loop that prints three numbers.” with no framing | No | Unclear | A task is supplied; its conversational function is unresolved. |
| “Can you solve this? Exercise: Write a loop that prints three numbers.” | No | Yes | A pasted exercise is expressly posed as a request, but no solution is supplied. |
| “I have a function. How do I apply it?” | No | Yes | Claims prior work and asks a question without submitting the function. |
| “I ran the tests; they passed.” | No | No | A claim of execution/success, without execution evidence. |
| `AssertionError: expected 6, got 9` | Yes | No, absent other request evidence | Diagnostic text is supplied; its authenticity or execution provenance is not established. |
| “Thanks, I'll try that.” | No | No | Acknowledgment and plan, without evidence of an attempt or understanding. |

Question marks are not required: “help”, “explain this” and equivalent requests
in other languages can express a request. A question mark inside code or a
quoted task does not by itself establish one. Context can resolve a referent;
it cannot turn all subsequent code or answers into requests merely because the
student initially asked for help.

## Evidence and uncertainty

For any future semantic annotation, preserve the exact current message and
identify the supporting span. If context resolves a fragment, identify the
particular preceding turn too. Use the same permitted window for recorded and
generated messages; exclude later messages, future notebook state, condition
names and saved human/model judgments from the coder's input.

An evidence span makes the judgment inspectable; it does not prove the judgment
is right. For no, inspect the complete current message rather than treating a
missing keyword as evidence. Preserve unclear, transport failure, human conflict
and missing data as different states. Report coverage and denominators alongside
any agreement or probability error; do not score only the easy cases silently.

Absence of a later recorded message is **not applicable** to these message-level
flags, rather than two no labels. It does not establish that the student chose
silence, worked independently, finished or abandoned the task. An explicitly
generated no-reply is a simulator decision; a blank recorded message and a
failed request are different events. Silence needs a defined observation window
and suitable real records before its probability can be evaluated.

Notebook edits and execution are a separate evidence channel. A chat claim that
tests passed remains a claim unless supported by a linked execution event.
Do not infer a notebook edit from pasted code. The existing notebook replay can
show captured or generated actions with their origins and execution status;
message-content scoring must not replace those event records.

## What we can measure now

| Evidence | Existing implementation | Allowed conclusion |
| --- | --- | --- |
| Exact message text, role and order | Saved conversation prefixes and continuations | What was supplied in this recorded/generated exchange. |
| Character counts, newlines and backticks | `src/agents/student_evidence.py:card` | Literal communication characteristics in the supplied messages. |
| Distributional error on fixed length/format categories | `experiments/2026-09-29-course-account-history/protocol.py` | Message-form fidelity under that declared definition, conditional on the existing return-message sample. |
| Linked notebook revisions and execution receipts | Existing notebook replay and execution adapters | The specific captured/generated actions and verified execution outcomes recorded there. |
| Proposed content/request observations | Definition above; no adopted automatic coder | A specification for semantic measurement, with uncertain cases retained. |
| Motivation, comprehension, answer dependence, likelihood of leaving | No validated measurement in this work | Unresolved; exclude from a quantitative fidelity claim. |

Reuse the existing literal measurements unchanged. Do not rename backticks to
code, length to reasoning, question marks to help-seeking, or passing an execution
check to learning. Form fidelity remains useful supporting evidence, with its
original limited claim; it does not replace the intended semantic comparison.

## Consequence for the student benchmark

1. **Keep the question concrete:** does simulated next-message content resemble
   the recorded next-message content, given the same preceding exchange?
   Content supplied is the proposed primary semantic outcome; expressed request
   is a secondary observation. This is a research design choice, not scorer adoption.
2. **Keep the old evidence intact:** neither old human flags nor the audit's
   model flags can automatically become labels for this new definition.
   Do not recalculate the closed study with revised answers and call it improvement.
3. **Keep the comparison fair:** a future frozen cohort compares a baseline
   simulator, a specified history-based variant and an empirical baseline using
   one shared measurement method. Declare the sampling unit, uncertainty handling
   and stopping rule before generation. Do not optimize against already inspected
   targets or treat repeated model draws as additional real students.
4. **Keep claims within evidence:** the existing audit does not validate semantic
   scoring under this definition. Merely rerunning the coder with new wording
   against old answers would not fix that. A semantic-fidelity result needs
   independent evidence for the clarified interpretation; no fresh cohort or
   additional coding batch is dispatched as part of this definition step.

This step ends with the definition and boundary examples. No automatic
classifier, interface, dependency or duplicate form scorer is implemented.
There are no provider calls, new human labeling requests or edits to closed
experiment artifacts. Simulator development and inspection can continue; claims
about semantic fidelity remain limited until the measurement is supported.

Verification: an independent review found no contradictory boundary examples or
claims of validated automatic measurement. The closed audit's report, approval
binding, source pins and raw-response replay still verify unchanged. This is a
documentation change; no code or runtime behavior changed.
