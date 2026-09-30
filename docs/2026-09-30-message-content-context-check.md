# One bounded revision for uncertainty and context evidence

The user approved one scorer revision and one separate authored check, then a
return to comparing student simulations. This is a specification check, not
validation against real student behavior. The original twelve-case run, scorer,
labels and research results stay intact.

## Fixed approach and stopping rule, written before dispatch

The definitions remain `message-content-v1`. The new `context-v2` scorer reuses
the original input validation, line numbering and exact-quote reconstruction.
Each judgment additionally declares its basis: message alone, preceding context,
or unresolved. Unresolved requires unclear; a resolved context judgment requires
a prefix citation plus current-message evidence. This verifies consistency, not
whether the model chose the right basis or cited sufficient context.

A separate author prepares sixteen invented examples: eight direct controls,
four context-dependent cases and four unresolved cases. They contain no real
student messages and are not an independent human-labeled evaluation set.
Expected values, per-flag bases and required prefix lines stay out of prompts.
Do not change the prompt after inspecting live results or replace failed cases.

Use Gemini 2.5 Flash, temperature 0, thinking budget 0, 2,048 output tokens,
120-second timeout, one SDK/adapter attempt, sequentially, at most sixteen calls.
Before sending, save exact prompts, expectations, schema, source hashes and SDK
version in a create-only output directory. Preserve raw responses. Stop on the
first technical failure; valid semantic disagreements remain in the report and
do not trigger repair calls. Never resume or overwrite this run.

A clean specification check requires all sixteen cases' values, bases and
required context citations to match. Regardless of outcome, report a conservative
fallback that excludes each flag unless its returned basis is message-only and
its value is yes/no. Preserve original judgments; exclusions are null, never no.
Report included, excluded and unavailable counts per flag, correct included
values, and any inclusions whose authored expected basis needed context or was
unresolved. Such unsafe inclusions demonstrate the fallback's own limitation.

If ambiguity remains unreliable, do not use it for quantitative simulation
scoring. Do not tune again, request more manual labels, adopt the scorer or
relabel closed studies. Even a clean authored check would not establish accuracy
on real student messages. The completed batch ends with one report.

## Connection to the student comparison

The existing workbench already compares current-exchange-only and full-history
simulations at the same ten recorded checkpoints: fifty saved replies per arm.
Its form error is 0.430 versus 0.400; the empirical form baseline is 0.155. Those
numbers concern length/formatting, not semantic realism. See the
[saved diagnosis](2026-09-30-history-benchmark-diagnosis.md).

This bounded scorer work addresses how to describe a message, not how to generate
a better student. After the report, simulator development can use that existing
comparison and its proposed student-only earlier-context condition. The current
complete exchange stays identical; only earlier tutor turns would be omitted.
That prospective comparison can report literal form and inspect continuations;
it must not claim validated semantic fidelity from this authored check. No new
private-data call, cohort, simulation or UI change is part of this scorer run.

## Completed result: the exclusion filter is also unreliable

All sixteen requests completed once, with zero transport, parsing or structural
evidence errors and no retries. Eight direct controls matched both values and
bases. Eleven of sixteen cases matched both values overall. Because this is a
different authored set, these counts are not an improvement estimate against
the original twelve-case run.

| Check | Matched / applicable |
| --- | ---: |
| Content supplied value | 14 / 16 |
| Expressed request value | 12 / 16 |
| Content supplied basis | 11 / 16 |
| Expressed request basis | 10 / 16 |
| Required resolving-context citations | 0 / 6 judgments |
| Expected unclear retained | 1 / 6 judgments |

The direct controls are deliberately explicit. They do not establish that the
scorer can recognize straightforward real messages or estimate their prevalence.
Of four context cases, three matched both values but all omitted required context
citations. The remaining case treated a tutor-requested pasted assignment as a
new request. All four ambiguous cases had at least one mismatching value.

For example, the invented fragment `Alternate?` remained unclear for supplied
content but became a definite request. A worksheet instruction with unresolved
conversational purpose also became a definite request. The model reported
message-only support for every definite judgment, despite the explicit basis
rule. Structural guards cannot detect an incorrectly claimed basis.

| Message-only fallback | Content supplied | Expressed request |
| --- | ---: | ---: |
| Included judgments | 15 / 16 | 16 / 16 |
| Excluded as unresolved/context-dependent | 1 / 16 | 0 / 16 |
| Unavailable due to technical failure | 0 | 0 |
| Included values matching authored expectations | 13 / 15 | 12 / 16 |
| Included despite an expected context/unresolved basis | 5 | 6 |

The fallback therefore does not reliably exclude the problematic judgments.
**Neither the full scorer nor its message-only subset is adopted for quantitative
student-fidelity scoring.** Keep both observations as development diagnostics;
do not turn excluded values into no or select apparently successful real cases
after seeing their scores. Existing semantic benchmark fields remain unavailable.

This closes the approved revision. No further prompt/model/schema changes,
resends, real-data calibration or manual labeling are queued. The next simulator
comparison can proceed with the existing literal form measurements and explicit
qualitative limits; it does not need this scorer to pass first. The prospective
intervention remains student-only earlier context with the complete current
exchange preserved. No improvement from that intervention has been measured yet.

## Reproduction and verification

The new helper is `src/eval/message_content_context.py`; the authored cases and
single-run runner are `experiments/2026-09-30-message-content-boundaries.json`
and its same-named `.py` file. Reusing validation in a separate module preserves
all original source pins. No dependencies or interface changes were introduced.

The completed ignored directory is `data/message-content-context-check-v2`.
Its plan SHA-256 is
`a93b7dfbebdb07ebe3fda789b22e77de673b514f5f4d92394e9f6bdfe49836d5`;
authored-case SHA-256 is
`db6d35441eeff78fbdf48b87b66f5ed8842efef6a6f974a42e628c428448fe96`.
The plan contains seven source pins, exact prompts and expectations, model
configuration and SDK version. Raw responses, progress and report are retained.
Only current example text, permitted prefix and definitions entered the provider
requests; expectations and case groups did not.

Both new offline checks first failed on their missing implementation, then
passed. All 32 focused checks pass; the full Python suite reports **979 passed,
3 skipped**, with one existing Starlette/httpx deprecation warning. Independent
pre-dispatch review found no remaining implementation issue and independently
confirmed the original closed smoke's plan and five source pins were unchanged.
Independent post-run verification reproduced all sixteen raw responses through
the schema and materializer, all seven code pins, saved prompts and hashes,
progress, label/basis/citation comparisons and fallback counts. Eight of sixteen
cases met the complete value/basis/citation contract. Required-context coverage
above counts only the six applicable judgments, not vacuous checks on other rows.
