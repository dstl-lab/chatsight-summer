# Student study prototype

Open **Examples & files > Student study demo** to explore invented examples.
This view is restricted to the synthetic demo in the existing instructor app;
the student selector is a development control, not access control.

The chart assigns each message to the first matching course concept in the
existing deterministic keyword list, with unmatched messages shown separately.
It describes topic mentions, not knowledge, mastery, grades, or learning gains.
Concepts can overlap and the first-match order affects the chart. The count and
the messages are shown together to make this limitation inspectable.

Practice questions are locally authored examples. Feedback reports correctness
on that question only. No model is called, no rating is calculated, and no
student data is transmitted. Student selections and answers are temporary.

The question activity section groups events by explicit event-level question
metadata, or by a session explicitly marked as question-scoped when event-level
metadata is absent. Unknown and conflicting links remain unassigned. Overlapping
source events are deduplicated. Recorded edit observations, source captures,
executions, check results, messages, and tutor replies remain distinct. Error
types are literal Python error names found in execution or check text. Passing a
single check is not proof of completion, and failure counts do not measure how
wrong an answer is. Real exports may lack precise question attribution or source
details, so the workflow must be validated against the original export.

Before connecting real data, build and verify student authentication and
server-side authorization scoped to each student's records. Validate identity
mapping, data coverage, student consent and permitted uses. Any future mastery
estimate requires a validated assessment and uncertainty model, transparent
evidence and an evaluation against independent assessments. Any future AI
question generation needs an approved data flow, curriculum grounding, quality
checks and clear disclosure of model-generated content.
