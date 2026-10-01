# Behavioral pilot: asking for help versus supplying an answer

**TL;DR:** The new three-dimension comparison finds a concrete development
mismatch: the recorded replies contain work in **1/10 cases**, versus **6–7/10
generated replies**, depending on the assistant coder. Recorded replies request
hints in 2/10 cases and move to another task in 4/10; the sampled generated replies
do so in 0/10 and 1/10. These are exploratory labels on exposed cases, not a
validated realism score. The fixed pilot is complete; no new human review is queued.

## What is implemented

The [frozen pilot](2026-10-01-behavior-pilot.md) adds an offline comparison of
requested assistance, material supplied and task relation. Labels can overlap,
each dimension can remain unclear, and every judgment retains exact source-line
evidence. The implementation reuses the existing strict input, context and
quote-reconstruction helpers; no production generator or old scorer changed.

Ten recorded replies are paired with generic draw 1 from the completed history
study, using the exact same preceding conversation in each pair. Eight invented
boundary examples bring the packet to 28 items. Two separate Codex assistant
passes saw the instructions, schema and numbered sources in shuffled order.
Origin, case mapping and expected judgments were excluded from their packet.
Both read all 28 current messages with permitted context and saved one coding
file after structural checks. They did not see each other's output. This is
limited masking, not a blind human reliability study; items could be recognizable,
and paired prefixes were visible within the packet.

## What the labels describe

All denominators below remain ten per source. Unknowns are retained, not converted
to absence. Requested kinds and supplied materials are multi-label observations,
so subtype counts need not sum to ten. Both coders agree unless a range is shown.

| Observation | Recorded | Generated |
|---|---:|---:|
| Any definite expressed assistance request | 9 | 3 |
| No expressed assistance request | 1 | 6–7 |
| Assistance function unclear | 0 | 0–1 |
| Hint requested | 2 | 0 |
| Checking requested | 2 | 2 |
| Solution/correction requested | 2–3 | 1 |
| Help requested, kind unspecified | 2–3 | 0 |
| Work/answer supplied | 1 | 6–7 |
| Neither work nor diagnostic supplied | 9 | 3 |
| Supplied material unclear | 0 | 0–1 |
| Same active task | 5 | 8 |
| Different active task | 4 | 1 |
| Task relation unclear | 1 | 1 |

Neither source has a diagnostic artifact or an explanation request in these
twenty selected messages under either coding. This does not imply those behaviors
are absent from the longer conversations; the preceding
[database reading](2026-10-01-behavior-examples.md) contains examples of both.

Several pairs make the practical issue visible. Case 1's recorded reply requests
help on a different task, whereas its generated reply supplies work for the
current task. Case 4 asks for checking in the recorded reply but supplies work in
the generated reply. Cases 5 and 9 request hints in the recorded continuation,
while the generated continuation supplies work. These are descriptions of the
saved alternatives, not findings that every alternative is implausible or that
the simulator must reproduce one exact recorded future.

## Where the coders and expectations disagree

| Dimension | Agreement on 20 recorded/generated items | Authored expectations matched, coder A / B |
|---|---:|---:|
| Requested assistance | 18/20 | 7/8 · 7/8 |
| Supplied material | 19/20 | 8/8 · 8/8 |
| Task relation | 20/20 | 6/8 · 7/8 |

For generated case 7, coder A calls the fragment work with no request; coder B
retains uncertainty for both dimensions. For recorded case 8, one codes general
help and the other a solution request. Both original judgments remain visible.
Neither coder is selected as the authority and no consensus label is manufactured.

Both coders abstain on assistance and task relation in the invented task-quotation
example, instead of the predeclared no-request/same-task expectations. Coder A
also abstains on task relation when a request combines a hint about the current
question with an explanation of a programming construct. These reveal unresolved
interpretation boundaries; authored expectations are not infallible human truth.
All required authored context selectors were present, and both coders matched all
eight material expectations. These checks establish neither real-message accuracy
nor the reliability of a self-reported basis. Perfect real-item task agreement
does not cancel the shared uncertainty on the invented example.

## Decision for simulator development

The next useful target is **the choice of what to communicate after tutoring**:
asking for further help, requesting checking, providing work, or moving to another
task. Keep the current conversation and notebook evidence where available; do not
assume a student must answer the tutor's latest invitation. Style remains a
secondary observation. This repeats a mismatch identified by the earlier saved
[human-label comparison](2026-09-30-evaluator-source-disagreement.md), though the
cohorts, rubric and sampling differ and their numbers must not be pooled.

Retain this as a behavioral development diagnostic. Do not adopt either assistant
as an automatic judge, use the labels to rank small simulator changes, train a
persona, or force future replies to match these ten references. No notebook edit,
execution, learning, success or silence probability is measured here. There is
one generated draw per account, not an estimated behavioral distribution.

The completed comparison closes this pilot. No prompt tuning, extra coding pass,
fresh account, Gemini batch, new student generation, human annotation request or
UI change was made. Old runs and labels remain intact.

## Verification and reproduction

The focused Python checks passed: **41 tests**, including the new list-valued
observations, unresolved states, task anchors, evidence validation, full-message
absence, input isolation, disagreement counts and missing-item rejection. Full
suite completion is not claimed. All 28 records per coder validate; the saved
report reproduces exactly from the original coding files and frozen inputs.
An independent audit checks the aggregate arithmetic and authored disagreements.
Private messages, mappings and evidence-bearing reports remain ignored under
`data/behavior-pilot-v1/`.

```sh
PYTHONPATH=. python -P -m pytest -q tests/test_behavior_pilot.py \
  tests/test_message_content_context.py tests/test_message_content.py
```

`experiments/2026-10-01-behavior-pilot.py prepare NEW_DIRECTORY` builds the fixed
packet from the locally saved closed study. After supplying both coding files,
`report DIRECTORY` produces a create-only report. Existing preparation, coding
files and completed report must be preserved; rebuilding a packet is not
authorization for another coding pass. The script contains no provider client.
